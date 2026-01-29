# app/core/category_cache.py
"""
Category Cache System - Lưu LLM category suggestions
Support 3 backends: SQLite, PostgreSQL (asyncpg), JSON file
KHÔNG dùng Prisma
"""

import json
import sqlite3
import os
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path


class CategoryCache:
    """
    Cache cho category suggestions từ LLM
    Tự động lưu category + attributes mới để tái sử dụng
    """
    
    def __init__(self, backend: str = "sqlite", db_path: str = None, pg_url: str = None):
        """
        Args:
            backend: "sqlite", "postgres", hoặc "json"
            db_path: Path to SQLite DB hoặc JSON file
            pg_url: PostgreSQL connection string (nếu dùng postgres)
        """
        self.backend = backend
        
        if backend == "sqlite":
            self.db_path = db_path or "data/category_cache.db"
            self._init_sqlite()
        elif backend == "postgres":
            self.pg_url = pg_url or os.getenv("DATABASE_URL")
            self._init_postgres()
        else:  # json
            self.json_path = db_path or "data/category_cache.json"
            self._init_json()
    
    # ============================================
    # SQLITE IMPLEMENTATION
    # ============================================
    
    def _init_sqlite(self):
        """Initialize SQLite database"""
        # Create data directory if not exists
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE NOT NULL,
                attributes TEXT NOT NULL,  -- JSON array
                keywords TEXT,             -- JSON array
                reason TEXT,
                confidence REAL DEFAULT 0.8,
                usage_count INTEGER DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category_name 
            ON category_suggestions(category_name)
        """)
        
        conn.commit()
        conn.close()
        print(f"✓ SQLite cache initialized: {self.db_path}")
    
    def save_suggestion_sqlite(self, suggestion: Dict[str, Any]) -> int:
        """Save suggestion to SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        try:
            # Check if exists
            cursor.execute(
                "SELECT id, usage_count FROM category_suggestions WHERE category_name = ?",
                (suggestion["name"],)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing
                cursor.execute("""
                    UPDATE category_suggestions 
                    SET attributes = ?, 
                        reason = ?,
                        usage_count = usage_count + 1,
                        updated_at = ?
                    WHERE category_name = ?
                """, (
                    json.dumps(suggestion.get("attributes", []), ensure_ascii=False),
                    suggestion.get("reason", ""),
                    now,
                    suggestion["name"]
                ))
                suggestion_id = existing[0]
                print(f"✓ Updated: {suggestion['name']} (usage: {existing[1] + 1})")
            else:
                # Insert new
                cursor.execute("""
                    INSERT INTO category_suggestions 
                    (category_name, attributes, keywords, reason, confidence, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    suggestion["name"],
                    json.dumps(suggestion.get("attributes", []), ensure_ascii=False),
                    json.dumps(self._extract_keywords(suggestion["name"]), ensure_ascii=False),
                    suggestion.get("reason", ""),
                    suggestion.get("confidence", 0.8),
                    now,
                    now
                ))
                suggestion_id = cursor.lastrowid
                print(f"✓ Saved: {suggestion['name']} (ID: {suggestion_id})")
            
            conn.commit()
            return suggestion_id
            
        except Exception as e:
            print(f"❌ SQLite error: {e}")
            conn.rollback()
            return -1
        finally:
            conn.close()
    
    def get_suggestion_sqlite(self, category_name: str) -> Optional[Dict[str, Any]]:
        """Get suggestion from SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT * FROM category_suggestions WHERE category_name = ?",
            (category_name,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return {
            "id": row[0],
            "category_name": row[1],
            "attributes": json.loads(row[2]),
            "keywords": json.loads(row[3]) if row[3] else [],
            "reason": row[4],
            "confidence": row[5],
            "usage_count": row[6],
            "created_at": row[7],
            "updated_at": row[8]
        }
    
    def get_all_suggestions_sqlite(self) -> List[Dict[str, Any]]:
        """Get all suggestions from SQLite"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM category_suggestions ORDER BY usage_count DESC")
        rows = cursor.fetchall()
        conn.close()
        
        return [
            {
                "id": row[0],
                "category_name": row[1],
                "attributes": json.loads(row[2]),
                "keywords": json.loads(row[3]) if row[3] else [],
                "reason": row[4],
                "confidence": row[5],
                "usage_count": row[6],
                "created_at": row[7],
                "updated_at": row[8]
            }
            for row in rows
        ]
    
    # ============================================
    # POSTGRESQL IMPLEMENTATION (without Prisma)
    # ============================================
    
    def _init_postgres(self):
        """Initialize PostgreSQL (using asyncpg or psycopg2)"""
        try:
            import psycopg2
            
            conn = psycopg2.connect(self.pg_url)
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS category_suggestions (
                    id SERIAL PRIMARY KEY,
                    category_name VARCHAR(255) UNIQUE NOT NULL,
                    attributes JSONB NOT NULL,
                    keywords JSONB,
                    reason TEXT,
                    confidence DECIMAL(3,2) DEFAULT 0.80,
                    usage_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_pg_category_name 
                ON category_suggestions(category_name)
            """)
            
            conn.commit()
            conn.close()
            print(f"✓ PostgreSQL cache initialized")
            
        except ImportError:
            print("⚠️  psycopg2 not installed. Run: pip install psycopg2-binary")
        except Exception as e:
            print(f"❌ PostgreSQL init error: {e}")
    
    def save_suggestion_postgres(self, suggestion: Dict[str, Any]) -> int:
        """Save suggestion to PostgreSQL"""
        try:
            import psycopg2
            from psycopg2.extras import Json
            
            conn = psycopg2.connect(self.pg_url)
            cursor = conn.cursor()
            
            # Upsert
            cursor.execute("""
                INSERT INTO category_suggestions 
                (category_name, attributes, keywords, reason, confidence, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ON CONFLICT (category_name) DO UPDATE SET
                    attributes = EXCLUDED.attributes,
                    reason = EXCLUDED.reason,
                    usage_count = category_suggestions.usage_count + 1,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                suggestion["name"],
                Json(suggestion.get("attributes", [])),
                Json(self._extract_keywords(suggestion["name"])),
                suggestion.get("reason", ""),
                suggestion.get("confidence", 0.8)
            ))
            
            suggestion_id = cursor.fetchone()[0]
            conn.commit()
            conn.close()
            
            print(f"✓ Saved to PostgreSQL: {suggestion['name']} (ID: {suggestion_id})")
            return suggestion_id
            
        except Exception as e:
            print(f"❌ PostgreSQL save error: {e}")
            return -1
    
    def get_suggestion_postgres(self, category_name: str) -> Optional[Dict[str, Any]]:
        """Get suggestion from PostgreSQL"""
        try:
            import psycopg2
            
            conn = psycopg2.connect(self.pg_url)
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM category_suggestions WHERE category_name = %s",
                (category_name,)
            )
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            return {
                "id": row[0],
                "category_name": row[1],
                "attributes": row[2],
                "keywords": row[3],
                "reason": row[4],
                "confidence": float(row[5]),
                "usage_count": row[6],
                "created_at": row[7].isoformat(),
                "updated_at": row[8].isoformat()
            }
            
        except Exception as e:
            print(f"❌ PostgreSQL get error: {e}")
            return None
    
    # ============================================
    # JSON FILE IMPLEMENTATION (simplest)
    # ============================================
    
    def _init_json(self):
        """Initialize JSON file cache"""
        Path(self.json_path).parent.mkdir(parents=True, exist_ok=True)
        
        if not os.path.exists(self.json_path):
            with open(self.json_path, 'w', encoding='utf-8') as f:
                json.dump({"suggestions": []}, f, ensure_ascii=False, indent=2)
        
        print(f"✓ JSON cache initialized: {self.json_path}")
    
    def save_suggestion_json(self, suggestion: Dict[str, Any]) -> int:
        """Save suggestion to JSON file"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        suggestions = data.get("suggestions", [])
        
        # Check if exists
        existing_idx = None
        for idx, s in enumerate(suggestions):
            if s["category_name"] == suggestion["name"]:
                existing_idx = idx
                break
        
        now = datetime.now().isoformat()
        
        if existing_idx is not None:
            # Update existing
            suggestions[existing_idx]["attributes"] = suggestion.get("attributes", [])
            suggestions[existing_idx]["reason"] = suggestion.get("reason", "")
            suggestions[existing_idx]["usage_count"] += 1
            suggestions[existing_idx]["updated_at"] = now
            suggestion_id = suggestions[existing_idx]["id"]
            print(f"✓ Updated JSON: {suggestion['name']} (usage: {suggestions[existing_idx]['usage_count']})")
        else:
            # Add new
            suggestion_id = len(suggestions) + 1
            suggestions.append({
                "id": suggestion_id,
                "category_name": suggestion["name"],
                "attributes": suggestion.get("attributes", []),
                "keywords": self._extract_keywords(suggestion["name"]),
                "reason": suggestion.get("reason", ""),
                "confidence": suggestion.get("confidence", 0.8),
                "usage_count": 1,
                "created_at": now,
                "updated_at": now
            })
            print(f"✓ Saved to JSON: {suggestion['name']} (ID: {suggestion_id})")
        
        data["suggestions"] = suggestions
        
        with open(self.json_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        return suggestion_id
    
    def get_suggestion_json(self, category_name: str) -> Optional[Dict[str, Any]]:
        """Get suggestion from JSON file"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for s in data.get("suggestions", []):
            if s["category_name"] == category_name:
                return s
        
        return None
    
    def get_all_suggestions_json(self) -> List[Dict[str, Any]]:
        """Get all suggestions from JSON"""
        with open(self.json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        suggestions = data.get("suggestions", [])
        return sorted(suggestions, key=lambda x: x["usage_count"], reverse=True)
    
    # ============================================
    # UNIFIED API (auto-routes to correct backend)
    # ============================================
    
    def save_suggestion(self, suggestion: Dict[str, Any]) -> int:
        """
        Save suggestion to cache
        
        Args:
            suggestion: {
                "name": "đồng hồ",
                "attributes": ["brand", "style", "price range"],
                "reason": "Classic gift...",
                "confidence": 0.85
            }
        
        Returns:
            Suggestion ID
        """
        if self.backend == "sqlite":
            return self.save_suggestion_sqlite(suggestion)
        elif self.backend == "postgres":
            return self.save_suggestion_postgres(suggestion)
        else:
            return self.save_suggestion_json(suggestion)
    
    def get_suggestion(self, category_name: str) -> Optional[Dict[str, Any]]:
        """Get cached suggestion for category"""
        if self.backend == "sqlite":
            return self.get_suggestion_sqlite(category_name)
        elif self.backend == "postgres":
            return self.get_suggestion_postgres(category_name)
        else:
            return self.get_suggestion_json(category_name)
    
    def get_all_suggestions(self) -> List[Dict[str, Any]]:
        """Get all cached suggestions"""
        if self.backend == "sqlite":
            return self.get_all_suggestions_sqlite()
        elif self.backend == "postgres":
            # Not implemented yet
            return []
        else:
            return self.get_all_suggestions_json()
    
    def save_multiple(self, suggestions: List[Dict[str, Any]]) -> List[int]:
        """Save multiple suggestions at once"""
        ids = []
        for suggestion in suggestions:
            suggestion_id = self.save_suggestion(suggestion)
            ids.append(suggestion_id)
        return ids
    
    # ============================================
    # HELPERS
    # ============================================
    
    def _extract_keywords(self, category_name: str) -> List[str]:
        """Extract keywords from category name"""
        keywords = [category_name, category_name.lower()]
        
        # Add without spaces
        if " " in category_name:
            keywords.append(category_name.replace(" ", ""))
        
        return list(set(keywords))


# ============================================
# EXAMPLE USAGE
# ============================================

def example_usage():
    """Example demonstrating different backends"""
    
    # LLM response
    llm_suggestions = [
        {
            "name": "mỹ phẩm",
            "reason": "Mỹ phẩm is a popular gift choice during Tết",
            "attributes": ["brand", "price range", "type"],
            "confidence": 0.9
        },
        {
            "name": "đồng hồ",
            "reason": "Classic gift symbolizing time and new beginnings",
            "attributes": ["brand", "style", "price range"],
            "confidence": 0.85
        },
        {
            "name": "túi xách",
            "reason": "Fashionable and practical gift",
            "attributes": ["style", "material", "size"],
            "confidence": 0.88
        }
    ]
    
    # ========================================
    # TEST 1: JSON Backend (simplest)
    # ========================================
    print("\n" + "="*50)
    print("TEST 1: JSON Backend")
    print("="*50)
    
    cache_json = CategoryCache(backend="json", db_path="data/categories.json")
    
    # Save suggestions
    print("\n📝 Saving suggestions...")
    ids = cache_json.save_multiple(llm_suggestions)
    print(f"✓ Saved {len(ids)} suggestions\n")
    
    # Retrieve one
    print("📖 Retrieving 'đồng hồ'...")
    dong_ho = cache_json.get_suggestion("đồng hồ")
    if dong_ho:
        print(f"✓ Found: {dong_ho['category_name']}")
        print(f"  Attributes: {dong_ho['attributes']}")
        print(f"  Usage count: {dong_ho['usage_count']}")
    
    # Get all
    print("\n📋 All cached suggestions:")
    all_suggestions = cache_json.get_all_suggestions()
    for s in all_suggestions:
        print(f"  - {s['category_name']}: {s['usage_count']} uses, confidence {s['confidence']}")
    
    # ========================================
    # TEST 2: SQLite Backend (recommended)
    # ========================================
    print("\n" + "="*50)
    print("TEST 2: SQLite Backend")
    print("="*50)
    
    cache_sqlite = CategoryCache(backend="sqlite", db_path="data/categories.db")
    
    # Save
    print("\n📝 Saving to SQLite...")
    cache_sqlite.save_multiple(llm_suggestions)
    
    # Retrieve
    print("\n📖 Retrieving 'túi xách'...")
    tui_xach = cache_sqlite.get_suggestion("túi xách")
    if tui_xach:
        print(f"✓ Found: {tui_xach['category_name']}")
        print(f"  Attributes: {tui_xach['attributes']}")
    
    # Re-save to increment usage
    print("\n🔄 Re-saving 'đồng hồ' to increment usage...")
    cache_sqlite.save_suggestion(llm_suggestions[1])
    
    dong_ho_updated = cache_sqlite.get_suggestion("đồng hồ")
    print(f"✓ Usage count now: {dong_ho_updated['usage_count']}")
    
    # Get all from SQLite
    print("\n📋 All SQLite suggestions:")
    all_sqlite = cache_sqlite.get_all_suggestions()
    for s in all_sqlite:
        print(f"  - {s['category_name']}: {s['usage_count']} uses")


if __name__ == "__main__":
    example_usage()
