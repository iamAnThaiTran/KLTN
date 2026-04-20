"""
ProductService - Microservice for product catalog management
Port: 8001

Handles:
- Product search and filtering
- Product and SKU management
- Category attribute configuration
"""

from fastapi import FastAPI, HTTPException, Query, Body, Depends
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime
import unicodedata
import re

logger = logging.getLogger(__name__)

# ============================================================================
# Helper Functions
# ============================================================================

def slugify(text: str) -> str:
    """
    Convert text to URL-friendly slug
    Removes Vietnamese diacritics: à→a, ư→u, etc.
    """
    # Normalize Vietnamese characters (NFD decomposition)
    nfkd_form = unicodedata.normalize('NFKD', text)
    # Remove combining marks (diacritics)
    ascii_form = ''.join([c for c in nfkd_form if not unicodedata.combining(c)])
    # Convert to lowercase
    slug = ascii_form.lower()
    # Replace spaces and underscores with hyphens
    slug = re.sub(r'[\s_]+', '-', slug)
    # Remove non-alphanumeric characters except hyphens
    slug = re.sub(r'[^a-z0-9-]', '', slug)
    # Remove multiple consecutive hyphens
    slug = re.sub(r'-+', '-', slug)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    return slug

# ============================================================================
# Environment Configuration
# ============================================================================

DB_USER = os.getenv("POSTGRES_USER", "postgres")
DB_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")
DB_HOST = os.getenv("DB_HOST", "postgres")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_NAME = "products_db"

DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# ============================================================================
# FastAPI Setup
# ============================================================================

app = FastAPI(
    title="ProductService",
    description="Microservice for product catalog management",
    version="1.0.0"
)

# CORS is handled by API Gateway (nginx)
# Don't add CORS middleware here to avoid duplicate headers

# ============================================================================
# Database Connection
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

from sqlalchemy import Column, Integer, String, Float, Text, TIMESTAMP, Boolean, JSON, ARRAY
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Category(Base):
    __tablename__ = "categories"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True)
    slug = Column(String(255), unique=True, nullable=False)
    description = Column(Text)
    parent_category_id = Column(Integer, nullable=True)
    category_type = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, nullable=False)  # Required!
    title = Column(String(500), nullable=False)  # Changed from 'name'
    brand = Column(String(100))
    description = Column(Text)
    product_url = Column(String(500))  # From crawler link
    thumbnail = Column(String(500))  # From crawler image
    source = Column(String(50))  # tiki, lazada, shopee
    tiki_product_id = Column(String(100))  # From crawler product_id
    tiki_spid = Column(String(100))  # From crawler spid
    seller_id = Column(String(100), default='1')
    is_active = Column(Boolean, default=True)  # Changed from is_available
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

class SKU(Base):
    __tablename__ = "skus"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)  # FK to products.id (INTEGER)
    sku_code = Column(String(100), unique=True)  # Changed from sku_id
    price = Column(Float, nullable=False)  # Selling price
    original_price = Column(Float)  # Original price before discount
    stock = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

class CategoryAttribute(Base):
    __tablename__ = "category_attributes"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer)
    attribute_name = Column(String(255))
    attribute_type = Column(String(50))
    is_filterable = Column(Boolean, default=True)
    values = Column(ARRAY(String))
    display_order = Column(Integer)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)

# ============================================================================
# Health Check
# ============================================================================

