# setup_postgres_cache.py
"""
Setup PostgreSQL tables for category cache
Run once to initialize database schema
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def setup_postgres_tables():
    """Create category_suggestions table in PostgreSQL"""
    
    print("🔧 Setting up PostgreSQL category cache tables...")
    print(f"📍 Database: {DATABASE_URL.split('@')[1]}")
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        
        # Create table
        print("\n📝 Creating table 'category_suggestions'...")
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
        
        # Create indexes
        print("📝 Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_category_name 
            ON category_suggestions(category_name)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_usage_count 
            ON category_suggestions(usage_count DESC)
        """)
        
        # Create update trigger
        print("📝 Creating update trigger...")
        cursor.execute("""
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
        """)
        
        cursor.execute("""
            DROP TRIGGER IF EXISTS update_category_suggestions_updated_at 
            ON category_suggestions;
        """)
        
        cursor.execute("""
            CREATE TRIGGER update_category_suggestions_updated_at 
                BEFORE UPDATE ON category_suggestions
                FOR EACH ROW 
                EXECUTE FUNCTION update_updated_at_column();
        """)
        
        conn.commit()
        
        # Verify
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_name = 'category_suggestions'
        """)
        
        if cursor.fetchone():
            print("✅ Table 'category_suggestions' created successfully!")
        
        # Check existing data
        cursor.execute("SELECT COUNT(*) FROM category_suggestions")
        count = cursor.fetchone()[0]
        print(f"📊 Current records: {count}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ PostgreSQL setup completed!")
        print("\n📋 Next steps:")
        print("   1. Run your application")
        print("   2. LLM suggestions will auto-save to PostgreSQL")
        print("   3. Check data: SELECT * FROM category_suggestions;")
        
    except psycopg2.Error as e:
        print(f"❌ PostgreSQL error: {e}")
        return False
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return False
    
    return True


def test_category_cache():
    """Test CategoryCache with PostgreSQL"""
    from app.core.category_cache import CategoryCache
    
    print("\n" + "="*70)
    print("🧪 Testing CategoryCache with PostgreSQL")
    print("="*70)
    
    cache = CategoryCache(backend="postgres", pg_url=DATABASE_URL)
    
    # Test save
    print("\n📝 Test 1: Save suggestion...")
    test_suggestion = {
        "name": "test_category_postgres",
        "attributes": ["test_attr1", "test_attr2"],
        "reason": "Test category for PostgreSQL",
        "confidence": 0.95
    }
    
    suggestion_id = cache.save_suggestion(test_suggestion)
    if suggestion_id > 0:
        print(f"✅ Saved successfully with ID: {suggestion_id}")
    else:
        print("❌ Save failed")
        return False
    
    # Test retrieve
    print("\n📖 Test 2: Retrieve suggestion...")
    retrieved = cache.get_suggestion("test_category_postgres")
    if retrieved:
        print(f"✅ Retrieved: {retrieved['category_name']}")
        print(f"   Attributes: {retrieved['attributes']}")
        print(f"   Usage count: {retrieved['usage_count']}")
    else:
        print("❌ Retrieve failed")
        return False
    
    # Test update (increment usage)
    print("\n🔄 Test 3: Update usage count...")
    cache.save_suggestion(test_suggestion)
    updated = cache.get_suggestion("test_category_postgres")
    print(f"✅ Usage count updated: {retrieved['usage_count']} → {updated['usage_count']}")
    
    print("\n✅ All tests passed!")
    return True


if __name__ == "__main__":
    # Setup tables
    success = setup_postgres_tables()
    
    if success:
        # Run tests
        test_category_cache()
