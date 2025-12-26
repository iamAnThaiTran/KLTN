"""
Generator tạo synthetic data cho hệ thống gợi ý sản phẩm tiếng Việt
Tạo 10,000+ mẫu training data realistic
"""

import random
import json
from typing import List, Dict, Tuple
from itertools import product as itertools_product

# ============================================
# 1. KNOWLEDGE BASES - Core data structures
# ============================================

# Product catalog (mở rộng từ thực tế)
PRODUCT_CATALOG = {
    "electronics": {
        "phones": [
            "Điện thoại {brand} {model} {ram}/{storage}",
            "{brand} {model} {ram}GB RAM {storage}GB",
            "Smartphone {brand} {model} Chính hãng",
        ],
        "brands": ["Samsung", "iPhone", "Xiaomi", "OPPO", "Vivo", "Realme", "OnePlus"],
        "models": {
            "Samsung": ["Galaxy S24", "Galaxy A54", "Galaxy Z Fold 5", "Galaxy M34"],
            "iPhone": ["15 Pro Max", "15", "14 Pro", "13", "SE 2022"],
            "Xiaomi": ["Redmi Note 13", "Mi 14", "Poco X6", "13T Pro"],
            "OPPO": ["Reno 11", "Find N3", "A78", "Reno 10"],
        },
        "specs": {
            "ram": ["4GB", "6GB", "8GB", "12GB", "16GB"],
            "storage": ["64GB", "128GB", "256GB", "512GB", "1TB"]
        }
    },
    
    "laptops": {
        "templates": [
            "Laptop {brand} {model} {cpu}/{ram}/{storage}",
            "{brand} {model} {screen} {cpu} {ram}",
            "Máy tính xách tay {brand} {model} Chính hãng",
        ],
        "brands": ["Dell", "HP", "Lenovo", "Asus", "Acer", "MSI", "MacBook"],
        "models": {
            "Dell": ["XPS 13", "XPS 15", "Inspiron 15", "Latitude 5430", "G15 Gaming"],
            "HP": ["Pavilion 15", "Envy 13", "Omen 16", "EliteBook 840"],
            "Asus": ["VivoBook 15", "ZenBook 14", "ROG Strix G15", "TUF Gaming"],
            "MacBook": ["Air M2", "Pro 14 M3", "Pro 16 M3 Max"],
        },
        "specs": {
            "cpu": ["i5-1335U", "i7-13700H", "Ryzen 5 7530U", "Ryzen 7 7735HS", "M2", "M3"],
            "ram": ["8GB", "16GB", "32GB", "64GB"],
            "storage": ["256GB SSD", "512GB SSD", "1TB SSD"],
            "screen": ["13.3 inch", "14 inch", "15.6 inch", "16 inch"]
        }
    },
    
    "fashion": {
        "categories": {
            "áo": ["Áo thun", "Áo sơ mi", "Áo khoác", "Áo len", "Áo blazer"],
            "quần": ["Quần jean", "Quần tây", "Quần short", "Quần jogger"],
            "giày": ["Giày sneaker", "Giày boot", "Giày lười", "Dép sandal"],
            "túi": ["Túi xách", "Balo", "Ví", "Clutch"],
        },
        "brands": ["Zara", "H&M", "Uniqlo", "Nike", "Adidas", "Gucci", "Louis Vuitton"],
        "materials": ["cotton", "kaki", "jean", "da", "vải", "lụa"],
        "colors": ["đen", "trắng", "xanh navy", "be", "đỏ", "xám", "hồng pastel"]
    },
    
    "cosmetics": {
        "categories": {
            "skincare": ["Sữa rửa mặt", "Toner", "Serum", "Kem dưỡng", "Kem chống nắng", "Mặt nạ"],
            "makeup": ["Son môi", "Phấn nền", "Mascara", "Phấn má", "Eyeliner"],
            "perfume": ["Nước hoa nam", "Nước hoa nữ", "Nước hoa unisex"],
        },
        "brands": ["Innisfree", "The Ordinary", "L'Oreal", "Maybelline", "MAC", "Chanel", "Dior"],
    },
    
    "home": {
        "categories": ["Nồi", "Chảo", "Máy pha cà phê", "Máy hút bụi", "Quạt", "Đèn", "Đồ trang trí"],
        "brands": ["Sunhouse", "Panasonic", "Philips", "Xiaomi", "Lock&Lock"],
    }
}

