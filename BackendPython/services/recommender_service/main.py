"""
RecommendatorService - Microservice for intent detection and product ranking
Port: 8002

Handles:
- User intent detection
- Product ranking and scoring
- Classification (7 cases)
- Clarification questions
- Recommendation algorithm configuration
"""

from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime, timedelta
import hashlib
import json

logger = logging.getLogger(__name__)

# ============================================================================
# Environment Configuration
# ============================================================================

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = "recommender_db"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================================================
# FastAPI Setup
# ============================================================================

app = FastAPI(
    title="RecommendatorService",
    description="Microservice for intent detection and product ranking",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ============================================================================
# Data Models (SQLAlchemy)
# ============================================================================

from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, Boolean, JSON, ARRAY, Numeric, DECIMAL
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class IntentCache(Base):
    __tablename__ = "intent_cache"
    id = Column(Integer, primary_key=True)
    user_input_hash = Column(String(64), unique=True)
    intent_type = Column(String(50))
    confidence = Column(DECIMAL(5, 4))
    categories = Column(ARRAY(String))
    intent_data = Column(JSON)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP)
    hit_count = Column(Integer, default=0)

class RankingWeights(Base):
    __tablename__ = "ranking_weights"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer)
    attribute_name = Column(String(100))
    weight = Column(DECIMAL(5, 2))
    description = Column(Text)

class DialogueTemplate(Base):
    __tablename__ = "dialogue_templates"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer)
    attribute_name = Column(String(100))
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50))
    options = Column(JSON)
    is_active = Column(Boolean, default=True)

class ClassificationCache(Base):
    __tablename__ = "classification_cache"
    id = Column(Integer, primary_key=True)
    input_hash = Column(String(64), unique=True)
    case_number = Column(Integer)  # 1-7
    case_name = Column(String(100))
    confidence = Column(DECIMAL(5, 4))
    attributes = Column(JSON)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    expires_at = Column(TIMESTAMP)

class RankingHistory(Base):
    __tablename__ = "ranking_history"
    id = Column(Integer, primary_key=True)
    query_id = Column(String(100))
    category_id = Column(Integer)
    ranked_products = Column(JSON)
    user_selected_product = Column(String(100))
    ranking_quality = Column(String(50))  # good, fair, poor
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

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
            "service": "RecommendatorService",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# ============================================================================
# Intent Detection
# ============================================================================

def hash_input(text: str) -> str:
    """Hash user input for cache lookup"""
    return hashlib.sha256(text.lower().encode()).hexdigest()

