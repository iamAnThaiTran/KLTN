# app/services/base_service.py
"""
Base Service Class - All microservices inherit from this
Provides common functionality: logging, error handling, config
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BaseService(ABC):
    
    # Service metadata - override in subclass
    SERVICE_NAME = "BaseService"
    SERVICE_VERSION = "1.0.0"
    SERVICE_TIMEOUT = 30  # seconds
    ENABLE_METRICS = True
    
    def __init__(self):
        self.logger = logging.getLogger(self.SERVICE_NAME)
        self.metrics = {
            "total_requests": 0,
            "total_errors": 0,
            "total_duration": 0.0,
            "started_at": datetime.now().isoformat()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Health check endpoint data
        
        Returns:
        {
            "service": "ProductService",
            "status": "healthy|degraded|unhealthy",
            "version": "1.0.0",
            "uptime": 3600,
            "metrics": {...}
        }
        """
        uptime = (datetime.now().timestamp() - 
                 datetime.fromisoformat(self.metrics["started_at"]).timestamp())
        
        return {
            "service": self.SERVICE_NAME,
            "status": self._get_health_status(),
            "version": self.SERVICE_VERSION,
            "uptime_seconds": int(uptime),
            "metrics": self.metrics
        }
    
    def _get_health_status(self) -> str:
        """Override in subclass for specific health logic"""
        error_rate = (self.metrics["total_errors"] / 
                     max(1, self.metrics["total_requests"]))
        
        if error_rate > 0.1:  # >10% errors = unhealthy
            return "unhealthy"
        elif error_rate > 0.05:  # >5% errors = degraded
            return "degraded"
        else:
            return "healthy"
    
    def log_operation(
        self,
        operation: str,
        level: str = "info",
        **kwargs
    ) -> None:
        """
        Structured logging
        
        Usage:
        self.log_operation("query_products", "info", 
                          category="Giày", count=25)
        
        Output:
        [ProductService] query_products | category=Giày | count=25
        """
        context = " | ".join([f"{k}={v}" for k, v in kwargs.items()])
        message = f"[{self.SERVICE_NAME}] {operation}"
        if context:
            message += f" | {context}"
        
        log_func = getattr(self.logger, level, self.logger.info)
        log_func(message)
    
    def measure_time(
        self,
        operation: str,
        duration: float
    ) -> None:
        """Track operation duration"""
        if self.ENABLE_METRICS:
            self.metrics["total_duration"] += duration
            self.log_operation(
                f"{operation}_completed",
                "info",
                duration_ms=f"{duration*1000:.2f}"
            )
    
    def record_error(
        self,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Record error with context
        
        Usage:
        self.record_error("query_products", exc, 
                         context={"category_id": 5})
        """
        self.metrics["total_errors"] += 1
        
        error_info = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error)
        }
        
        if context:
            error_info.update(context)
        
        self.log_operation(
            f"{operation}_error",
            "error",
            **error_info
        )
    
    def handle_service_error(
        self,
        operation: str,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        raise_error: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        Standard error handling
        
        Args:
            operation: Operation name that failed
            error: Exception that occurred
            context: Additional context dict
            raise_error: Whether to re-raise after recording
        
        Returns:
            Error response dict if raise_error=False
        """
        self.record_error(operation, error, context)
        
        error_response = {
            "success": False,
            "error": str(error),
            "operation": operation,
            "error_type": type(error).__name__
        }
        
        if raise_error:
            raise error
        else:
            return error_response
    
    def track_request(self, operation: str) -> None:
        """Track incoming request"""
        self.metrics["total_requests"] += 1
    
    @abstractmethod
    def validate_inputs(self, **kwargs) -> bool:
        """
        Validate input parameters
        Override in subclass
        
        Returns: True if valid, False otherwise
        """
        pass

# ============================================================================
# SERVICE CLIENT BASE CLASS
# ============================================================================

class ServiceClient(ABC):
    """
    Base class for inter-service communication
    Handles request routing, error recovery, timeout management
    """
    
    CLIENT_NAME = "ServiceClient"
    REQUEST_TIMEOUT = 30  # seconds
    RETRY_COUNT = 3
    RETRY_DELAY = 1  # seconds
    
    def __init__(self):
        self.logger = logging.getLogger(self.CLIENT_NAME)
    
    def call_service(
        self,
        service_method: callable,
        *args,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Call another service with retry logic and error handling
        
        Usage:
        result = client.call_service(
            product_service.query_products,
            category_id=5,
            limit=10
        )
        """
        retry_count = 0
        last_error = None
        
        while retry_count < self.RETRY_COUNT:
            try:
                self.logger.info(f"[{self.CLIENT_NAME}] Calling {service_method.__name__} (attempt {retry_count+1})")
                
                result = service_method(*args, **kwargs)
                
                self.logger.info(f"[{self.CLIENT_NAME}] ✅ {service_method.__name__} succeeded")
                return result
                
            except Exception as e:
                last_error = e
                retry_count += 1
                
                if retry_count < self.RETRY_COUNT:
                    wait_time = self.RETRY_DELAY * retry_count
                    self.logger.warning(
                        f"[{self.CLIENT_NAME}] ⚠️ {service_method.__name__} failed (attempt {retry_count}), "
                        f"retrying in {wait_time}s: {e}"
                    )
                    time.sleep(wait_time)
                else:
                    self.logger.error(
                        f"[{self.CLIENT_NAME}] ❌ {service_method.__name__} failed after {self.RETRY_COUNT} attempts"
                    )
        
        raise last_error or Exception("Service call failed")

# ============================================================================
# SERVICE REGISTRY
# ============================================================================

class ServiceRegistry:
    """
    Simple service discovery/registry
    Maps service names to instances
    
    Usage:
    registry = ServiceRegistry()
    registry.register("product", product_service)
    product_svc = registry.get("product")
    """
    
    _services: Dict[str, BaseService] = {}
    _logger = logging.getLogger("ServiceRegistry")
    
    @classmethod
    def register(cls, service_name: str, service: BaseService) -> None:
        """Register a service"""
        cls._services[service_name] = service
        cls._logger.info(f"✅ Registered service: {service_name}")
    
    @classmethod
    def get(cls, service_name: str) -> Optional[BaseService]:
        """Get registered service"""
        service = cls._services.get(service_name)
        if not service:
            cls._logger.warning(f"⚠️ Service not found: {service_name}")
        return service
    
    @classmethod
    def get_all(cls) -> Dict[str, BaseService]:
        """Get all registered services"""
        return cls._services.copy()
    
    @classmethod
    def health_check_all(cls) -> Dict[str, Dict[str, Any]]:
        """Get health status of all services"""
        health_statuses = {}
        for name, service in cls._services.items():
            health_statuses[name] = service.health_check()
        return health_statuses