# Occasions và recipient mapping
OCCASIONS = {
    "sinh nhật": {
        "recipients": {
            "bạn gái": {
                "age_groups": ["18-25", "26-35", "36+"],
                "preferences": ["romantic", "luxury", "practical", "cute"],
                "products": [
                    ("cosmetics", "perfume", "Nước hoa nữ {brand} EDT 100ml"),
                    ("fashion", "túi", "Túi xách {brand} da cao cấp"),
                    ("jewelry", None, "Vòng tay bạc 925 {style}"),
                    ("cosmetics", "makeup", "Son môi {brand} màu {color}"),
                ]
            },
            "bạn trai": {
                "preferences": ["sporty", "tech", "fashion", "practical"],
                "products": [
                    ("electronics", "watches", "Đồng hồ nam {brand} {style}"),
                    ("fashion", "giày", "Giày sneaker {brand} phiên bản mới"),
                    ("cosmetics", "perfume", "Nước hoa nam {brand} EDT mạnh mẽ"),
                    ("electronics", "accessories", "Tai nghe {brand} chống ồn cao cấp"),
                ]
            },
            "mẹ": {
                "age_groups": ["40-50", "50-60", "60+"],
                "preferences": ["health", "comfort", "practical", "traditional"],
                "products": [
                    ("health", None, "Máy massage cổ vai gáy {brand}"),
                    ("cosmetics", "skincare", "Set dưỡng da chống lão hóa {brand}"),
                    ("home", None, "Máy xay sinh tố đa năng {brand}"),
                    ("fashion", None, "Khăn lụa cao cấp họa tiết hoa"),
                ]
            },
            "bố": {
                "preferences": ["health", "tech", "traditional", "hobby"],
                "products": [
                    ("electronics", None, "Máy đo huyết áp điện tử {brand}"),
                    ("fashion", None, "Ví da nam {brand} cao cấp"),
                    ("beverages", None, "Rượu {brand} {year} năm hộp quà"),
                    ("electronics", "watches", "Đồng hồ nam {brand} lịch lãm"),
                ]
            },
            "sếp nam": {
                "preferences": ["luxury", "professional", "traditional"],
                "products": [
                    ("office", None, "Bút ký {brand} cao cấp"),
                    ("beverages", None, "Set rượu whisky {brand} {year} năm"),
                    ("office", None, "Bộ phụ kiện bàn làm việc gỗ óc chó"),
                    ("art", None, "Tranh phong thủy Thuận Buồm Xuôi Gió"),
                ]
            },
            "sếp nữ": {
                "preferences": ["luxury", "elegant", "professional"],
                "products": [
                    ("cosmetics", "perfume", "Nước hoa {brand} sang trọng"),
                    ("fashion", "túi", "Túi xách {brand} công sở cao cấp"),
                    ("office", None, "Bộ trà gốm sứ Nhật Bản tinh xảo"),
                    ("jewelry", None, "Vòng tay {brand} mạ vàng 18K"),
                ]
            },
            "con trai": {
                "age_groups": ["3-5", "6-10", "11-15"],
                "products": [
                    ("toys", None, "Đồ chơi LEGO {theme} {piece} chi tiết"),
                    ("toys", None, "Xe điều khiển từ xa {type}"),
                    ("sports", None, "Bóng đá size {size} {brand}"),
                    ("electronics", "games", "Máy chơi game cầm tay"),
                ]
            },
            "con gái": {
                "age_groups": ["3-5", "6-10", "11-15"],
                "products": [
                    ("toys", None, "Búp bê Barbie {theme}"),
                    ("toys", None, "Đồ chơi nấu ăn bằng gỗ"),
                    ("fashion", None, "Balo học sinh hình {character}"),
                    ("books", None, "Bộ truyện {title} tranh màu"),
                ]
            },
        }
    },
    
    "tốt nghiệp": {
        "recipients": {
            "bạn": ["Đồng hồ đeo tay", "Balo laptop", "Sách tự phát triển"],
            "em": ["Laptop", "Tablet", "Loa bluetooth"],
        }
    },
    
    "cưới": {
        "recipients": {
            "đồng nghiệp": ["Bộ chăn ga gối", "Nồi cơm điện", "Lò vi sóng"],
            "bạn thân": ["Mâm quả cưới", "Phong bì", "Set đồ gia dụng"],
        }
    },
    
    "thăng chức": {
        "recipients": {
            "sếp": ["Rượu cao cấp", "Tranh phong thủy", "Bút ký xa xỉ"],
            "đồng nghiệp": ["Hoa chúc mừng", "Bánh kem", "Cây cảnh phong thủy"],
        }
    }
}

