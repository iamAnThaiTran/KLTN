"""
ProductService - Microservice for product catalog management
Port: 8001

Handles:
- Product search and filtering
- Product and SKU management
- Category attribute configuration
"""

from fastapi import FastAPI, HTTPException, Query, Body, Depends, Request
import logging
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker, Session
import os
from datetime import datetime
import unicodedata
import re
import json
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# ============================================================================
# Pydantic Models (Request/Response)
# ============================================================================

class AddCategoryAttributesRequest(BaseModel):
    """Request model for adding category attributes"""
    attributes: List[str] = Field(..., description="List of attribute names to add")
    
    class Config:
        json_schema_extra = {
            "example": {
                "attributes": ["khả năng chống nước", "tính năng mới"]
            }
        }

class SyncSKUAttributesRequest(BaseModel):
    """Request model for syncing SKU attributes"""
    attributes: List[str] = Field(..., description="List of attributes to sync")
    only_missing: bool = Field(True, description="Only add missing attributes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "attributes": ["khả năng chống nước"],
                "only_missing": True
            }
        }

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
    schema_version = Column(Integer, default=1)
    last_updated_attributes = Column(TIMESTAMP, default=datetime.utcnow)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow)

class Product(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True)
    category_id = Column(Integer, nullable=False)  # Required!
    title = Column(String(500), nullable=False)  # Changed from 'name'
    brand = Column(String(500))
    description = Column(Text)
    product_url = Column(String(500))  # From crawler link
    thumbnail = Column(String(500))  # From crawler image
    source = Column(String(50))  # tiki, lazada, shopee
    tiki_product_id = Column(String(100))  # From crawler product_id
    tiki_spid = Column(String(100))  # From crawler spid
    seller_id = Column(String(100), default='1')
    is_active = Column(Boolean, default=True)  # Changed from is_available
    last_schema_version = Column(Integer, default=1)
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
    search_count = Column(Integer, default=0)  # Track search popularity
    rating = Column(Float, default=0)  # Product rating 0-5
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

class ProductCategory(Base):
    """Many-to-Many relationship between products and categories"""
    __tablename__ = "product_categories"
    id = Column(Integer, primary_key=True)
    product_id = Column(Integer, nullable=False)
    category_id = Column(Integer, nullable=False)
    is_primary = Column(Boolean, default=False)
    added_at = Column(TIMESTAMP, default=datetime.utcnow)