@app.post("/api/intent/detect")
async def detect_intent(
    input: str = Body(..., embed=True),
    context: Optional[Dict[str, Any]] = Body(None, embed=True)
):
    """
    Detect user intent from natural language
    
    Example:
    {
        "input": "I want a laptop under 500",
        "context": {"previous_category": "electronics"}
    }
    """
    db = SessionLocal()
    try:
        input_hash = hash_input(input)
        
        # Check cache first
        cached = db.query(IntentCache).filter(
            IntentCache.user_input_hash == input_hash,
            IntentCache.expires_at > datetime.utcnow()
        ).first()
        
        if cached:
            cached.hit_count += 1
            db.commit()
            return {
                "intent_type": cached.intent_type,
                "confidence": float(cached.confidence) if cached.confidence else 0.0,
                "categories": cached.categories or [],
                "attributes": cached.intent_data or {},
                "cached": True
            }
        
        # Simulate intent detection (would use ML model in production)
        # Extract keywords for "under", "below", "max", etc. → price constraint
        # Extract keywords for product types → category
        intent_data = {
            "price_constraint": "under_500" if "under 500" in input.lower() else None,
            "product_type": "laptop" if "laptop" in input.lower() else None
        }
        
        intent_type = "purchase_inquiry"
        confidence = 0.85
        categories = ["electronics", "computers"]
        
        # Cache the result (24 hour TTL)
        cache_entry = IntentCache(
            user_input_hash=input_hash,
            intent_type=intent_type,
            confidence=confidence,
            categories=categories,
            intent_data=intent_data,
            expires_at=datetime.utcnow() + timedelta(hours=24),
            hit_count=1
        )
        db.add(cache_entry)
        db.commit()
        
        return {
            "intent_type": intent_type,
            "confidence": confidence,
            "categories": categories,
            "attributes": intent_data,
            "cached": False
        }
    except Exception as e:
        logger.error(f"Intent detection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Classification (7 Cases)
# ============================================================================

@app.post("/api/classify")
async def classify_intent(
    input: str = Body(..., embed=True),
    category: Optional[str] = Body(None, embed=True)
):
    """
    Classify user input into 7 cases for routing
    
    7 Cases:
    1. Simple search
    2. Filter-based search
    3. Comparison inquiry
    4. Specification inquiry
    5. Price inquiry
    6. Availability inquiry
    7. Review/feedback inquiry
    """
    db = SessionLocal()
    try:
        input_hash = hash_input(input)
        
        # Check cache
        cached = db.query(ClassificationCache).filter(
            ClassificationCache.input_hash == input_hash,
            ClassificationCache.expires_at > datetime.utcnow()
        ).first()
        
        if cached:
            return {
                "case": cached.case_number,
                "case_name": cached.case_name,
                "attributes": cached.attributes or {},
                "confidence": float(cached.confidence) if cached.confidence else 0.0
            }
        
        # Classification logic (rule-based, would use ML in production)
        case_number = 1  # Default
        case_name = "simple_search"
        confidence = 0.8
        attributes = {}
        
        if "compare" in input.lower() or "vs" in input.lower():
            case_number = 3
            case_name = "comparison_inquiry"
        elif "price" in input.lower():
            case_number = 5
            case_name = "price_inquiry"
        elif "available" in input.lower() or "stock" in input.lower():
            case_number = 6
            case_name = "availability_inquiry"
        elif "review" in input.lower() or "rating" in input.lower():
            case_number = 7
            case_name = "review_inquiry"
        elif any(word in input.lower() for word in ["filter", "brand", "color", "size"]):
            case_number = 2
            case_name = "filter_based_search"
        
        # Cache result
        cache_entry = ClassificationCache(
            input_hash=input_hash,
            case_number=case_number,
            case_name=case_name,
            confidence=confidence,
            attributes=attributes,
            expires_at=datetime.utcnow() + timedelta(hours=24)
        )
        db.add(cache_entry)
        db.commit()
        
        return {
            "case": case_number,
            "case_name": case_name,
            "attributes": attributes,
            "confidence": confidence
        }
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Product Ranking and Scoring
# ============================================================================

@app.post("/api/rank")
async def rank_products(
    products: List[Dict[str, Any]] = Body(..., embed=True),
    category: str = Body(..., embed=True),
    user_preferences: Optional[Dict[str, Any]] = Body(None, embed=True),
    weights: Optional[Dict[str, float]] = Body(None, embed=True)
):
    """
    Rank products by relevance
    
    Example:
    {
        "products": [
            {"product_id": "1", "name": "Laptop A", "price": 800},
            {"product_id": "2", "name": "Laptop B", "price": 1200}
        ],
        "category": "electronics",
        "user_preferences": {"price_sensitivity": 0.8},
        "weights": {"price": 0.5, "brand": 0.3, "rating": 0.2}
    }
    """
    db = SessionLocal()
    try:
        # Get default weights if not provided
        if not weights:
            db_weights = db.query(RankingWeights).filter(
                RankingWeights.category_id == None
            ).all()
            weights = {w.attribute_name: float(w.weight) for w in db_weights} if db_weights else {}
        
        # Score and rank each product
        scored_products = []
        for product in products:
            # Simple scoring (would be more sophisticated in production)
            score = 0.0
            
            # Price scoring (lower is better, up to a point)
            if "price" in product and weights.get("price", 0):
                price_score = 1.0 - (product["price"] / 2000)  # Normalize to max price
                score += max(0, price_score) * weights.get("price", 0)
            
            # Brand scoring (popular brands)
            if "brand" in product and weights.get("brand", 0):
                popular_brands = ["Dell", "HP", "Lenovo", "Apple"]
                brand_score = 1.0 if product.get("brand") in popular_brands else 0.5
                score += brand_score * weights.get("brand", 0)
            
            # Rating scoring
            if "rating" in product and weights.get("rating", 0):
                score += (product.get("rating", 0) / 5.0) * weights.get("rating", 0)
            
            product["relevance_score"] = min(1.0, score)
            scored_products.append(product)
        
        # Sort by score descending
        ranked = sorted(scored_products, key=lambda x: x.get("relevance_score", 0), reverse=True)
        
        return {
            "ranked_products": ranked,
            "category": category,
            "weights_used": weights
        }
    except Exception as e:
        logger.error(f"Ranking failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/score")
async def score_product(
    product: Dict[str, Any] = Body(..., embed=True),
    category: str = Body(..., embed=True),
    criteria: Optional[Dict[str, Any]] = Body(None, embed=True)
):
    """Score a single product"""
    db = SessionLocal()
    try:
        score = 0.8  # Placeholder
        
        return {
            "product_id": product.get("product_id"),
            "score": score,
            "component_scores": {
                "price": 0.7,
                "quality": 0.85,
                "availability": 0.9
            }
        }
    except Exception as e:
        logger.error(f"Scoring failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Dialog and Questions
# ============================================================================

@app.get("/api/questions")
async def get_clarification_questions(
    intent: str,
    category: str,
    limit: int = 3
):
    """Get clarification questions for user"""
    db = SessionLocal()
    try:
        questions = db.query(DialogueTemplate).filter(
            DialogueTemplate.is_active == True,
            DialogueTemplate.question_type.ilike(f"%{intent}%")
        ).limit(limit).all()
        
        return {
            "questions": [
                {
                    "id": q.id,
                    "question": q.question_text,
                    "question_type": q.question_type,
                    "options": q.options or []
                }
                for q in questions
            ]
        }
    except Exception as e:
        logger.error(f"Get questions failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Ranking Configuration
# ============================================================================

@app.get("/api/weights/{category}")
async def get_ranking_weights(category: str):
    """Get current ranking weights for category"""
    db = SessionLocal()
    try:
        weights = db.query(RankingWeights).filter(
            RankingWeights.category_id == int(category) if category.isdigit() else True
        ).all()
        
        return {
            "weights": {w.attribute_name: float(w.weight) for w in weights}
        }
    except Exception as e:
        logger.error(f"Get weights failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/api/weights/{category}")
async def update_ranking_weights(
    category: str,
    weights: Dict[str, float] = Body(..., embed=True)
):
    """Update ranking weights (admin operation)"""
    db = SessionLocal()
    try:
        for attr, weight in weights.items():
            db_weight = db.query(RankingWeights).filter(
                RankingWeights.attribute_name == attr
            ).first()
            
            if db_weight:
                db_weight.weight = weight
            else:
                db_weight = RankingWeights(
                    attribute_name=attr,
                    weight=weight,
                    category_id=int(category) if category.isdigit() else None
                )
                db.add(db_weight)
        
        db.commit()
        return {"status": "updated", "category": category}
    except Exception as e:
        db.rollback()
        logger.error(f"Update weights failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Cache Management
# ============================================================================

@app.get("/api/cache/stats")
async def get_cache_hit_rate():
    """Get intent detection cache statistics"""
    db = SessionLocal()
    try:
        total_entries = db.query(IntentCache).count()
        total_hits = db.query(IntentCache).with_entities(sum(IntentCache.hit_count)).scalar() or 0
        hit_rate = (total_hits / total_entries * 100) if total_entries > 0 else 0
        
        return {
            "cache_entries": total_entries,
            "total_hits": total_hits,
            "hit_rate_percent": hit_rate
        }
    except Exception as e:
        logger.error(f"Cache stats failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.delete("/api/cache/intent")
async def clear_intent_cache(older_than_hours: int = 24):
    """Clear expired cache entries"""
    db = SessionLocal()
    try:
        cutoff_time = datetime.utcnow() - timedelta(hours=older_than_hours)
        deleted = db.query(IntentCache).filter(
            IntentCache.created_at < cutoff_time
        ).delete()
        db.commit()
        
        return {"deleted_entries": deleted}
    except Exception as e:
        db.rollback()
        logger.error(f"Clear cache failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Startup and Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("RecommendatorService starting up...")
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    logger.info("RecommendatorService shutting down...")
    engine.dispose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8002,
        reload=False,
        log_level="info"
    )