# Attributes mapping
ATTRIBUTES = {
    "mạnh mẽ": {
        "keywords": ["powerful", "strong", "bold", "aggressive", "masculine"],
        "products": [
            "Xe máy {brand} {model} thể thao",
            "Nước hoa nam {brand} mùi hương nam tính",
            "Giày boot {brand} da cao cổ",
            "Đồng hồ G-Shock chống nước 200m",
            "Loa bluetooth bass cực mạnh",
        ]
    },
    
    "mềm mại": {
        "keywords": ["soft", "gentle", "delicate", "feminine", "smooth"],
        "products": [
            "Áo len cashmere {color} mềm mịn",
            "Nước hoa {brand} hương hoa nhẹ nhàng",
            "Chăn lông cừu Tencel siêu mềm",
            "Túi xách da mềm {brand}",
        ]
    },
    
    "sang trọng": {
        "keywords": ["luxury", "elegant", "premium", "sophisticated"],
        "products": [
            "Đồng hồ {brand} Swiss Made",
            "Túi xách {brand} da thật cao cấp",
            "Nước hoa {brand} dòng Prestige",
            "Bút ký {brand} mạ vàng 18K",
        ]
    },
    
    "tiện lợi": {
        "keywords": ["convenient", "practical", "efficient", "handy"],
        "products": [
            "Bàn nâng hạ điện tự động",
            "Robot hút bụi lau nhà tự động",
            "Máy pha cà phê tự động {brand}",
            "Lò nướng đa năng {brand}",
        ]
    },
    
    "năng động": {
        "keywords": ["active", "energetic", "sporty", "dynamic"],
        "products": [
            "Giày chạy bộ {brand} {model}",
            "Đồng hồ thể thao GPS {brand}",
            "Balo leo núi {brand} {size}L",
            "Áo thun thể thao {brand} thoát mồ hôi",
        ]
    },
    
    "thư giãn": {
        "keywords": ["relaxing", "calming", "peaceful", "soothing"],
        "products": [
            "Máy khuếch tán tinh dầu {brand}",
            "Ghế massage toàn thân {brand}",
            "Võng xếp du lịch siêu nhẹ",
            "Bộ pha trà Kung Fu gốm sứ",
        ]
    }
}

