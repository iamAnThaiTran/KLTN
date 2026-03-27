"""
Simple test: Add to cart với access token + SPID

⚠️ ĐÚNG format từ Tiki API:
{
  "products": [
    {"product_id": "276583986", "qty": 1}
  ]
}

Không phải:
{
  "product_id": "276583986",
  "qty": 1
}
"""

import requests
import json

# =====================
# CONFIG
# =====================

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/api/tiki/cart/add-to-cart-test"

# Paste token thực của bạn
TIKI_ACCESS_TOKEN = "eyJhbGciOiJSUzI1NiJ9.eyJzdWIiOiIzMDYwMzI0MCIsImlhdCI6MTc3NDU1MzI4OCwiZXhwIjoxNzc0NjM5Njg4LCJpc3MiOiJodHRwczovL3Rpa2kudm4iLCJjdXN0b21lcl9pZCI6IjMwNjAzMjQwIiwiZW1haWwiOiJhbnRoYWl0cmFuMTAwMUBnbWFpbC5jb20iLCJjbGllbnRfaWQiOiJ0aWtpLXNzbyIsIm5hbWUiOiIzMDYwMzI0MCIsInNjb3BlIjoic3NvIiwiZ3JhbnRfdHlwZSI6Imdvb2dsZSJ9.Y1TxesbvPrA-KSl2i-NBALyc4offZxBfIJF0dt2hmCq5E1JWZALynV1V1p2yrcjiXOyIKcUfkK-oyGY0DsPGvGTPSeCmbf5hKEwT7Y2hM4G5IUaV62o-gOGFaxXfP5l1PniO0afTKGPB8pSmIg90-rErJHlyzrwNMYR9UjKIDLzESty52B5_WBcWP7118E54U0DXQ6kSSdIOZHKL9kCk5XvCRLdQt9Zi8SQOmq8sWBJ24rM7ey925YX0k-0BgC046CSS6wUNQsQRKE9pZrdUADXdzb8ni7Ph6DtJ1cJ588rB6i6A9PMLLlZZqUXh6ItT1jYjGWlAhfraHGQw7Dz0v414AiWsSmzu2EYA3BsuC6yYng82vfiDSIlMeiOTqiHZqL4rbhj9RWflYF-T7uwgffmbWBDqIf51XqEKYsRRnNnShvhZ3M7Sq9hE4EVa1nn9Rz4DpuY0IMImIyTGfQQCt5IjVsb5kcmD_eygsrFK5mi2Nw-d6rsAvyG2zhLvl-yLudvFhLgljcqGLhwRqkmkMBzq_aWYPYcnvDK9VzXTlk5rm6_B8waXiXpn45pnjaV2SYxSqwYVrgisnqZvW394Q8Vyri7THACNpLPtruzNq3A4F0RFxJ7yAwjRyb-0NepNK8Z0knu_HmlbdM93GZDGbcwFeyLFX_H74QSu3x0mdr8"

# ⚠️ SPID = SKU ID (từ URL ?spid=276583986)
# product_id = 76467768 (từ URL p76467768)
# Tiki API cần SPID không phải product_id!
PRODUCT_ID = "76467768"  # Product ID chung
SPID = "276583986"  # SKU ID từ URL ?spid=xxx
QTY = 1

# =====================
# TEST
# =====================

def test_add_to_cart():
    """Test thêm 1 sản phẩm vào giỏ"""
    
    print("=" * 60)
    print("  🛒 TEST ADD TO CART")
    print("=" * 60)
    print()
    
    # ✅ Đúng format của Tiki API
    payload = {
        "products": [
            {"product_id": SPID, "qty": QTY}
        ],
        "access_token": TIKI_ACCESS_TOKEN,
    }
    
    print(f"📤 POST {ENDPOINT}")
    print()
    print(f"📦 Payload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    print()
    
    try:
        response = requests.post(ENDPOINT, json=payload, timeout=10)
        
        print(f"Status Code: {response.status_code}")
        print()
        
        data = response.json()
        print(f"Response:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
        print()
        
        if data.get("success"):
            print("✅ SUCCESS - Thêm vào giỏ hàng thành công!")
        else:
            print(f"❌ FAILED - {data.get('message') or data.get('error')}")
    
    except requests.exceptions.ConnectionError:
        print("❌ Không kết nối được backend")
        print("   Chạy: poetry run python -m uvicorn main:app")
    except Exception as e:
        print(f"❌ Lỗi: {str(e)}")
    
    print()
    print("=" * 60)
    print()


if __name__ == "__main__":
    test_add_to_cart()
