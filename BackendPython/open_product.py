"""
open_product.py - Playwright automation script for opening products

Chạy script: python open_product.py "https://tiki.vn/..."
"""

import asyncio
import sys
import io
from pathlib import Path
from playwright.async_api import async_playwright

# ✅ FIX: Set UTF-8 encoding for stdout (Windows compatibility)
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Chrome profile path
USER_DATA_DIR = r"C:\Users\Admin\AppData\Local\Google\Chrome\User Data"
PROFILE_NAME = "Profile 2"  # ✅ Changed from Profile 1 to Profile 2


async def open_product(product_url: str):
    """
    Open product URL in Chrome and click "Mua ngay" button
    
    Args:
        product_url: URL of the product to open
    """
    print("⚠️  LƯU Ý: Đóng hết Chrome trước khi chạy script!")
    print(f"📂 Đang dùng profile: {USER_DATA_DIR}")
    print(f"🛍️  Product URL: {product_url}")
    
    async with async_playwright() as p:
        try:
            # Try launching with persistent context first
            print("📱 Cố gắng launch browser với persistent context...")
            context = await p.chromium.launch_persistent_context(
                user_data_dir=USER_DATA_DIR,
                headless=False,
                channel="chrome",  # Use installed Chrome, not Chromium
                slow_mo=500,
                args=[
                    f"--profile-directory={PROFILE_NAME}",
                    "--disable-blink-features=AutomationControlled"  # Hide bot signature
                ]
            )
            print("✅ Browser context created successfully")
            
        except Exception as e:
            print(f"⚠️ Persistent context failed: {e}")
            print("📱 Trying regular browser launch instead...")
            
            # Fallback: Launch regular browser (not persistent)
            browser = await p.chromium.launch(
                headless=False,
                channel="chrome",
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox"
                ]
            )
            context = await browser.new_context()
            print("✅ Browser launched with fallback mode")
        
        try:
            # Get first page or create new one
            page = context.pages[0] if context.pages else await context.new_page()
            
            # 1️⃣ Open product page
            print("🔄 Đang mở trang sản phẩm...")
            await page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
            print("✅ Trang đã load")
            
            await asyncio.sleep(3)
            
            # 2️⃣ Click "Mua ngay" button
            print("🔍 Tìm nút 'Mua ngay'...")
            buy_button = page.locator('button:has-text("Mua ngay")').first
            await buy_button.wait_for(state="visible", timeout=10000)
            await buy_button.click()
            print("🛒 Đã click 'Mua ngay'")
            
            # 3️⃣ Keep browser open (don't auto close)
            print("✅ Chrome đã mở - bạn tự xử lý tiếp")
            print("⏳ Giữ script chạy để browser không tắt...")
            
            # Keep browser alive indefinitely
            while True:
                await asyncio.sleep(60)
            
        except Exception as error:
            print(f"❌ Lỗi: {str(error)}")
            try:
                await page.screenshot(path="error_screenshot.png")
                print("📸 Lưu ảnh lỗi: error_screenshot.png")
            except:
                pass
            await asyncio.sleep(15)


if __name__ == "__main__":
    # Get product URL from command line argument
    if len(sys.argv) < 2:
        print("❌ Lỗi: Vui lòng cung cấp product URL")
        print("Cách dùng: python open_product.py 'https://tiki.vn/...'")
        sys.exit(1)
    
    product_url = sys.argv[1]
    
    # Run the async function
    asyncio.run(open_product(product_url))