# Vietnamese query patterns (cách người Việt hỏi thực tế)
QUERY_PATTERNS = {
    "direct": [
        "{product}",
        "tìm {product}",
        "mua {product}",
        "{product} giá rẻ",
        "{product} chính hãng",
        "cho tôi xem {product}",
        "có {product} không",
        "{product} loại nào tốt",
    ],
    
    "occasion": [
        "mua quà {occasion} cho {recipient}",
        "tặng gì cho {recipient} vào {occasion}",
        "gợi ý quà {occasion} {recipient}",
        "chọn quà {occasion} cho {recipient} như thế nào",
        "quà {occasion} {recipient} nên mua gì",
        "tôi muốn tặng {recipient} nhân dịp {occasion}",
        "{occasion} {recipient} tặng quà gì ý nghĩa",
        "cần tư vấn quà {occasion} cho {recipient}",
        "quà {occasion} phù hợp với {recipient}",
    ],
    
    "attribute": [
        "tôi muốn thứ gì đó {attribute}",
        "cần thứ {attribute}",
        "tìm sản phẩm {attribute}",
        "gợi ý đồ {attribute}",
        "có gì {attribute} không",
        "muốn mua đồ {attribute} để {purpose}",
        "tìm món đồ {attribute} {attribute2}",
        "cần thứ vừa {attribute} vừa {attribute2}",
    ]
}

