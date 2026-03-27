"""
Script example để test Tiki Cart Routes

Cách sử dụng:
1. Lấy TIKI_ACCESS_TOKEN từ browser (F12 → Application → Cookies)
2. Replace 'YOUR_TOKEN_HERE' bằng token thực
3. Python test_tiki_cart_example.py
"""

import requests
import json
from typing import Dict, Any

# =====================
# CONFIGURATION
# =====================

BASE_URL = "http://localhost:8000"
TIKI_ROUTES_PREFIX = f"{BASE_URL}/api/tiki"

# ⚠️ Thay bằng token thực của bạn
TIKI_ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIzMDYwMzI0MCIsImlhdCI6MTc3NDU1MzI4OCwiZXhwIjoxNzc0NjM5Njg4LCJpc3MiOiJodHRwczovL3Rpa2kudm4iLCJjdXN0b21lcl9pZCI6IjMwNjAzMjQwIiwiZW1haWwiOiJhbnRoYWl0cmFuMTAwMUBnbWFpbC5jb20iLCJjbGllbnRfaWQiOiJ0aWtpLXNzbyIsIm5hbWUiOiIzMDYwMzI0MCIsInNjb3BlIjoic3NvIiwiZ3JhbnRfdHlwZSI6Imdvb2dsZSJ9.Y1TxesbvPrA-KSl2i-NBALyc4offZxBfIJF0dt2hmCq5E1JWZALynV1V1p2yrcjiXOyIKcUfkK-oyGY0DsPGvGTPSeCmbf5hKEwT7Y2hM4G5IUaV62o-gOGFaxXfP5l1PniO0afTKGPB8pSmIg90-rErJHlyzrwNMYR9UjKIDLzESty52B5_WBcWP7118E54U0DXQ6kSSdIOZHKL9kCk5XvCRLdQt9Zi8SQOmq8sWBJ24rM7ey925YX0k-0BgC046CSS6wUNQsQRKE9pZrdUADXdzb8ni7Ph6DtJ1cJ588rB6i6A9PMLLlZZqUXh6ItT1jYjGWlAhfraHGQw7Dz0v414AiWsSmzu2EYA3BsuC6yYng82vfiDSIlMeiOTqiHZqL4rbhj9RWflYF-T7uwgffmbWBDqIf51XqEKYsRRnNnShvhZ3M7Sq9hE4EVa1nn9Rz4DpuY0IMImIyTGfQQCt5IjVsb5kcmD_eygsrFK5mi2Nw-d6rsAvyG2zhLvl-yLudvFhLgljcqGLhwRqkmkMBzq_aWYPYcnvDK9VzXTlk5rm6_B8waXiXpn45pnjaV2SYxSqwYVrgisnqZvW394Q8Vyri7THACNpLPtruzNq3A4F0RFxJ7yAwjRyb-0NepNK8Z0knu_HmlbdM93GZDGbcwFeyLFX_H74QSu3x0mdr8"
  # Lấy từ F12 → Cookies → TIKI_ACCESS_TOKEN

# Test product IDs
TEST_PRODUCTS = {
      # Ví dụ từ prompt
    "generic_product": "76467768",  # Thay bằng product ID thực
}


# =====================
# HELPER FUNCTIONS
# =====================

