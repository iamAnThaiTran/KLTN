# app/config/rabbitmq.py
"""
RabbitMQ Configuration & Connection Management
Handles queue setup, connection pooling, error recovery
"""

import pika
import logging
import os
from typing import Optional, Callable, Dict, Any
from functools import lru_cache
from pika.adapters.blocking_connection import BlockingConnection
from pika.connection import ConnectionParameters
from pika.channel import Channel

logger = logging.getLogger(__name__)

# ============================================================================
# RABBITMQ CONFIGURATION
# ============================================================================

class RabbitMQConfig:
    """Configuration for RabbitMQ connection and queues"""
    
    # Connection Settings
    HOST = os.getenv("RABBITMQ_HOST", "localhost")
    PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
    USER = os.getenv("RABBITMQ_USER", "guest")
    PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")
    VHOST = os.getenv("RABBITMQ_VHOST", "/")
    
    # Connection Pool
    CONNECTION_TIMEOUT = 10  # seconds
    CHANNEL_MAX = 2048
    HEARTBEAT = 30  # seconds
    BLOCKED_CONNECTION_TIMEOUT = 300  # seconds
    
    # Queue Configuration
    CRAWL_QUEUE = "crawl_tasks"
    COMPARISON_QUEUE = "comparison_tasks"
    DLQ_SUFFIX = ".dlq"  # Dead Letter Queue
    
    # Exchange Configuration
    MAIN_EXCHANGE = "product.events"
    EXCHANGE_TYPE = "topic"
    
    # Message Configuration
    CRAWL_TASK_TTL = int(os.getenv("CRAWL_TASK_TTL", "7200"))  # 2 hours
    CRAWL_MAX_RETRIES = int(os.getenv("CRAWL_MAX_RETRIES", "3"))
    
    # Feature Flags
    USE_RABBITMQ = os.getenv("USE_RABBITMQ", "true").lower() == "true"

# ============================================================================
# RABBITMQ CONNECTION MANAGER
# ============================================================================

class RabbitMQConnection:
    """
    Singleton connection manager for RabbitMQ
    Handles connection pooling, reconnection, and channel management
    """
    
    _instance: Optional['RabbitMQConnection'] = None
    _connection: Optional[BlockingConnection] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._connection = None
        self._channels = {}  # channel_id -> Channel
        self._connect()
    
    def _connect(self):
        """Establish connection to RabbitMQ"""
        try:
            credentials = pika.PlainCredentials(
                RabbitMQConfig.USER,
                RabbitMQConfig.PASSWORD
            )
            
            parameters = ConnectionParameters(
                host=RabbitMQConfig.HOST,
                port=RabbitMQConfig.PORT,
                virtual_host=RabbitMQConfig.VHOST,
                credentials=credentials,
                connection_attempts=3,
                retry_delay=2,
                socket_connect_timeout=RabbitMQConfig.CONNECTION_TIMEOUT,
                heartbeat=RabbitMQConfig.HEARTBEAT,
                blocked_connection_timeout=RabbitMQConfig.BLOCKED_CONNECTION_TIMEOUT,
                channel_max=RabbitMQConfig.CHANNEL_MAX
            )
            
            self._connection = pika.BlockingConnection(parameters)
            logger.info(f"✅ Connected to RabbitMQ at {RabbitMQConfig.HOST}:{RabbitMQConfig.PORT}")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to RabbitMQ: {e}")
            self._connection = None
            raise
    
    def get_channel(self, channel_id: str = "default") -> Channel:
        """Get or create a channel"""
        if channel_id not in self._channels:
            if self._connection is None:
                self._connect()
            
            try:
                channel = self._connection.channel()
                self._channels[channel_id] = channel
                logger.info(f"✅ Created channel: {channel_id}")
            except Exception as e:
                logger.error(f"❌ Failed to create channel {channel_id}: {e}")
                self._reconnect()
                channel = self._connection.channel()
                self._channels[channel_id] = channel
        
        return self._channels[channel_id]
    
    def _reconnect(self):
        """Reconnect to RabbitMQ if connection lost"""
        try:
            logger.warning("🔄 Attempting to reconnect to RabbitMQ...")
            self._channels = {}
            self._connect()
        except Exception as e:
            logger.error(f"❌ Reconnection failed: {e}")
            raise
    
    def is_connected(self) -> bool:
        """Check if connected"""
        return self._connection is not None and self._connection.is_open
    
    def close(self):
        """Close all channels and connection"""
        try:
            for channel_id, channel in self._channels.items():
                if channel.is_open:
                    channel.close()
                    logger.info(f"✅ Closed channel: {channel_id}")
            
            if self._connection and self._connection.is_open:
                self._connection.close()
                logger.info("✅ Closed RabbitMQ connection")
        except Exception as e:
            logger.error(f"❌ Error closing connection: {e}")

