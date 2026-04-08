# app/tasks/crawl_worker.py
"""
Crawl Worker - RabbitMQ Consumer
Pulls crawl tasks from queue and executes crawlers (Tiki, Lazada, Shopee)
"""

import json
import logging
import pika
import argparse
import sys
from typing import Dict, Any
from datetime import datetime
from app.config.rabbitmq import (
    get_rabbitmq_channel,
    RabbitMQConfig,
    QueueSetup
)
from app.config.redis import redis_client
from app.services.product_service import ProductService
from app.crawler.multi_crawler import MultiCrawler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(name)s] - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CrawlWorker:
    """
    RabbitMQ Consumer for crawl tasks
    
    Workflow:
    1. Consume message from queue
    2. Validate task
    3. Execute crawlers (Tiki, Lazada, Shopee)
    4. Save results to database
    5. Update task status
    6. ACK message (remove from queue)
    7. On error: retry or send to DLQ
    """
    
    MAX_EVENTS = 1  # Process one task at a time
    AUTO_ACK = False  # Manual ACK after successful processing
    PREFETCH_SIZE = 1  # Only fetch one task at a time
    
    def __init__(self, queue_name: str = None):
        """
        Initialize worker
        
        Args:
            queue_name: Queue to consume from (default: CRAWL_QUEUE)
        """
        self.queue_name = queue_name or RabbitMQConfig.CRAWL_QUEUE
        self.channel = None
        
        # Initialize services
        self.product_service = ProductService()
        self.crawler = MultiCrawler()
        
        logger.info(f"[CrawlWorker] Initialized with queue: {self.queue_name}")
    
    def start(self) -> None:
        """Start consuming messages from queue"""
        try:
            # Setup RabbitMQ
            logger.info(f"[CrawlWorker] Setting up RabbitMQ...")
            self.channel = get_rabbitmq_channel("worker")
            QueueSetup.setup_crawl_queue(self.channel)
            
            # Set QoS (Quality of Service)
            self.channel.basic_qos(
                prefetch_size=0,  # No byte limit
                prefetch_count=self.PREFETCH_SIZE,  # One task at a time
                global_qos=False
            )
            
            # Register callback
            self.channel.basic_consume(
                queue=self.queue_name,
                on_message_callback=self.callback,
                auto_ack=self.AUTO_ACK
            )
            
            logger.info(f"[CrawlWorker] ✅ Starting consumer on queue: {self.queue_name}")
            logger.info(f"[CrawlWorker] Waiting for messages... (Press Ctrl+C to exit)")
            
            # Start consuming
            self.channel.start_consuming()
            
        except KeyboardInterrupt:
            logger.info("[CrawlWorker] Interrupted by user")
            self.stop()
        except Exception as e:
            logger.error(f"[CrawlWorker] Fatal error: {e}")
            self.stop()
            raise
    
    def callback(
        self,
        channel: pika.adapters.blocking_connection.BlockingChannel,
        method: pika.spec.Basic.Deliver,
        properties: pika.spec.BasicProperties,
        body: bytes
    ) -> None:
        """
        Callback function for processing messages
        
        Args:
            channel: RabbitMQ channel
            method: Delivery method
            properties: Message properties
            body: Message body (JSON)
        """
        task_id = None
        
        try:
            # Parse message
            message = json.loads(body.decode())
            task_id = message.get("task_id")
            
            logger.info(f"[CrawlWorker] 📥 Received task: {task_id}")
            
            # Validate message
            if not self._validate_message(message):
                logger.error(f"[CrawlWorker] ❌ Invalid message format: {task_id}")
                channel.basic_nack(method.delivery_tag, requeue=False)
                return
            
            # Process task
            result = self._process_task(message)
            
            if result.get("success"):
                # ✅ SUCCESS: ACK and move on
                logger.info(f"[CrawlWorker] ✅ Task completed: {task_id}")
                channel.basic_ack(method.delivery_tag)
            else:
                # ❌ FAILURE: Check retry logic
                retry_count = message.get("retry_count", 0)
                max_retries = message.get("max_retries", RabbitMQConfig.CRAWL_MAX_RETRIES)
                
                if retry_count < max_retries:
                    # Retry: Publish back to queue
                    logger.warning(
                        f"[CrawlWorker] 🔄 Retrying task: {task_id} "
                        f"(attempt {retry_count + 1}/{max_retries})"
                    )
                    message["retry_count"] = retry_count + 1
                    self._republish_message(message, high_priority=True)
                    channel.basic_ack(method.delivery_tag)
                else:
                    # Max retries exceeded: NACK and let RabbitMQ send to DLQ
                    logger.error(
                        f"[CrawlWorker] ❌ Max retries exceeded for {task_id}, "
                        f"sending to DLQ"
                    )
                    channel.basic_nack(method.delivery_tag, requeue=False)
        
        except json.JSONDecodeError as e:
            logger.error(f"[CrawlWorker] ❌ Failed to parse message JSON: {e}")
            channel.basic_nack(method.delivery_tag, requeue=False)
        
        except Exception as e:
            logger.error(f"[CrawlWorker] ❌ Unexpected error processing {task_id}: {e}")
            channel.basic_nack(method.delivery_tag, requeue=False)
    
    def _validate_message(self, message: Dict[str, Any]) -> bool:
        """Validate message structure"""
        required_fields = ["task_id", "category", "category_id", "attributes"]
        return all(field in message for field in required_fields)
    
    def _process_task(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process crawl task
        
        Steps:
        1. Update task status to RUNNING
        2. Crawl from multiple sources
        3. Save results to database
        4. Update task status to COMPLETED
        """
        task_id = message.get("task_id")
        category = message.get("category")
        category_id = message.get("category_id")
        attributes = message.get("attributes", {})
        
        try:
            # Update status: RUNNING
            self._update_task_status(task_id, "running")
            
            logger.info(
                f"[CrawlWorker] 🌐 Starting crawl for {task_id} | "
                f"Category: {category} | Attributes: {attributes}"
            )
            
            # Execute crawlers
            crawled_products = self.crawler.crawl(
                category=category,
                attributes=attributes
            )
            
            if not crawled_products:
                logger.warning(f"[CrawlWorker] ⚠️ No products found for {task_id}")
                self._update_task_status(
                    task_id,
                    "completed",
                    products_found=0,
                    error=None
                )
                return {"success": True}
            
            logger.info(
                f"[CrawlWorker] ✅ Crawled {len(crawled_products)} products "
                f"for {task_id} from {len(set(p.get('source') for p in crawled_products))} sources"
            )
            
            # Save to database
            save_result = self.product_service.save_products_batch(
                category_id=category_id,
                products=crawled_products
            )
            
            if not save_result.get("success"):
                error_msg = save_result.get("error", "Failed to save products")
                logger.error(f"[CrawlWorker] ❌ Failed to save products for {task_id}: {error_msg}")
                self._update_task_status(
                    task_id,
                    "failed",
                    error=error_msg
                )
                return {"success": False, "error": error_msg}
            
            saved_count = save_result.get("saved_count", 0)
            logger.info(f"[CrawlWorker] 💾 Saved {saved_count} products to database for {task_id}")
            
            # Update status: COMPLETED
            sources = set(p.get("source") for p in crawled_products)
            self._update_task_status(
                task_id,
                "completed",
                products_found=saved_count,
                sources_completed=list(sources)
            )
            
            # Publish event (optional: for other components to listen)
            self._publish_event(
                event_type="crawl.completed",
                data={
                    "task_id": task_id,
                    "category": category,
                    "products_count": saved_count
                }
            )
            
            return {
                "success": True,
                "task_id": task_id,
                "products_found": saved_count
            }
            
        except Exception as e:
            logger.error(f"[CrawlWorker] ❌ Error processing {task_id}: {e}", exc_info=True)
            self._update_task_status(task_id, "failed", error=str(e))
            return {"success": False, "error": str(e)}
    
    def _update_task_status(
        self,
        task_id: str,
        status: str,
        products_found: int = None,
        sources_completed: list = None,
        error: str = None
    ) -> None:
        """
        Update task status in Redis
        
        Args:
            task_id: Task ID
            status: New status (pending|running|completed|failed|retrying)
            products_found: Number of products found
            sources_completed: List of sources that completed
            error: Error message if failed
        """
        try:
            status_key = f"crawl_task:{task_id}"
            task_data = redis_client.get(status_key)
            
            if task_data:
                task_info = json.loads(task_data)
            else:
                task_info = {"task_id": task_id}
            
            # Update fields
            task_info["status"] = status
            
            if status == "running":
                task_info["started_at"] = datetime.now().isoformat()
            elif status == "completed":
                task_info["completed_at"] = datetime.now().isoformat()
            elif status == "failed":
                task_info["failed_at"] = datetime.now().isoformat()
            
            if products_found is not None:
                task_info["products_found"] = products_found
                task_info["progress"] = 100 if status == "completed" else 50
            
            if sources_completed:
                task_info["sources_completed"] = sources_completed
            
            if error:
                task_info["error"] = error
            
            # Save back to Redis
            redis_client.set(
                status_key,
                json.dumps(task_info),
                ex=86400  # 24 hours expiry
            )
            
            logger.info(f"[CrawlWorker] 📊 Updated {task_id} status to: {status}")
            
        except Exception as e:
            logger.error(f"[CrawlWorker] ❌ Failed to update status for {task_id}: {e}")
    
    def _republish_message(
        self,
        message: Dict[str, Any],
        high_priority: bool = False
    ) -> None:
        """Republish message for retry"""
        try:
            channel = get_rabbitmq_channel("republish")
            priority = 10 if high_priority else 5
            
            channel.basic_publish(
                exchange=RabbitMQConfig.MAIN_EXCHANGE,
                routing_key="crawl.retry",
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    priority=priority,
                    content_type="application/json"
                )
            )
            
            logger.info(f"[CrawlWorker] 🔄 Republished message: {message.get('task_id')}")
        except Exception as e:
            logger.error(f"[CrawlWorker] ❌ Failed to republish message: {e}")
    
    def _publish_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """Publish event for other components"""
        try:
            channel = get_rabbitmq_channel("events")
            
            event = {
                "event_type": event_type,
                "timestamp": datetime.now().isoformat(),
                "data": data
            }
            
            channel.basic_publish(
                exchange=RabbitMQConfig.MAIN_EXCHANGE,
                routing_key=event_type,
                body=json.dumps(event),
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    content_type="application/json"
                )
            )
        except Exception as e:
            logger.warning(f"[CrawlWorker] ⚠️ Failed to publish event: {e}")
    
    def stop(self) -> None:
        """Stop worker gracefully"""
        try:
            if self.channel:
                self.channel.stop_consuming()
                logger.info("[CrawlWorker] ✅ Stopped consuming")
        except Exception as e:
            logger.error(f"[CrawlWorker] Error stopping worker: {e}")

# ============================================================================
# WORKER STARTUP
# ============================================================================

def main():
    """CLI entry point"""
    parser = argparse.ArgumentParser(description="Crawl Worker - RabbitMQ Consumer")
    parser.add_argument(
        "--queue",
        default=RabbitMQConfig.CRAWL_QUEUE,
        help=f"Queue to consume from (default: {RabbitMQConfig.CRAWL_QUEUE})"
    )
    
    args = parser.parse_args()
    
    # Create and start worker
    worker = CrawlWorker(queue_name=args.queue)
    
    try:
        worker.start()
    except Exception as e:
        logger.error(f"[CrawlWorker] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
