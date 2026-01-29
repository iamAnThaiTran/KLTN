# app/core/category_suggestion_manager.py
"""
Category Suggestion Manager - Lưu và quản lý LLM category suggestions vào DB
Tích hợp với PostgreSQL qua Prisma (sử dụng HTTP API hoặc direct connection)
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime


class CategorySuggestionManager:
    """
    Quản lý category suggestions từ LLM
    - Lưu suggestions vào database
    - Tự động generate schema cho category mới
    - Track usage statistics
    """
    
    def __init__(self, db_adapter=None):
        """
        Args:
            db_adapter: Database adapter (Prisma client hoặc HTTP client to Node.js API)
                       Nếu None, fallback to in-memory storage
        """
        self.db = db_adapter
        self.in_memory_cache = {}  # Fallback khi không có DB
        
    # ============================================
    # SAVE LLM SUGGESTIONS
    # ============================================
    
    async def save_suggestions(
        self, 
        suggestions: List[Dict[str, Any]],
        source: str = "llm"
    ) -> List[int]:
        """
        Lưu LLM suggestions vào database
        
        Args:
            suggestions: List of suggestions từ LLM
                [
                    {
                        "name": "đồng hồ",
                        "reason": "Classic gift...",
                        "attributes": ["brand", "style", "price range"]
                    },
                    ...
                ]
            source: Nguồn suggestion ("llm", "manual", "user")
        
        Returns:
            List of created suggestion IDs
        """
        if not self.db:
            return self._save_to_memory(suggestions, source)
        
        created_ids = []
        
        for suggestion in suggestions:
            try:
                # Upsert: Update nếu đã tồn tại, Insert nếu chưa có
                result = await self.db.category_suggestion.upsert(
                    where={
                        "categoryName": suggestion["name"]
                    },
                    update={
                        "reason": suggestion.get("reason", ""),
                        "attributes": json.dumps(suggestion.get("attributes", [])),
                        "usageCount": {"increment": 1},  # Tăng usage count
                        "updatedAt": datetime.now()
                    },
                    create={
                        "categoryName": suggestion["name"],
                        "reason": suggestion.get("reason", ""),
                        "attributes": json.dumps(suggestion.get("attributes", [])),
                        "keywords": self._extract_keywords(suggestion["name"]),
                        "source": source,
                        "confidence": suggestion.get("confidence", 0.8),
                        "usageCount": 1,
                        "isActive": True
                    }
                )
                
                created_ids.append(result["id"])
                print(f"✓ Saved suggestion: {suggestion['name']} (ID: {result['id']})")
                
            except Exception as e:
                print(f"❌ Failed to save suggestion '{suggestion['name']}': {e}")
        
        return created_ids
    
    # ============================================
    # RETRIEVE SUGGESTIONS
    # ============================================
    
    async def get_suggestions_for_category(
        self, 
        category_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Lấy suggestion đã lưu cho một category
        
        Returns:
            {
                "id": 1,
                "categoryName": "đồng hồ",
                "attributes": ["brand", "style", "price range"],
                "keywords": ["đồng hồ", "watch", "clock"],
                "usageCount": 5,
                ...
            }
        """
        if not self.db:
            return self.in_memory_cache.get(category_name)
        
        try:
            result = await self.db.category_suggestion.find_unique(
                where={"categoryName": category_name}
            )
            return result
        except Exception as e:
            print(f"❌ Failed to get suggestion for '{category_name}': {e}")
            return None
    
    async def get_all_active_suggestions(self) -> List[Dict[str, Any]]:
        """Lấy tất cả active suggestions"""
        if not self.db:
            return list(self.in_memory_cache.values())
        
        try:
            return await self.db.category_suggestion.find_many(
                where={"isActive": True},
                order_by={"usageCount": "desc"}
            )
        except Exception as e:
            print(f"❌ Failed to get suggestions: {e}")
            return []
    
    # ============================================
    # DYNAMIC SCHEMA GENERATION & STORAGE
    # ============================================
    
    async def generate_and_save_schema(
        self,
        category_name: str,
        attributes: List[str],
        llm_generator_func
    ) -> Optional[Dict[str, Any]]:
        """
        Generate schema cho category mới và lưu vào DB
        
        Args:
            category_name: Tên category
            attributes: List attributes gợi ý từ LLM
            llm_generator_func: Function để gen schema (from dynamic_schema.py)
        
        Returns:
            Generated schema hoặc None nếu lỗi
        """
        # Check xem đã có schema chưa
        existing = await self.get_schema(category_name)
        if existing:
            print(f"ℹ️  Schema for '{category_name}' already exists (version {existing['version']})")
            return existing
        
        # Generate schema using LLM
        try:
            schema = await llm_generator_func(category_name, attributes)
            
            # Save to database
            if self.db:
                # Get suggestion ID if exists
                suggestion = await self.get_suggestions_for_category(category_name)
                suggestion_id = suggestion["id"] if suggestion else None
                
                result = await self.db.dynamic_category_schema.create(
                    data={
                        "categoryName": category_name,
                        "schemaJson": json.dumps(schema),
                        "suggestionId": suggestion_id,
                        "generatedBy": "llm",
                        "version": 1,
                        "usageCount": 0,
                        "successRate": 0.0,
                        "isActive": True,
                        "isVerified": False
                    }
                )
                
                print(f"✓ Generated and saved schema for '{category_name}' (ID: {result['id']})")
                return result
            else:
                # In-memory fallback
                self.in_memory_cache[f"schema_{category_name}"] = schema
                return schema
                
        except Exception as e:
            print(f"❌ Failed to generate schema for '{category_name}': {e}")
            return None
    
    async def get_schema(
        self, 
        category_name: str
    ) -> Optional[Dict[str, Any]]:
        """
        Lấy schema đã generate cho category
        
        Returns:
            {
                "id": 1,
                "categoryName": "đồng hồ",
                "schemaJson": {...},
                "version": 1,
                "usageCount": 10,
                ...
            }
        """
        if not self.db:
            return self.in_memory_cache.get(f"schema_{category_name}")
        
        try:
            # Lấy latest active version
            result = await self.db.dynamic_category_schema.find_first(
                where={
                    "categoryName": category_name,
                    "isActive": True
                },
                order_by={"version": "desc"}
            )
            
            return result
        except Exception as e:
            print(f"❌ Failed to get schema for '{category_name}': {e}")
            return None
    
    # ============================================
    # USAGE TRACKING
    # ============================================
    
    async def increment_usage(
        self, 
        category_name: str,
        success: bool = True
    ):
        """
        Track usage của một category
        
        Args:
            category_name: Tên category
            success: Có thành công không (dùng để tính success rate)
        """
        if not self.db:
            return
        
        try:
            # Update suggestion
            await self.db.category_suggestion.update(
                where={"categoryName": category_name},
                data={
                    "usageCount": {"increment": 1}
                }
            )
            
            # Update schema
            schema = await self.get_schema(category_name)
            if schema:
                new_usage = schema["usageCount"] + 1
                new_success_rate = (
                    (schema["successRate"] * schema["usageCount"] + (1 if success else 0))
                    / new_usage
                )
                
                await self.db.dynamic_category_schema.update(
                    where={"id": schema["id"]},
                    data={
                        "usageCount": new_usage,
                        "successRate": new_success_rate
                    }
                )
                
        except Exception as e:
            print(f"⚠️  Failed to increment usage for '{category_name}': {e}")
    
    # ============================================
    # HELPERS
    # ============================================
    
    def _extract_keywords(self, category_name: str) -> List[str]:
        """Extract keywords từ category name"""
        # Basic implementation - có thể enhance với LLM
        keywords = [category_name]
        
        # Add variations
        keywords.append(category_name.replace(" ", ""))  # Remove spaces
        keywords.append(category_name.lower())
        
        return list(set(keywords))
    
    def _save_to_memory(
        self, 
        suggestions: List[Dict[str, Any]],
        source: str
    ) -> List[int]:
        """Fallback: Save to in-memory cache"""
        ids = []
        for idx, suggestion in enumerate(suggestions):
            suggestion_id = len(self.in_memory_cache) + idx + 1
            self.in_memory_cache[suggestion["name"]] = {
                "id": suggestion_id,
                "categoryName": suggestion["name"],
                "reason": suggestion.get("reason", ""),
                "attributes": suggestion.get("attributes", []),
                "keywords": self._extract_keywords(suggestion["name"]),
                "source": source,
                "usageCount": 1,
                "createdAt": datetime.now().isoformat()
            }
            ids.append(suggestion_id)
            print(f"✓ Saved to memory: {suggestion['name']} (ID: {suggestion_id})")
        
        return ids


