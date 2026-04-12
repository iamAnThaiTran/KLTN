# app/services/session_manager.py
"""
Session Manager - handles both Redis and in-memory fallback
Keeps conversation state + manages persistence
"""

import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import redis

from config.redis import RedisConnectionManager, is_redis_available  # ✅ LOCAL


class SessionManager:
    """
    Manages conversation sessions with Redis persistence + in-memory fallback.
    
    Transparently switches between:
    - Redis (production) - persistent, shareable across servers
    - In-memory dict (fallback) - when Redis unavailable
    """
    
    def __init__(self):
        """Initialize session manager"""
        self.redis_client = RedisConnectionManager.get_connection()
        self.use_redis = is_redis_available()
        self.in_memory_sessions = {}  # Fallback storage
        self.key_prefix = "conversation_session:"
        self.ttl_seconds = 86400  # 24 hours
        
        status = "✓ Redis" if self.use_redis else "⚠️ In-Memory (Redis unavailable)"
        print(f"[SessionManager] Session storage: {status}")
    
    def create_session(self) -> str:
        """
        Create a new session and return conversation_id
        
        Returns:
            str: conversation_id (UUID)
        """
        conversation_id = str(uuid.uuid4())
        self.set_session(conversation_id, None)
        print(f"[SessionManager] Created session: {conversation_id}")
        return conversation_id
    
    def set_session(self, conversation_id: str, state: Optional[Dict[str, Any]]) -> bool:
        """
        Save conversation state to storage
        
        Args:
            conversation_id: Session ID
            state: Conversation state dict (can be None for init)
        
        Returns:
            bool: Success status
        """
        try:
            if self.use_redis:
                # Save to Redis with TTL
                key = f"{self.key_prefix}{conversation_id}"
                data = json.dumps(state) if state is not None else json.dumps({})
                self.redis_client.setex(
                    key,
                    self.ttl_seconds,
                    data
                )
                return True
            else:
                # Fallback to in-memory
                self.in_memory_sessions[conversation_id] = state
                return True
        except Exception as e:
            print(f"[SessionManager] ⚠️ Error saving session {conversation_id}: {e}")
            # Fallback if Redis fails
            if self.use_redis and not self._check_redis_health():
                print(f"[SessionManager] Redis failed, falling back to in-memory")
                self.use_redis = False
                self.in_memory_sessions[conversation_id] = state
                return True
            return False
    
    def get_session(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve conversation state from storage
        
        Args:
            conversation_id: Session ID
        
        Returns:
            Dict or None: Conversation state, or None if not found
        """
        try:
            if self.use_redis:
                # Get from Redis
                key = f"{self.key_prefix}{conversation_id}"
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            else:
                # Get from in-memory
                return self.in_memory_sessions.get(conversation_id)
        except Exception as e:
            print(f"[SessionManager] ⚠️ Error retrieving session {conversation_id}: {e}")
            # Fallback if Redis fails
            if self.use_redis and not self._check_redis_health():
                print(f"[SessionManager] Redis failed, falling back to in-memory")
                self.use_redis = False
                return self.in_memory_sessions.get(conversation_id)
            return None
    
    def delete_session(self, conversation_id: str) -> bool:
        """
        Delete conversation session
        
        Args:
            conversation_id: Session ID
        
        Returns:
            bool: Success status
        """
        try:
            if self.use_redis:
                # Delete from Redis
                key = f"{self.key_prefix}{conversation_id}"
                self.redis_client.delete(key)
                return True
            else:
                # Delete from in-memory
                self.in_memory_sessions.pop(conversation_id, None)
                return True
        except Exception as e:
            print(f"[SessionManager] ⚠️ Error deleting session {conversation_id}: {e}")
            return False
    
    def update_session(self, conversation_id: str, state: Dict[str, Any]) -> bool:
        """
        Update existing session state (merge with current)
        
        Args:
            conversation_id: Session ID
            state: New state dict (will be merged with current)
        
        Returns:
            bool: Success status
        """
        try:
            current = self.get_session(conversation_id)
            if current is None:
                current = {}
            
            # Merge states
            current.update(state)
            return self.set_session(conversation_id, current)
        except Exception as e:
            print(f"[SessionManager] ⚠️ Error updating session {conversation_id}: {e}")
            return False
    
    def session_exists(self, conversation_id: str) -> bool:
        """Check if session exists"""
        try:
            state = self.get_session(conversation_id)
            return state is not None
        except:
            return False
    
    def list_active_sessions(self) -> list:
        """
        List all active session IDs
        
        Returns:
            list: List of conversation_ids
        """
        try:
            if self.use_redis:
                # Get from Redis keys
                pattern = f"{self.key_prefix}*"
                keys = self.redis_client.keys(pattern)
                return [k.replace(self.key_prefix, "") for k in keys]
            else:
                # Get from in-memory
                return list(self.in_memory_sessions.keys())
        except Exception as e:
            print(f"[SessionManager] ⚠️ Error listing sessions: {e}")
            return []
    
    def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions
        (Redis auto-expires, but in-memory needs manual cleanup)
        
        Returns:
            int: Number of sessions cleaned
        """
        try:
            if not self.use_redis:
                # Manual cleanup for in-memory (optional - can skip)
                # For now, keep expired sessions in memory
                return 0
            return 0
        except Exception as e:
            print(f"[SessionManager] ⚠️ Error cleaning up sessions: {e}")
            return 0
    
    def _check_redis_health(self) -> bool:
        """Check if Redis connection is healthy"""
        try:
            if self.redis_client:
                self.redis_client.ping()
                return True
            return False
        except:
            return False
    
    def get_storage_type(self) -> str:
        """Get current storage type for debugging"""
        return "Redis" if self.use_redis else "In-Memory"
    
    def get_session_count(self) -> int:
        """Get number of active sessions"""
        try:
            if self.use_redis:
                pattern = f"{self.key_prefix}*"
                return self.redis_client.dbsize()
            else:
                return len(self.in_memory_sessions)
        except:
            return 0


# Global session manager instance
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get or create global session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
