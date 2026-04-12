# services/job_manager.py
"""
Async Job Manager - Handle long-running /api/analyze jobs

Jobs are stored in Redis with structure:
  job:{jobId} -> {
    "status": "pending" | "done" | "error",
    "created_at": timestamp,
    "result": {...},
    "error": "error message"
  }
"""

import json
import uuid
from typing import Optional, Dict, Any
from datetime import datetime
import logging

from config.redis import RedisConnectionManager, is_redis_available

logger = logging.getLogger("job_manager")


class JobManager:
    """Manages async analyze jobs with Redis backend"""
    
    def __init__(self):
        """Initialize job manager"""
        self.redis_client = RedisConnectionManager.get_connection()
        self.use_redis = is_redis_available()
        self.in_memory_jobs = {}  # Fallback storage
        self.key_prefix = "analyze_job:"
        self.ttl_seconds = 3600  # 1 hour - jobs auto-expire
        
        status = "✓ Redis" if self.use_redis else "⚠️ In-Memory"
        logger.info(f"[JobManager] Storage: {status}")
    
    def create_job(
        self, 
        user_input: str, 
        conversation_id: Optional[str] = None
    ) -> str:
        """
        Create a new analyze job and return jobId
        
        Args:
            user_input: User's search input
            conversation_id: Optional conversation context
        
        Returns:
            str: jobId (UUID)
        """
        job_id = str(uuid.uuid4())
        
        job_data = {
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "user_input": user_input,
            "conversation_id": conversation_id,
            "result": None,
            "error": None
        }
        
        try:
            if self.use_redis:
                key = f"{self.key_prefix}{job_id}"
                self.redis_client.setex(
                    key,
                    self.ttl_seconds,
                    json.dumps(job_data)
                )
            else:
                self.in_memory_jobs[job_id] = job_data
            
            logger.info(f"[JobManager] Created job {job_id}: {user_input[:50]}")
            return job_id
        except Exception as e:
            logger.error(f"[JobManager] Error creating job: {e}")
            raise
    
    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get job status and result
        
        Args:
            job_id: Job ID
        
        Returns:
            Job dict with status/result, or None if not found
        """
        try:
            if self.use_redis:
                key = f"{self.key_prefix}{job_id}"
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            else:
                return self.in_memory_jobs.get(job_id)
        except Exception as e:
            logger.error(f"[JobManager] Error retrieving job {job_id}: {e}")
            return None
    
    def set_job_result(self, job_id: str, result: Dict[str, Any]) -> bool:
        """
        Mark job as done with result
        
        Args:
            job_id: Job ID
            result: Analysis result
        
        Returns:
            bool: Success status
        """
        try:
            job = self.get_job(job_id)
            if not job:
                logger.error(f"[JobManager] Job {job_id} not found")
                return False
            
            job["status"] = "done"
            job["result"] = result
            job["completed_at"] = datetime.utcnow().isoformat()
            
            if self.use_redis:
                key = f"{self.key_prefix}{job_id}"
                self.redis_client.setex(
                    key,
                    self.ttl_seconds,
                    json.dumps(job)
                )
            else:
                self.in_memory_jobs[job_id] = job
            
            logger.info(f"[JobManager] Job {job_id} completed")
            return True
        except Exception as e:
            logger.error(f"[JobManager] Error setting result for {job_id}: {e}")
            return False
    
    def set_job_error(self, job_id: str, error_message: str) -> bool:
        """
        Mark job as error
        
        Args:
            job_id: Job ID
            error_message: Error description
        
        Returns:
            bool: Success status
        """
        try:
            job = self.get_job(job_id)
            if not job:
                logger.error(f"[JobManager] Job {job_id} not found")
                return False
            
            job["status"] = "error"
            job["error"] = error_message
            job["completed_at"] = datetime.utcnow().isoformat()
            
            if self.use_redis:
                key = f"{self.key_prefix}{job_id}"
                self.redis_client.setex(
                    key,
                    self.ttl_seconds,
                    json.dumps(job)
                )
            else:
                self.in_memory_jobs[job_id] = job
            
            logger.error(f"[JobManager] Job {job_id} error: {error_message}")
            return True
        except Exception as e:
            logger.error(f"[JobManager] Error setting error for {job_id}: {e}")
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """
        Delete job (cleanup)
        
        Args:
            job_id: Job ID
        
        Returns:
            bool: Success status
        """
        try:
            if self.use_redis:
                key = f"{self.key_prefix}{job_id}"
                self.redis_client.delete(key)
            else:
                self.in_memory_jobs.pop(job_id, None)
            
            logger.info(f"[JobManager] Deleted job {job_id}")
            return True
        except Exception as e:
            logger.error(f"[JobManager] Error deleting job {job_id}: {e}")
            return False


# Global instance
_job_manager = None


def get_job_manager() -> JobManager:
    """Get or create job manager singleton"""
    global _job_manager
    if _job_manager is None:
        _job_manager = JobManager()
    return _job_manager
