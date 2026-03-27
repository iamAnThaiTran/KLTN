"""
Tiki Cart Routes
Handles testing Tiki cart operations with user's access token
"""

import logging
import requests
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.config.database_orm import get_db
from app.api.auth_middleware import get_current_user_optional

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tiki", tags=["tiki-cart"])

# ===== REQUEST/RESPONSE MODELS =====

class AddToCartRequest(BaseModel):
    """Request to add item to Tiki cart"""
    product_id: str
    qty: int = 1
    access_token: str  # Tiki access token from browser
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "254558",
                "qty": 2,
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class CartResponse(BaseModel):
    """Response from add to cart operation"""
    success: bool
    data: Optional[Dict[Any, Any]] = None
    error: Optional[str] = None
    message: Optional[str] = None


class ProductItem(BaseModel):
    """Single product item to add to cart"""
    product_id: str  # SPID (SKU ID)
    qty: int = 1


class AddToCartTestRequest(BaseModel):
    """Test request with products array and access token
    
    ✅ Format chính xác của Tiki API:
    {
        "products": [
            {"product_id": "276583986", "qty": 1}
        ],
        "access_token": "..."
    }
    """
    products: List[ProductItem]
    access_token: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "products": [
                    {"product_id": "276583986", "qty": 1}
                ],
                "access_token": "eyJhbGciOiJSUzI1NiJ9..."
            }
        }


class TestTokenRequest(BaseModel):
    """Request to test Tiki access token validity"""
    access_token: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


# ===== TIKI API CONFIG =====

TIKI_API_BASE = "https://tiki.vn/api/v2"
TIKI_CART_ENDPOINT = f"{TIKI_API_BASE}/carts/mine/items"

DEFAULT_HEADERS = {
    "Content-Type": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}


# ===== ROUTES =====

