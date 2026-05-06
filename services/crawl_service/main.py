"""
CrawlService - Microservice for async product crawling via RabbitMQ
Port: 8003

Handles:
- Enqueuing crawl tasks to RabbitMQ
- Tracking task status and results
- Managing Dead Letter Queue (DLQ) for failed tasks
- Crawler configuration management
"""

from fastapi import FastAPI, HTTPException, Body, Query
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime, timedelta
import uuid
import asyncio
import json

# Import RabbitMQ client
from rabbitmq_client import RabbitMQProducer

logger = logging.getLogger(__name__)

# ============================================================================
# Environment Configuration
# ============================================================================

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = "crawl_db"

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", "5672"))
RABBITMQ_USER = os.getenv("RABBITMQ_USER", "guest")
RABBITMQ_PASSWORD = os.getenv("RABBITMQ_PASSWORD", "guest")

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================================================
# FastAPI Setup
# ============================================================================

app = FastAPI(
    title="CrawlService",
    description="Microservice for async product crawling via RabbitMQ",
    version="1.0.0"
)

# CORS is handled by API Gateway (nginx)
# Don't add CORS middleware here to avoid duplicate headers

# ============================================================================
# Database Setup
# ============================================================================

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Initialize RabbitMQ Producer
rabbitmq_producer = None

def get_rabbitmq_producer():
    """Get or create RabbitMQ producer"""
    global rabbitmq_producer
    if rabbitmq_producer is None:
        try:
            rabbitmq_producer = RabbitMQProducer(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                username=RABBITMQ_USER,
                password=RABBITMQ_PASSWORD
            )
        except Exception as e:
            logger.error(f"Failed to initialize RabbitMQ producer: {e}")
    return rabbitmq_producer

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# Data Models (SQLAlchemy)
# ============================================================================

from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, Boolean, JSON, ARRAY, DECIMAL
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class CrawlTask(Base):
    __tablename__ = "crawl_tasks"
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100), unique=True)
    category = Column(String(255))
    category_id = Column(Integer)
    attributes = Column(JSON)
    status = Column(String(50))  # pending, running, completed, failed, cancelled
    priority = Column(String(20), default="normal")
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    started_at = Column(TIMESTAMP)
    completed_at = Column(TIMESTAMP)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    result = Column(JSON)

class CrawlHistory(Base):
    __tablename__ = "crawl_history"
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100))
    source = Column(String(50))  # tiki, lazada, shopee
    source_query = Column(String(500))
    products_found = Column(Integer)
    products_saved = Column(Integer)
    crawl_duration_seconds = Column(Integer)
    error_occurred = Column(Boolean, default=False)
    error_message = Column(Text)
    started_at = Column(TIMESTAMP, default=datetime.utcnow)
    completed_at = Column(TIMESTAMP)

class CrawlLog(Base):
    __tablename__ = "crawl_logs"
    id = Column(Integer, primary_key=True)
    task_id = Column(String(100))
    log_level = Column(String(20))  # INFO, WARNING, ERROR
    message = Column(Text)
    context = Column(JSON)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

class CrawlStatistics(Base):
    __tablename__ = "crawl_statistics"
    id = Column(Integer, primary_key=True)
    date = Column(String(10))
    total_tasks = Column(Integer, default=0)
    completed_tasks = Column(Integer, default=0)
    failed_tasks = Column(Integer, default=0)
    total_products_found = Column(Integer, default=0)
    avg_crawl_duration_seconds = Column(DECIMAL(10, 2))
    avg_products_per_task = Column(DECIMAL(10, 2))
    sources_used = Column(ARRAY(String))