def print_section(title: str):
    """In tiêu đề section"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}\n")


def print_response(response_data: Dict[str, Any], status_code: int = None):
    """Format và in response"""
    if status_code:
        print(f"Status Code: {status_code}")
    print(json.dumps(response_data, indent=2, ensure_ascii=False))
    print()


def test_token_validity():
    """Test 1: Kiểm tra token có hợp lệ không"""
    print_section("TEST 1: Kiểm tra Token Hợp Lệ")
    
    if TIKI_ACCESS_TOKEN == "YOUR_TOKEN_HERE":
        print("⚠️ Vui lòng set TIKI_ACCESS_TOKEN trước!")
        return False
    
    try:
        url = f"{TIKI_ROUTES_PREFIX}/cart/test-token"
        
        print(f"📤 Calling: POST {url}")
        print(f"📦 Token: {TIKI_ACCESS_TOKEN[:50]}...\n")
        
        response = requests.post(
            url,
            json={"access_token": TIKI_ACCESS_TOKEN},
            timeout=10
        )
        
        print_response(response.json(), response.status_code)
        
        # Check result
        if response.json().get("valid"):
            print("✅ Token hợp lệ! Có thể tiếp tục test.\n")
            return True
        else:
            print("❌ Token không hợp lệ. Vui lòng lấy token mới từ browser.\n")
            return False
    
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}\n")
        return False


def add_to_cart_test(product_id: str, qty: int = 1):
    """Test 2: Thêm sản phẩm vào giỏ hàng"""
    print_section(f"TEST 2: Thêm Sản Phẩm ({product_id}) vào Giỏ")
    
    try:
        url = f"{TIKI_ROUTES_PREFIX}/cart/add-to-cart-test"
        
        payload = {
            "product_id": product_id,
            "qty": qty,
            "access_token": TIKI_ACCESS_TOKEN,
            "use_personal_account": True
        }
        
        print(f"📤 Calling: POST {url}")
        print(f"📦 Payload:")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print()
        
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )
        
        data = response.json()
        print_response(data, response.status_code)
        
        if data.get("success"):
            print(f"✅ Thêm sản phẩm thành công!")
            return True
        else:
            print(f"❌ Lỗi: {data.get('message') or data.get('error')}")
            return False
    
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}\n")
        return False


def get_cart_info():
    """Test 3: Lấy thông tin giỏ hàng"""
    print_section("TEST 3: Lấy Thông Tin Giỏ Hàng")
    
    try:
        url = f"{TIKI_ROUTES_PREFIX}/cart/info"
        
        print(f"📤 Calling: GET {url}")
        print(f"📝 Params: access_token=***\n")
        
        response = requests.get(
            url,
            params={"access_token": TIKI_ACCESS_TOKEN},
            timeout=10
        )
        
        data = response.json()
        print_response(data, response.status_code)
        
        if data.get("success"):
            cart_data = data.get("data", {})
            items = cart_data.get("items", [])
            print(f"✅ Giỏ hàng có {len(items)} sản phẩm\n")
            return True
        else:
            print(f"❌ Lỗi: {data.get('message')}")
            return False
    
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}\n")
        return False


def test_invalid_token():
    """Test 4: Test với token không hợp lệ"""
    print_section("TEST 4: Test Error Handling (Invalid Token)")
    
    try:
        url = f"{TIKI_ROUTES_PREFIX}/cart/add-to-cart-test"
        
        payload = {
            "product_id": "999999",
            "qty": 1,
            "access_token": "invalid_token_12345",
            "use_personal_account": True
        }
        
        print(f"📤 Calling: POST {url}")
        print(f"📦 Using invalid token to test error handling\n")
        
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )
        
        data = response.json()
        print_response(data, response.status_code)
        
        if not data.get("success"):
            print("✅ Error handling works correctly!\n")
            return True
        else:
            print("⚠️ Expected error but got success\n")
            return False
    
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}\n")
        return False


def test_missing_fields():
    """Test 5: Test với missing required fields"""
    print_section("TEST 5: Test Validation (Missing Fields)")
    
    try:
        url = f"{TIKI_ROUTES_PREFIX}/cart/add-to-cart-test"
        
        payload = {
            "product_id": "",  # Empty!
            "qty": 1,
            "access_token": TIKI_ACCESS_TOKEN,
        }
        
        print(f"📤 Calling: POST {url}")
        print(f"📦 Testing with empty product_id\n")
        
        response = requests.post(
            url,
            json=payload,
            timeout=10
        )
        
        data = response.json()
        print_response(data, response.status_code)
        
        if not data.get("success"):
            print("✅ Validation works correctly!\n")
            return True
        else:
            print("⚠️ Expected validation error\n")
            return False
    
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}\n")
        return False


# =====================
# MAIN
# =====================

def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("  🛒 TIKI CART ROUTES - TEST SUITE")
    print("="*60)
    print(f"\nBase URL: {BASE_URL}")
    print(f"Routes Prefix: {TIKI_ROUTES_PREFIX}")
    print(f"Token: {TIKI_ACCESS_TOKEN[:50]}..." if TIKI_ACCESS_TOKEN != "YOUR_TOKEN_HERE" else "Token: ⚠️ NOT SET")
    
    # Check if backend is accessible
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        print("\n✅ Backend is accessible\n")
    except:
        print("\n❌ Backend is NOT accessible. Start backend first!")
        print("   python main.py (in BackendPython/)")
        return
    
    # Check if token is set
    if TIKI_ACCESS_TOKEN == "YOUR_TOKEN_HERE":
        print("\n⚠️ TIKI_ACCESS_TOKEN not set!")
        print("   Please paste your actual token from browser cookies.")
        print("   Instructions at: TIKI_CART_ROUTES_GUIDE.md")
        print("\n   Skipping token-dependent tests...\n")
    
    # Run tests
    results = {}
    
    # Test 4 & 5 don't need valid token
    results["test_invalid_token"] = test_invalid_token()
    results["test_missing_fields"] = test_missing_fields()
    
    # These need valid token
    if TIKI_ACCESS_TOKEN != "YOUR_TOKEN_HERE":
        results["test_token_validity"] = test_token_validity()
        
        if results["test_token_validity"]:
            # Only run cart tests if token is valid
            results["add_to_cart"] = add_to_cart_test(
                TEST_PRODUCTS["generic_product"], 
                qty=2
            )
            results["get_cart_info"] = get_cart_info()
    
    # Summary
    print_section("TEST SUMMARY")
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"\nTotal: {passed}/{total} tests passed")
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