class SKUAttribute(Base):
    """Flexible attribute storage for SKUs (variants)"""
    __tablename__ = "sku_attributes"
    sku_id = Column(Integer, primary_key=True)
    attribute_name = Column(String(100), primary_key=True)
    attribute_value = Column(Text, nullable=False, default="")

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
                    "id": p.id,  # ✅ Internal database ID for React keys
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
        logger.info(f"✅ Retrieved {len(categories)} active categories")
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
            logger.info(f"✅ Category '{category_name}' already exists (id={existing.id})")
            return {
                "success": True,
                "id": existing.id,
                "name": existing.name,
                "description": existing.description,
                "type": existing.category_type,
                "reason": "Category already exists",
                "attributes_created": 0
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
    
    ✅ FIXED: Lấy giá trị thực từ sku_attributes (không từ category_attributes.values)
    - Lấy danh sách attribute names từ category_attributes
    - Lấy giá trị thực từ sku_attributes của các SKU trong category
    """
    db = SessionLocal()
    try:
        logger.info(f"🔍 get_category_filters called with slug: '{category_slug}'")
        
        # Find category by slug
        category = db.query(Category).filter(
            Category.slug == category_slug
        ).first()
        
        logger.info(f"Query by slug result: {category}")
        
        # Fallback: if not found by slug, search all categories and match by slugified name
        if not category:
            logger.info(f"Slug '{category_slug}' not found, searching by name...")
            all_categories = db.query(Category).all()
            logger.info(f"Found {len(all_categories)} total categories")
            for cat in all_categories:
                if slugify(cat.name) == category_slug:
                    category = cat
                    logger.info(f"Matched category by name: {cat.name} → {category_slug}")
                    break
        
        if not category:
            logger.warning(f"Category not found: {category_slug}")
            raise HTTPException(status_code=404, detail=f"Category '{category_slug}' not found")
        
        logger.info(f"✅ Found category: id={category.id}, name={category.name}, slug={category.slug}")
        
        # Update slug if missing (data migration)
        if not category.slug:
            category.slug = slugify(category.name)
            db.commit()
            logger.info(f"✅ Updated category '{category.name}' with slug: {category.slug}")
        
        # Query category attributes for this category
        logger.info(f"Querying attributes for category_id={category.id}...")
        category_attrs = db.query(CategoryAttribute).filter(
            CategoryAttribute.category_id == category.id,
            CategoryAttribute.is_filterable == True
        ).order_by(CategoryAttribute.display_order).all()
        
        logger.info(f"Found {len(category_attrs)} category attributes")
        
        filters = []
        
        # For each category attribute, get actual values from sku_attributes
        for attr_def in category_attrs:
            logger.info(f"Processing attribute: {attr_def.attribute_name}")
            
            # Get all products in this category
            products_in_category = db.query(Product.id).filter(
                Product.category_id == category.id
            ).all()
            product_ids = [p[0] for p in products_in_category]
            
            if not product_ids:
                logger.info(f"  No products in category {category.id}")
                filters.append({
                    "name": attr_def.attribute_name,
                    "display_name": attr_def.attribute_name,
                    "type": attr_def.attribute_type or "text",
                    "values": []
                })
                continue
            
            # Get all SKUs for products in this category
            skus_in_category = db.query(SKU.id).filter(
                SKU.product_id.in_(product_ids)
            ).all()
            sku_ids = [s[0] for s in skus_in_category]
            
            if not sku_ids:
                logger.info(f"  No SKUs in category {category.id}")
                filters.append({
                    "name": attr_def.attribute_name,
                    "display_name": attr_def.attribute_name,
                    "type": attr_def.attribute_type or "text",
                    "values": []
                })
                continue
            
            # Get distinct values of this attribute from sku_attributes
            # ✅ Lấy giá trị thực từ sku_attributes (không từ category_attributes.values)
            distinct_values = db.query(SKUAttribute.attribute_value).filter(
                SKUAttribute.sku_id.in_(sku_ids),
                SKUAttribute.attribute_name == attr_def.attribute_name
            ).distinct().all()
            
            values = [v[0] for v in distinct_values if v[0]]  # Remove None/empty values
            values = sorted(list(set(values)))  # Remove duplicates and sort
            
            logger.info(f"  Found {len(values)} distinct values for '{attr_def.attribute_name}': {values[:5]}{'...' if len(values) > 5 else ''}")
            
            filter_obj = {
                "name": attr_def.attribute_name,
                "display_name": attr_def.attribute_name,
                "type": attr_def.attribute_type or "text",
                "values": values
            }
            filters.append(filter_obj)
            logger.info(f"  ✅ Added filter: {filter_obj['name']} with {len(values)} values")
        
        logger.info(f"✅ Retrieved {len(filters)} filters for category '{category.name}'")
        return {
            "category_id": category.id,
            "category_name": category.name,
            "filters": filters
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get category filters failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get filters: {str(e)}")
    finally:
        db.close()

# ============================================================================
# Schema Evolution APIs (NEW)
# ============================================================================

@app.get("/api/categories/{category_id}/details")
async def get_category_details(category_id: int):
    """
    Get category details with all attributes and schema information
    
    Returns:
    {
        "id": 5,
        "name": "Laptop",
        "slug": "laptop",
        "description": "Máy tính xách tay",
        "category_type": "electronics",
        "schema_version": 2,
        "last_updated_attributes": "2026-05-13T...",
        "attributes": [
            {
                "id": 1,
                "attribute_name": "brand",
                "attribute_type": "text",
                "is_filterable": true,
                "display_order": 1
            },
            ...
        ]
    }
    """
    db = SessionLocal()
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Get all attributes for this category
        attributes = db.query(CategoryAttribute).filter(
            CategoryAttribute.category_id == category_id
        ).order_by(CategoryAttribute.display_order).all()
        
        return {
            "id": category.id,
            "name": category.name,
            "slug": category.slug,
            "description": category.description,
            "category_type": category.category_type,
            "schema_version": category.schema_version,
            "last_updated_attributes": category.last_updated_attributes.isoformat() if category.last_updated_attributes else None,
            "attributes": [
                {
                    "id": attr.id,
                    "attribute_name": attr.attribute_name,
                    "attribute_type": attr.attribute_type or "text",
                    "is_filterable": attr.is_filterable,
                    "display_order": attr.display_order or 0
                }
                for attr in attributes
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get category details failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.put("/api/categories/{category_id}/attributes")
async def add_category_attributes(category_id: int, request: AddCategoryAttributesRequest):
    """
    Add (append) new attributes to an existing category
    
    Request body:
    {
        "attributes": ["khả năng chống nước", "tính năng mới"]
    }
    
    Response:
    {
        "success": true,
        "category_id": 5,
        "attributes_added": ["khả năng chống nước", "tính năng mới"],
        "attributes_count": 5,
        "products_synced": 1250,
        "schema_version": 3
    }
    """
    db = SessionLocal()
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        new_attributes = request.attributes if request.attributes else []
        if not new_attributes:
            return {
                "success": False,
                "category_id": category_id,
                "attributes_added": [],
                "reason": "No attributes provided"
            }
        
        # Get existing attributes (normalize for comparison)
        existing_attrs = db.query(CategoryAttribute).filter(
            CategoryAttribute.category_id == category_id
        ).all()
        existing_names = {attr.attribute_name.lower().strip() for attr in existing_attrs}
        
        # Find new attributes (avoid duplicates)
        attrs_to_add = []
        for attr in new_attributes:
            attr_clean = str(attr).strip()
            if attr_clean.lower() not in existing_names:
                attrs_to_add.append(attr_clean)
                existing_names.add(attr_clean.lower())
        
        if not attrs_to_add:
            logger.info(f"No new attributes to add for category {category_id}")
            return {
                "success": True,
                "category_id": category_id,
                "attributes_added": [],
                "attributes_count": len(existing_attrs),
                "products_synced": 0,
                "schema_version": category.schema_version,
                "reason": "All attributes already exist"
            }
        
        # Add new attributes
        max_order = max([attr.display_order or 0 for attr in existing_attrs]) if existing_attrs else 0
        
        for idx, attr_name in enumerate(attrs_to_add, 1):
            cat_attr = CategoryAttribute(
                category_id=category_id,
                attribute_name=attr_name,
                attribute_type="text",
                is_filterable=True,
                display_order=max_order + idx
            )
            db.add(cat_attr)
        
        # Update category schema version
        category.schema_version += 1
        category.last_updated_attributes = datetime.utcnow()
        
        db.commit()
        
        logger.info(f"✅ Added {len(attrs_to_add)} attributes to category {category_id}")
        
        return {
            "success": True,
            "category_id": category_id,
            "attributes_added": attrs_to_add,
            "attributes_count": len(existing_attrs) + len(attrs_to_add),
            "products_synced": 0,  # Will be updated by sync endpoint
            "schema_version": category.schema_version
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Add category attributes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/categories/{category_id}/sync-sku-attributes")
async def sync_sku_attributes(category_id: int, request: SyncSKUAttributesRequest):
    """
    Sync SKU attributes for all products in a category
    Add missing attributes with empty values (user can fill in later)
    
    Request body:
    {
        "attributes": ["khả năng chống nước"],
        "only_missing": true
    }
    
    Response:
    {
        "success": true,
        "category_id": 5,
        "products_synced": 1250,
        "sku_attributes_added": 1250
    }
    """
    db = SessionLocal()
    try:
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        attributes = request.attributes if request.attributes else []
        only_missing = request.only_missing
        
        if not attributes:
            return {
                "success": False,
                "category_id": category_id,
                "products_synced": 0,
                "sku_attributes_added": 0,
                "reason": "No attributes provided"
            }
        
        # Get all products in this category
        products = db.query(Product).filter(Product.category_id == category_id).all()
        
        if not products:
            logger.info(f"No products found in category {category_id}")
            return {
                "success": True,
                "category_id": category_id,
                "products_synced": 0,
                "sku_attributes_added": 0,
                "reason": "No products in category"
            }
        
        # For each product, get its SKUs and add missing attributes
        total_synced = 0
        total_attrs_added = 0
        
        for product in products:
            skus = db.query(SKU).filter(SKU.product_id == product.id).all()
            
            for sku in skus:
                # Get existing attributes for this SKU using ORM
                existing_attrs = db.query(SKUAttribute).filter(
                    SKUAttribute.sku_id == sku.id
                ).all()
                existing_names = {attr.attribute_name.lower() for attr in existing_attrs}
                
                # Add missing attributes
                for attr in attributes:
                    attr_clean = str(attr).strip()
                    if attr_clean.lower() not in existing_names:
                        # Create new SKU attribute with empty value
                        sku_attr = SKUAttribute(
                            sku_id=sku.id,
                            attribute_name=attr_clean,
                            attribute_value=""  # Empty value - user can fill in later
                        )
                        db.add(sku_attr)
                        total_attrs_added += 1
                        existing_names.add(attr_clean.lower())
                        logger.debug(f"  Added attribute '{attr_clean}' to SKU {sku.id}")
            
            total_synced += 1
        
        db.commit()
        
        logger.info(f"✅ Synced {total_synced} products, added {total_attrs_added} attribute entries")
        
        return {
            "success": True,
            "category_id": category_id,
            "products_synced": total_synced,
            "sku_attributes_added": total_attrs_added
        }
    
    except Exception as e:
        db.rollback()
        logger.error(f"Sync SKU attributes failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/products/{product_id}/add-category")
async def add_product_to_category(product_id: str, body: Dict[str, Any] = Body(...)):
    """
    Add a product to an additional category (many-to-many)
    
    Request body:
    {
        "category_id": 10,
        "is_primary": false
    }
    
    Response:
    {
        "success": true,
        "product_id": 123,
        "category_id": 10,
        "categories": [5, 10],
        "message": "Product added to category"
    }
    """
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.tiki_product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        category_id = body.get("category_id")
        is_primary = body.get("is_primary", False)
        
        if not category_id:
            raise HTTPException(status_code=400, detail="category_id is required")
        
        # Verify category exists
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")
        
        # Check if product-category mapping already exists
        existing = db.query(ProductCategory).filter(
            ProductCategory.product_id == product.id,
            ProductCategory.category_id == category_id
        ).first()
        
        if existing:
            logger.warning(f"Product {product_id} already belongs to category {category_id}")
            return {
                "success": False,
                "product_id": product.id,
                "category_id": category_id,
                "reason": "Product already belongs to this category"
            }
        
        # Add product to category
        product_cat = ProductCategory(
            product_id=product.id,
            category_id=category_id,
            is_primary=is_primary
        )
        db.add(product_cat)
        db.commit()
        
        # Get all categories for this product
        categories = db.query(ProductCategory.category_id).filter(
            ProductCategory.product_id == product.id
        ).all()
        
        logger.info(f"✅ Product {product_id} added to category {category_id}")
        
        return {
            "success": True,
            "product_id": product.id,
            "category_id": category_id,
            "categories": [cat[0] for cat in categories],
            "message": "Product added to category successfully"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Add product to category failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.get("/api/products/{product_id}/categories")
async def get_product_categories(product_id: str):
    """
    Get all categories for a product (many-to-many)
    
    Response:
    {
        "product_id": 123,
        "categories": [
            {
                "id": 5,
                "name": "Laptop",
                "is_primary": true
            },
            {
                "id": 10,
                "name": "Thiết bị công nghệ",
                "is_primary": false
            }
        ]
    }
    """
    db = SessionLocal()
    try:
        product = db.query(Product).filter(Product.tiki_product_id == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        # Get all categories for this product
        categories = db.query(ProductCategory, Category).join(
            Category, ProductCategory.category_id == Category.id
        ).filter(
            ProductCategory.product_id == product.id
        ).all()
        
        return {
            "product_id": product.id,
            "categories": [
                {
                    "id": cat.id,
                    "name": cat.name,
                    "is_primary": prod_cat.is_primary
                }
                for prod_cat, cat in categories
            ]
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get product categories failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

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
        
        return {"status": "updated", "sku_id": sku_id}
    except Exception as e:
        db.rollback()
        logger.error(f"Update SKU price failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

@app.post("/api/skus/{sku_code}/attributes")
async def save_sku_attributes(sku_code: str, body: Dict[str, Any] = Body(...)):
    """
    Save/update attributes for a specific SKU
    
    Args:
        sku_code: SKU code (e.g., spid from Tiki)
        body: {
            "attributes": {
                "RAM": "8GB",
                "CPU": "Intel i5",
                "Storage": "512GB SSD",
                ...
            }
        }
    
    Returns:
        {
            "status": "saved",
            "sku_code": "...",
            "attributes_count": 3
        }
    """
    db = SessionLocal()
    try:
        # Find SKU by sku_code
        sku = db.query(SKU).filter(SKU.sku_code == sku_code).first()
        if not sku:
            logger.warning(f"SKU not found: {sku_code}")
            raise HTTPException(status_code=404, detail=f"SKU not found: {sku_code}")
        
        attributes = body.get("attributes", {})
        if not attributes:
            return {
                "status": "no_attributes",
                "sku_code": sku_code,
                "message": "No attributes provided"
            }
        
        # Delete existing attributes first
        from sqlalchemy import text as sql_text
        db.execute(
            sql_text("DELETE FROM sku_attributes WHERE sku_id = :sku_id"),
            {"sku_id": sku.id}
        )
        
        # Insert new attributes
        for attr_name, attr_value in attributes.items():
            # Convert value to string if it's a list or dict
            if isinstance(attr_value, (list, dict)):
                attr_value = json.dumps(attr_value, ensure_ascii=False)
            else:
                attr_value = str(attr_value)
            
            db.execute(
                sql_text("""
                    INSERT INTO sku_attributes (sku_id, attribute_name, attribute_value)
                    VALUES (:sku_id, :attr_name, :attr_value)
                """),
                {
                    "sku_id": sku.id,
                    "attr_name": str(attr_name),
                    "attr_value": attr_value
                }
            )
        
        sku.updated_at = datetime.utcnow()
        db.commit()
        
        logger.info(f"✅ Saved {len(attributes)} attributes for SKU: {sku_code}")
        
        return {
            "status": "saved",
            "sku_code": sku_code,
            "attributes_count": len(attributes)
        }
    
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error saving SKU attributes: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Product Query by Category & Attributes (for Recommender Service)
# ============================================================================

@app.post("/api/products/query-by-category")
async def query_products_by_category(
    body: Dict[str, Any] = Body(...)
):
    """
    Query products by category_id + optional attributes/filters
    
    ✅ STRATEGY: Return products with attributes, let Recommender rank
    
    Called by Recommender Service to get products for a category.
    - Applies STRICT filtering: brand, price range only (DB-level)
    - Returns ALL matching products + their attributes
    - Recommender Service ranks by attribute match score
    - UI always has products to display (even if not exact attribute match)
    
    Request body:
    {
        "category_id": 5,
        "attributes": {
            "brand": "Nike",
            "color": "đen",              ← Not filtered in DB
            "size": "42",                ← Not filtered in DB
            "price_min": 1000000,        ← Filtered in DB
            "price_max": 5000000,        ← Filtered in DB
            ...
        },
        "limit": 50
    }
    
    Returns:
    {
        "products": [
            {
                "id": 123,
                "product_id": "276183351",
                "spid": "276183355",
                "title": "Giày thể thao nam...",
                "brand": "Nike",
                "price": 620000,
                "original_price": 1000000,
                "stock": 10,
                "thumbnail": "https://...",
                "category_id": 5,
                "rating": 4.5,
                "search_count": 150,
                "attributes": [           ← ✅ For Recommender to rank
                    {"name": "color", "value": "đen"},
                    {"name": "size", "value": "42"},
                    {"name": "material", "value": "da"}
                ],
                ...
            },
            ...
        ]
    }
    """
    db = SessionLocal()
    try:
        from sqlalchemy import text as sql_text
        
        category_id = body.get("category_id")
        attributes = body.get("attributes", {})
        limit = body.get("limit", 50)
        
        if not category_id:
            logger.warning("❌ category_id is required")
            raise HTTPException(status_code=400, detail="category_id is required")
        
        # Verify category exists
        category = db.query(Category).filter(Category.id == category_id).first()
        if not category:
            logger.warning(f"❌ Category {category_id} not found")
            return {"products": []}  # Return empty list - will trigger crawl
        
        logger.info(f"🔍 Querying products: category={category.name} (id={category_id}), attributes={attributes}")
        
        # Identify which attributes are dynamic (stored in sku_attributes table)
        # vs fixed (brand, price, etc.) - for logging purposes
        dynamic_attribute_filters = {}
        
        # Start with products in this category
        query = db.query(Product, SKU).join(
            SKU, Product.id == SKU.product_id
        ).filter(
            Product.category_id == category_id
        )
        
        # Apply attribute filters
        
        # Filter by brand if provided
        if "brand" in attributes and attributes["brand"]:
            brand_filter = attributes["brand"]
            if isinstance(brand_filter, list):
                query = query.filter(Product.brand.in_(brand_filter))
            else:
                query = query.filter(Product.brand == brand_filter)
            logger.info(f"  Applied brand filter: {brand_filter}")
        
        # Filter by price range
        price_min = attributes.get("price_min")
        price_max = attributes.get("price_max")
        
        # Handle alternative price keys: 'gia', 'price', 'price_range'
        if not price_min and not price_max:
            for price_key in ["gia", "price", "price_range"]:
                if price_key in attributes:
                    price_value = attributes[price_key]
                    if isinstance(price_value, list) and price_value:
                        if isinstance(price_value[0], dict):
                            price_min = price_value[0].get("min", price_min)
                            price_max = price_value[0].get("max", price_max)
                    elif isinstance(price_value, dict):
                        price_min = price_value.get("min", price_min)
                        price_max = price_value.get("max", price_max)
        
        if price_min is not None or price_max is not None:
            if price_min and price_max:
                query = query.filter(SKU.price.between(price_min, price_max))
                logger.info(f"  Applied price filter: {price_min}-{price_max}")
            elif price_min:
                query = query.filter(SKU.price >= price_min)
                logger.info(f"  Applied min price filter: >= {price_min}")
            elif price_max:
                query = query.filter(SKU.price <= price_max)
                logger.info(f"  Applied max price filter: <= {price_max}")
        
        # Collect dynamic attribute filters for logging (not for DB filtering)
        # Recommender Service will use these to rank products by attribute match
        for attr_name, attr_value in attributes.items():
            if attr_name not in ["brand", "price_min", "price_max", "gia", "price", "price_range"] and attr_value:
                dynamic_attribute_filters[attr_name] = attr_value
        
        # Execute query and get results (only apply brand/price filters)
        # Don't filter by other attributes here - let Recommender Service rank by match score
        results = query.order_by(SKU.id).limit(limit).all()
        
        if not results:
            logger.info(f"✅ No products found in DB for category {category.name}")
            return {"products": []}  # Return empty list - will trigger crawl
        
        # Extract SKU IDs to fetch attributes
        sku_ids = [sku.id for product, sku in results]
        
        # Fetch all attributes for these SKUs
        sku_attributes_raw = db.query(SKUAttribute).filter(
            SKUAttribute.sku_id.in_(sku_ids)
        ).all()
        
        # Organize attributes by SKU ID
        sku_attrs_map = {}
        for attr in sku_attributes_raw:
            if attr.sku_id not in sku_attrs_map:
                sku_attrs_map[attr.sku_id] = []
            sku_attrs_map[attr.sku_id].append({
                "name": attr.attribute_name,
                "value": attr.attribute_value
            })
        
        # Format all results with attributes
        # Recommender Service will handle ranking based on requested attributes
        products_list = []
        for product, sku in results:
            # Get attributes for this SKU
            attrs = sku_attrs_map.get(sku.id, [])
            
            products_list.append({
                "id": product.id,
                "product_id": product.tiki_product_id,
                "spid": product.tiki_spid,
                "title": product.title,
                "brand": product.brand,
                "price": float(sku.price),
                "original_price": float(sku.original_price) if sku.original_price else None,
                "stock": sku.stock,
                "is_available": sku.is_available,
                "thumbnail": product.thumbnail,
                "product_url": product.product_url,
                "category_id": product.category_id,
                "source": product.source,
                "rating": float(sku.rating) if sku.rating else 0,
                "search_count": sku.search_count or 0,
                "attributes": attrs  # ✅ Include SKU attributes for Recommender to rank
            })
        
        # Log requested attributes for reference (Recommender will rank by these)
        if dynamic_attribute_filters:
            logger.info(f"  📊 Requested attribute filters (for Recommender ranking): {dynamic_attribute_filters}")
        
        logger.info(f"✅ Found {len(products_list)} products in DB with attributes (Recommender will rank by requested filters)")
        return {"products": products_list}
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query products by category failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# ============================================================================
# Recommendations APIs
# ============================================================================

@app.get("/api/recommendations/homepage")
async def get_homepage_recommendations(
    request: Request,
    limit: int = 20
):
    """
    Get homepage recommendations - main orchestration endpoint.
    
    Microservices Flow:
    - API Gateway routes here with/without Authorization header
    
    Authenticated User (has Authorization header):
    1. Forward Authorization header to User Service
    2. User Service validates token and returns criteria
    3. Call /api/recommendations/by-criteria with criteria
    4. Return personalized products
    
    Non-Authenticated User (no Authorization header):
    1. Call /api/recommendations/public
    2. Return trending products
    """
    db = SessionLocal()
    try:
        # Check for Authorization header
        auth_header = request.headers.get("Authorization", "")
        
        if auth_header and auth_header.startswith("Bearer "):
            # Authenticated user - get personalized recommendations
            try:
                import httpx
                import os
                
                user_service_url = os.getenv("USER_SERVICE_URL", "http://user-service:8000")
                
                # Call User Service to get recommendation criteria
                # Pass Authorization header for token validation
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.get(
                        f"{user_service_url}/api/users/me/recommendation-criteria",
                        headers={
                            "Accept": "application/json",
                            "Authorization": auth_header
                        }
                    )
                    
                    if response.status_code == 200:
                        criteria_data = response.json()
                        criteria = criteria_data.get("criteria", {})
                        has_history = criteria_data.get("has_history", False)
                        
                        if has_history and (criteria.get("top_categories") or criteria.get("top_brands")):
                            # Query products by criteria
                            logger.info(f"[get_homepage_recommendations] Returning personalized recommendations")
                            return await get_recommendations_by_criteria(
                                criteria=criteria,
                                limit=limit
                            )
                    
                    logger.warning(f"[get_homepage_recommendations] User Service returned {response.status_code}")
            except httpx.TimeoutException:
                logger.warning(f"[get_homepage_recommendations] User Service timeout")
            except httpx.ConnectError as e:
                logger.warning(f"[get_homepage_recommendations] User Service connection error: {e}")
            except Exception as e:
                logger.warning(f"[get_homepage_recommendations] Failed to call User Service: {e}")
            
            # If we reach here, fallback to public recommendations
            logger.info(f"[get_homepage_recommendations] Falling back to public recommendations")
            return await get_public_recommendations(limit=limit)
        else:
            # Non-authenticated user - get trending recommendations
            logger.info(f"[get_homepage_recommendations] Non-authenticated user - returning trending")
            return await get_public_recommendations(limit=limit)
            
    except Exception as e:
        logger.error(f"[get_homepage_recommendations] Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "products": [],
            "recommendation_type": "error"
        }
    finally:
        db.close()

@app.get("/api/recommendations/public")
async def get_public_recommendations(limit: int = 20):
    """
    Get public/trending recommendations for non-authenticated users.
    
    Returns trending products sorted by search_count and rating.
    Joins SKU with Product and Category to get complete product info.
    
    Returns:
    {
        "status": "success",
        "products": [...],
        "recommendation_type": "trending",
        "popular_categories": [...],
        "popular_brands": [...],
        "total_products": 20,
        "message": "Recommended products based on trending/popularity"
    }
    """
    db = SessionLocal()
    try:
        from sqlalchemy import desc, func
        
        # Query trending products by search_count and rating (with JOINs)
        trending_results = db.query(SKU, Product, Category).join(
            Product, SKU.product_id == Product.id
        ).join(
            Category, Product.category_id == Category.id
        ).order_by(
            desc(SKU.search_count),
            desc(SKU.rating),
            desc(SKU.created_at)
        ).limit(limit).all()
        
        # Handle empty results
        if not trending_results:
            logger.warning(f"[get_public_recommendations] No products found in database")
            return {
                "status": "success",
                "products": [],
                "recommendation_type": "trending",
                "popular_categories": [],
                "popular_brands": [],
                "total_products": 0,
                "message": "No products available yet. Please add products to the catalog."
            }
        
        products_data = [
            {
                "id": product.id,  # ✅ Use Product ID, not SKU ID
                "sku_code": sku.sku_code,
                "product_id": product.tiki_product_id,
                "title": product.title,
                "price": float(sku.price),
                "original_price": float(sku.original_price) if sku.original_price else 0,
                "brand": product.brand or "Unknown",
                "category": category.name or "Other",
                "thumbnail": product.thumbnail,
                "rating": float(sku.rating) if sku.rating else 0,
                "search_count": sku.search_count or 0,
                "stock": sku.stock
            }
            for sku, product, category in trending_results
        ]
        
        # Get popular categories by counting products
        popular_categories = db.query(
            Category.name,
            func.count(SKU.id).label('count')
        ).join(
            Product, Category.id == Product.category_id
        ).join(
            SKU, Product.id == SKU.product_id
        ).group_by(Category.name).order_by(
            desc('count')
        ).limit(5).all()
        
        # Get popular brands by counting products
        popular_brands = db.query(
            Product.brand,
            func.count(SKU.id).label('count')
        ).join(
            SKU, Product.id == SKU.product_id
        ).filter(
            Product.brand.isnot(None)
        ).group_by(Product.brand).order_by(
            desc('count')
        ).limit(5).all()
        
        return {
            "status": "success",
            "products": products_data,
            "recommendation_type": "trending",
            "popular_categories": [cat[0] for cat in popular_categories],
            "popular_brands": [brand[0] for brand in popular_brands],
            "total_products": len(products_data),
            "message": f"Showing {len(products_data)} trending products"
        }
    except Exception as e:
        logger.error(f"[get_public_recommendations] Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "products": [],
            "recommendation_type": "error",
            "popular_categories": [],
            "popular_brands": [],
            "total_products": 0
        }
    finally:
        db.close()

@app.post("/api/recommendations/by-criteria")
async def get_recommendations_by_criteria(
    criteria: Dict[str, Any] = Body(...),
    limit: int = 20
):
    """
    Get product recommendations based on criteria.
    
    This endpoint is called by Recommender Service after User Service builds criteria.
    Joins SKU with Product and Category to apply filters and get complete info.
    
    Request:
    {
        "top_categories": ["Giày", "Đồng hồ"],
        "top_brands": ["Nike", "Apple"],
        "keywords": ["chạy bộ"],
        "price_range": {"min": 1000000, "max": 50000000}
    }
    
    Returns:
    {
        "status": "success",
        "products": [...],
        "recommendation_type": "personalized",
        "total_products": 20,
        "message": "..."
    }
    """
    db = SessionLocal()
    try:
        from sqlalchemy import desc
        
        # Build query with JOINs
        query = db.query(SKU, Product, Category).join(
            Product, SKU.product_id == Product.id
        ).join(
            Category, Product.category_id == Category.id
        )
        
        # Filter by categories if provided
        categories = criteria.get("top_categories", [])
        if categories:
            query = query.filter(Category.name.in_(categories))
        
        # Filter by brands if provided
        brands = criteria.get("top_brands", [])
        if brands:
            query = query.filter(Product.brand.in_(brands))
        
        # Filter by price range
        price_range = criteria.get("price_range", {})
        min_price = price_range.get("min", 0)
        max_price = price_range.get("max", float('inf'))
        
        if min_price > 0 or max_price < float('inf'):
            query = query.filter(
                SKU.price.between(min_price, max_price)
            )
        
        # Order by rating and search count (popularity)
        query = query.order_by(
            desc(SKU.rating),
            desc(SKU.search_count),
            desc(SKU.created_at)
        )
        
        results = query.limit(limit).all()
        
        # Handle empty results
        if not results:
            logger.warning(f"[get_recommendations_by_criteria] No products found matching criteria: {criteria}")
            return {
                "status": "success",
                "products": [],
                "recommendation_type": "personalized",
                "total_products": 0,
                "message": f"No products found matching your criteria. Try adjusting: categories={categories}, brands={brands}, price_range={price_range}"
            }
        
        products_data = [
            {
                "id": product.id,  # ✅ Use Product ID, not SKU ID
                "sku_code": sku.sku_code,
                "product_id": product.tiki_product_id,
                "title": product.title,
                "price": float(sku.price),
                "original_price": float(sku.original_price) if sku.original_price else 0,
                "brand": product.brand or "Unknown",
                "category": category.name or "Other",
                "thumbnail": product.thumbnail,
                "rating": float(sku.rating) if sku.rating else 0,
                "search_count": sku.search_count or 0,
                "stock": sku.stock
            }
            for sku, product, category in results
        ]
        
        return {
            "status": "success",
            "products": products_data,
            "recommendation_type": "personalized",
            "total_products": len(products_data),
            "message": f"Showing {len(products_data)} personalized recommendations"
        }
    except Exception as e:
        logger.error(f"[get_recommendations_by_criteria] Error: {e}")
        return {
            "status": "error",
            "message": str(e),
            "products": [],
            "recommendation_type": "error",
            "total_products": 0
        }
    finally:
        db.close()

# ============================================================================
# Filter & Ranking API (for Frontend UI)
# ============================================================================

@app.post("/api/products/filter-with-ranking")
async def filter_products_with_ranking(body: Dict[str, Any] = Body(...)):
    """
    Filter products by category + attributes, then rank by degree of match.
    
    ✅ STRATEGY: Return ALL products of category, ranked by attribute match score
    
    Request body:
    {
        "category_id": 5,              # Either category_id or category_name
        "category_name": "Giày",       # Will find category by name
        "attributes": {
            "brand": ["Nike"],           # Multi-select values
            "size": ["42", "43"],        # Multiple values to match
            "color": ["đen"]
        },
        "limit": 50
    }
    
    Returns:
    {
        "success": true,
        "category_id": 5,
        "category_name": "Giày",
        "products": [
            {
                "id": 123,
                "product_id": "276183351",
                "title": "Giày thể thao nam...",
                "brand": "Nike",
                "price": 620000,
                "stock": 10,
                "thumbnail": "...",
                "match_score": 3,              ← How many attributes matched
                "matched_attributes": {         ← Which attributes matched
                    "brand": "Nike",
                    "size": "42"
                },
                "attributes": [...]            ← All attributes of product
            },
            ...
        ],
        "total": 15
    }
    """
    db = SessionLocal()
    try:
        category_id = body.get("category_id")
        category_name = body.get("category_name")
        attributes_filter = body.get("attributes", {})
        limit = body.get("limit", 50)
        
        # Find category by ID or name
        category = None
        if category_id:
            category = db.query(Category).filter(Category.id == category_id).first()
        elif category_name:
            # Search by name (case-insensitive)
            category = db.query(Category).filter(
                Category.name.ilike(category_name)
            ).first()
        
        if not category:
            logger.warning(f"❌ Category not found: id={category_id}, name={category_name}")
            raise HTTPException(status_code=404, detail="Category not found")
        
        logger.info(f"🔍 Filter with ranking: category={category.name} (id={category.id})")
        logger.info(f"   Requested attributes: {attributes_filter}")
        
        # Query all products + SKUs of this category
        products_skus = db.query(Product, SKU).join(
            SKU, Product.id == SKU.product_id
        ).filter(
            Product.category_id == category.id
        ).all()
        
        if not products_skus:
            logger.info(f"✅ No products found in category {category.name}")
            return {
                "success": True,
                "category_id": category.id,
                "category_name": category.name,
                "products": [],
                "total": 0
            }
        
        # Extract SKU IDs to fetch attributes
        sku_ids = [sku.id for _, sku in products_skus]
        
        # Fetch all attributes for these SKUs
        sku_attributes_raw = db.query(SKUAttribute).filter(
            SKUAttribute.sku_id.in_(sku_ids)
        ).all()
        
        # Organize attributes by SKU ID
        sku_attrs_map = {}
        for attr in sku_attributes_raw:
            if attr.sku_id not in sku_attrs_map:
                sku_attrs_map[attr.sku_id] = {}
            sku_attrs_map[attr.sku_id][attr.attribute_name] = attr.attribute_value
        
        # Calculate match score for each product
        products_with_scores = []
        
        for product, sku in products_skus:
            sku_attrs = sku_attrs_map.get(sku.id, {})
            
            # Calculate match score
            match_score = 0
            matched_attrs = {}
            
            # Check each requested attribute
            for attr_name, requested_values in attributes_filter.items():
                if not isinstance(requested_values, list):
                    requested_values = [requested_values]
                
                # Get product's actual value for this attribute
                actual_value = sku_attrs.get(attr_name)
                
                if actual_value and actual_value in requested_values:
                    match_score += 1
                    matched_attrs[attr_name] = actual_value
            
            # Format product with match info
            product_data = {
                "id": product.id,
                "product_id": product.tiki_product_id,
                "spid": product.tiki_spid,
                "title": product.title,
                "brand": product.brand,
                "price": float(sku.price),
                "original_price": float(sku.original_price) if sku.original_price else None,
                "stock": sku.stock,
                "is_available": sku.is_available,
                "thumbnail": product.thumbnail,
                "product_url": product.product_url,
                "category_id": product.category_id,
                "source": product.source,
                "rating": float(sku.rating) if sku.rating else 0,
                "search_count": sku.search_count or 0,
                "match_score": match_score,
                "matched_attributes": matched_attrs,
                # Include all attributes for reference
                "attributes": [
                    {"name": attr_name, "value": attr_value}
                    for attr_name, attr_value in sku_attrs.items()
                ]
            }
            
            products_with_scores.append(product_data)
        
        # Sort by: match_score DESC → rating DESC → search_count DESC
        products_with_scores.sort(
            key=lambda p: (-p["match_score"], -p["rating"], -p["search_count"])
        )
        
        # Apply limit
        products_list = products_with_scores[:limit]
        
        logger.info(f"✅ Filtered {len(products_list)} products (total: {len(products_with_scores)})")
        logger.info(f"   Top product match score: {products_list[0]['match_score'] if products_list else 'N/A'}")
        
        return {
            "success": True,
            "category_id": category.id,
            "category_name": category.name,
            "products": products_list,
            "total": len(products_list)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Filter with ranking failed: {e}", exc_info=True)
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
