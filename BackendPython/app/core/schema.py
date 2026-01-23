# app/core/schema.py

from typing import Dict, List, Optional
from pydantic import BaseModel

class AttributeConstraint(BaseModel):
    """Ràng buộc cho một attribute"""
    type: str  # "enum", "range", "text"
    values: Optional[List[str]] = None  # cho enum
    min_val: Optional[float] = None  # cho range
    max_val: Optional[float] = None
    required: bool = False

class CategorySchema(BaseModel):
    """Schema cho một category sản phẩm"""
    name: str
    attributes: Dict[str, AttributeConstraint]
    keywords: List[str]  # Từ khóa để nhận dạng category
    
# ============================================
# SCHEMA CHO GIÀY
# ============================================
GIAY_SCHEMA = CategorySchema(
    name="giày",
    keywords=["giày", "giầy", "shoe", "sneaker", "sandal", "dép"],
    attributes={
        "brand": AttributeConstraint(
            type="enum",
            values=["nike", "adidas", "puma", "reebok", "asics", "new balance", "converse", "vans", "on", "saucony"],
            required=False
        ),
        "dong": AttributeConstraint(
            type="text",
            required=False
        ),
        "gender": AttributeConstraint(
            type="enum",
            values=["nam", "nữ", "unisex"],
            required=False
        ),
        "loai": AttributeConstraint(
            type="enum",
            values=[
                "thể thao", "chạy bộ", "sneaker", 
                "tây", "sandal", "dép", "boot"
            ],
            required=False  # Không bắt buộc -  có thể bỏ qua
        ),
        "muc_dich": AttributeConstraint(
            type="enum",
            values=["văn phòng", "thể thao", "dạo phố", "leo núi", "đi biển"],
            required=False
        ),
        "size": AttributeConstraint(
            type="enum",
            values=["35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45"],
            required=False
        ),
        "mau": AttributeConstraint(
            type="enum",
            values=["đen", "trắng", "nâu", "xanh", "đỏ", "vàng", "hồng", "xám"],
            required=False
        ),
        "chat_lieu": AttributeConstraint(
            type="enum",
            values=["da", "vải", "mesh", "cao su", "synthetic"],
            required=False
        ),
        "gia": AttributeConstraint(
            type="range",
            min_val=0,
            max_val=10000000,
            required=False
        )
    }
)

# ============================================
# SCHEMA CHO BỘT GIẶT (mở rộng)
# ============================================
BOT_GIAT_SCHEMA = CategorySchema(
    name="bột giặt",
    keywords=["bột giặt", "nước giặt", "detergent", "ariel", "omo", "tide"],
    attributes={
        "loai": AttributeConstraint(
            type="enum",
            values=["bột", "nước", "viên nén", "gel"],
            required=True
        ),
        "thuong_hieu": AttributeConstraint(
            type="enum",
            values=["omo", "ariel", "tide", "surf", "comfort"],
            required=False
        ),
        "huong": AttributeConstraint(
            type="enum",
            values=["hương hoa", "hương biển", "không mùi"],
            required=False
        ),
        "dung_tich": AttributeConstraint(
            type="enum",
            values=["1kg", "2kg", "3kg", "5kg", "1L", "2L"],
            required=False
        )
    }
)

# ============================================
# REGISTRY - Tất cả schemas
# ============================================
CATEGORY_REGISTRY = {
    "giày": GIAY_SCHEMA,
    "bột giặt": BOT_GIAT_SCHEMA
    # Thêm category khác ở đây
}

def get_schema(category_name: str) -> Optional[CategorySchema]:
    """Lấy schema theo tên category"""
    return CATEGORY_REGISTRY.get(category_name.lower())

def get_all_categories() -> List[str]:
    """Lấy danh sách tất cả categories"""
    return list(CATEGORY_REGISTRY.keys())