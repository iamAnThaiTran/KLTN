# app/services/product_service.py
"""
ProductService - Microservice for product data layer
Responsibilities:
- Product querying from database
- Category validation and management
- Attribute extraction (rule-based)
- SKU management
- Filter generation
- Product normalization
"""

import logging
from typing import Dict, List, Any, Optional, Tuple
from .base_service import BaseService  # ✅ LOCAL
from .product_repository import ProductRepository  # ✅ LOCAL
from .category_validator import CategoryValidator  # ✅ LOCAL
from ..core.extractor import AttributeExtractor  # ✅ LOCAL
from ..db.sku_repository import SKURepository  # ✅ LOCAL

logger = logging.getLogger(__name__)

class ProductService(BaseService):
    """
    Product Service - Manages products, categories, attributes, SKUs
    
    Provides unified interface for:
    - Category validation
    - Product querying
    - Attribute extraction
    - Filter management
    - Normalizing product data
    """
    
    SERVICE_NAME = "ProductService"
    SERVICE_VERSION = "1.0.0"
    SERVICE_TIMEOUT = 30
    
    def __init__(self):
        super().__init__()
        
        # Initialize dependencies
        self.product_repo = ProductRepository()
        self.category_validator = CategoryValidator()
        self.attribute_extractor = AttributeExtractor()
        self.sku_repo = SKURepository()
        
        self.log_operation("initialized", "info")
    
    # ========================================================================
    # CATEGORY OPERATIONS
    # ========================================================================
    
    def validate_category(self, category_name: str) -> Dict[str, Any]:
        """
        Validate and normalize category name
        
        Args:
            category_name: User-provided category name (e.g., "Giày")
        
        Returns:
        {
            "success": True,
            "category": "Giày",
            "category_id": 3,
            "status": "existing|new",  # 'new' if just created
            "original": "Giày"
        }
        """
        self.track_request("validate_category")
        
        try:
            self.log_operation(
                "validate_category_start",
                "info",
                input_category=category_name
            )
            
            result = self.category_validator.validate_category(category_name)
            
            self.log_operation(
                "validate_category_success",
                "info",
                category_id=result.get("category_id"),
                status=result.get("status")
            )
            
            return result
            
        except Exception as e:
            return self.handle_service_error(
                "validate_category",
                e,
                context={"input": category_name},
                raise_error=False
            )
    
    # ========================================================================
    # ATTRIBUTE OPERATIONS
    # ========================================================================
    
    def extract_attributes(
        self,
        user_input: str,
        category: str,
        use_llm: bool = False
    ) -> Dict[str, Any]:
        """
        Extract product attributes from user input
        
        Args:
            user_input: User's input (e.g., "Nike size 40")
            category: Product category (e.g., "Giày")
            use_llm: Whether to use LLM for extraction (else rule-based)
        
        Returns:
        {
            "success": True,
            "extracted": {"brand": "Nike", "size": "40"},
            "confidence": 0.85,
            "attributes_found": 2
        }
        """
        self.track_request("extract_attributes")
        
        try:
            self.log_operation(
                "extract_attributes_start",
                "info",
                category=category,
                use_llm=use_llm
            )
            
            result = self.attribute_extractor.extract(
                user_input,
                category,
                use_llm=use_llm
            )
            
            self.log_operation(
                "extract_attributes_success",
                "info",
                attributes_count=len(result.get("extracted", {})),
                confidence=result.get("confidence", 0)
            )
            
            return result
            
        except Exception as e:
            return self.handle_service_error(
                "extract_attributes",
                e,
                context={"user_input": user_input, "category": category},
                raise_error=False
            )
    
    # ========================================================================
    # PRODUCT QUERYING
    # ========================================================================
    
    def query_products(
        self,
        category_id: int,
        attributes: Dict[str, Any],
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Query products from database by category and attributes
        
        Args:
            category_id: Category ID (from validation)
            attributes: Extracted attributes dict (e.g., {"brand": "Nike"})
            limit: Max results
            offset: Pagination offset
        
        Returns:
        {
            "success": True,
            "products": [...],
            "total_count": 24,
            "cache_hit": True|False,
            "query_time_ms": 45
        }
        """
        self.track_request("query_products")
        
        try:
            self.log_operation(
                "query_products_start",
                "info",
                category_id=category_id,
                attributes_count=len(attributes),
                limit=limit
            )
            
            result = self.product_repo.query_by_category_and_attributes(
                category_id=category_id,
                attributes=attributes,
                limit=limit,
                offset=offset
            )
            
            products = result.get("products", [])
            
            self.log_operation(
                "query_products_success",
                "info",
                products_found=len(products),
                total_count=result.get("total_count", 0),
                cache_hit=result.get("cache_hit", False)
            )
            
            return {
                "success": True,
                "products": products,
                "total_count": result.get("total_count", len(products)),
                "cache_hit": result.get("cache_hit", False),
                "query_time_ms": result.get("query_time_ms", 0)
            }
            
        except Exception as e:
            return self.handle_service_error(
                "query_products",
                e,
                context={"category_id": category_id},
                raise_error=False
            )
    
    # ========================================================================
    # PRODUCT SAVING (for crawled products)
    # ========================================================================
    
    def save_products_batch(
        self,
        category_id: int,
        products: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Save batch of products to database (from crawlers)
        
        Args:
            category_id: Category ID
            products: List of product dicts from crawler
        
        Returns:
        {
            "success": True,
            "saved_count": 24,
            "products": [...]  # Saved product records
        }
        """
        self.track_request("save_products_batch")
        
        if not products:
            return {"success": True, "saved_count": 0, "products": []}
        
        try:
            self.log_operation(
                "save_products_batch_start",
                "info",
                category_id=category_id,
                count=len(products)
            )
            
            result = self.product_repo.save_products_batch(
                category_id=category_id,
                products=products
            )
            
            saved_count = result.get("saved_count", 0)
            
            self.log_operation(
                "save_products_batch_success",
                "info",
                saved_count=saved_count
            )
            
            return result
            
        except Exception as e:
            return self.handle_service_error(
                "save_products_batch",
                e,
                context={"category_id": category_id, "count": len(products)},
                raise_error=False
            )
    
    # ========================================================================
    # FILTER OPERATIONS
    # ========================================================================
    
    def get_filters_for_category(
        self,
        category_id: int,
        products: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Get available filters for a category
        
        Can either:
        1. Get filters from category schema (all possible values)
        2. Extract filters from product list (only available values)
        
        Args:
            category_id: Category ID
            products: Optional - if provided, extract from these products
        
        Returns:
        {
            "success": True,
            "filters": [
                {
                    "attribute_name": "brand",
                    "display_name": "Thương hiệu",
                    "data_type": "enum",
                    "values": ["Nike", "Adidas", "Puma"],
                    "count": 3
                },
                ...
            ]
        }
        """
        self.track_request("get_filters_for_category")
        
        try:
            self.log_operation(
                "get_filters_for_category_start",
                "info",
                category_id=category_id,
                has_products=products is not None
            )
            
            if products:
                # Extract filters from product list
                filters = self._extract_filters_from_products(products)
            else:
                # Get filters from category schema
                filters = self.sku_repo.get_filters_by_category(category_id)
            
            self.log_operation(
                "get_filters_for_category_success",
                "info",
                filters_count=len(filters)
            )
            
            return {
                "success": True,
                "filters": filters
            }
            
        except Exception as e:
            return self.handle_service_error(
                "get_filters_for_category",
                e,
                context={"category_id": category_id},
                raise_error=False
            )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _extract_filters_from_products(
        self,
        products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Extract available filter values from product list
        
        Input:
        [
            {
                "title": "Nike Air",
                "attributes": {"brand": "Nike", "size": "40"}
            },
            ...
        ]
        
        Output:
        [
            {
                "attribute_name": "brand",
                "display_name": "Thương hiệu",
                "values": ["Nike", "Adidas"],
                "count": 2
            },
            ...
        ]
        """
        if not products:
            return []
        
        # Collect all attributes and their values
        attribute_values = {}
        
        for product in products:
            attrs = product.get("attributes", {})
            
            for attr_name, attr_value in attrs.items():
                if attr_name not in attribute_values:
                    attribute_values[attr_name] = set()
                
                if isinstance(attr_value, (list, tuple)):
                    attribute_values[attr_name].update(attr_value)
                else:
                    attribute_values[attr_name].add(str(attr_value))
        
        # Convert to filter format
        filters = []
        display_map = {
            "brand": "Thương hiệu",
            "size": "Kích cỡ",
            "color": "Màu sắc",
            "type": "Loại",
            "material": "Chất liệu",
            "price_range": "Giá"
        }
        
        for attr_name, values in attribute_values.items():
            filters.append({
                "attribute_name": attr_name,
                "display_name": display_map.get(attr_name, attr_name),
                "data_type": "enum",
                "values": sorted(list(values)),
                "count": len(values)
            })
        
        return sorted(filters, key=lambda f: f["attribute_name"])
    
    def normalize_product(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize product data to standard format
        
        Ensures all products have required fields
        """
        return {
            "id": product.get("id"),
            "title": product.get("title", ""),
            "brand": product.get("brand", ""),
            "price": product.get("price", 0),
            "original_price": product.get("original_price"),
            "thumbnail": product.get("thumbnail"),
            "product_url": product.get("product_url"),
            "source": product.get("source", "unknown"),
            "attributes": product.get("attributes", {}),
            "stock": product.get("stock", 0),
            "rating": product.get("rating"),
            "review_count": product.get("review_count", 0)
        }
    
    def validate_inputs(self, **kwargs) -> bool:
        """Validate service method inputs"""
        # Implement specific validation rules
        return True
