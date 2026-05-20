# -*- coding: utf-8 -*-
"""
ProductService HTTP Client Interface

Định nghĩa các methods mà CategoryValidator + CategorySchemaEvolution dùng
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional


class IProductServiceClient(ABC):
    """Interface cho ProductService client"""
    
    @abstractmethod
    async def list_categories(self) -> List[Dict[str, Any]]:
        """
        Lấy danh sách tất cả categories
        
        Returns:
            [
                {"id": 1, "name": "Giày", "slug": "giay", ...},
                {"id": 2, "name": "Laptop", "slug": "laptop", ...}
            ]
        """
        pass
    
    @abstractmethod
    async def get_category_details(self, category_id: int) -> Dict[str, Any]:
        """
        Lấy category details với attributes
        
        Args:
            category_id: ID của category
        
        Returns:
            {
                "id": 5,
                "name": "Laptop",
                "attributes": [
                    {"id": 1, "attribute_name": "brand", ...},
                    {"id": 2, "attribute_name": "cpu", ...}
                ]
            }
        """
        pass
    
    @abstractmethod
    async def create_category(
        self,
        name: str,
        description: str = "",
        category_type: str = "general",
        attributes: List[str] = None
    ) -> Dict[str, Any]:
        """
        Tạo category mới với attributes
        
        Args:
            name: Tên category
            description: Mô tả
            category_type: Loại category
            attributes: Danh sách attributes
        
        Returns:
            {
                "success": bool,
                "id": int,
                "name": str,
                "attributes_created": int
            }
        """
        pass
    
    @abstractmethod
    async def add_category_attributes(
        self,
        category_id: int,
        attributes: List[str]
    ) -> Dict[str, Any]:
        """
        Thêm (append) attributes vào category
        
        Args:
            category_id: ID của category
            attributes: Danh sách attributes mới
        
        Returns:
            {
                "success": bool,
                "category_id": int,
                "attributes_added": List[str],
                "attributes_count": int,
                "schema_version": int
            }
        """
        pass
    
    @abstractmethod
    async def sync_product_sku_attributes(
        self,
        category_id: int,
        attributes: List[str]
    ) -> Dict[str, Any]:
        """
        Sync SKU attributes cho tất cả products của category
        
        Args:
            category_id: ID của category
            attributes: Danh sách attributes mới
        
        Returns:
            {
                "success": bool,
                "category_id": int,
                "products_synced": int
            }
        """
        pass
