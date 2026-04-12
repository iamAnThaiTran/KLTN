# app/services/redis_session_manager.py
"""
Redis-based session manager for storing search sessions.
Replaces in-memory storage for production.
"""

import redis
import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from .search_models import SearchSession  # ✅ LOCAL


class RedisSessionManager:
    """
    Manages SearchSession persistence in Redis.
    Also supports conversation-based sessions using dict storage.
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379"):
        """
        Initialize Redis connection.
        
        Args:
            redis_url: Redis connection URL, e.g., "redis://localhost:6379/0"
        """
        self.redis_client = redis.from_url(redis_url, decode_responses=True)
        self.key_prefix = "search_session:"
        self.conversation_prefix = "conversation_session:"
        self.ttl_seconds = 86400  # 24 hours
    
    def save_session(self, session: SearchSession) -> bool:
        """
        Save session to Redis.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            key = f"{self.key_prefix}{session.session_id}"
            data = json.dumps(session.to_dict())
            
            # Set with expiration
            self.redis_client.setex(
                key,
                self.ttl_seconds,
                data
            )
            
            # Also add to a set of active sessions
            self.redis_client.sadd("active_search_sessions", session.session_id)
            
            return True
        except Exception as e:
            print(f"Error saving session to Redis: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[SearchSession]:
        """
        Retrieve session from Redis.
        
        Returns:
            SearchSession if found, None otherwise
        """
        try:
            key = f"{self.key_prefix}{session_id}"
            data = self.redis_client.get(key)
            
            if not data:
                return None
            
            session_dict = json.loads(data)
            return SearchSession.from_dict(session_dict)
        except Exception as e:
            print(f"Error retrieving session from Redis: {e}")
            return None
    
    def delete_session(self, session_id: str) -> bool:
        """
        Delete session from Redis.
        """
        try:
            key = f"{self.key_prefix}{session_id}"
            self.redis_client.delete(key)
            self.redis_client.srem("active_search_sessions", session_id)
            return True
        except Exception as e:
            print(f"Error deleting session from Redis: {e}")
            return False
    
    def list_active_sessions(self) -> list[str]:
        """Get list of all active session IDs"""
        try:
            return list(self.redis_client.smembers("active_search_sessions"))
        except Exception as e:
            print(f"Error listing sessions: {e}")
            return []
    
    def update_session_progress(self, session_id: str, progress: Dict[str, Any]) -> bool:
        """
        Increment progress for a session.
        Useful for crawl updates.
        
        progress: {
            "crawl_progress": {"tiki": 45, "lazada": 30},
            "total_products": 100
        }
        """
        try:
            session = self.get_session(session_id)
            if not session:
                return False
            
            # Update fields
            if "crawl_progress" in progress:
                session.crawl_progress.update(progress["crawl_progress"])
            
            if "total_products" in progress:
                session.total_products = progress["total_products"]
            
            if "state" in progress:
                from .search_models import SearchState  # ✅ LOCAL
                session.state = SearchState(progress["state"])
            
            session.last_updated_at = datetime.utcnow()
            
            return self.save_session(session)
        except Exception as e:
            print(f"Error updating session progress: {e}")
            return False
    
    def cleanup_expired_sessions(self) -> int:
        """
        Cleanup expired sessions from Redis set.
        Redis will auto-expire keys, but we need to clean the set.
        
        Returns: Count of sessions cleaned
        """
        try:
            active_sessions = self.list_active_sessions()
            cleaned = 0
            
            for session_id in active_sessions:
                if not self.get_session(session_id):
                    # Session expired, remove from active set
                    self.redis_client.srem("active_search_sessions", session_id)
                    cleaned += 1
            
            return cleaned
        except Exception as e:
            print(f"Error cleaning up sessions: {e}")
            return 0
    
    def get_storage_type(self) -> str:
        """Get current storage type for debugging"""
        return "Redis"
    
    # ========== Conversation-based session methods ==========
    def create_session(self) -> str:
        """
        Create a new conversation session and return conversation_id
        
        Returns:
            str: conversation_id (UUID)
        """
        conversation_id = str(uuid.uuid4())
        self.set_session(conversation_id, None)
        print(f"[SessionManager] Created session: {conversation_id}")
        return conversation_id
    
    def set_session(self, conversation_id: str, state: Optional[Dict[str, Any]]) -> bool:
        """
        Save conversation state to Redis
        
        Args:
            conversation_id: Session ID
            state: Conversation state dict (can be None for init)
        
        Returns:
            bool: Success status
        """
        try:
            key = f"{self.conversation_prefix}{conversation_id}"
            data = json.dumps(state) if state is not None else json.dumps({})
            self.redis_client.setex(
                key,
                self.ttl_seconds,
                data
            )
            return True
        except Exception as e:
            print(f"[SessionManager] ⚠️ Error saving session {conversation_id}: {e}")
            return False
    
    def get_session_dict(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve conversation state from Redis as dict
        
        Args:
            conversation_id: Session ID
        
        Returns:
            Dict or None: Conversation state, or None if not found
        """
        try:
            key = f"{self.conversation_prefix}{conversation_id}"
            data = self.redis_client.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            print(f"[SessionManager] ⚠️ Error retrieving session {conversation_id}: {e}")
            return None
    
    def session_exists(self, conversation_id: str) -> bool:
        """
        Check if conversation session exists
        
        Args:
            conversation_id: Session ID
        
        Returns:
            bool: True if session exists, False otherwise
        """
        try:
            state = self.get_session_dict(conversation_id)
            return state is not None
        except:
            return False


class InMemorySessionManager:
    """
    In-memory session manager for development/testing.
    Replaces Redis when it's not available.
    """
    
    def __init__(self):
        self._sessions: Dict[str, SearchSession] = {}
        self._created_at: Dict[str, datetime] = {}
        self.ttl_seconds = 86400  # 24 hours
    
    def save_session(self, session: SearchSession) -> bool:
        """Save session to memory"""
        self._sessions[session.session_id] = session
        self._created_at[session.session_id] = datetime.utcnow()
        return True
    
    def get_session(self, session_id: str) -> Optional[SearchSession]:
        """Retrieve session from memory"""
        session = self._sessions.get(session_id)
        
        if session:
            # Check if expired
            created = self._created_at.get(session_id)
            if created and (datetime.utcnow() - created).total_seconds() > self.ttl_seconds:
                del self._sessions[session_id]
                del self._created_at[session_id]
                return None
        
        return session
    
    def delete_session(self, session_id: str) -> bool:
        """Delete session from memory"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            del self._created_at[session_id]
            return True
        return False
    
    def list_active_sessions(self) -> list[str]:
        """Get list of active session IDs"""
        # Clean up expired first
        self.cleanup_expired_sessions()
        return list(self._sessions.keys())
    
    def update_session_progress(self, session_id: str, progress: Dict[str, Any]) -> bool:
        """Update session progress"""
        session = self.get_session(session_id)
        if not session:
            return False
        
        if "crawl_progress" in progress:
            session.crawl_progress.update(progress["crawl_progress"])
        
        if "total_products" in progress:
            session.total_products = progress["total_products"]
        
        if "state" in progress:
            from .search_models import SearchState  # ✅ LOCAL
            session.state = SearchState(progress["state"])
        
        session.last_updated_at = datetime.utcnow()
        return True
    
    def cleanup_expired_sessions(self) -> int:
        """Remove expired sessions"""
        now = datetime.utcnow()
        expired_ids = [
            sid for sid, created in self._created_at.items()
            if (now - created).total_seconds() > self.ttl_seconds
        ]
        
        for sid in expired_ids:
            del self._sessions[sid]
            del self._created_at[sid]
        
        return len(expired_ids)
    
    def get_storage_type(self) -> str:
        """Get current storage type for debugging"""
        return "In-Memory"
