"""
Product Comparison Service for Recommender Microservice
Handles:
- Enqueuing product crawl tasks to CrawlService (via RabbitMQ)
- Collecting crawl results
- Calling LLM for comparison analysis
- Building comparison responses
"""

import asyncio
import logging
import json
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ProductComparisonService:
    """
    Service to orchestrate product comparison via microservices
    
    Flow:
    1. Enqueue crawl tasks for each product to CrawlService (RabbitMQ)
    2. Wait for crawl results from database
    3. Build LLM prompt from snapshots
    4. Call LLM for analysis
    5. Return comparison result
    """

    def __init__(self, crawl_service_client=None, llm_utils=None):
        """
        Initialize comparison service
        
        Args:
            crawl_service_client: CrawlServiceClient instance
            llm_utils: LLM utilities for calling OpenAI
        """
        self.crawl_service_client = crawl_service_client
        self.llm_utils = llm_utils
        self.crawl_timeout = int(os.getenv("CRAWL_TIMEOUT", "60"))  # seconds

    async def  compare_products(
        self,
        product_ids: List[int],
        llm_model: str = "gpt-4o-mini",
        seller_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compare multiple products via microservices
        
        Flow:
        1. Enqueue crawl tasks for each product (via CrawlService + RabbitMQ)
        2. Wait for crawl results from database
        3. Build LLM prompt from snapshots
        4. Call LLM for analysis
        5. Return comparison result
        
        Args:
            product_ids: List of product IDs to compare (2-4)
            llm_model: LLM model to use
            seller_id: Optional seller ID
            
        Returns:
            {
                "status": "success" | "error",
                "snapshots": [snapshot_a, snapshot_b, ...],
                "comparison": "Markdown text",
                "prompt": "Full prompt sent to LLM",
                "error": "Error message if status == error"
            }
        """
        try:
            if not self.crawl_service_client:
                raise Exception("CrawlServiceClient not initialized")
            
            if len(product_ids) < 2 or len(product_ids) > 4:
                raise ValueError(f"Expected 2-4 product IDs, got {len(product_ids)}")
            
            logger.info(f"🔍 Starting microservice comparison for products: {product_ids}")
            
            # Step 1: Enqueue crawl tasks
            logger.info(f"📤 Enqueuing crawl tasks for {len(product_ids)} products...")
            crawl_task_ids = []
            
            for idx, product_id in enumerate(product_ids):
                try:
                    task_id = await self.crawl_service_client.enqueue_single_crawl(
                        product_id=product_id,
                        seller_id=seller_id or "1",
                        priority="high"  # Compare tasks have high priority
                    )
                    crawl_task_ids.append({
                        "product_id": product_id,
                        "task_id": task_id,
                        "index": idx
                    })
                    logger.info(f"  ✅ Task {task_id} enqueued for product {product_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to enqueue task for product {product_id}: {e}")
                    raise
            
            # Step 2: Wait for crawl results
            logger.info(f"⏳ Waiting for crawl results (timeout: {self.crawl_timeout}s)...")
            snapshots = {}
            
            try:
                # Wait for all tasks with timeout
                tasks = [
                    self._wait_for_crawl_result(task_info, self.crawl_timeout)
                    for task_info in crawl_task_ids
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                # Process results
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        logger.error(f"❌ Task failed: {result}")
                        raise result
                    
                    if result is None:
                        raise TimeoutError(
                            f"Crawl task for product {crawl_task_ids[idx]['product_id']} timed out"
                        )
                    
                    snapshots[idx] = result
                    logger.info(
                        f"  ✅ Snapshot {idx}: {result.get('name', 'Unknown')[:50]}"
                    )
                
            except Exception as e:
                logger.error(f"❌ Error waiting for crawl results: {e}")
                raise
            
            # Step 3: Build LLM prompt
            logger.info("📝 Building comparison prompt...")
            prompt = self._build_comparison_prompt(list(snapshots.values()))
            
            # Step 4: Call LLM
            logger.info(f"🤖 Calling LLM ({llm_model})...")
            comparison_text = await self._call_llm(
                prompt=prompt,
                model=llm_model
            )
            
            # Step 5: Build and return response
            response = {
                "status": "success",
                "snapshots": list(snapshots.values()),
                "comparison": comparison_text,
                "prompt": prompt,
                "product_ids": product_ids,
                "llm_model": llm_model,
                "completed_at": datetime.utcnow().isoformat(),
            }
            
            logger.info("✅ Comparison completed successfully")
            return response
            
        except Exception as e:
            logger.error(f"❌ Error in compare_products: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "snapshots": None,
                "comparison": None,
                "prompt": None,
                "product_ids": product_ids,
            }

    async def compare_tiki_products(
        self,
        product_a: Dict[str, str],
        product_b: Dict[str, str],
        llm_model: str = "gpt-4o-mini",
    ) -> Dict:
        """
        [DEPRECATED] Legacy method for backward compatibility.
        Use compare_products() instead.
        
        So sánh 2 sản phẩm từ Tiki với LLM (OpenAI).

        Args:
            product_a: {"product_id": "16268021", "spid": "16268022", "seller_id": "1"}
            product_b: {"product_id": "11111111", "spid": "22222222", "seller_id": "1"}
            llm_model: LLM model to use (default: gpt-4o-mini)

        Returns:
            {
                "status": "success" | "error",
                "snapshot_a": {...},           # Full product A snapshot
                "snapshot_b": {...},           # Full product B snapshot
                "prompt": "...",               # Formatted comparison prompt (for debugging)
                "comparison": "...",           # LLM response in Markdown
                "error": "..." (if status == "error")
            }
        """
        logger.warning("⚠️ compare_tiki_products() is deprecated, use compare_products() instead")
        # Convert to new format and call compare_products
        try:
            product_ids = [
                product_a.get("product_id"),
                product_b.get("product_id")
            ]
            result = await self.compare_products(
                product_ids=product_ids,
                llm_model=llm_model,
                seller_id=product_a.get("seller_id")
            )
            
            # Convert response format for backward compatibility
            if result["status"] == "success":
                snapshots = result.get("snapshots", [])
                return {
                    "status": "success",
                    "snapshot_a": snapshots[0] if len(snapshots) > 0 else None,
                    "snapshot_b": snapshots[1] if len(snapshots) > 1 else None,
                    "prompt": result.get("prompt"),
                    "comparison": result.get("comparison"),
                }
            return result
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "snapshot_a": None,
                "snapshot_b": None,
                "prompt": None,
                "comparison": None,
            }

    async def get_single_product_analysis(
        self,
        product_id: str,
        spid: str,
        seller_id: str = "1",
        label: str = "",
    ) -> Dict:
        """
        Lấy phân tích chi tiết của 1 sản phẩm (details + reviews).
        Hữu ích để hiển thị riêng lẻ hoặc cache.

        Args:
            product_id: Tiki product ID
            spid: Tiki seller product ID (SKU)
            seller_id: Seller ID (default: 1 = Tiki official)
            label: Optional label for logging

        Returns:
            {
                "status": "success" | "error",
                "snapshot": {...},      # Full product snapshot
                "error": "..." (if status == "error")
            }
        """
        try:
            logger.info(f"📦 Fetching product snapshot: {product_id}")

            snapshot = await self.crawler.get_product_snapshot(
                product_id=product_id,
                spid=spid,
                seller_id=seller_id,
                label=label,
            )

            return {
                "status": "success",
                "snapshot": snapshot,
            }

        except Exception as e:
            logger.error(f"❌ Product analysis error: {e}")
            return {
                "status": "error",
                "snapshot": None,
                "error": str(e),
            }

    def validate_product_ids(
        self, product_a: Dict[str, str], product_b: Dict[str, str]
    ) -> tuple[bool, str]:
        """
        Validate product IDs before comparison.

        Returns:
            (is_valid, error_message)
        """
        required_fields = ["product_id", "spid", "seller_id"]

        for product_dict, label in [(product_a, "Product A"), (product_b, "Product B")]:
            for field in required_fields:
                if field not in product_dict or not product_dict[field]:
                    return False, f"{label} missing required field: {field}"

        # Check nếu 2 sản phẩm là giống nhau
        if (
            product_a["product_id"] == product_b["product_id"]
            and product_a["spid"] == product_b["spid"]
        ):
            return False, "Cannot compare same product with itself"

        return True, ""

    def format_product_info_for_display(self, snapshot: Dict) -> Dict:
        """
        Format product snapshot cho display/API response.
        Strip ra những field chỉ dùng internally.

        Args:
            snapshot: Full product snapshot from crawler

        Returns:
            Formatted product info suitable for API response
        """
        return {
            "product_id": snapshot.get("product_id"),
            "name": snapshot.get("name"),
            "brand": snapshot.get("brand"),
            "category": snapshot.get("category"),
            "price": snapshot.get("price"),
            "original_price": snapshot.get("original_price"),
            "discount_pct": snapshot.get("discount_pct"),
            "url": snapshot.get("url"),
            "thumbnail": snapshot.get("thumbnail"),
            "rating_avg": snapshot.get("rating_avg"),
            "rating_count": snapshot.get("rating_count"),
            "rating_breakdown": snapshot.get("rating_breakdown"),
            "sizes": snapshot.get("sizes", [])[:10],  # Limit to 10
            "colors": snapshot.get("colors", [])[:10],  # Limit to 10
            "specifications": snapshot.get("specifications", [])[:5],  # Limit to 5 groups
            "review_count": len(snapshot.get("reviews", [])),
            "review_summary": self._summarize_reviews(snapshot.get("reviews", [])),
        }

    def _summarize_reviews(self, reviews: list) -> Dict:
        """
        Create a quick summary of reviews without including full text.

        Args:
            reviews: List of review dicts

        Returns:
            {
                "total": int,
                "avg_rating": float,
                "purchased_count": int,
                "verified_count": int,
            }
        """
        if not reviews:
            return {"total": 0, "avg_rating": 0, "purchased_count": 0, "verified_count": 0}

        total = len(reviews)
        avg_rating = sum(r.get("rating", 0) for r in reviews) / total if total > 0 else 0
        purchased = sum(1 for r in reviews if r.get("is_purchased")) 
        verified = sum(1 for r in reviews if r.get("is_purchased"))

        return {
            "total": total,
            "avg_rating": round(avg_rating, 2),
            "purchased_count": purchased,
            "verified_count": verified,
        }
    
    # ========================================================================
    # Helper Methods for Microservice Comparison
    # ========================================================================
    
    async def _wait_for_crawl_result(
        self,
        task_info: Dict[str, Any],
        timeout: int
    ) -> Optional[Dict[str, Any]]:
        """
        Wait for a crawl task to complete with polling
        
        Args:
            task_info: {"product_id": ..., "task_id": ..., "index": ...}
            timeout: Timeout in seconds
            
        Returns:
            Snapshot dict or None if timeout
        """
        task_id = task_info["task_id"]
        product_id = task_info["product_id"]
        start_time = asyncio.get_event_loop().time()
        poll_count = 0
        
        while True:
            try:
                # Check task status
                result = await self.crawl_service_client.get_task_result(task_id)
                poll_count += 1
                
                if result is None:
                    logger.warning(f"  ⚠️ No response from get_task_result for {task_id}")
                elif result.get("status") == "completed":
                    snapshot = result.get("snapshot")
                    logger.info(f"  ✓ Task {task_id} completed (poll #{poll_count})")
                    return snapshot
                elif result.get("status") == "failed":
                    error_msg = result.get("error", "Unknown error")
                    logger.error(f"  ✗ Task {task_id} failed: {error_msg}")
                    raise Exception(f"Crawl task failed: {error_msg}")
                else:
                    status = result.get("status", "unknown")
                    logger.debug(f"  ⏳ Task {task_id} status: {status} (poll #{poll_count})")
                
                # Check timeout
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    logger.warning(f"⏱️ Task {task_id} timed out after {elapsed:.0f}s ({poll_count} polls)")
                    return None
                
                # Wait before retrying
                await asyncio.sleep(2)
                
            except Exception as e:
                logger.error(f"Error checking task status: {e}")
                raise
    
    def _build_comparison_prompt(self, snapshots: List[Dict[str, Any]]) -> str:
        """
        Build LLM prompt from product snapshots
        
        Args:
            snapshots: List of product snapshots
            
        Returns:
            Formatted prompt string
        """
        prompt_lines = [
            "# So sánh Sản phẩm\n",
            "Vui lòng so sánh chi tiết các sản phẩm sau đây và cung cấp nhận xét khách quan:\n",
        ]
        
        for idx, snapshot in enumerate(snapshots, 1):
            prompt_lines.append(f"\n## Sản phẩm {idx}: {snapshot.get('name', 'Unknown')}")
            prompt_lines.append(f"**Giá:** {snapshot.get('price', 'N/A')} VND")
            prompt_lines.append(f"**Đánh giá:** {snapshot.get('rating_avg', 0)}/5 ({snapshot.get('rating_count', 0)} reviews)")
            
            if snapshot.get('brand'):
                prompt_lines.append(f"**Thương hiệu:** {snapshot['brand']}")
            
            # Specs
            if snapshot.get('specs'):
                prompt_lines.append("\n**Thông số kỹ thuật:**")
                for spec_group in snapshot['specs']:
                    prompt_lines.append(f"- {spec_group.get('group', 'Specs')}")
                    for attr in spec_group.get('attrs', []):
                        if attr.get('value'):
                            prompt_lines.append(f"  - {attr['name']}: {attr['value']}")
            
            # Reviews
            if snapshot.get('reviews'):
                prompt_lines.append(f"\n**Đánh giá từ người dùng (Top 5):**")
                for i, review in enumerate(snapshot['reviews'][:5], 1):
                    prompt_lines.append(
                        f"{i}. ⭐{review.get('rating', 0)} - {review.get('title', 'No title')}\n"
                        f"   {review.get('content', '')[:100]}..."
                    )
        
        prompt_lines.extend([
            "\n## Yêu cầu phân tích:",
            "1. So sánh các điểm nổi bật và yếu điểm",
            "2. Đánh giá tỷ lệ giá/chất lượng",
            "3. Đưa ra khuyến nghị dựa trên các tiêu chí:",
            "   - Tính năng và hiệu năng",
            "   - Chất lượng tổng thể",
            "   - Giá trị cho tiền bỏ ra",
            "   - Đánh giá từ người dùng",
            "4. Kết luận: Sản phẩm nào là lựa chọn tốt nhất và tại sao?",
        ])
        
        return "\n".join(prompt_lines)
    
    async def _call_llm(self, prompt: str, model: str) -> str:
        """
        Call LLM for comparison analysis
        
        Args:
            prompt: Formatted prompt
            model: Model name
            
        Returns:
            LLM response
        """
        if not self.llm_utils:
            logger.warning("LLM utils not initialized, returning mock response")
            return "[LLM response not available]"
        
        try:
            response = await self.llm_utils.call_openai_async(
                prompt=prompt,
                model=model,
                max_tokens=2048,
                temperature=0.7,
            )
            return response or "[No LLM response]"
        except Exception as e:
            logger.error(f"LLM call failed: {e}")
            raise
