# app/config/redis.py
"""
Redis configuration and connection management.
"""

import os
import redis
from typing import Optional
from dotenv import load_dotenv

load_dotenv()


class RedisConfig:
    """Redis configuration"""
    
    # Redis connection settings
    HOST = os.getenv("REDIS_HOST", "localhost")
    PORT = int(os.getenv("REDIS_PORT", 6379))
    DB = int(os.getenv("REDIS_DB", 0))
    PASSWORD = os.getenv("REDIS_PASSWORD", None)
    
    # Session settings
    SESSION_TTL = int(os.getenv("REDIS_SESSION_TTL", 86400))  # 24 hours
    
    @classmethod
    def get_url(cls) -> str:
        """Get Redis URL for connection"""
        if cls.PASSWORD:
            return f"redis://:{cls.PASSWORD}@{cls.HOST}:{cls.PORT}/{cls.DB}"
        return f"redis://{cls.HOST}:{cls.PORT}/{cls.DB}"


class RedisConnectionManager:
    """
    Manages Redis connection with health checks and error handling.
    """
    
    _instance: Optional[redis.Redis] = None
    _is_available = False
    
    @classmethod
    def get_connection(cls) -> Optional[redis.Redis]:
        """
        Get or create Redis connection.
        Returns None if Redis is not available.
        """
        if cls._instance is None:
            try:
                cls._instance = redis.from_url(
                    RedisConfig.get_url(),
                    decode_responses=True,
                    socket_connect_timeout=5,
                    socket_keepalive=True
                )
                # Test connection
                cls._instance.ping()
                cls._is_available = True
                print("✓ Redis connected successfully")
            except Exception as e:
                print(f"✗ Redis connection failed: {e}")
                print("→ Falling back to in-memory session manager")
                cls._is_available = False
                cls._instance = None
        
        return cls._instance if cls._is_available else None
    
    @classmethod
    def is_available(cls) -> bool:
        """Check if Redis is available"""
        cls.get_connection()  # Initialize if needed
        return cls._is_available
    
    @classmethod
    def close(cls):
        """Close Redis connection"""
        if cls._instance:
            try:
                cls._instance.close()
                cls._instance = None
                cls._is_available = False
                print("✓ Redis connection closed")
            except Exception as e:
                print(f"Error closing Redis: {e}")


def get_redis_client() -> Optional[redis.Redis]:
    """Get Redis client (returns None if not available)"""
    return RedisConnectionManager.get_connection()


def is_redis_available() -> bool:
    """Check if Redis is available"""
    return RedisConnectionManager.is_available()