@router.post("/cart/add-to-cart-test", response_model=CartResponse)
async def add_to_cart_test(
    request: AddToCartTestRequest,
    user=Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Test adding item to Tiki cart dengan access token cá nhân
    
    ⚠️ **QUAN TRỌNG:** product_id parameter thực chất là **SPID** (SKU ID), không phải product_id!
    
    Cách lấy SPID từ URL Tiki:
    - URL: https://tiki.vn/.../pXXXXXXX.html?spid=SPID
    - SPID = giá trị ?spid=xxx (không phải pXXXXXXX)
    - Ví dụ: https://tiki.vn/.../p76467768.html?spid=276583986
      → SPID = 276583986 (đây cần gửi, không phải 76467768)
    
    Flow:
    1. Nhận product_id (SPID), qty, và access_token từ client
    2. Gọi Tiki API: POST /api/v2/carts/mine/items
    3. Trả về response từ Tiki
    
    **Cách sử dụng:**
    - Mở DevTools (F12) → Application → Cookies
    - Tìm TIKI_ACCESS_TOKEN, copy giá trị
    - Tìm SPID từ URL ?spid=xxx
    - Gửi request với products array
    
    **Đúng format của Tiki API:**
    ```
    POST /api/tiki/cart/add-to-cart-test
    {
        "products": [
            {"product_id": "276583986", "qty": 1}
        ],
        "access_token": "eyJhbGciOiJSUzI1NiJ9..."
    }
    ```
    
    Args:
        request: AddToCartTestRequest với products array + access_token
        user: Current user (optional - for logging)
        db: Database session
    
    Returns:
        CartResponse: success status + response data từ Tiki
    """
    try:
        logger.info(
            f"🛒 Add to cart test from user: {user.id if user else 'Anonymous'} | "
            f"products: {len(request.products)} item(s)"
        )
        
        # Validate
        if not request.products or len(request.products) == 0:
            raise HTTPException(
                status_code=400,
                detail="products array không được để trống"
            )
        
        # Validate each product
        for product in request.products:
            if not product.product_id or not product.product_id.strip():
                raise HTTPException(
                    status_code=400,
                    detail="product_id trong products không được để trống"
                )
            if product.qty <= 0:
                raise HTTPException(
                    status_code=400,
                    detail="qty phải > 0"
                )
        
        if not request.access_token or not request.access_token.strip():
            raise HTTPException(
                status_code=400,
                detail="access_token không được để trống. Lấy từ F12 → Application → Cookies"
            )
        
        # Prepare headers with access token
        headers = DEFAULT_HEADERS.copy()
        headers["x-access-token"] = request.access_token
        
        # Prepare payload - đúng format của Tiki API
        payload = {
            "products": [
                {"product_id": str(p.product_id), "qty": p.qty}
                for p in request.products
            ]
        }
        
        logger.info(f"  📤 Calling Tiki API: POST {TIKI_CART_ENDPOINT}")
        logger.debug(f"  📦 Payload: {payload}")
        
        # Call Tiki API
        response = requests.post(
            TIKI_CART_ENDPOINT,
            headers=headers,
            json=payload,
            timeout=10
        )
        
        logger.info(f"  📥 Tiki response status: {response.status_code}")
        
        # Parse response
        try:
            response_data = response.json()
        except:
            response_data = {"raw_text": response.text}
        
        # Check for errors
        if response.status_code == 401:
            return CartResponse(
                success=False,
                error="UNAUTHORIZED",
                message="Access token hết hạn hoặc không hợp lệ. Lấy token mới từ browser."
            )
        
        if response.status_code == 400:
            error_msg = response_data.get("message") or response_data.get("error") or "Bad request"
            return CartResponse(
                success=False,
                error="INVALID_REQUEST",
                message=f"Lỗi từ Tiki: {error_msg}",
                data=response_data
            )
        
        if response.status_code >= 500:
            return CartResponse(
                success=False,
                error="SERVER_ERROR",
                message="Tiki server error",
                data=response_data
            )
        
        if response.status_code >= 400:
            return CartResponse(
                success=False,
                error="HTTP_ERROR",
                message=f"HTTP {response.status_code}",
                data=response_data
            )
        
        # Success
        logger.info(f"  ✅ Successfully added product to cart")
        return CartResponse(
            success=True,
            data=response_data,
            message="✅ Thêm vào giỏ hàng thành công"
        )
    
    except requests.exceptions.Timeout:
        logger.error("Tiki API timeout")
        return CartResponse(
            success=False,
            error="TIMEOUT",
            message="Request timeout - Tiki server không phản hồi kịp thời"
        )
    
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        return CartResponse(
            success=False,
            error="CONNECTION_ERROR",
            message="Lỗi kết nối - Kiểm tra internet hoặc Tiki có thể chặn request"
        )
    
    except Exception as e:
        logger.error(f"Unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
        return CartResponse(
            success=False,
            error="INTERNAL_ERROR",
            message=f"Lỗi: {str(e)}"
        )


@router.post("/cart/test-token", response_model=Dict[str, Any])
async def test_tiki_token(
    request: TestTokenRequest,
    user=Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Test xem access token có hợp lệ không
    
    Cách sử dụng:
    - Gửi JSON body với access_token
    
    **Example:**
    ```
    POST /api/tiki/cart/test-token
    {
        "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    }
    ```
    
    Returns:
        {
            "valid": true/false,
            "message": "Token hợp lệ/hết hạn",
            "user_info": {...}  // nếu token valid
        }
    """
    try:
        logger.info(f"🔐 Testing token validity")
        
        access_token = request.access_token
        
        if not access_token or not access_token.strip():
            return {
                "valid": False,
                "message": "Token không được để trống"
            }
        
        # Call a simple Tiki API endpoint to check token
        headers = DEFAULT_HEADERS.copy()
        headers["x-access-token"] = access_token
        
        # Use /me or /users/me endpoint to verify token
        test_endpoint = f"{TIKI_API_BASE}/auth/me"
        response = requests.get(test_endpoint, headers=headers, timeout=10)
        
        logger.info(f"  Token validation response: {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            return {
                "valid": True,
                "message": "✅ Token hợp lệ",
                "user_info": user_data
            }
        elif response.status_code == 401:
            return {
                "valid": False,
                "message": "❌ Token hết hạn hoặc không hợp lệ"
            }
        else:
            return {
                "valid": False,
                "message": f"Lỗi: HTTP {response.status_code}",
                "status_code": response.status_code
            }
    
    except Exception as e:
        logger.error(f"Token test error: {str(e)}")
        return {
            "valid": False,
            "message": f"Lỗi: {str(e)}"
        }


@router.get("/cart/info", response_model=Dict[str, Any])
async def get_cart_info(
    access_token: str,
    user=Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """
    Lấy thông tin giỏ hàng hiện tại
    
    Args:
        access_token: Tiki access token
    
    Returns:
        Cart info từ Tiki: items, totals, etc.
    """
    try:
        logger.info(f"🛒 Getting cart info")
        
        if not access_token or not access_token.strip():
            return {
                "success": False,
                "message": "Token không được để trống"
            }
        
        headers = DEFAULT_HEADERS.copy()
        headers["x-access-token"] = access_token
        
        response = requests.get(
            TIKI_CART_ENDPOINT.replace("/items", ""),  # GET /carts/mine instead of /carts/mine/items
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "data": response.json()
            }
        else:
            return {
                "success": False,
                "message": f"HTTP {response.status_code}",
                "error": response.json() if response.status_code < 500 else None
            }
    
    except Exception as e:
        logger.error(f"Error getting cart info: {str(e)}")
        return {
            "success": False,
            "message": f"Lỗi: {str(e)}"
        }