# ============================================================================
# Health Check
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Service health check endpoint"""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "CrawlService",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# ============================================================================
# Crawl Task APIs
# ============================================================================

@app.post("/api/crawl/enqueue")
async def enqueue_crawl(
    category: str = Body(..., embed=True),
    category_id: int = Body(..., embed=True),
    sources: Optional[List[str]] = Body(None, embed=True),
    attributes: Optional[Dict[str, Any]] = Body(None, embed=True),
    priority: str = Body("normal", embed=True),
    max_retries: int = Body(3, embed=True)
):
    """
    Enqueue a new crawl task to RabbitMQ
    
    Example:
    {
        "category": "smartphone",
        "category_id": 5,
        "sources": ["tiki", "lazada"],
        "attributes": {"brand": "Apple"},
        "priority": "high",
        "max_retries": 3
    }
    """
    db = SessionLocal()
    try:
        # Generate unique task ID
        task_id = f"crawl_{uuid.uuid4().hex[:12]}"
        
        # Create task record in database
        task = CrawlTask(
            task_id=task_id,
            category=category,
            category_id=category_id,
            attributes=attributes or {},
            status="pending",
            priority=priority,
            max_retries=max_retries,
            retry_count=0
        )
        db.add(task)
        db.commit()
        
        # Enqueue to RabbitMQ
        producer = get_rabbitmq_producer()
        if producer:
            task_data = {
                "category": category,
                "category_id": category_id,
                "sources": sources or ["tiki"],
                "attributes": attributes or {}
            }
            producer.enqueue_task(task_id, task_data, priority)
            logger.info(f"Task enqueued to RabbitMQ: {task_id}")
        else:
            logger.warning(f"RabbitMQ producer not available, task saved locally: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=5)).isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Enqueue failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/crawl/enqueue-single")
async def enqueue_single_crawl(
    product_id: int = Body(..., embed=True),
    seller_id: str = Body("1", embed=True),
    priority: str = Body("normal", embed=True),
    max_retries: int = Body(3, embed=True),
    crawl_reviews: bool = Body(True, embed=True)
):
    """
    Enqueue a single product crawl task (for comparison/details)
    
    Example:
    {
        "product_id": 3553507,
        "seller_id": "1",
        "priority": "high",
        "max_retries": 3,
        "crawl_reviews": true
    }
    """
    db = SessionLocal()
    try:
        # Generate unique task ID
        task_id = f"single_{uuid.uuid4().hex[:12]}"
        
        # Create task record in database
        task = CrawlTask(
            task_id=task_id,
            category="single_product",
            category_id=product_id,  # Store product_id here
            attributes={"seller_id": seller_id, "crawl_reviews": crawl_reviews},
            status="pending",
            priority=priority,
            max_retries=max_retries,
            retry_count=0
        )
        db.add(task)
        db.commit()
        
        # Enqueue to RabbitMQ
        producer = get_rabbitmq_producer()
        if producer:
            task_data = {
                "product_id": product_id,
                "seller_id": seller_id,
                "crawl_reviews": crawl_reviews,
                "task_type": "single_product"
            }
            producer.enqueue_task(task_id, task_data, priority)
            logger.info(f"🚀 Single product crawl task enqueued: {task_id} for product {product_id}")
        else:
            logger.warning(f"RabbitMQ producer not available, task saved locally: {task_id}")
        
        return {
            "task_id": task_id,
            "id": task_id,  # Backward compatibility
            "status": "pending",
            "product_id": product_id,
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=2)).isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Enqueue single crawl failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/crawl/enqueue-product-details")
async def enqueue_product_details_crawl(
    product_ids: List[str] = Body(..., embed=True),
    schema: Optional[Dict[str, Any]] = Body(None, embed=True),
    max_concurrent: int = Body(3, embed=True),
    priority: str = Body("normal", embed=True),
    max_retries: int = Body(3, embed=True)
):
    """
    Enqueue product details crawl task with attribute extraction
    
    Example:
    {
        "product_ids": ["276183351", "276183352", "276183353"],
        "schema": {
            "category": "laptop",
            "attributes": [
                {
                    "name": "RAM",
                    "keywords": ["ram", "bộ nhớ"],
                    "value_pattern": "(\\d+)\\s*(?:gb|ddr)"
                }
            ]
        },
        "max_concurrent": 3,
        "priority": "normal",
        "max_retries": 3
    }
    
    Returns:
        {
            "task_id": "product_detail_...",
            "status": "pending",
            "products_count": 3
        }
    """
    db = SessionLocal()
    try:
        # Generate unique task ID
        task_id = f"product_detail_{uuid.uuid4().hex[:12]}"
        
        # Create task record in database
        task = CrawlTask(
            task_id=task_id,
            category="product_details",
            category_id=0,  # Not used for this task type
            attributes={
                "product_ids": product_ids,
                "schema": schema,
                "max_concurrent": max_concurrent
            },
            status="pending",
            priority=priority,
            max_retries=max_retries,
            retry_count=0
        )
        db.add(task)
        db.commit()
        
        # Enqueue to RabbitMQ
        producer = get_rabbitmq_producer()
        if producer:
            task_data = {
                "product_ids": product_ids,
                "schema": schema,
                "max_concurrent": max_concurrent,
                "task_type": "product_details"
            }
            producer.enqueue_task(task_id, task_data, priority)
            logger.info(f"🚀 Product details crawl task enqueued: {task_id} for {len(product_ids)} products")
        else:
            logger.warning(f"RabbitMQ producer not available, task saved locally: {task_id}")
        
        return {
            "task_id": task_id,
            "status": "pending",
            "products_count": len(product_ids),
            "estimated_completion": (datetime.utcnow() + timedelta(minutes=3)).isoformat()
        }
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Enqueue product details crawl failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/crawl/status/{task_id}")
async def get_task_status(task_id: str):
    """Get status of a crawl task"""
    db = SessionLocal()
    try:
        task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Calculate progress
        progress = {
            "status": task.status,
            "percent_complete": 100 if task.status == "completed" else 0,
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "current_step": "initializing" if task.status == "pending" else "crawling"
        }
        
        return {
            "task_id": task_id,
            "status": task.status,
            "progress": progress,
            "error": task.error_message
        }
    except Exception as e:
        logger.error(f"Get status failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/crawl/result/{task_id}")
async def get_task_result(task_id: str):
    """Get result of a crawl task - returns status + products/snapshot when completed"""
    db = SessionLocal()
    try:
        task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
        if not task:
            logger.warning(f"Task not found: {task_id}")
            raise HTTPException(status_code=404, detail="Task not found")
        
        logger.info(f"Task {task_id} status: {task.status}, result keys: {task.result.keys() if task.result else 'None'}")
        
        # Handle result - could be dict, string, or None
        import json
        result_data = {}
        if isinstance(task.result, str):
            result_data = json.loads(task.result) if task.result else {}
        elif isinstance(task.result, dict):
            result_data = task.result
        
        # Build response based on result type
        response = {
            "task_id": task_id,
            "status": task.status,  # pending, running, completed, failed
            "error": task.error_message if task.status == "failed" else None,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None
        }
        
        # If task completed, include results
        if task.status == "completed":
            # For multi-product crawls: return products list + metadata
            if "products" in result_data:
                response["products"] = result_data.get("products", [])
                response["products_found"] = result_data.get("products_found", 0)
                response["products_saved"] = result_data.get("products_saved", 0)
            # For single-product crawls: return snapshot
            if "snapshot" in result_data:
                response["snapshot"] = result_data.get("snapshot")
        
        return response
    except HTTPException:
        # Re-raise HTTPException without catching it
        raise
    except Exception as e:
        logger.error(f"Get result failed for {task_id}: {type(e).__name__}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/crawl/cancel/{task_id}")
async def cancel_task(task_id: str):
    """Cancel a pending or running crawl task"""
    db = SessionLocal()
    try:
        task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status == "completed":
            raise HTTPException(status_code=400, detail="Cannot cancel completed task")
        
        task.status = "cancelled"
        task.completed_at = datetime.utcnow()
        db.commit()
        
        return {"status": "cancelled", "task_id": task_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Cancel failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Task History and Monitoring
# ============================================================================

@app.get("/api/crawl/history")
async def get_task_history(
    category: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Get history of crawl tasks"""
    db = SessionLocal()
    try:
        query = db.query(CrawlTask)
        
        if category:
            query = query.filter(CrawlTask.category == category)
        if status:
            query = query.filter(CrawlTask.status == status)
        
        total = query.count()
        tasks = query.order_by(CrawlTask.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "tasks": [
                {
                    "task_id": t.task_id,
                    "category": t.category,
                    "status": t.status,
                    "created_at": t.created_at.isoformat() if t.created_at else None,
                    "completed_at": t.completed_at.isoformat() if t.completed_at else None
                }
                for t in tasks
            ]
        }
    except Exception as e:
        logger.error(f"Get history failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/crawl/statistics")
