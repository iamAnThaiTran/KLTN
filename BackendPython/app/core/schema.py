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
            values=["nike", "adidas", "puma", "reebok", "asics", "new balance", "converse", "vans", "on", "saucony", "chưa rõ"],
            required=False
        ),
        "dong": AttributeConstraint(
            type="text",
            required=False
        ),
        "gender": AttributeConstraint(
            type="enum",
            values=["nam", "nữ", "unisex", "chưa rõ"],
            required=False
        ),
        "loai": AttributeConstraint(
            type="enum",
            values=[
                "thể thao", "chạy bộ", "sneaker", 
                "tây", "sandal", "dép", "boot", "chưa rõ"
            ],
            required=False
        ),
        "muc_dich": AttributeConstraint(
            type="enum",
            values=["văn phòng", "thể thao", "dạo phố", "leo núi", "đi biển", "chưa rõ"],
            required=False
        ),
        "size": AttributeConstraint(
            type="enum",
            values=["35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "chưa rõ"],
            required=False 
        ),
        "mau": AttributeConstraint(
            type="enum",
            values=["đen", "trắng", "nâu", "xanh", "đỏ", "vàng", "hồng", "xám", "chưa rõ"],
            required=False
        ),
        "chat_lieu": AttributeConstraint(
            type="enum",
            values=["da", "vải", "mesh", "cao su", "synthetic", "chưa rõ"],
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
# SCHEMA CHO QUÀ TẶNG
# ============================================
QUA_TANG_SCHEMA = CategorySchema(
    name="quà tặng",
    keywords=["quà", "quà tặng", "gift", "present", "tặng", "món quà"],
    attributes={
        "loai": AttributeConstraint(
            type="enum",
            values=["quần áo", "giày", "phụ kiện", "mỹ phẩm", "sách", "đồ chơi", "phần cứng", "hoa", "kẹo", "khác"],
            required=False
        ),
        "gia_tien": AttributeConstraint(
            type="range",
            min_val=0,
            max_val=50000000,
            required=False
        ),
        "doi_tuong": AttributeConstraint(
            type="enum",
            values=["bạn gái", "bạn trai", "bạn", "chị", "anh", "ba", "mẹ", "em", "bé"],
            required=False
        ),
        "su_kien": AttributeConstraint(
            type="enum",
            values=["sinh nhật", "ngày kỷ niệm", "valentine", "8/3", "20/10", "tết", "tốt nghiệp", "khác"],
            required=False
        ),
        "chat_lieu": AttributeConstraint(
            type="enum",
            values=["da", "vải", "nhôm", "gỗ", "nhựa", "giấy", "khác"],
            required=False
        )
    }
)

# ============================================
# SCHEMA CHO BẢO CAO SU
# ============================================
BAO_CAO_SU_SCHEMA = CategorySchema(
    name="bao cao su",
    keywords=["bao cao su", "condom", "bcs", "tránh thai"],
    attributes={
        "brand": AttributeConstraint(
            type="enum",
            values=["durex", "trojan", "okamoto", "lelo", "pasante", "chưa rõ"],
            required=False
        ),
        "size": AttributeConstraint(
            type="enum",
            values=["S", "M", "L", "XL", "chưa rõ"],
            required=False
        ),
        "loai": AttributeConstraint(
            type="enum",
            values=["cơ bản", "siêu mỏng", "giãn rộng", "kích thích", "tự sáng", "gân gợn", "chưa rõ"],
            required=False
        ),
        "so_luong": AttributeConstraint(
            type="enum",
            values=["1 cái", "3 cái", "10 cái", "20 cái", "50 cái", "100 cái"],
            required=False
        ),
        "gia": AttributeConstraint(
            type="range",
            min_val=0,
            max_val=500000,
            required=False
        )
    }
)

# ============================================
# SCHEMA CHO ÁO
# ============================================
AO_SCHEMA = CategorySchema(
    name="áo",
    keywords=["áo", "áo phông", "áo sơ mi", "áo khoác", "shirt", "t-shirt"],
    attributes={
        "brand": AttributeConstraint(
            type="enum",
            values=["nike", "adidas", "puma", "gucci", "h&m", "zara", "chưa rõ"],
            required=False
        ),
        "loai": AttributeConstraint(
            type="enum",
            values=["áo phông", "áo sơ mi", "áo khoác", "áo len", "áo dệt kim", "chưa rõ"],
            required=False
        ),
        "mau": AttributeConstraint(
            type="enum",
            values=["đen", "trắng", "xanh", "đỏ", "vàng", "hồng", "xám", "nâu", "chưa rõ"],
            required=False
        ),
        "size": AttributeConstraint(
            type="enum",
            values=["XS", "S", "M", "L", "XL", "XXL", "XXXL", "chưa rõ"],
            required=False
        ),
        "chat_lieu": AttributeConstraint(
            type="enum",
            values=["bông", "vải", "tơ lụa", "polyester", "kén", "vải blended", "chưa rõ"],
            required=False
        ),
        "gender": AttributeConstraint(
            type="enum",
            values=["nam", "nữ", "unisex", "chưa rõ"],
            required=False
        ),
        "gia": AttributeConstraint(
            type="range",
            min_val=0,
            max_val=5000000,
            required=False
        )
    }
)

# ============================================
# SCHEMA CHO TÚI XÁCH
# ============================================
TUI_XACH_SCHEMA = CategorySchema(
    name="túi xách",
    keywords=["túi", "túi xách", "balo", "túi đeo", "backpack", "handbag"],
    attributes={
        "brand": AttributeConstraint(
            type="enum",
            values=["gucci", "louis vuitton", "coach", "mk", "charles & keith", "zara", "chưa rõ"],
            required=False
        ),
        "loai": AttributeConstraint(
            type="enum",
            values=["túi xách", "balo", "túi đeo chéo", "túi du lịch", "clutch", "chưa rõ"],
            required=False
        ),
        "mau": AttributeConstraint(
            type="enum",
            values=["đen", "nâu", "trắng", "xanh", "đỏ", "hồng", "xám", "chưa rõ"],
            required=False
        ),
        "chat_lieu": AttributeConstraint(
            type="enum",
            values=["da", "vải", "nylon", "canvas", "pvc", "chưa rõ"],
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
# SCHEMA CHO MỸ PHẨM
# ============================================
MY_PHAM_SCHEMA = CategorySchema(
    name="mỹ phẩm",
    keywords=["mỹ phẩm", "skincare", "trang điểm", "makeup", "cosmetics", "mascara", "lipstick"],
    attributes={
        "loai": AttributeConstraint(
            type="enum",
            values=["trang điểm", "dưỡng da", "chăm sóc tóc", "nước hoa", "sữa tắm", "chưa rõ"],
            required=False
        ),
        "brand": AttributeConstraint(
            type="enum",
            values=["maybelline", "mac", "estee lauder", "loreal", "shiseido", "lancome", "chưa rõ"],
            required=False
        ),
        "muc_dich": AttributeConstraint(
            type="enum",
            values=["làm đẹp da", "chăm sóc lão hóa", "trị mụn", "làm trắng", "dưỡng ẩm", "chưa rõ"],
            required=False
        ),
        "loai_da": AttributeConstraint(
            type="enum",
            values=["da khô", "da dầu", "da hỗn hợp", "da nhạy cảm", "chưa rõ"],
            required=False
        ),
        "gia": AttributeConstraint(
            type="range",
            min_val=0,
            max_val=3000000,
            required=False
        )
    }
)

# ============================================
# REGISTRY - Tất cả schemas
# ============================================
CATEGORY_REGISTRY = {
    "giày": GIAY_SCHEMA,
    "bột giặt": BOT_GIAT_SCHEMA,
    "quà tặng": QUA_TANG_SCHEMA,
    "bao cao su": BAO_CAO_SU_SCHEMA,
    "áo": AO_SCHEMA,
    "túi xách": TUI_XACH_SCHEMA,
    "mỹ phẩm": MY_PHAM_SCHEMA,
}

def get_schema(category_name: str) -> Optional[CategorySchema]:
    """Lấy schema theo tên category"""
    return CATEGORY_REGISTRY.get(category_name.lower())

def get_all_categories() -> List[str]:
    """Lấy danh sách tất cả categories"""
    return list(CATEGORY_REGISTRY.keys())