# ============================================
# 2. GENERATION FUNCTIONS
# ============================================
format_dict = {
    "brand": "Premium",
    "style": "sang trọng",
    "color": "đen",
    "year": "12",        # ← Thêm year
    "theme": "...",      # ← Thêm theme cho LEGO
    "piece": "500",      # ← Thêm piece
    "type": "...",       # ← Thêm type cho xe RC
    # ... etc
}
def generate_direct_samples(n=3000) -> List[Dict]:
    """Generate samples cho intent: direct product search"""
    samples = []
    
    # Electronics - Phones
    for _ in range(n // 3):
        brand = random.choice(PRODUCT_CATALOG["electronics"]["brands"])
        if brand in PRODUCT_CATALOG["electronics"]["models"]:
            model = random.choice(PRODUCT_CATALOG["electronics"]["models"][brand])
            ram = random.choice(PRODUCT_CATALOG["electronics"]["specs"]["ram"])
            storage = random.choice(PRODUCT_CATALOG["electronics"]["specs"]["storage"])
            
            pattern = random.choice(QUERY_PATTERNS["direct"])
            query_base = f"điện thoại {brand.lower()} {model.lower()}"
            query = pattern.format(product=query_base)
            
            template = random.choice(PRODUCT_CATALOG["electronics"]["phones"])
            products = [
                template.format(brand=brand, model=model, ram=ram, storage=storage),
                template.format(brand=brand, model=model, ram=ram, storage=random.choice([s for s in PRODUCT_CATALOG["electronics"]["specs"]["storage"] if s != storage])),
                f"Điện thoại {brand} {model} Chính hãng - {storage}",
            ]
            
            samples.append({
                "intent": "direct",
                "input": query,
                "context": {
                    "category": "electronics",
                    "subcategory": "phones",
                    "brand": brand,
                    "model": model
                },
                "products": products[:random.randint(2, 3)]
            })
    
    # Laptops
    for _ in range(n // 3):
        brand = random.choice(PRODUCT_CATALOG["laptops"]["brands"])
        if brand in PRODUCT_CATALOG["laptops"]["models"]:
            model = random.choice(PRODUCT_CATALOG["laptops"]["models"][brand])
            cpu = random.choice(PRODUCT_CATALOG["laptops"]["specs"]["cpu"])
            ram = random.choice(PRODUCT_CATALOG["laptops"]["specs"]["ram"])
            storage = random.choice(PRODUCT_CATALOG["laptops"]["specs"]["storage"])
            
            pattern = random.choice(QUERY_PATTERNS["direct"])
            query = pattern.format(product=f"laptop {brand.lower()} {model.lower()}")
            
            template = random.choice(PRODUCT_CATALOG["laptops"]["templates"])
            products = [
                template.format(brand=brand, model=model, cpu=cpu, ram=ram, storage=storage, screen="15.6 inch"),
                f"Laptop {brand} {model} Chính hãng {cpu}/{ram}",
                f"{brand} {model} {cpu} {ram} {storage}",
            ]
            
            samples.append({
                "intent": "direct",
                "input": query,
                "context": {
                    "category": "electronics",
                    "subcategory": "laptops",
                    "brand": brand,
                    "model": model
                },
                "products": products[:random.randint(2, 3)]
            })
    
    # Fashion items
    for _ in range(n // 3):
        category = random.choice(list(PRODUCT_CATALOG["fashion"]["categories"].keys()))
        item = random.choice(PRODUCT_CATALOG["fashion"]["categories"][category])
        brand = random.choice(PRODUCT_CATALOG["fashion"]["brands"])
        color = random.choice(PRODUCT_CATALOG["fashion"]["colors"])
        
        pattern = random.choice(QUERY_PATTERNS["direct"])
        query = pattern.format(product=f"{item.lower()} {brand.lower()}")
        
        products = [
            f"{item} {brand} {color} cao cấp",
            f"{item} {brand} chính hãng màu {color}",
            f"{item} nam/nữ {brand} phong cách Hàn Quốc",
        ]
        
        samples.append({
            "intent": "direct",
            "input": query,
            "context": {
                "category": "fashion",
                "subcategory": category,
                "brand": brand,
                "color": color
            },
            "products": products[:random.randint(2, 3)]
        })
    
    return samples

def generate_occasion_samples(n=3500) -> List[Dict]:
    """Generate samples cho intent: occasion-based recommendation"""
    samples = []
    
    for _ in range(n):
        occasion = random.choice(list(OCCASIONS.keys()))
        recipient = random.choice(list(OCCASIONS[occasion]["recipients"].keys()))
        
        # Get pattern
        pattern = random.choice(QUERY_PATTERNS["occasion"])
        query = pattern.format(occasion=occasion, recipient=recipient)
        
        # Get products for this recipient
        recipient_data = OCCASIONS[occasion]["recipients"][recipient]
        
        if isinstance(recipient_data, dict) and "products" in recipient_data:
            # Complex recipient with product templates
            product_templates = recipient_data["products"]
            selected = random.sample(product_templates, min(3, len(product_templates)))
            
            products = []
            for cat, subcat, template in selected:
                if cat == "cosmetics":
                    brand = random.choice(PRODUCT_CATALOG["cosmetics"]["brands"])
                    if "{brand}" in template:
                        products.append(template.format(brand=brand, color="hồng nude"))
                    else:
                        products.append(template)
                elif cat == "fashion":
                    brand = random.choice(PRODUCT_CATALOG["fashion"]["brands"])
                    products.append(template.format(brand=brand, style="thời trang"))
                else:
                    products.append(template.format(brand="Premium", style="sang trọng", color="đen"))
        else:
            # Simple recipient with product list
            products = recipient_data if isinstance(recipient_data, list) else ["Sản phẩm phù hợp", "Quà tặng ý nghĩa"]
        
        samples.append({
            "intent": "occasion",
            "input": query,
            "context": {
                "occasion": occasion,
                "recipient": recipient,
                "relationship": "personal" if recipient in ["bạn gái", "bạn trai", "mẹ", "bố"] else "professional"
            },
            "products": products[:random.randint(2, 4)]
        })
    
    return samples

def generate_attribute_samples(n=2500) -> List[Dict]:
    """Generate samples cho intent: attribute-based recommendation"""
    samples = []
    
    for _ in range(n):
        attr = random.choice(list(ATTRIBUTES.keys()))
        attr_data = ATTRIBUTES[attr]
        
        # Random purpose
        purposes = ["làm việc", "đi chơi", "tập gym", "đi học", "dùng hàng ngày", "du lịch"]
        purpose = random.choice(purposes)
        
        # Generate query
        patterns = QUERY_PATTERNS["attribute"]
        
        # Sometimes combine 2 attributes
        if random.random() < 0.3:  # 30% chance
            attr2 = random.choice([a for a in ATTRIBUTES.keys() if a != attr])
            pattern = random.choice([p for p in patterns if "{attribute2}" in p])
            query = pattern.format(attribute=attr, attribute2=attr2, purpose=purpose)
        else:
            pattern = random.choice([p for p in patterns if "{attribute2}" not in p])
            query = pattern.format(attribute=attr, purpose=purpose)
        
        # Get products
        products = random.sample(attr_data["products"], min(3, len(attr_data["products"])))
        
        # Fill in placeholders
        filled_products = []
        for p in products:
            if "{brand}" in p:
                brand = random.choice(["Nike", "Adidas", "Samsung", "LG", "Panasonic"])
                p = p.replace("{brand}", brand)
            if "{model}" in p:
                p = p.replace("{model}", "Premium")
            if "{color}" in p:
                color = random.choice(PRODUCT_CATALOG["fashion"]["colors"])
                p = p.replace("{color}", color)
            if "{size}" in p:
                p = p.replace("{size}", "30")
            filled_products.append(p)
        
        samples.append({
            "intent": "attribute",
            "input": query,
            "context": {
                "attributes": [attr],
                "keywords": attr_data["keywords"],
                "purpose": purpose
            },
            "products": filled_products
        })
    
    return samples

# ============================================
# 3. MAIN GENERATION PIPELINE
# ============================================

def generate_full_dataset(
    n_direct=3000,
    n_occasion=3500,
    n_attribute=2500,
    output_file="synthetic_training_data.json"
):
    """Generate complete synthetic dataset"""
    
    print("🎲 Generating synthetic data...")
    
    # Generate each intent type
    print(f"  📱 Direct samples: {n_direct}")
    direct_samples = generate_direct_samples(n_direct)
    
    print(f"  🎁 Occasion samples: {n_occasion}")
    occasion_samples = generate_occasion_samples(n_occasion)
    
    print(f"  ✨ Attribute samples: {n_attribute}")
    attribute_samples = generate_attribute_samples(n_attribute)
    
    # Combine and shuffle
    all_samples = direct_samples + occasion_samples + attribute_samples
    random.shuffle(all_samples)
    
    # Split train/val/test
    n_total = len(all_samples)
    n_train = int(n_total * 0.8)
    n_val = int(n_total * 0.1)
    
    dataset = {
        "train": all_samples[:n_train],
        "validation": all_samples[n_train:n_train+n_val],
        "test": all_samples[n_train+n_val:]
    }
    
    # Save to JSON
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ Generated {n_total} samples!")
    print(f"   📊 Train: {len(dataset['train'])}")
    print(f"   📊 Validation: {len(dataset['validation'])}")
    print(f"   📊 Test: {len(dataset['test'])}")
    print(f"   💾 Saved to: {output_file}")
    
    # Statistics
    print("\n📈 Intent distribution:")
    for split in ["train", "validation", "test"]:
        intents = {}
        for sample in dataset[split]:
            intent = sample["intent"]
            intents[intent] = intents.get(intent, 0) + 1
        print(f"   {split.upper()}: {intents}")
    
    return dataset

# ============================================
# 4. QUALITY CHECK & EXAMPLES
# ============================================

def print_samples(dataset, n=5):
    """Print sample data for inspection"""
    print("\n" + "="*60)
    print("🔍 SAMPLE DATA EXAMPLES")
    print("="*60)
    
    for intent in ["direct", "occasion", "attribute"]:
        print(f"\n📌 INTENT: {intent.upper()}")
        print("-" * 60)
        
        samples = [s for s in dataset["train"] if s["intent"] == intent][:n]
        
        for i, sample in enumerate(samples, 1):
            print(f"\nExample {i}:")
            print(f"  Input: {sample['input']}")
            print(f"  Context: {sample['context']}")
            print(f"  Products:")
            for p in sample['products']:
                print(f"    - {p}")

# Run if executed directly
if __name__ == "__main__":
    # Generate dataset
    dataset = generate_full_dataset(
        n_direct=3000,
        n_occasion=3500,
        n_attribute=2500
    )
    
    # Show examples
    print_samples(dataset, n=3)
    
    print("\n🎉 Synthetic data generation complete!")
    print("📝 Next steps:")
    print("   1. Review samples in 'synthetic_training_data.json'")
    print("   2. Fine-tune quality if needed")
    print("   3. Run training script")