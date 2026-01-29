# test_progressive_search.py
"""
Test script for progressive search functionality.

Run this to verify the progressive search system is working correctly.

Usage:
    cd BackendPython
    poetry run python test_progressive_search.py
"""

import asyncio
import json
import httpx
from typing import Dict, Any
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1/search/progressive"

# Test queries
TEST_QUERIES = [
    "giày thể thao",
    "quần áo nam",
    "mỹ phẩm nước hoa",
    "túi xách nữ",
]


class ProgressiveSearchTester:
    """Test the progressive search system"""
    
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=30)
    
    async def test_start_search(self, query: str) -> Dict[str, Any]:
        """
        Test starting a search.
        
        Expected: Immediate response with session_id + category + filters
        """
        print(f"\n{'='*60}")
        print(f"TEST: Start Search")
        print(f"Query: {query}")
        print('='*60)
        
        url = f"{self.base_url}{API_PREFIX}/start"
        payload = {
            "query": query,
            "sources": ["tiki", "lazada"]
        }
        
        start_time = time.time()
        response = await self.client.post(url, json=payload)
        elapsed = (time.time() - start_time) * 1000
        
        print(f"Status: {response.status_code}")
        print(f"Response time: {elapsed:.1f}ms")
        
        if response.status_code == 200:
            data = response.json()
            
            print(f"\n✓ Session created: {data['session_id'][:8]}...")
            print(f"✓ Category detected: {data['detected_category']}")
            print(f"✓ Confidence: {data['intent_confidence']:.0%}")
            print(f"✓ State: {data['state']}")
            
            filters = data.get('suggested_filters', {})
            print(f"✓ Filter suggestions: {len(filters)} groups")
            
            for filter_name, filter_data in list(filters.items())[:3]:
                count = len(filter_data.get('options', []))
                print(f"  - {filter_name}: {count} options")
            
            if len(filters) > 3:
                print(f"  ... and {len(filters) - 3} more")
            
            return data
        else:
            print(f"✗ Error: {response.text}")
            return None
    
    async def test_poll_results(self, session_id: str, max_polls: int = 30) -> Dict[str, Any]:
        """
        Test polling for results.
        
        Expected: Products appear as crawl completes
        """
        print(f"\n{'='*60}")
        print(f"TEST: Poll Results")
        print(f"Session: {session_id[:8]}...")
        print('='*60)
        
        url = f"{self.base_url}{API_PREFIX}/results/{session_id}"
        
        for poll_count in range(max_polls):
            start_time = time.time()
            response = await self.client.get(url)
            elapsed = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                state = data['state']
                crawling = data['is_crawling']
                products = len(data.get('products', []))
                total = data.get('total_products', 0)
                
                # Progress bars
                progress_str = ""
                if data.get('crawl_progress'):
                    for source, pct in data['crawl_progress'].items():
                        if pct < 0:
                            progress_str += f" {source}:✗"
                        else:
                            progress_str += f" {source}:{pct}%"
                
                status = "⏳" if crawling else "✓"
                print(f"[{poll_count:2d}] {status} {state:10s} | "
                      f"Products: {products:3d}/{total:3d} | "
                      f"Response: {elapsed:.1f}ms{progress_str}")
                
                # Stop when done
                if not crawling:
                    print(f"\n✓ Crawl complete!")
                    print(f"  Total products: {total}")
                    print(f"  Filtered products: {products}")
                    return data
            
            else:
                print(f"✗ Error: {response.status_code}")
                return None
            
            await asyncio.sleep(1)  # Poll every 1 second
        
        print(f"\n✗ Timeout after {max_polls} polls")
        return None
    
    async def test_apply_filters(self, session_id: str, 
                                 data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Test applying filters.
        
        Expected: Products filtered instantly
        """
        print(f"\n{'='*60}")
        print(f"TEST: Apply Filters")
        print(f"Session: {session_id[:8]}...")
        print('='*60)
        
        # Get first filter option from first filter
        filters_to_apply = {}
        suggested = data.get('suggested_filters', {})
        
        for filter_name, filter_data in suggested.items():
            options = filter_data.get('options', [])
            if options:
                # Pick first 2 options
                values = [opt['attribute_value'] for opt in options[:2]]
                filters_to_apply[filter_name] = values
                print(f"✓ Applying {filter_name}: {values}")
                break  # Just test with one filter
        
        if not filters_to_apply:
            print("✗ No filters available to test")
            return None
        
        url = f"{self.base_url}{API_PREFIX}/filters/{session_id}"
        payload = {
            "session_id": session_id,
            "filters": filters_to_apply
        }
        
        start_time = time.time()
        response = await self.client.post(url, json=payload)
        elapsed = (time.time() - start_time) * 1000
        
        print(f"Response time: {elapsed:.1f}ms")
        
        if response.status_code == 200:
            result = response.json()
            total = result.get('total_products', 0)
            filtered = result.get('filtered_products_count', 0)
            
            print(f"\n✓ Filters applied!")
            print(f"  Original: {total} products")
            print(f"  Filtered: {filtered} products")
            print(f"  Reduction: {total - filtered} products")
            
            return result
        else:
            print(f"✗ Error: {response.text}")
            return None
    
    async def test_check_status(self, session_id: str) -> Dict[str, Any]:
        """
        Test checking session status.
        
        Expected: Quick lightweight response
        """
        print(f"\n{'='*60}")
        print(f"TEST: Check Status")
        print(f"Session: {session_id[:8]}...")
        print('='*60)
        
        url = f"{self.base_url}{API_PREFIX}/status/{session_id}"
        
        start_time = time.time()
        response = await self.client.get(url)
        elapsed = (time.time() - start_time) * 1000
        
        print(f"Response time: {elapsed:.1f}ms (should be < 50ms)")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Status retrieved")
            print(f"  State: {data['state']}")
            print(f"  Crawling: {data['is_crawling']}")
            print(f"  Total products: {data['total_products']}")
            return data
        else:
            print(f"✗ Error: {response.status_code}")
            return None
    
    async def test_cleanup_session(self, session_id: str) -> bool:
        """
        Test cleaning up a session.
        """
        print(f"\n{'='*60}")
        print(f"TEST: Cleanup Session")
        print(f"Session: {session_id[:8]}...")
        print('='*60)
        
        url = f"{self.base_url}{API_PREFIX}/session/{session_id}"
        response = await self.client.delete(url)
        
        if response.status_code == 200:
            print(f"✓ Session deleted")
            return True
        else:
            print(f"✗ Error: {response.status_code}")
            return False
    
    async def run_full_test(self, query: str) -> bool:
        """
        Run complete test flow for a query.
        """
        # 1. Start search
        start_data = await self.test_start_search(query)
        if not start_data:
            return False
        
        session_id = start_data['session_id']
        
        # 2. Poll results
        results = await self.test_poll_results(session_id)
        if not results:
            return False
        
        # 3. Apply filters (if we have products)
        if results.get('products'):
            await self.test_apply_filters(session_id, start_data)
        
        # 4. Check status
        await self.test_check_status(session_id)
        
        # 5. Cleanup
        await self.test_cleanup_session(session_id)
        
        return True


async def main():
    """Run all tests"""
    tester = ProgressiveSearchTester()
    
    print("\n" + "="*60)
    print("PROGRESSIVE SEARCH - SYSTEM TEST")
    print("="*60)
    
    # Test with first query
    query = TEST_QUERIES[0]
    
    print(f"\nTesting with query: '{query}'")
    print(f"Server: {BASE_URL}")
    
    success = await tester.run_full_test(query)
    
    print("\n" + "="*60)
    if success:
        print("✓ ALL TESTS PASSED")
    else:
        print("✗ TESTS FAILED")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
    except Exception as e:
        print(f"\n\nTest error: {e}")
        import traceback
        traceback.print_exc()