# ============================================================================
# QUEUE SETUP MANAGER
# ============================================================================

class QueueSetup:
    """Initialize exchanges, queues, and bindings"""
    
    @staticmethod
    def setup_crawl_queue(channel: Channel) -> None:
        """
        Setup crawl task queue with dead letter exchange
        
        Flow:
        crawl_tasks (main) → [expires/rejected] → crawl_tasks.dlq
        """
        
        # Declare main exchange
        channel.exchange_declare(
            exchange=RabbitMQConfig.MAIN_EXCHANGE,
            exchange_type=RabbitMQConfig.EXCHANGE_TYPE,
            durable=True,
            auto_delete=False
        )
        logger.info(f"✅ Declared exchange: {RabbitMQConfig.MAIN_EXCHANGE}")
        
        # Declare dead letter exchange (for rejected messages)
        dlq_exchange = f"{RabbitMQConfig.MAIN_EXCHANGE}.dlx"
        channel.exchange_declare(
            exchange=dlq_exchange,
            exchange_type="direct",
            durable=True,
            auto_delete=False
        )
        logger.info(f"✅ Declared DLX: {dlq_exchange}")
        
        # Declare main crawl queue
        channel.queue_declare(
            queue=RabbitMQConfig.CRAWL_QUEUE,
            durable=True,
            arguments={
                "x-message-ttl": RabbitMQConfig.CRAWL_TASK_TTL * 1000,  # Convert to ms
                "x-dead-letter-exchange": dlq_exchange,
                "x-dead-letter-routing-key": f"{RabbitMQConfig.CRAWL_QUEUE}.dlq"
            }
        )
        logger.info(f"✅ Declared queue: {RabbitMQConfig.CRAWL_QUEUE} (TTL: {RabbitMQConfig.CRAWL_TASK_TTL}s)")
        
        # Declare dead letter queue
        dlq_name = f"{RabbitMQConfig.CRAWL_QUEUE}.dlq"
        channel.queue_declare(
            queue=dlq_name,
            durable=True
        )
        logger.info(f"✅ Declared DLQ: {dlq_name}")
        
        # Bind main queue to exchange
        channel.queue_bind(
            queue=RabbitMQConfig.CRAWL_QUEUE,
            exchange=RabbitMQConfig.MAIN_EXCHANGE,
            routing_key="crawl.*"
        )
        logger.info(f"✅ Bound {RabbitMQConfig.CRAWL_QUEUE} to {RabbitMQConfig.MAIN_EXCHANGE}")
        
        # Bind DLQ to DLX
        channel.queue_bind(
            queue=dlq_name,
            exchange=dlq_exchange,
            routing_key=f"{RabbitMQConfig.CRAWL_QUEUE}.dlq"
        )
        logger.info(f"✅ Bound {dlq_name} to {dlq_exchange}")
    
    @staticmethod
    def setup_all(channel: Channel) -> None:
        """Setup all queues"""
        QueueSetup.setup_crawl_queue(channel)
        logger.info("✅ All queues configured!")

# ============================================================================
# SINGLETON FACTORY
# ============================================================================

@lru_cache(maxsize=1)
def get_rabbitmq_connection() -> RabbitMQConnection:
    """Get singleton RabbitMQ connection"""
    return RabbitMQConnection()

def get_rabbitmq_channel(channel_id: str = "default") -> Channel:
    """Get RabbitMQ channel (creates if needed)"""
    conn = get_rabbitmq_connection()
    return conn.get_channel(channel_id)

# ============================================================================
# ASYNC SETUP (for FastAPI startup event)
# ============================================================================

async def setup_rabbitmq() -> None:
    """
    Setup RabbitMQ on application startup
    Call this in FastAPI startup event:
    
    @app.on_event("startup")
    async def startup():
        await setup_rabbitmq()
    """
    try:
        if not RabbitMQConfig.USE_RABBITMQ:
            logger.warning("⚠️ RabbitMQ is disabled (USE_RABBITMQ=false)")
            return
        
        conn = get_rabbitmq_connection()
        channel = conn.get_channel("setup")
        QueueSetup.setup_all(channel)
        logger.info("✅ RabbitMQ setup complete!")
    except Exception as e:
        logger.error(f"❌ RabbitMQ setup failed: {e}")
        if os.getenv("ENV", "development") == "production":
            raise  # Fail fast in production
