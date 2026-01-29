# app/core/dialogue.py

from typing import Dict, Any, List
from .schema import get_schema, get_all_categories

class DialogueManager:
    """Quản lý hội thoại với user khi thiếu thông tin"""
    
    def generate_question(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate câu hỏi dựa trên state hiện tại
        
        state = {
            "has_category": bool,
            "category": str,
            "extracted": {},
            "missing_required": [],
            "user_input": str
        }
        
        Returns:
            {
                "question": str,
                "options": [{"label": str, "value": str}],
                "question_type": "category" | "attribute",
                "next_step": str
            }
        """
        
        # Case 1: Không có category
        if not state.get("has_category"):
            return self._ask_category(state.get("user_input", ""))
        
        # Case 2: Có category nhưng thiếu required attributes
        if state.get("missing_required"):
            return self._ask_required_attributes(
                state["category"],
                state["missing_required"],
                state.get("extracted", {})
            )
        
        # Case 3: Có đủ required nhưng có thể hỏi thêm optional để tốt hơn
        return self._ask_optional_attributes(
            state["category"],
            state.get("extracted", {})
        )
    
    def _ask_category(self, user_input: str, intent_map: Dict[str, Any] = None) -> Dict[str, Any]:
        """Hỏi user muốn mua gì (khi không detect được category)
        
        Args:
            user_input: User's text input
            intent_map: Optional - pre-detected intent + filtered categories
                {"intent": str, "categories": [list], "confidence": float}
        """
        
        # If intent was pre-detected → use SMART question with filtered categories
        if intent_map and intent_map.get("intent") and intent_map.get("categories"):
            # Use intent mapper's smart question
            from .intent_mapper import IntentMapper
            mapper = IntentMapper()
            return mapper.get_fallback_question(
                intent_map["intent"],
                intent_map["categories"]
            )
        
        # Fallback: Generic question (when no intent detected or intent_map not provided)
        question = "Bạn đang tìm loại sản phẩm nào?"
        
        categories = get_all_categories()
        
        return {
            "question": question,
            "options": [
                {"label": cat.capitalize(), "value": cat}
                for cat in categories
            ],
            "question_type": "category",
            "next_step": "extract_attributes"
        }
    
    def _ask_required_attributes(
        self, 
        category: str, 
        missing: List[str],
        extracted: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Hỏi về required attributes còn thiếu"""
        
        schema = get_schema(category)
        
        # Hỏi attribute đầu tiên trong missing
        attr_name = missing[0]
        
        # Handle KeyError: attribute không tồn tại trong schema
        if attr_name not in schema.attributes:
            print(f"DEBUG: Attribute '{attr_name}' not in schema for category '{category}'")
            print(f"DEBUG: Available attributes: {list(schema.attributes.keys())}")
            # Skip this attribute và hỏi attribute khác
            return {
                "question": f"Vui lòng cung cấp thêm thông tin",
                "options": [],
                "question_type": "open",
                "attribute_name": attr_name,
                "skipped": True  # Mark as skipped
            }
        
        constraint = schema.attributes[attr_name]
        
        # Tạo câu hỏi thân thiện
        question_map = {
            "loai": f"Bạn cần {category} loại nào?",
            "gender": "Bạn cần giày nam hay nữ?",
            "size": "Size giày của bạn là bao nhiêu?",
            "muc_dich": "Bạn dùng để làm gì?"
        }
        
        question = question_map.get(
            attr_name, 
            f"Bạn muốn {attr_name} như thế nào?"
        )
        
        # Tạo options từ enum values
        options = []
        if constraint.type == "enum":
            options = [
                {"label": val.capitalize(), "value": val}
                for val in constraint.values
            ]
        
        return {
            "question": question,
            "options": options,
            "question_type": "attribute",
            "attribute_name": attr_name,
            "next_step": "check_complete" if len(missing) == 1 else "ask_more"
        }
    
    def _ask_optional_attributes(
        self, 
        category: str,
        extracted: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Hỏi optional attributes để refine kết quả
        (Chỉ hỏi 1-2 cái quan trọng nhất)
        """
        
        schema = get_schema(category)
        
        # Tìm optional attributes chưa có
        optional = [
            attr for attr, constraint in schema.attributes.items()
            if not constraint.required and attr not in extracted
        ]
        
        if not optional:
            # Đủ info rồi, không cần hỏi thêm
            return {
                "question": None,
                "next_step": "search"
            }
        
        # Hỏi attribute quan trọng nhất (theo thứ tự ưu tiên)
        priority = ["size", "mau", "gia", "muc_dich"]
        
        for attr in priority:
            if attr in optional:
                constraint = schema.attributes[attr]
                
                return {
                    "question": f"Bạn có muốn chọn {attr} cụ thể không? (Có thể bỏ qua)",
                    "options": [
                        {"label": "Bỏ qua", "value": "skip"}
                    ] + [
                        {"label": val, "value": val}
                        for val in constraint.values
                    ] if constraint.type == "enum" else [],
                    "question_type": "optional",
                    "attribute_name": attr,
                    "next_step": "search"
                }
        
        # Không có gì để hỏi
        return {
            "question": None,
            "next_step": "search"
        }

    def generate_clarifying_hints(
        self,
        category: str,
        extracted: Dict[str, Any]
    ) -> List[str]:
        """
        Generate 2-3 clarifying hints để refine search khi có category + partial attributes
        
        Logic:
        1. Lấy schema của category
        2. Xem attribute nào thiếu (required hoặc important optional)
        3. Generate friendly questions từ missing attributes
        4. Return danh sách 2-3 hints
        
        Args:
            category: Tên category (e.g., "giày")
            extracted: Đã extract được attributes nào (e.g., {"loai": "thể thao"})
        
        Returns:
            List of hints, e.g.:
            ["👟 Giày nam hay nữ?", "🏃 Dùng cho mục đích nào?", "💰 Giá bao nhiêu?"]
        """
        
        schema = get_schema(category)
        if not schema:
            return []
        
        hints = []
        
        # Priority: attributes cần hỏi (required + important optional)
        priority_attrs = [
            ("gender", "👟 Giày nam hay nữ?"),
            ("muc_dich", "🎯 Dùng cho mục đích nào?"),
            ("size", "📏 Size của bạn là bao nhiêu?"),
            ("loai", "🏷️ Loại nào bạn thích?"),
            ("gia", "💰 Giá bao nhiêu?"),
            ("mau", "🎨 Màu sắc ưa thích?"),
            ("material", "🧵 Chất liệu như thế nào?"),
            ("brand", "🏢 Thương hiệu nào?")
        ]
        
        # Xem attribute nào thiếu
        missing_important = []
        for attr_key, hint_text in priority_attrs:
            # Nếu attribute này trong schema và chưa extract được, thêm vào missing
            if attr_key in schema.attributes and attr_key not in extracted:
                constraint = schema.attributes[attr_key]
                # Ưu tiên required attributes trước
                if constraint.required or attr_key in ["gender", "muc_dich"]:
                    missing_important.append(hint_text)
        
        # Trả về 2-3 hints (hoặc ít hơn nếu không có đủ)
        hints = missing_important[:3]
        
        return hints