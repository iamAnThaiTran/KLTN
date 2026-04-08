"""
Integration tests for inter-service communication
Test microservices working together in real scenarios
"""

import asyncio
import httpx
from typing import Dict, Any

# Service URLs
PRODUCT_SERVICE_URL = "http://localhost:8001"
RECOMMENDER_SERVICE_URL = "http://localhost:8002"
CRAWL_SERVICE_URL = "http://localhost:8003"
USER_SERVICE_URL = "http://localhost:8004"

class IntegrationTests:
    """Test inter-service communication scenarios"""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
        self.results = []
    
    async def test_health_checks(self):
        """Test all services are healthy"""
        print("\n🔍 Testing Health Checks...")
        
        services = {
            "ProductService": f"{PRODUCT_SERVICE_URL}/api/health",
            "RecommendatorService": f"{RECOMMENDER_SERVICE_URL}/api/health",
            "CrawlService": f"{CRAWL_SERVICE_URL}/api/health",
            "UserService": f"{USER_SERVICE_URL}/api/health",
        }
        
        for service_name, url in services.items():
            try:
                response = await self.client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    print(f"  ✅ {service_name}: {data.get('status', 'unknown')}")
                    self.results.append({"test": f"{service_name} Health Check", "status": "PASS"})
                else:
                    print(f"  ❌ {service_name}: HTTP {response.status_code}")
                    self.results.append({"test": f"{service_name} Health Check", "status": "FAIL"})
            except Exception as e:
                print(f"  ❌ {service_name}: {str(e)}")
                self.results.append({"test": f"{service_name} Health Check", "status": "FAIL"})
    
    async def test_product_service_search(self):
        """Test ProductService search API"""
        print("\n🔍 Testing ProductService Search...")
        
        try:
            response = await self.client.post(
                f"{PRODUCT_SERVICE_URL}/api/products/search",
                json={
                    "query": "laptop",
                    "category": "electronics",
                    "limit": 10,
                    "offset": 0
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ Search returned {data.get('total', 0)} results")
                self.results.append({"test": "ProductService Search", "status": "PASS"})
            else:
                print(f"  ❌ Search failed with status {response.status_code}")
                self.results.append({"test": "ProductService Search", "status": "FAIL"})
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.results.append({"test": "ProductService Search", "status": "FAIL"})
    
    async def test_user_creation_and_preferences(self):
        """Test UserService create user and set preferences"""
        print("\n🔍 Testing UserService User Creation...")
        
        try:
            # Create user
            create_response = await self.client.post(
                f"{USER_SERVICE_URL}/api/users",
                json={
                    "email": f"test_{int(asyncio.get_event_loop().time())}@example.com",
                    "full_name": "Test User",
                    "password": "testpass123",
                    "provider": "local"
                }
            )
            
            if create_response.status_code == 200:
                user_data = create_response.json()
                user_id = user_data.get("user_id")
                print(f"  ✅ User created: {user_id}")
                self.results.append({"test": "UserService Create User", "status": "PASS"})
                
                # Set preferences
                pref_response = await self.client.put(
                    f"{USER_SERVICE_URL}/api/users/{user_id}/preferences",
                    json={
                        "language": "en",
                        "preferred_currency": "USD",
                        "categories": ["electronics", "smartphones"]
                    }
                )
                
                if pref_response.status_code == 200:
                    print(f"  ✅ User preferences updated")
                    self.results.append({"test": "UserService Update Preferences", "status": "PASS"})
                else:
                    print(f"  ❌ Preferences update failed: {pref_response.status_code}")
                    self.results.append({"test": "UserService Update Preferences", "status": "FAIL"})
            else:
                print(f"  ❌ User creation failed: {create_response.status_code}")
                self.results.append({"test": "UserService Create User", "status": "FAIL"})
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.results.append({"test": "UserService Create User", "status": "FAIL"})
    
    async def test_intent_detection(self):
        """Test RecommendatorService intent detection"""
        print("\n🔍 Testing RecommendatorService Intent Detection...")
        
        try:
            response = await self.client.post(
                f"{RECOMMENDER_SERVICE_URL}/api/intent/detect",
                json={
                    "input": "I want a gaming laptop under 1000 dollars",
                    "context": {"category": "electronics"}
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                intent = data.get("intent_type", "unknown")
                confidence = data.get("confidence", 0)
                print(f"  ✅ Intent detected: {intent} (confidence: {confidence})")
                self.results.append({"test": "RecommendatorService Intent Detection", "status": "PASS"})
            else:
                print(f"  ❌ Intent detection failed: {response.status_code}")
                self.results.append({"test": "RecommendatorService Intent Detection", "status": "FAIL"})
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.results.append({"test": "RecommendatorService Intent Detection", "status": "FAIL"})
    
    async def test_crawl_task_enqueue(self):
        """Test CrawlService task enqueueing"""
        print("\n🔍 Testing CrawlService Task Enqueueing...")
        
        try:
            response = await self.client.post(
                f"{CRAWL_SERVICE_URL}/api/crawl/enqueue",
                json={
                    "category": "smartphone",
                    "category_id": 5,
                    "sources": ["tiki", "lazada"],
                    "priority": "normal",
                    "max_retries": 3
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                task_id = data.get("task_id")
                print(f"  ✅ Task enqueued: {task_id}")
                self.results.append({"test": "CrawlService Enqueue", "status": "PASS"})
                
                # Check task status
                status_response = await self.client.get(
                    f"{CRAWL_SERVICE_URL}/api/crawl/status/{task_id}"
                )
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    status = status_data.get("status", "unknown")
                    print(f"  ✅ Task status: {status}")
                    self.results.append({"test": "CrawlService Status Check", "status": "PASS"})
                else:
                    print(f"  ❌ Status check failed: {status_response.status_code}")
                    self.results.append({"test": "CrawlService Status Check", "status": "FAIL"})
            else:
                print(f"  ❌ Task enqueue failed: {response.status_code}")
                self.results.append({"test": "CrawlService Enqueue", "status": "FAIL"})
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.results.append({"test": "CrawlService Enqueue", "status": "FAIL"})
    
    async def test_product_ranking(self):
        """Test RecommendatorService ranking with sample products"""
        print("\n🔍 Testing RecommendatorService Product Ranking...")
        
        try:
            response = await self.client.post(
                f"{RECOMMENDER_SERVICE_URL}/api/rank",
                json={
                    "products": [
                        {"product_id": "1", "name": "Laptop A", "price": 800, "rating": 4.5},
                        {"product_id": "2", "name": "Laptop B", "price": 1200, "rating": 4.8},
                        {"product_id": "3", "name": "Laptop C", "price": 950, "rating": 4.6},
                    ],
                    "category": "electronics",
                    "weights": {"price": 0.4, "rating": 0.6}
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                ranked = data.get("ranked_products", [])
                print(f"  ✅ Ranked {len(ranked)} products")
                for idx, product in enumerate(ranked[:3], 1):
                    score = product.get("relevance_score", 0)
                    print(f"     {idx}. {product.get('name')} (score: {score:.2f})")
                self.results.append({"test": "RecommendatorService Ranking", "status": "PASS"})
            else:
                print(f"  ❌ Ranking failed: {response.status_code}")
                self.results.append({"test": "RecommendatorService Ranking", "status": "FAIL"})
        except Exception as e:
            print(f"  ❌ Error: {str(e)}")
            self.results.append({"test": "RecommendatorService Ranking", "status": "FAIL"})
    
    async def run_all_tests(self):
        """Run all integration tests"""
        print("\n" + "="*60)
        print("MICROSERVICES INTEGRATION TESTS")
        print("="*60)
        
        await self.test_health_checks()
        await self.test_product_service_search()
        await self.test_user_creation_and_preferences()
        await self.test_intent_detection()
        await self.test_crawl_task_enqueue()
        await self.test_product_ranking()
        
        # Summary
        print("\n" + "="*60)
        print("TEST SUMMARY")
        print("="*60)
        
        passed = sum(1 for r in self.results if r["status"] == "PASS")
        total = len(self.results)
        
        for result in self.results:
            status_symbol = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_symbol} {result['test']}: {result['status']}")
        
        print(f"\nTotal: {passed}/{total} tests passed")
        print("="*60 + "\n")
        
        if passed == total:
            print("🎉 All tests PASSED! Services are working correctly.")
        else:
            print(f"⚠️  {total - passed} test(s) FAILED. Check service logs.")
        
        await self.client.aclose()
        return passed == total


async def main():
    """Run integration tests"""
    tester = IntegrationTests()
    success = await tester.run_all_tests()
    return 0 if success else 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
