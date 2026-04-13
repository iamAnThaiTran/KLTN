"""
RabbitMQ Producer and Consumer utilities for CrawlService
Handles task enqueueing and message consumption
"""

import pika
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class RabbitMQProducer:
    """Producer for enqueuing crawl tasks to RabbitMQ"""
    
    def __init__(self, host: str, port: int, username: str, password: str):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.connection = None
        self.channel = None
        self.queue_name = "crawl_tasks"
        self.connect()
    
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue with persistence
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True
            )
            
            # Declare DLQ for failed messages
            self.channel.queue_declare(
                queue=f"{self.queue_name}_dlq",
                durable=True
            )
            
            logger.info(f"Connected to RabbitMQ at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def _ensure_connected(self):
        """Ensure connection is alive, reconnect if needed"""
        try:
            if self.connection and self.connection.is_open and self.channel and self.channel.is_open:
                return True
            # Connection is closed, attempt reconnect
            logger.warning("RabbitMQ connection closed, attempting reconnect...")
            self.connect()
            return True
        except Exception as e:
            logger.error(f"Failed to ensure RabbitMQ connection: {e}")
            return False
    
    def enqueue_task(self, task_id: str, task_data: Dict[str, Any], priority: str = "normal"):
        """
        Enqueue a crawl task to RabbitMQ
        
        Args:
            task_id: Unique task identifier
            task_data: Task configuration (category, sources, attributes, etc.)
            priority: Task priority (low, normal, high)
        """
        try:
            # Ensure connection is alive before publishing
            if not self._ensure_connected():
                logger.error(f"Failed to enqueue task {task_id}: Cannot establish RabbitMQ connection")
                return False
            
            message = {
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat(),
                "priority": priority,
                **task_data
            }
            
            # Convert to JSON and publish
            body = json.dumps(message)
            
            self.channel.basic_publish(
                exchange='',
                routing_key=self.queue_name,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,  # Make message persistent
                    content_type='application/json'
                )
            )
            
            logger.info(f"Task enqueued: {task_id} with priority {priority}")
            return True
        except Exception as e:
            logger.error(f"Failed to enqueue task {task_id}: {e}")
            # Try to reconnect and retry once more
            try:
                logger.info(f"Retrying enqueue for task {task_id} after reconnect...")
                self.connect()
                self.channel.basic_publish(
                    exchange='',
                    routing_key=self.queue_name,
                    body=body,
                    properties=pika.BasicProperties(
                        delivery_mode=2,
                        content_type='application/json'
                    )
                )
                logger.info(f"Task enqueued (retry): {task_id}")
                return True
            except Exception as retry_error:
                logger.error(f"Retry failed for task {task_id}: {retry_error}")
                return False
    
    def close(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection:
                self.connection.close()
            logger.info("RabbitMQ connection closed")
        except Exception as e:
            logger.error(f"Error closing RabbitMQ connection: {e}")


class RabbitMQConsumer:
    """Consumer for processing crawl tasks from RabbitMQ"""
    
    def __init__(self, host: str, port: int, username: str, password: str, callback):
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.callback = callback  # Function to call when message received
        self.connection = None
        self.channel = None
        self.queue_name = "crawl_tasks"
    
    def connect(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(self.username, self.password)
            parameters = pika.ConnectionParameters(
                host=self.host,
                port=self.port,
                credentials=credentials,
                heartbeat=600,
                blocked_connection_timeout=300
            )
            self.connection = pika.BlockingConnection(parameters)
            self.channel = self.connection.channel()
            
            # Declare queue (should already exist)
            self.channel.queue_declare(
                queue=self.queue_name,
                durable=True
            )
            
            # Set QoS - process one message at a time
            self.channel.basic_qos(prefetch_count=1)
            
            logger.info(f"Consumer connected to RabbitMQ at {self.host}:{self.port}")
        except Exception as e:
            logger.error(f"Failed to connect to RabbitMQ: {e}")
            raise
    
    def process_message(self, ch, method, properties, body):
        """
        Process message from queue
        
        Args:
            ch: Channel
            method: Method frame
            properties: Properties
            body: Message body
        """
        try:
            message = json.loads(body)
            task_id = message.get("task_id")
            
            logger.info(f"Processing task: {task_id}")
            
            # Call the callback function to process the task
            success = self.callback(message)
            
            if success:
                # Acknowledge message (remove from queue)
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Task completed: {task_id}")
            else:
                # Negative acknowledge - requeue or send to DLQ
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                logger.warning(f"Task failed: {task_id}")
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
    
    def start_consuming(self):
        """Start consuming messages from queue with automatic reconnect"""
        retry_count = 0
        max_retries = 10
        
        while retry_count < max_retries:
            try:
                # Ensure connection is fresh
                if not self.connection or not self.connection.is_open:
                    logger.info("Reconnecting to RabbitMQ consumer...")
                    self.connect()
                    retry_count = 0  # Reset on successful reconnect
                
                self.channel.basic_consume(
                    queue=self.queue_name,
                    on_message_callback=self.process_message
                )
                
                logger.info(f"Starting to consume messages from {self.queue_name}")
                self.channel.start_consuming()
            
            except Exception as e:
                retry_count += 1
                logger.error(f"Consumer error (attempt {retry_count}/{max_retries}): {e}")
                
                try:
                    if self.connection:
                        self.connection.close()
                except:
                    pass
                
                if retry_count < max_retries:
                    import time
                    wait_time = min(30, 2 ** retry_count)  # Exponential backoff, max 30s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Max retries exceeded, stopping consumer")
                    raise
    
    def close(self):
        """Close RabbitMQ connection"""
        try:
            if self.connection:
                self.connection.close()
            logger.info("Consumer connection closed")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
