# app/services/session_manager_factory.py
"""
Session Manager Factory - automatically choose between Redis and In-Memory.
"""

from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

from .redis_session_manager import (  # ✅ LOCAL
    RedisSessionManager,
    InMemorySessionManager,
)
from .search_models import SearchSession  # ✅ LOCAL
from config.redis import is_redis_available, RedisConfig  # ✅ LOCAL: Use local config


class BaseSessionManager(ABC):
    """Abstract base for session managers"""
    
    @abstractmethod
    def save_session(self, session: SearchSession) -> bool:
        pass
    
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[SearchSession]:
        pass
    
    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        pass
    
    @abstractmethod
    def list_active_sessions(self) -> List[str]:
        pass
    
    @abstractmethod
    def update_session_progress(self, session_id: str, progress: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def cleanup_expired_sessions(self) -> int:
        pass


class SessionManagerFactory:
    """
    Factory for creating appropriate session manager.
    
    Automatically uses Redis if available, falls back to in-memory.
    
    Usage:
        manager = SessionManagerFactory.create()
        manager.save_session(session)
    """
    
    _instance: Optional[BaseSessionManager] = None
    _using_redis = False
    
    @classmethod
    def create(cls) -> BaseSessionManager:
        """
        Create or return cached session manager instance.
        """
        if cls._instance is None:
            if is_redis_available():
                # print("📦 Using Redis Session Manager")
                cls._instance = RedisSessionManager(redis_url=RedisConfig.get_url())
                cls._using_redis = True
            else:
                # print("💾 Using In-Memory Session Manager (Redis not available)")
                cls._instance = InMemorySessionManager()
                cls._using_redis = False
        
        return cls._instance
    
    @classmethod
    def is_using_redis(cls) -> bool:
        """Check if currently using Redis"""
        cls.create()  # Initialize if needed
        return cls._using_redis
    
    @classmethod
    def reset(cls):
        """Reset the manager (for testing)"""
        cls._instance = None
        cls._using_redis = False


def get_session_manager() -> BaseSessionManager:
    """
    Get session manager instance.
    
    Convenience function for importing and using.
    """
    return SessionManagerFactory.create()