# ============================================
# EXAMPLE USAGE
# ============================================

async def example_usage():
    """Example demonstrating how to use CategorySuggestionManager"""
    
    # Initialize manager (without DB for demo)
    manager = CategorySuggestionManager(db_adapter=None)
    
    # LLM response
    llm_suggestions = [
        {
            "name": "mỹ phẩm",
            "reason": "Popular Tết gift for beauty",
            "attributes": ["brand", "price range", "type"]
        },
        {
            "name": "đồng hồ",
            "reason": "Classic gift symbolizing time",
            "attributes": ["brand", "style", "price range"]
        }
    ]
    
    # Save suggestions
    print("📝 Saving LLM suggestions...")
    ids = await manager.save_suggestions(llm_suggestions, source="llm")
    print(f"✓ Saved {len(ids)} suggestions with IDs: {ids}\n")
    
    # Retrieve suggestion
    print("📖 Retrieving suggestion for 'đồng hồ'...")
    suggestion = await manager.get_suggestions_for_category("đồng hồ")
    print(f"✓ Found: {json.dumps(suggestion, indent=2, ensure_ascii=False)}\n")
    
    # Get all suggestions
    print("📋 Getting all active suggestions...")
    all_suggestions = await manager.get_all_active_suggestions()
    print(f"✓ Total: {len(all_suggestions)} suggestions")
    for s in all_suggestions:
        print(f"  - {s['categoryName']}: {s['usageCount']} uses")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