@app.get("/api/health")
async def health_check():
    """Service health check endpoint"""
    try:
        # Verify database connection
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        return {
            "status": "healthy",
            "service": "ProductService",
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

# ============================================================================
# Product Search & Query APIs
# ============================================================================

@app.post("/api/products/search")
async def search_products(
    query: str = Body(..., embed=True),
    category: Optional[str] = Body(None, embed=True),
    filters: Optional[Dict[str, Any]] = Body(None, embed=True),
    limit: int = Body(20, embed=True),
    offset: int = Body(0, embed=True),
    db: Session = Depends(get_db)
):
    """
    Search products by keyword and optional filters
    
    Example:
    {
        "query": "laptop",
        "category": "electronics",
        "filters": {"price_max": 1000, "brand": "Dell"},
        "limit": 20,
        "offset": 0
    }
    """
    try:
        # Base query
        base_query = db.query(Product).filter(
            (Product.title.ilike(f"%{query}%")) |
            (Product.description.ilike(f"%{query}%"))
        )
        
        # Apply category filter
        if category:
            category_obj = db.query(Category).filter(
                Category.name.ilike(category)
            ).first()
            if category_obj:
                base_query = base_query.filter(Product.category_id == category_obj.id)
        
        # Apply additional filters
        if filters:
            if "brand" in filters:
                base_query = base_query.filter(Product.brand == filters["brand"])
            if "price_min" in filters or "price_max" in filters:
                sku_query = db.query(SKU).filter(SKU.product_id.in_(
                    base_query.with_entities(Product.product_id)
                ))
                if "price_min" in filters:
                    sku_query = sku_query.filter(SKU.price >= filters["price_min"])
                if "price_max" in filters:
                    sku_query = sku_query.filter(SKU.price <= filters["price_max"])
                
                valid_product_ids = [sku.product_id for sku in sku_query.all()]
                base_query = base_query.filter(Product.product_id.in_(valid_product_ids))
        
        # Get total count
        total = base_query.count()
        
        # Apply pagination
        products = base_query.offset(offset).limit(limit).all()
        
        return {
            "total": total,
            "limit": limit,
            "offset": offset,
            "products": [
                {
                    "product_id": p.tiki_product_id,
                    "spid": p.tiki_spid,  # ✅ Include spid in search results
                    "title": p.title,
                    "brand": p.brand,
                    "category_id": p.category_id,
                    "is_active": p.is_active,
                    "thumbnail": p.thumbnail,
                    "source": p.source
                }
                for p in products
            ]
        }
    except Exception as e:
        logger.error(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/products/{product_id}")
async def get_product(product_id: str):
    """Get product details by ID (tiki_product_id)"""
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.tiki_product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        skus = db.query(SKU).filter(SKU.product_id == product.id).all()
        
        return {
            "product_id": product.tiki_product_id,
            "spid": product.tiki_spid,  # ✅ Include spid in product details
            "title": product.title,
            "description": product.description,
            "brand": product.brand,
            "category_id": product.category_id,
            "thumbnail": product.thumbnail,
            "product_url": product.product_url,
            "source": product.source,
            "is_active": product.is_active,
            "skus": [
                {
                    "sku_code": sku.sku_code,
                    "price": sku.price,
                    "original_price": sku.original_price,
                    "stock": sku.stock,
                    "is_available": sku.is_available
                }
                for sku in skus
            ],
            "created_at": product.created_at.isoformat() if product.created_at else None
        }
    except Exception as e:
        logger.error(f"Get product failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/skus/{sku_id}")
async def get_sku(sku_id: str):
    """Get SKU details by code (sku_code from Tiki spid)"""
    db = SessionLocal()
    try:
        sku = db.query(SKU).filter(SKU.sku_code == sku_id).first()
        if not sku:
            raise HTTPException(status_code=404, detail="SKU not found")
        
        product = db.query(Product).filter(Product.id == sku.product_id).first()
        
        return {
            "sku_code": sku.sku_code,
            "product_id": product.tiki_product_id if product else None,
            "product_title": product.title if product else None,
            "price": sku.price,
            "original_price": sku.original_price,
            "stock": sku.stock,
            "is_available": sku.is_available
        }
    except Exception as e:
        logger.error(f"Get SKU failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Category APIs
# ============================================================================

@app.get("/api/categories")
async def list_categories():
    """List all product categories"""
    db = SessionLocal()
    try:
        categories = db.query(Category).filter(Category.is_active == True).all()
        return {
            "categories": [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "description": cat.description,
                    "type": cat.category_type
                }
                for cat in categories
            ]
        }
    except Exception as e:
        logger.error(f"List categories failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/categories/{category_id}")
async def get_category(category_id: int):
    """Get category details with attributes"""
    db = SessionLocal()
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        product_count = db.query(Product).filter(Product.category_id == category_id).count()
        
        return {
            "id": category.id,
            "name": category.name,
            "description": category.description,
            "type": category.category_type,
            "product_count": product_count,
            "is_active": category.is_active
        }
    except Exception as e:
        logger.error(f"Get category failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/categories")
async def create_category(
    body: Dict[str, Any] = Body(...)
):
    """
    Create new product category with attributes
    
    Request body:
    {
        "name": "Giày",
        "description": "Tất cả loại giày",
        "category_type": "footwear",
        "attributes": ["brand", "size", "color", "type", "material", "gender", "price_range"]
    }
    
    Returns:
    {
        "id": 1,
        "name": "Giày",
        "description": "...",
        "attributes_created": 7
    }
    """
    db = SessionLocal()
    try:
        category_name = body.get("name", "").strip()
        description = body.get("description", "").strip()
        category_type = body.get("category_type", "general")
        attributes = body.get("attributes", [])
        
        if not category_name:
            raise HTTPException(status_code=400, detail="Category name is required")
        
        # Generate slug from category name (removes diacritics, lowercase, hyphenated)
        category_slug = slugify(category_name)
        
        # Check if category already exists
        existing = db.query(Category).filter(
            Category.name.ilike(category_name)
        ).first()
        
        if existing:
            logger.warning(f"Category '{category_name}' already exists")
            return {
                "success": False,
                "id": existing.id,
                "name": existing.name,
                "reason": "Category already exists"
            }
        
        # Create new category
        new_category = Category(
            name=category_name,
            slug=category_slug,
            description=description,
            category_type=category_type,
            is_active=True
        )
        db.add(new_category)
        db.flush()  # Get the ID without committing
        
        category_id = new_category.id
        logger.info(f"✅ Created category '{category_name}' (id={category_id}, slug={category_slug})")
        
        # Save category_attributes if provided
        attributes_created = 0
        if attributes and len(attributes) > 0:
            logger.info(f"💾 Saving {len(attributes)} attributes for category '{category_name}'...")
            
            for idx, attr_name in enumerate(attributes, 1):
                try:
                    attr_name_clean = str(attr_name).strip()
                    
                    # Create category_attribute record
                    cat_attr = CategoryAttribute(
                        category_id=category_id,
                        attribute_name=attr_name_clean,
                        attribute_type="text",
                        is_filterable=True,
                        display_order=idx
                    )
                    db.add(cat_attr)
                    attributes_created += 1
                    logger.info(f"  ✅ Saved attribute #{idx}: '{attr_name_clean}'")
                except Exception as e:
                    logger.warning(f"  ⚠️  Failed to save attribute '{attr_name}': {str(e)}")
        
        db.commit()
        
        return {
            "success": True,
            "id": category_id,
            "name": category_name,
            "description": description,
            "type": category_type,
            "attributes_created": attributes_created
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Create category failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create category: {str(e)}")
    finally:
        db.close()


@app.get("/api/categories/{category_slug}/filters")
async def get_category_filters(category_slug: str):
    """
    Get available filters (attributes) for a category by slug
    
    Args:
        category_slug: Category slug (e.g., "giay", "dien-thoai")
    
    Returns:
    {
        "filters": [
            {
                "name": "brand",
                "display_name": "Thương hiệu",
                "type": "text",
                "values": ["Nike", "Adidas", ...]
            }
        ]
    }
    """
    db = SessionLocal()
    try:
        # Find category by slug
        category = db.query(Category).filter(
            Category.slug == category_slug
        ).first()
        
        # Fallback: if not found by slug, search all categories and match by slugified name
        if not category:
            logger.info(f"Slug '{category_slug}' not found, searching by name...")
            all_categories = db.query(Category).all()
            for cat in all_categories:
                if slugify(cat.name) == category_slug:
                    category = cat
                    logger.info(f"Matched category by name: {cat.name} → {category_slug}")
                    break
        
        if not category:
            logger.warning(f"Category not found: {category_slug}")
            raise HTTPException(status_code=404, detail=f"Category '{category_slug}' not found")
        
        # Update slug if missing (data migration)
        if not category.slug:
            category.slug = slugify(category.name)
            db.commit()
            logger.info(f"✅ Updated category '{category.name}' with slug: {category.slug}")
        
        # Query category attributes for this category using raw SQL
        # (fallback for different schema versions)
        try:
            result = db.execute(text("""
                SELECT id, category_id, attribute_name, 
                       COALESCE(attribute_type, 'text') as attribute_type,
                       is_filterable, values, display_order
                FROM category_attributes
                WHERE category_id = :category_id AND is_filterable = true
                ORDER BY COALESCE(display_order, 0)
            """), {"category_id": category.id})
            attributes = result.fetchall()
        except Exception as e:
            logger.warning(f"Raw SQL query failed, trying ORM: {e}")
            attributes = db.query(CategoryAttribute).filter(
                CategoryAttribute.category_id == category.id,
                CategoryAttribute.is_filterable == True
            ).order_by(CategoryAttribute.display_order).all()
        
        filters = []
        for attr in attributes:
            # Handle both tuple (raw query) and object (ORM) results
            if hasattr(attr, 'keys'):  # Row object from raw query
                filter_obj = {
                    "name": attr['attribute_name'],
                    "display_name": attr['attribute_name'],
                    "type": attr['attribute_type'] or "text",
                }
                if attr['values']:
                    filter_obj["values"] = list(attr['values'])
            else:  # ORM object
                filter_obj = {
                    "name": attr.attribute_name,
                    "display_name": attr.attribute_name,
                    "type": attr.attribute_type or "text",
                }
                if attr.values:
                    filter_obj["values"] = list(attr.values)
            filters.append(filter_obj)
        
        logger.info(f"✅ Retrieved {len(filters)} filters for category '{category.name}'")
        return {
            "category_id": category.id,
            "category_name": category.name,
            "filters": filters
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get category filters failed: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get filters: {str(e)}")
    finally:
        db.close()

# ============================================================================
# Product Save & Update APIs
# ============================================================================

@app.post("/api/products/batch")
async def save_products(
    body: Dict[str, Any] = Body(...)
):
    """
    Save/update products from crawler (e.g., Tiki scraper)
    
    Request body example:
    {
        "category_id": 5,               # ✅ REQUIRED: From RecommendationService
        "source": "tiki",
        "products": [
            {
                "product_id": "276183351",      # From crawler (product ID)
                "title": "Giày thể thao nam...", # From crawler (title)
                "brand": "BEE GEE",
                "price": 620000,                # Selling price
                "discount": 50,                 # Discount percentage
                "spid": "276183355",            # From crawler (SKU ID)
                "image": "https://...",         # Product thumbnail
                "link": "https://tiki.vn/..."   # Product URL
            }
        ]
    }
    """
    products = body.get("products", [])
    source = body.get("source", "crawler")
    category_id = body.get("category_id")  # ✅ Extract from request body
    
    # Validate category_id is provided
    if not category_id:
        logger.error("❌ category_id is required in request body")
        raise HTTPException(
            status_code=400, 
            detail="category_id is required in request body"
        )
    db = SessionLocal()
    try:
        saved = 0
        updated = 0
        errors = []
        
        for product_data in products:
            try:
                # Validate required fields
                product_id = product_data.get("product_id")
                title = product_data.get("title") or product_data.get("name")
                
                if not product_id or str(product_id).strip() == "":
                    errors.append({
                        "product_id": product_id, 
                        "error": "product_id is required"
                    })
                    logger.warning(f"Skipping product without product_id")
                    continue
                
                if not title:
                    errors.append({
                        "product_id": product_id,
                        "error": "title is required"
                    })
                    logger.warning(f"Skipping product {product_id}: missing title")
                    continue
                
                # Check if product exists by tiki_product_id
                product = db.query(Product).filter(
                    Product.tiki_product_id == str(product_id)
                ).first()
                
                if product:
                    # Update existing product
                    product.title = title
                    product.brand = product_data.get("brand", product.brand)
                    product.description = product_data.get("description", product.description)
                    product.thumbnail = product_data.get("image", product.thumbnail)
                    product.product_url = product_data.get("link", product.product_url)
                    product.tiki_spid = product_data.get("spid", product.tiki_spid)  # ✅ Update spid too
                    product.updated_at = datetime.utcnow()
                    db.flush()
                    updated += 1
                    logger.info(f"✏️ Updated product: {product_id}")
                else:
                    # Create new product
                    product = Product(
                        tiki_product_id=str(product_id),
                        tiki_spid=product_data.get("spid"),  # ✅ IMPORTANT: Save spid here too
                        category_id=category_id,
                        title=title,
                        brand=product_data.get("brand"),
                        description=product_data.get("description"),
                        thumbnail=product_data.get("image"),
                        product_url=product_data.get("link"),
                        source=source,
                        seller_id=product_data.get("seller_id", "1"),
                        is_active=True
                    )
                    db.add(product)
                    db.flush()  # Flush to get product.id
                    saved += 1
                    logger.info(f"✅ Created product: {product_id}")
                
                # Add/Update SKU if price info provided
                if "price" in product_data and product.id:
                    spid = product_data.get("spid", str(product_id))
                    sku = db.query(SKU).filter(SKU.sku_code == str(spid)).first()
                    
                    price = float(product_data.get("price", 0))
                    discount_percent = float(product_data.get("discount", 0))
                    
                    # Calculate original price if discount is provided
                    original_price = None
                    if discount_percent > 0:
                        original_price = price / (1 - discount_percent / 100)
                    
                    if sku:
                        # Update existing SKU
                        sku.price = price
                        sku.original_price = original_price
                        sku.stock = product_data.get("stock", sku.stock)
                        sku.is_available = product_data.get("is_available", True)
                        sku.updated_at = datetime.utcnow()
                        logger.info(f"✏️ Updated SKU: {spid}")
                    else:
                        # Create new SKU
                        sku = SKU(
                            product_id=product.id,  # Use product.id (INTEGER FK)
                            sku_code=str(spid),
                            price=price,
                            original_price=original_price,
                            stock=product_data.get("stock", 0),
                            is_available=product_data.get("is_available", True)
                        )
                        db.add(sku)
                        logger.info(f"✅ Created SKU: {spid}")
                
            except Exception as e:
                error_msg = str(e)
                errors.append({
                    "product_id": product_data.get("product_id"),
                    "error": error_msg
                })
                logger.error(f"❌ Error saving product {product_data.get('product_id')}: {error_msg}")
        
        db.commit()
        logger.info(f"Batch save completed: {saved} saved, {updated} updated, {len(errors)} errors")
        
        return {
            "saved": saved,
            "updated": updated,
            "errors": errors,
            "total": saved + updated + len(errors)
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Batch save failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/api/products/{product_id}")
async def update_product(product_id: str, update_data: Dict[str, Any] = Body(...)):
    """Update single product by tiki_product_id"""
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.tiki_product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Allow updating certain fields only
        allowed_fields = ["title", "brand", "description", "thumbnail", "product_url", "is_active"]
        for key, value in update_data.items():
            if key in allowed_fields and hasattr(product, key):
                setattr(product, key, value)
        
        product.updated_at = datetime.utcnow()
        db.commit()
        
        return {"status": "updated", "product_id": product_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Update product failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/api/skus/{sku_id}/price")
async def update_sku_price(sku_id: str, price: float = Body(..., embed=True), stock: Optional[int] = Body(None, embed=True), original_price: Optional[float] = Body(None, embed=True)):
    """Update SKU price and optional stock by sku_code"""
    db = SessionLocal()
    try:
        sku = db.query(SKU).filter(SKU.sku_code == sku_id).first()
        if not sku:
            raise HTTPException(status_code=404, detail="SKU not found")
        
        sku.price = price
        if stock is not None:
            sku.stock = stock
        if original_price is not None:
            sku.original_price = original_price
        sku.updated_at = datetime.utcnow()
        
        db.commit()
        
        return {"status": "updated", "sku_code": sku_id, "new_price": price}
    except Exception as e:
        db.rollback()
        logger.error(f"Update SKU price failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Startup and Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize service on startup"""
    logger.info("ProductService starting up...")
    try:
        # Verify database connection
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        logger.info("Database connection verified")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on service shutdown"""
    logger.info("ProductService shutting down...")
    engine.dispose()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        log_level="info"
    )
