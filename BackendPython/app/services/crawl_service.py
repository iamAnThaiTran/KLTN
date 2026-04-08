# app/services/crawl_service.py
"""
CrawlService - Microservice for async web crawling
Responsibilities:
- Enqueue crawl tasks to RabbitMQ
- Track crawl task status
- Manage retry logic
- Handle dead letter queue
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from app.services.base_service import BaseService
from app.config.rabbitmq import (
    get_rabbitmq_channel,
    RabbitMQConfig,
    RabbitMQConnection
)
from app.config.redis import redis_client

logger = logging.getLogger(__name__)

class CrawlTaskStatus:
    """Enum for crawl task statuses"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"

class CrawlService(BaseService):
    """
    Crawl Service - Manages web crawling via RabbitMQ
    
    Responsibilities:
    - Create and enqueue crawl tasks
    - Track task status
    - Handle retries and failures
    - Integration with DQ (Dead Letter Queue)
    """
    
    SERVICE_NAME = "CrawlService"
    SERVICE_VERSION = "1.0.0"
    SERVICE_TIMEOUT = 5  # Producer should be fast
    
    def __init__(self):
        super().__init__()
        self.redis_client = redis_client
        self.log_operation("initialized", "info")
    
    # ========================================================================
    # TASK CREATION & ENQUEUEING
    # ========================================================================
    
    def enqueue_crawl_task(
        self,
        category: str,
        category_id: int,
        attributes: Dict[str, Any],
        priority: str = "normal",
        max_retries: int = None
    ) -> Dict[str, Any]:
        """
        Enqueue a crawl task to RabbitMQ
        
        Args:
            category: Category name (e.g., "Giày")
            category_id: Category ID from database
            attributes: Extracted attributes (e.g., {"brand": "Nike"})
            priority: "high" | "normal" | "low"
            max_retries: Max retry attempts (default from config)
        
        Returns:
        {
            "success": True,
            "task_id": "crawl_abc123def456",
            "status": "pending",
            "message": "Task enqueued",
            "estimate_wait_time": 45  # seconds
        }
        """
        self.track_request("enqueue_crawl_task")
        
        task_id = f"crawl_{uuid.uuid4().hex[:12]}"
        max_retries = max_retries or RabbitMQConfig.CRAWL_MAX_RETRIES
        
        try:
            self.log_operation(
                "enqueue_crawl_task_start",
                "info",
                task_id=task_id,
                category=category,
                category_id=category_id
            )
            
            # Prepare message
            message = {
                "task_id": task_id,
                "category": category,
                "category_id": category_id,
                "attributes": attributes,
                "priority": priority,
                "max_retries": max_retries,
                "created_at": datetime.now().isoformat(),
                "retry_count": 0
            }
            
            # Enqueue to RabbitMQ
            self._publish_message(
                message=message,
                routing_key="crawl.new",
                priority=priority
            )
            
            # Initialize task status in Redis
            self._init_task_status(
                task_id=task_id,
                category=category,
                attributes=attributes
            )
            
            self.log_operation(
                "enqueue_crawl_task_success",
                "info",
                task_id=task_id
            )
            
            return {
                "success": True,
                "task_id": task_id,
                "status": CrawlTaskStatus.PENDING,
                "message": "Task enqueued successfully",
                "estimate_wait_time": self._estimate_wait_time()
            }
            
        except Exception as e:
            result = self.handle_service_error(
                "enqueue_crawl_task",
                e,
                context={"category": category, "category_id": category_id},
                raise_error=False
            )
            error_response = {**result, "task_id": task_id}
            return error_response
    
    # ========================================================================
    # TASK STATUS TRACKING
    # ========================================================================
    
    def get_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get status of a crawl task
        
        Args:
            task_id: Task ID (e.g., "crawl_abc123")
        
        Returns:
        {
            "task_id": "crawl_abc123",
            "status": "running|completed|failed",
            "progress": 65,  # percentage
            "products_found": 18,
            "started_at": "2024-04-07T10:00:00Z",
            "completed_at": "2024-04-07T10:05:30Z",
            "error": null,
            "retry_count": 0,
            "sources_completed": ["tiki", "lazada"]
        }
        """
        self.track_request("get_task_status")
        
        try:
            # Get from Redis
            status_key = f"crawl_task:{task_id}"
            task_data = self.redis_client.get(status_key)
            
            if not task_data:
                self.log_operation(
                    "get_task_status_not_found",
                    "warning",
                    task_id=task_id
                )
                return {
                    "success": False,
                    "error": f"Task not found: {task_id}"
                }
            
            task_info = json.loads(task_data)
            
            self.log_operation(
                "get_task_status_success",
                "info",
                task_id=task_id,
                status=task_info.get("status")
            )
            
            return {
                "success": True,
                "task_id": task_id,
                **task_info
            }
            
        except Exception as e:
            return self.handle_service_error(
                "get_task_status",
                e,
                context={"task_id": task_id},
                raise_error=False
            )
    
    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """
        Cancel a pending/running crawl task
        
        Args:
            task_id: Task ID to cancel
        
        Returns:
        {
            "success": True,
            "task_id": "crawl_abc123",
            "previous_status": "running",
            "new_status": "cancelled"
        }
        """
        self.track_request("cancel_task")
        
        try:
            status_key = f"crawl_task:{task_id}"
            task_data = self.redis_client.get(status_key)
            
            if not task_data:
                return {
                    "success": False,
                    "error": f"Task not found: {task_id}"
                }
            
            task_info = json.loads(task_data)
            previous_status = task_info.get("status")
            
            # Update status
            task_info["status"] = CrawlTaskStatus.CANCELLED
            task_info["cancelled_at"] = datetime.now().isoformat()
            
            self.redis_client.set(
                status_key,
                json.dumps(task_info),
                ex=86400  # 24 hours expiry
            )
            
            self.log_operation(
                "cancel_task_success",
                "info",
                task_id=task_id,
                previous_status=previous_status
            )
            
            return {
                "success": True,
                "task_id": task_id,
                "previous_status": previous_status,
                "new_status": CrawlTaskStatus.CANCELLED
            }
            
        except Exception as e:
            return self.handle_service_error(
                "cancel_task",
                e,
                context={"task_id": task_id},
                raise_error=False
            )
    
    # ========================================================================
    # DEAD LETTER QUEUE MANAGEMENT
    # ========================================================================
    
    def get_dlq_messages(self, limit: int = 10) -> Dict[str, Any]:
        """
        Get failed tasks from Dead Letter Queue
        
        Args:
            limit: Max messages to retrieve
        
        Returns:
        {
            "success": True,
            "dlq_size": 5,
            "messages": [
                {
                    "task_id": "crawl_abc123",
                    "category": "Giày",
                    "error": "Network timeout",
                    "failed_at": "2024-04-07T09:45:00Z",
                    "retry_count": 3
                },
                ...
            ]
        }
        """
        self.track_request("get_dlq_messages")
        
        try:
            channel = get_rabbitmq_channel("dlq_consumer")
            dlq_name = f"{RabbitMQConfig.CRAWL_QUEUE}{RabbitMQConfig.DLQ_SUFFIX}"
            
            # Get DLQ message count
            method, properties, body = channel.basic_get(dlq_name)
            
            dlq_messages = []
            message_count = 0
            
            while method and message_count < limit:
                try:
                    message = json.loads(body.decode())
                    dlq_messages.append(message)
                    channel.basic_ack(method.delivery_tag)
                    message_count += 1
                    
                    method, properties, body = channel.basic_get(dlq_name)
                except Exception as e:
                    logger.error(f"Error processing DLQ message: {e}")
                    channel.basic_nack(method.delivery_tag, requeue=True)
                    break
            
            self.log_operation(
                "get_dlq_messages_success",
                "info",
                message_count=len(dlq_messages)
            )
            
            return {
                "success": True,
                "dlq_size": message_count,
                "messages": dlq_messages
            }
            
        except Exception as e:
            return self.handle_service_error(
                "get_dlq_messages",
                e,
                raise_error=False
            )
    
    def retry_dlq_message(
        self,
        task_id: str,
        requeue: bool = True
    ) -> Dict[str, Any]:
        """
        Retry a failed message from DLQ
        
        Args:
            task_id: Task ID to retry
            requeue: True = send back to main queue, False = just mark as retried
        
        Returns:
        {
            "success": True,
            "task_id": "crawl_abc123",
            "requeued": True
        }
        """
        self.track_request("retry_dlq_message")
        
        try:
            # Get task data
            status_key = f"crawl_task:{task_id}"
            task_data = self.redis_client.get(status_key)
            
            if not task_data:
                return {"success": False, "error": f"Task not found: {task_id}"}
            
            task_info = json.loads(task_data)
            retry_count = task_info.get("retry_count", 0)
            max_retries = task_info.get("max_retries", RabbitMQConfig.CRAWL_MAX_RETRIES)
            
            if requeue and retry_count < max_retries:
                # Update task status
                task_info["status"] = CrawlTaskStatus.RETRYING
                task_info["retry_count"] = retry_count + 1
                task_info["retried_at"] = datetime.now().isoformat()
                
                self.redis_client.set(
                    status_key,
                    json.dumps(task_info),
                    ex=86400
                )
                
                # Requeue to main queue
                self._publish_message(
                    message=task_info,
                    routing_key="crawl.retry",
                    priority="high"
                )
            
            self.log_operation(
                "retry_dlq_message_success",
                "info",
                task_id=task_id,
                requeued=requeue
            )
            
            return {
                "success": True,
                "task_id": task_id,
                "requeued": requeue
            }
            
        except Exception as e:
            return self.handle_service_error(
                "retry_dlq_message",
                e,
                context={"task_id": task_id},
                raise_error=False
            )
    
    # ========================================================================
    # PRIVATE HELPER METHODS
    # ========================================================================
    
    def _publish_message(
        self,
        message: Dict[str, Any],
        routing_key: str,
        priority: str = "normal"
    ) -> None:
        """
        Publish message to RabbitMQ
        
        Args:
            message: Message dict
            routing_key: Routing key for exchange
            priority: Priority level
        """
        try:
            channel = get_rabbitmq_channel("producer")
            
            # Convert priority to RabbitMQ priority
            priority_map = {"high": 10, "normal": 5, "low": 0}
            priority_value = priority_map.get(priority, 5)
            
            # Publish message
            channel.basic_publish(
                exchange=RabbitMQConfig.MAIN_EXCHANGE,
                routing_key=routing_key,
                body=json.dumps(message),
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Persistent
                    priority=priority_value,
                    content_type="application/json"
                )
            )
            
            logger.info(f"✅ Published message to {routing_key}: task_id={message.get('task_id')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish message: {e}")
            raise
    
    def _init_task_status(
        self,
        task_id: str,
        category: str,
        attributes: Dict[str, Any]
    ) -> None:
        """Initialize task status in Redis"""
        status_data = {
            "task_id": task_id,
            "status": CrawlTaskStatus.PENDING,
            "progress": 0,
            "products_found": 0,
            "created_at": datetime.now().isoformat(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "retry_count": 0,
            "sources_completed": [],
            "category": category,
            "attributes": attributes
        }
        
        status_key = f"crawl_task:{task_id}"
        self.redis_client.set(
            status_key,
            json.dumps(status_data),
            ex=RabbitMQConfig.CRAWL_TASK_TTL  # Auto-expire
        )
        
        logger.info(f"✅ Initialized task status: {task_id}")
    
    def _estimate_wait_time(self) -> int:
        """Estimate wait time based on queue depth"""
        try:
            channel = get_rabbitmq_channel("stats")
            method = channel.queue_declare(
                queue=RabbitMQConfig.CRAWL_QUEUE,
                passive=True
            )
            
            # Rough estimate: 10 seconds per task in queue
            queue_depth = method.method.message_count
            return max(5, queue_depth * 10)
            
        except Exception:
            return 30  # Default estimate if can't get actual count
    
    def validate_inputs(self, **kwargs) -> bool:
        """Validate service inputs"""
        required = ["category", "category_id", "attributes"]
        return all(k in kwargs for k in required)

# Import pika for BasicProperties
import pika