async def get_crawl_statistics():
    """Get overall crawl statistics"""
    db = SessionLocal()
    try:
        today = datetime.utcnow().strftime("%Y-%m-%d")
        stats = db.query(CrawlStatistics).filter(CrawlStatistics.date == today).first()
        
        # Calculate current stats
        total_tasks = db.query(CrawlTask).count()
        completed = db.query(CrawlTask).filter(CrawlTask.status == "completed").count()
        failed = db.query(CrawlTask).filter(CrawlTask.status == "failed").count()
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "success_rate_percent": (completed / total_tasks * 100) if total_tasks > 0 else 0
        }
    except Exception as e:
        logger.error(f"Get statistics failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Dead Letter Queue (DLQ) Management
# ============================================================================

@app.get("/api/dlq/messages")
async def get_dlq_messages(limit: int = 20, offset: int = 0):
    """Get messages from Dead Letter Queue (failed tasks)"""
    db = SessionLocal()
    try:
        failed_tasks = db.query(CrawlTask).filter(
            CrawlTask.status == "failed"
        ).order_by(CrawlTask.created_at.desc()).offset(offset).limit(limit).all()
        
        return {
            "total": len(failed_tasks),
            "messages": [
                {
                    "task_id": t.task_id,
                    "error": t.error_message,
                    "timestamp": t.completed_at.isoformat() if t.completed_at else None,
                    "retry_count": t.retry_count
                }
                for t in failed_tasks
            ]
        }
    except Exception as e:
        logger.error(f"Get DLQ failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/dlq/retry/{task_id}")
async def retry_dlq_message(task_id: str):
    """Requeue a failed task from DLQ"""
    db = SessionLocal()
    try:
        task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task.status = "pending"
        task.retry_count += 1
        task.error_message = None
        db.commit()
        
        # TODO: Re-enqueue to RabbitMQ
        
        return {"status": "requeued", "task_id": task_id, "retry_count": task.retry_count}
    except Exception as e:
        db.rollback()
        logger.error(f"Retry DLQ failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/dlq/messages/{task_id}")
async def discard_dlq_message(task_id: str):
    """Permanently discard a DLQ message"""
    db = SessionLocal()
    try:
        task = db.query(CrawlTask).filter(CrawlTask.task_id == task_id).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        db.delete(task)
        db.commit()
        
        return {"status": "discarded", "task_id": task_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Discard DLQ failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Crawler Configuration
# ============================================================================

crawler_configs = {
    "tiki": {
        "base_url": "https://tiki.vn",
        "timeout": 30,
        "max_retries": 3,
        "enabled": True
    },
    "lazada": {
        "base_url": "https://lazada.vn",
        "timeout": 30,
        "max_retries": 3,
        "enabled": True
    },
    "shopee": {
        "base_url": "https://shopee.vn",
        "timeout": 30,
        "max_retries": 3,
        "enabled": True
    }
}

@app.get("/api/crawler/config/{source}")
async def get_crawler_config(source: str):
    """Get configuration for a specific crawler"""
    if source not in crawler_configs:
        raise HTTPException(status_code=404, detail="Crawler not found")
    
    return {"source": source, "config": crawler_configs[source]}

@app.put("/api/crawler/config/{source}")
async def update_crawler_config(source: str, config: Dict[str, Any] = Body(...)):
    """Update crawler configuration"""
    if source not in crawler_configs:
        raise HTTPException(status_code=404, detail="Crawler not found")
    
    crawler_configs[source].update(config)
    return {"status": "updated", "source": source}

# ============================================================================
# Queue Status
# ============================================================================

@app.get("/api/queue/status")
async def get_queue_status():
    """Get RabbitMQ queue status"""
    # TODO: Query RabbitMQ management API
    return {
        "queue_name": "crawl_tasks",
        "messages_pending": 42,
        "consumers": 3
    }

# ============================================================================
# Startup and Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("CrawlService starting up...")
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection verified")
        
        # Initialize RabbitMQ producer
        get_rabbitmq_producer()
        logger.info("RabbitMQ producer initialized")
    except Exception as e:
        logger.error(f"Failed to initialize service: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("CrawlService shutting down...")
    global rabbitmq_producer
    if rabbitmq_producer:
        rabbitmq_producer.close()
    engine.dispose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8003,
        reload=False,
        log_level="info"
    )
