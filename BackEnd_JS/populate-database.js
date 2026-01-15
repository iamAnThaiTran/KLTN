import pg from 'pg';
import dotenv from 'dotenv';
import { logger } from './src/utils/logger.js';

dotenv.config();

const pool = new pg.Pool({
  user: process.env.DB_USER || 'postgres',
  password: process.env.DB_PASSWORD || 'password',
  host: process.env.DB_HOST || 'localhost',
  port: process.env.DB_PORT || 5432,
  database: process.env.DB_NAME || 'kltn_db'
});

/**
 * Category Structure with Vietnamese products
 */
const categoryHierarchy = {
  'Điện tử & Công nghệ': {
    slug: 'dien-tu-cong-nghe',
    icon: '💻',
    subcategories: {
      'Điện thoại di động': {
        slug: 'dien-thoai-di-dong',
        products: ['iPhone 15 Pro', 'Samsung Galaxy S24', 'Xiaomi 14 Pro', 'Google Pixel 8', 'OnePlus 12', 'OPPO Find X7', 'Vivo X100', 'Realme 12 Pro', 'Motorola Edge 50', 'Nothing Phone 2']
      },
      'Laptop & Máy tính': {
        slug: 'laptop-may-tinh',
        products: ['MacBook Pro M3', 'MacBook Air M2', 'Dell XPS 15', 'Dell Inspiron 15', 'Asus VivoBook', 'Asus ZenBook', 'HP Pavilion', 'Lenovo ThinkPad', 'ASUS TUF Gaming', 'Acer Aspire']
      },
      'Máy tính bảng': {
        slug: 'may-tinh-bang',
        products: ['iPad Pro 12.9', 'iPad Air', 'iPad Mini', 'Samsung Galaxy Tab S9', 'Samsung Galaxy Tab A', 'Xiaomi Pad 6', 'Lenovo Tab P12', 'OnePlus Pad', 'Google Pixel Tablet', 'Microsoft Surface Go']
      },
      'Tai nghe & Loa': {
        slug: 'tai-nghe-loa',
        products: ['AirPods Pro', 'AirPods Max', 'Sony WH-1000XM5', 'JBL Live Pro 2', 'Bose QuietComfort', 'Sennheiser Momentum', 'Bang & Olufsen', 'Beats Studio Pro', 'Audio-Technica ATH', 'Technics AZ']
      },
      'Camera & Máy quay phim': {
        slug: 'camera-may-quay',
        products: ['Canon EOS R5', 'Canon EOS 5D', 'Nikon Z9', 'Sony A7R V', 'Fujifilm X-T5', 'DJI Mini 4 Pro', 'DJI Air 3S', 'GoPro Hero 12', 'Insta360 X4', 'DJI Osmo']
      },
      'Đồng hồ thông minh': {
        slug: 'dong-ho-thong-minh',
        products: ['Apple Watch Series 9', 'Apple Watch Ultra', 'Samsung Galaxy Watch 6', 'Garmin Fenix 7', 'Fitbit Sense 2', 'Amazfit GTR', 'Withings ScanWatch', 'Polar Grit X', 'Coros Vertix', 'Honor Watch']
      },
      'Phụ kiện công nghệ': {
        slug: 'phu-kien-cong-nghe',
        products: ['Anker PowerBank 65W', 'Anker 3-in-1 Cable', 'Belkin Magsafe', 'Mophie Wireless Charger', 'Casetify iPhone Case', 'OtterBox Defender', 'Spigen Rugged Armor', 'dbrand Grip', 'PopSocket', 'Moment Lens']
      },
      'Máy in & Thiết bị văn phòng': {
        slug: 'may-in-thiet-bi',
        products: ['HP LaserJet Pro', 'Canon ImageRunner', 'Brother HL-L9310CDW', 'Xerox VersaLink', 'Epson WorkForce', 'Ricoh MP C3004', 'Kyocera Ecosys', 'Konica Minolta', 'Sharp MX', 'Muratec']
      },
      'Bàn phím & Chuột': {
        slug: 'ban-phim-chuot',
        products: ['Logitech MX Keys', 'Apple Magic Keyboard', 'Corsair K95', 'SteelSeries Apex', 'Razer DeathStalker', 'Das Keyboard', 'Ducky One 3', 'Keychron K2', 'HHKB Hybrid', 'Leopold FC']
      },
      'Màn hình máy tính': {
        slug: 'man-hinh-may-tinh',
        products: ['LG UltraWide 34\"', 'Dell UltraSharp 27"', 'ASUS ProArt 32"', 'BenQ PD3220U', 'Eizo ColorEdge', 'Sony PVM', 'Samsung M8', 'LG OLED 27"', 'Acer Predator 32"', 'MSI Curved 34"']
      },
      'Bộ nguồn & Quản lý dây': {
        slug: 'bo-nguon-day',
        products: ['Corsair AX1600i', 'EVGA SuperNOVA 850 G6', 'Seasonic Prime 850', 'be quiet! Straight Power 12', 'Thermaltake Toughpower', 'MSI MPG A1000G', 'ASUS ROG Strix 1000G', 'Gigabyte P1000GM', 'SilverStone ET1000', 'Phanteks PH 1000PS']
      },
      'Ổ cứng & SSD': {
        slug: 'o-cung-ssd',
        products: ['Samsung 990 Pro NVMe', 'WD Black SN850X', 'Corsair MP600 GEN4', 'Kingston Fury Beast', 'Crucial P5 Plus', 'Sabrent Rocket 4 Plus', 'SK Hynix P41', 'Team CardExpress', 'Transcend StoreJet', 'Seagate IronWolf Pro']
      }
    }
  },
  'Thời trang & Phụ kiện': {
    slug: 'thoi-trang-phu-kien',
    icon: '👗',
    subcategories: {
      'Áo sơ mi & Áo khoác': {
        slug: 'ao-so-mi-khoac',
        products: ['Áo sơ mi Oxford', 'Áo khoác Denim', 'Áo Polo Ralph Lauren', 'Áo Bomber Zara', 'Áo Khoác Hugo Boss', 'Áo Sơ Mi Gucci', 'Áo Khoác Burberry', 'Áo Tommy Hilfiger', 'Áo Calvin Klein', 'Áo Lacoste']
      },
      'Quần tây & Quần jeans': {
        slug: 'quan-tay-jeans',
        products: ['Quần Jeans Levi\'s 501', 'Quần Jeans Lee Regular', 'Quần Tây Hugo Boss', 'Quần Chinos Banana Republic', 'Quần Gap Jeans', 'Quần Zara', 'Quần H&M', 'Quần Diesel', 'Quần Saint Laurent', 'Quần Balenciaga']
      },
      'Giày thể thao': {
        slug: 'giay-the-thao',
        products: ['Nike Air Max 90', 'Nike Air Jordan 1', 'Adidas Ultraboost 22', 'Adidas Yeezy 350', 'Puma RS-X', 'New Balance 990v6', 'Asics Gel-Lyte', 'VANS Old Skool', 'Converse Chuck Taylor', 'Reebok Classic']
      },
      'Giày lười & Giày tây': {
        slug: 'giay-luoi-tay',
        products: ['Giày lười Gucci', 'Giày Loafer Cole Haan', 'Giày Tây Allen Edmonds', 'Giày Tây John Lobb', 'Giày Lười Ferragamo', 'Giày Tây Berluti', 'Giày Lười Bruno Magli', 'Giày Tây Geox', 'Giày Lười Clarks', 'Giày Tây Florsheim']
      },
      'Tú xách & Ba lô': {
        slug: 'tu-xach-ba-lo',
        products: ['Túi xách Hermès Birkin', 'Túi xách Chanel Classic', 'Túi xách Louis Vuitton Speedy', 'Ba lô Fjällräven Kånken', 'Ba lô Peak Design', 'Ba lô Thule', 'Ba lô Herschel', 'Túi xách Gucci', 'Túi xách Prada', 'Ba lô The North Face']
      },
      'Dây đeo & Thắt lưng': {
        slug: 'day-deo-that-lung',
        products: ['Thắt lưng Gucci GG Marmont', 'Dây đeo Coach', 'Thắt lưng Burberry', 'Thắt lưng Versace', 'Dây đeo Prada', 'Thắt lưng Louis Vuitton', 'Thắt lưng Hermès', 'Dây đeo Bottega Veneta', 'Thắt lưng Montblanc', 'Dây đeo Saint Laurent']
      },
      'Nón & Khăn quàng': {
        slug: 'non-khan-quang',
        products: ['Nón beret Kangol', 'Nón trucker Carhartt', 'Nón snapback New Era', 'Khăn quàng Hermès', 'Khăn Burberry', 'Nón panama Gucci', 'Nón Boston Cap', 'Nón Adidas', 'Nón Nike', 'Khăn Yves Saint Laurent']
      },
      'Trang sức': {
        slug: 'trang-suc',
        products: ['Vòng tay Cartier Love', 'Vòng tay Tiffany & Co', 'Dây chuyền Hermès', 'Nhẫn Kim Cương De Beers', 'Nhẫn Bulgari', 'Vòng tay Van Cleef & Arpels', 'Dây chuyền Chopard', 'Nhẫn Harry Winston', 'Vòng tay Piaget', 'Dây chuyền Graff']
      },
      'Đồng hồ thời trang': {
        slug: 'dong-ho-thoi-trang',
        products: ['Rolex Submariner', 'Rolex Datejust', 'Omega Seamaster', 'Breitling Navitimer', 'TAG Heuer Carrera', 'Patek Philippe Aquanaut', 'Seiko Prospex', 'Citizen Eco-Drive', 'Orient Mako', 'Timex Weekender']
      },
      'Kính mắt thời trang': {
        slug: 'kinh-mat-thoi-trang',
        products: ['Kính Ray-Ban Aviator', 'Kính Ray-Ban Wayfarer', 'Kính Gucci GG0724S', 'Kính Chanel CH5393', 'Kính Prada PR 57XS', 'Kính Tom Ford', 'Kính Versace VE4398', 'Kính Dolce & Gabbana', 'Kính Burberry', 'Kính Saint Laurent']
      }
    }
  },
  'Gia dụng & Nội thất': {
    slug: 'gia-dung-noi-that',
    icon: '🏠',
    subcategories: {
      'Nội thất phòng ngủ': {
        slug: 'noi-that-phong-ngu',
        products: ['Giường ngủ king size', 'Giường ngủ queen', 'Tủ quần áo gỗ', 'Bàn trang điểm', 'Tủ đầu giường', 'Khung giường sắt', 'Giường trần', 'Giường ngân hàng', 'Nệm cao su', 'Giường gấp']
      },
      'Bàn ghế phòng ăn': {
        slug: 'ban-ghe-phong-an',
        products: ['Bàn ăn gỗ tự nhiên', 'Bàn ăn kính cường lực', 'Ghế ăn gỗ sồi', 'Ghế ăn bọc nệm', 'Ghế bar cao', 'Ghế ăn kiểu Scandinavia', 'Bàn ăn tròn', 'Ghế ăn hồng tuyến', 'Bàn ăn extendable', 'Ghế ăn inox']
      },
      'Sofa & Ghế thư giãn': {
        slug: 'sofa-ghe-thu-gian',
        products: ['Sofa chữ L', 'Sofa góc', 'Sofa vải nỉ', 'Sofa da thật', 'Sofa bọc nỉ cao cấp', 'Sofa Scandinavian', 'Sofa modular', 'Sofa giường', 'Ghế thư giãn xô', 'Sofa 3 chỗ']
      },
      'Tủ lạnh & Tủ đông': {
        slug: 'tu-lanh-tu-dong',
        products: ['Tủ lạnh LG Inverter', 'Tủ lạnh Samsung Digital', 'Tủ lạnh Electrolux', 'Tủ lạnh Hitachi', 'Tủ lạnh Panasonic', 'Tủ lạnh Sharp', 'Tủ lạnh Sanyo', 'Tủ lạnh Whirlpool', 'Tủ đông mặt kính', 'Tủ lạnh side by side']
      },
      'Bếp từ & Bếp hơi': {
        slug: 'bep-tu-bep-hoi',
        products: ['Bếp từ Sunhouse', 'Bếp từ Kangaroo', 'Bếp từ Comet', 'Bếp từ Aqua', 'Bếp hơi Rinnai', 'Bếp hơi Paloma', 'Bếp hơi Electrolux', 'Bếp hơi Kaff', 'Bếp từ Teka', 'Bếp hơi Bosch']
      },
      'Máy giặt & Máy sấy': {
        slug: 'may-giat-may-say',
        products: ['Máy giặt LG Inverter', 'Máy giặt Samsung', 'Máy giặt Electrolux', 'Máy giặt Panasonic', 'Máy giặt Sharp', 'Máy giặt Toshiba', 'Máy giặt Bosch', 'Máy sấy LG', 'Máy sấy Electrolux', 'Máy sấy Whirlpool']
      },
      'Lò vi sóng & Lò nướng': {
        slug: 'lo-vi-song-lo-nuong',
        products: ['Lò vi sóng Midea', 'Lò vi sóng LG', 'Lò vi sóng Electrolux', 'Lò vi sóng Sharp', 'Lò nướng Electrolux', 'Lò nướng Teka', 'Lò nướng Bosch', 'Lò nướng Kaff', 'Lò nướng Sunhouse', 'Lò vi sóng Panasonic']
      },
      'Máy hút mùi & Quạt': {
        slug: 'may-hut-mui-quat',
        products: ['Máy hút mùi Kaff', 'Máy hút mùi Teka', 'Máy hút mùi Electrolux', 'Máy hút mùi Bosch', 'Quạt điều hòa Sunhouse', 'Quạt cây Panasonic', 'Quạt treo tường LG', 'Quạt hộp Daikin', 'Quạt mini di động', 'Quạt tính năng ionic']
      },
      'Đèn trang trí': {
        slug: 'den-trang-tri',
        products: ['Đèn chùm pha lê', 'Đèn tường hình sao', 'Đèn treo phòng khách', 'Đèn bàn đọc sách', 'Đèn nền LED RGB', 'Đèn âm trần', 'Đèn cây cảnh', 'Đèn thông minh Philips Hue', 'Đèn Nanoleaf', 'Đèn dây LED']
      },
      'Rèm & Thảm': {
        slug: 'rem-tham',
        products: ['Rèm vải cao cấp', 'Rèm cửa sổ', 'Rèm cửa phòng', 'Thảm trải sàn lông xù', 'Thảm trải sàn cotton', 'Rèm chống nắng tự động', 'Rèm lá dọc', 'Thảm lót sàn', 'Rèm vải jacquard', 'Thảm du lịch']
      }
    }
  },
  'Sách, Sản phẩm kỹ thuật số & Media': {
    slug: 'sach-san-pham-ky-thuat-so',
    icon: '📚',
    subcategories: {
      'Sách tiểu thuyết': {
        slug: 'sach-tieu-thuyet',
        products: ['Harry Potter Bộ đầy đủ', 'Twilight Saga', 'The Hobbit', 'Việt Nam Những đứa trẻ lạc lối', 'Conan Đoàn Thất Lâm', 'One Piece Manga', 'Attack on Titan Manga', 'My Hero Academia', 'Demon Slayer', 'Jujutsu Kaisen']
      },
      'Sách tâm lý & Self-help': {
        slug: 'sach-tam-ly-self-help',
        products: ['Dễ Dàng Giao Tiếp', 'Thói Quen Vàng', 'Bắt Đầu Từ Tại Sao', 'Năng Lực Của Ý Chí', 'Tâm Lý Học Vui Vẻ', 'Trí Thông Minh Cảm Xúc', 'Người Giàu Nhất Thành Babylon', 'Cha Giàu Cha Nghèo', 'Những Người Thành Công Dậy Sớm', 'Khoa Học Về Hạnh Phúc']
      },
      'Sách kinh tế & Kinh doanh': {
        slug: 'sach-kinh-te-kinh-doanh',
        products: ['Lean Startup', 'Good to Great', 'The 7 Habits', 'Thinking Fast and Slow', 'Blue Ocean Strategy', 'Platform Revolution', 'Sapiens', 'Zero to One', 'The Business Model Canvas', 'Sprint']
      },
      'Sách khoa học & Kỹ thuật': {
        slug: 'sach-khoa-hoc-ky-thuat',
        products: ['Python for Data Science', 'Clean Code', 'Design Patterns', 'Algorithms Illuminated', 'Machine Learning Basics', 'Deep Learning', 'Artificial Intelligence', 'The Pragmatic Programmer', 'Code Complete', 'Refactoring']
      },
      'Sách lịch sử & Văn hóa': {
        slug: 'sach-lich-su-van-hoa',
        products: ['Lịch Sử Thế Giới Loạt Tập', 'Lịch Sử Việt Nam', 'Tây Du Ký', 'Tam Quốc Diễn Nghĩa', 'Nước Ngoài Gia Tư', 'Đất Nước Của Tôi', 'Bộ Sách Lịch Sử Á Châu', 'Nền Văn Minh Phương Tây', 'Những Điều Bạn Cần Biết', 'Lịch Sử Nhân Loại']
      },
      'Sách nấu ăn & Công thức': {
        slug: 'sach-nau-an-cong-thuc',
        products: ['Jamie Oliver Cook Book', 'Gordon Ramsay Recipes', 'Bên Mình Nấu Ăn', 'Nấu Ăn Nhật Bản Cơ Bản', 'Bánh Nước Ngoài', 'Ẩm Thực Á Châu', 'Công Thức Nấu Ăn Hàng Ngày', 'Nấu Ăn Nhanh Chóng', 'Thực Phẩm Sạch', 'Món Ăn Từ Rau Củ']
      },
      'Truyện tranh & Manga': {
        slug: 'truyen-tranh-manga',
        products: ['Dragon Ball Bộ Đầy Đủ', 'Naruto Complete Series', 'Bleach Collection', 'One Piece Latest', 'Tokyo Ghoul', 'Death Note', 'Fullmetal Alchemist', 'Steins;Gate Manga', 'Sword Art Online', 'Code Geass']
      },
      'Tạp chí & Báo': {
        slug: 'tap-chi-bao',
        products: ['Tạp Chí National Geographic', 'Tạp Chí Forbes', 'Tạp Chí Time', 'Tạp Chí Economist', 'Báo Tuổi Trẻ', 'Báo Người Lao Động', 'Tạp Chí Thế Giới', 'Tạp Chí Đầu Tư', 'Tạp Chí Gia Đình', 'Tạp Chí Khoa Học Phổ Thông']
      },
      'Ebooks & Audiobooks': {
        slug: 'ebooks-audiobooks',
        products: ['Kindle Unlimited Subscription', 'Audiobook Audible Premium', 'Scribd Premium', 'Kindle eBook Collection', 'Google Play Books', 'Apple Books', 'Wattpad Premium', 'Storytel Subscription', 'Voicebook Premium', 'Libby eBook Access']
      }
    }
  },
  'Thực phẩm & Đồ uống': {
    slug: 'thuc-pham-do-uong',
    icon: '🍔',
    subcategories: {
      'Cà phê & Trà': {
        slug: 'ca-phe-tra',
        products: ['Cà phê Arabica Trung Nguyên', 'Cà phê Robusta Nâu Đắk Lắk', 'Cà phê Espresso Lavazza', 'Cà phê Starbucks', 'Cà phê Nescafé', 'Trà Oolong Đài Loan', 'Trà Xanh Lâm Đồng', 'Trà Jasmine Premium', 'Trà Đen Ceylon', 'Cà phê Light Roast Premium']
      },
      'Snack & Bánh quy': {
        slug: 'snack-banh-quy',
        products: ['Bánh quy Oreo', 'Bánh quy Tim Tam', 'Bánh Lotte Choco Pie', 'Bánh Kinh Đô', 'Bánh Bảo Việt', 'Khoai tây chiên Lays', 'Popcorn Orville', 'Bánh Bourbon', 'Bánh Bơ Nướng', 'Bánh Socola Milka']
      },
      'Sữa & Sản phẩm từ sữa': {
        slug: 'sua-san-pham-sua',
        products: ['Sữa Vinamilk', 'Sữa TH True Milk', 'Sữa Mạnh Khỏe', 'Phomai Cheddar', 'Sữa Chua Yoplait', 'Sữa Đặc Ông Thọ', 'Bơ Lurpak', 'Sữa Tươi Ava', 'Sữa Bột Nuti IQ', 'Sữa Hạt Macca']
      },
      'Dầu & Gia vị': {
        slug: 'dau-gia-vi',
        products: ['Dầu Olive Carapelli', 'Dầu Mè Mười Năm', 'Dầu Cây Nành Cimori', 'Tương Cà Chua Heinz', 'Mắm Cá Ba Miền', 'Nước Mam Phú Quốc', 'Xì Dầu Kikkoman', 'Tương Ớt Sambal Oelek', 'Dầu Dừa Bảo Châu', 'Nước Tương Tamari']
      },
      'Ngũ cốc & Lương thực': {
        slug: 'ngu-coc-luong-thuc',
        products: ['Gạo Tám Xoan', 'Gạo Tấm Cơm Tấm', 'Lúa Mì Nguyên Cám', 'Đậu Xanh Sạch', 'Đậu Đen Tây Nguyên', 'Yến Mạch Quaker', 'Cơm Instant Sunrise', 'Lúa Mạch Ngoại Hạng', 'Khoai Tây Nạo', 'Khoai Lang Mỹ']
      },
      'Candy & Kẹo': {
        slug: 'candy-keo',
        products: ['Kẹo Trident', 'Kẹo Stride', 'Kẹo Tootsie Roll', 'Kẹo Gummy Haribo', 'Kẹo Nendo', 'Kẹo Halls', 'Kẹo Ricola', 'Kẹo Altoids', 'Kẹo Ginger Ale', 'Kẹo Mentos']
      },
      'Nước uống & Thức uống': {
        slug: 'nuoc-uong-thuc-uong',
        products: ['Nước Aquafina', 'Nước Vinaland', 'Nước Tâm Việt', 'Nước Lợi Hay', 'Juice Tràng An', 'Coca Cola', 'Pepsi', 'Sprite', 'Sting Energy', 'Red Bull']
      },
      'Mứt & Nước trái cây': {
        slug: 'mut-nuoc-trai-cay',
        products: ['Mứt Dâu Bonne Maman', 'Mứt Cam Bonne Maman', 'Mứt Dâu Tây Axa', 'Nước Cam Cô Gái', 'Nước Chanh Cô Gái', 'Nước Ổi Cô Gái', 'Sốt Mâm Xôi Lakeland', 'Mứt Việt Quất', 'Nước Cà Rốt Sunshine', 'Mứt Chuối Bột']
      },
      'Thực phẩm hữu cơ & Vegan': {
        slug: 'thuc-pham-huu-co-vegan',
        products: ['Tofu hữu cơ', 'Tempeh Organic', 'Nước tương không GMO', 'Sữa Đậu Nành Hữu Cơ', 'Gạo Lứt Hữu Cơ', 'Rau Xanh Hữu Cơ', 'Trứng Vịt Hữu Cơ', 'Sữa Gạo Nâu', 'Thịt Chay Đậu', 'Phô Mai Vegan']
      }
    }
  },
  'Sắc đẹp & Chăm sóc cá nhân': {
    slug: 'sac-dep-cham-soc',
    icon: '💄',
    subcategories: {
      'Mỹ phẩm mặt': {
        slug: 'my-pham-mat',
        products: ['Kem dưỡng ẩm Cetaphil', 'Kem dưỡng da Olay', 'Serum Vitamin C SkinCeuticals', 'Kem chống nắng La Roche Posay', 'Toner Hada Labo', 'Mặt nạ sheet SK-II', 'Kem mắt Estée Lauder', 'Sữa rửa mặt Neutrogena', 'Kem trị mụn Differin', 'Kem trắng da Shiseido']
      },
      'Chăm sóc tóc': {
        slug: 'cham-soc-toc',
        products: ['Dầu gội Pantene', 'Dầu gội Head & Shoulders', 'Dầu xả Dove', 'Dầu gội Schwarzkopf', 'Serum tóc Moroccanoil', 'Kem ủ tóc Kerastase', 'Dầu dừa Cô Gái', 'Dầu argan Ordinary', 'Tinh dầu bưởi Larus', 'Dầu gội tinh chất thảo dược']
      },
      'Nước hoa & Nước hoa xịt': {
        slug: 'nuoc-hoa-nuoc-hoa-xit',
        products: ['Nước hoa Chanel No.5', 'Nước hoa Dior J\'adore', 'Nước hoa Guerlain La Vie Belle', 'Nước hoa Paco Rabanne 1 Million', 'Nước hoa Calvin Klein Eternity', 'Nước hoa Lancôme La Vie Est Belle', 'Nước hoa Yves Saint Laurent Black Opium', 'Nước hoa Givenchy Gentlemen', 'Nước hoa Tom Ford Black Orchid', 'Nước hoa Dolce Gabbana Light Blue']
      },
      'Son & Lipstick': {
        slug: 'son-lipstick',
        products: ['Son Dior Rouge', 'Son Mac Retro Matte', 'Son Maybelline Superstay', 'Son Revlon ColorStay', 'Son Charlotte Tilbury Red Carpet Red', 'Son Nars Heat Wave', 'Son Tom Ford Beauty', 'Son Bobbi Brown', 'Son Clinique Pop', 'Son Estée Lauder Double Wear']
      },
      'Trang điểm mắt': {
        slug: 'trang-diem-mat',
        products: ['Phấn mắt Urban Decay Naked Palette', 'Phấn mắt Anastasia Beverly Hills', 'Mascara Maybelline Lash Sensational', 'Eyeliner Marc Jacobs', 'Phấn mắt Lorac Pro', 'Mascara Benefit They\'re Real', 'Chì mắt MAC', 'Phấn mắt Tarte Tartelette', 'Mascara Clinique Lash Power', 'Phấn mắt Makeup Forever']
      },
      'Phấn nền & Foundation': {
        slug: 'phan-nen-foundation',
        products: ['Foundation MAC Face & Body', 'Foundation Fenty Beauty Pro Filt\'r', 'Foundation Estée Lauder Double Wear', 'Foundation Clinique Beyond Perfecting', 'Foundation NARS All Day Luminous', 'Foundation Giorgio Armani Luminous', 'Cushion Clio Kill Cover', 'Phấn nước Shiseido Synchro Skin', 'Foundation Hera UV Mist', 'Foundation L\'Oreal Infallible']
      },
      'Sản phẩm chăm sóc cơ thể': {
        slug: 'san-pham-cham-soc-co-the',
        products: ['Sữa tắm Dove', 'Sữa tắm Lux', 'Dầu tắm Johnson\'s', 'Kem dưỡng cơ thể Vaseline', 'Lotion Eucerin', 'Gel tắm Protex', 'Sữa tắm Lifebuoy', 'Scrub cơ thể The Body Shop', 'Kem massage Yoko Spa', 'Dầu tắm Weleda']
      },
      'Chăm sóc răng & Miệng': {
        slug: 'cham-soc-rang-mieng',
        products: ['Kem đánh răng Crest', 'Kem đánh răng Colgate', 'Kem đánh răng Sensodyne', 'Kem đánh răng Oral-B', 'Nước súc miệng Listerine', 'Chỉ nha khoa Reach', 'Kem đánh răng Dệp', 'Kem đánh răng Sunstar', 'Nước súc miệng Lô Hội', 'Kem trắng răng Whitestrips']
      },
      'Khử mùi & Lăn khử mùi': {
        slug: 'khu-mui-lan-khu-mui',
        products: ['Lăn khử mùi Dove', 'Lăn khử mùi Rexona', 'Spray khử mùi Axe', 'Lăn khử mùi Old Spice', 'Spray khử mùi Secret', 'Lăn khử mùi Right Guard', 'Spray khử mùi Ban', 'Lăn khử mùi Degree', 'Spray khử mùi Gillette Foamy', 'Lăn khử mùi Speedstick']
      }
    }
  },
  'Thể thao & Ngoài trời': {
    slug: 'the-thao-ngoai-troi',
    icon: '⚽',
    subcategories: {
      'Quần áo thể thao': {
        slug: 'quan-ao-the-thao',
        products: ['Áo thể thao Nike Dri-FIT', 'Áo thể thao Adidas Climalite', 'Áo thể thao Puma', 'Áo thể thao Under Armour', 'Áo thể thao Reebok', 'Áo thể thao New Balance', 'Áo thể thao Asics', 'Áo thể thao YONEX', 'Áo thể thao Lululemon', 'Áo thể thao Arc\'teryx']
      },
      'Giày chạy & Giày thể thao': {
        slug: 'giay-chay-giay-the-thao',
        products: ['Giày chạy Nike Running', 'Giày chạy Adidas Running', 'Giày chạy Brooks Ghost', 'Giày chạy ASICS Gel', 'Giày chạy New Balance 990', 'Giày chạy Saucony', 'Giày chạy Hoka One One', 'Giày chạy Mizuno', 'Giày chạy On Cloud', 'Giày chạy Brooks Beast']
      },
      'Túi & Ba lô thể thao': {
        slug: 'tui-ba-lo-the-thao',
        products: ['Ba lô Nike', 'Ba lô Adidas', 'Ba lô Puma', 'Ba lô Under Armour', 'Ba lô Dakine', 'Ba lô Osprey', 'Ba lô Deuter', 'Ba lô The North Face', 'Ba lô Incase', 'Ba lô Marmot']
      },
      'Dụng cụ phòng tập': {
        slug: 'dung-cu-phong-tap',
        products: ['Tạ Dumbell Elliptical', 'Dumbbell neopren Marcy', 'Barbell Olympic', 'Tạ xây dựng thân hình', 'Kettlebell Rogue', 'Yoga Mat Lifeline', 'Bàn tạ thay đổi', 'Tạp chế thương Mại Tâng', 'Horizontal Bar Chin Up', 'Thảm tập Yoga']
      },
      'Dụng cụ ngoài trời': {
        slug: 'dung-cu-ngoai-troi',
        products: ['Lều cắm trại Coleman', 'Lều cắm trại Kelty', 'Balo đi bộ Osprey', 'Túi ngủ Mountain Hardwear', 'Giày leo núi Salomon', 'Giày leo núi Scarpa', 'Dây thừa Leo Núi Maxim', 'Carabiner Black Diamond', 'Kẹp tuyết Crampons', 'Trục Máy Bộ Đục']
      },
      'Dụng cụ bóng': {
        slug: 'dung-cu-bong',
        products: ['Bóng đá FIFA Official', 'Bóng rổ Spalding', 'Bóng chuyền Mikasa', 'Bóng tennis Wilson', 'Bóng cầu lông Yonex', 'Bóng bàn Nittaku', 'Bóng ngoài Spalding', 'Bóng nước Intex', 'Bóng lục lạc yoga', 'Bóng đá tập luyện']
      },
      'Thiết bị bơi': {
        slug: 'thiet-bi-boi',
        products: ['Áo tắm Speedo', 'Kính bơi Nike', 'Bộ ống thở Cressi', 'Mũ bơi Speedo', 'Mua giỏi bơi', 'Xà phòng Dutti tắm', 'Tấm lót bơi Intex', 'Bơm điện cho bể bơi', 'Lưới vớt lá hồ bơi', 'Áo bơi bé gái']
      },
      'Thiết bị xe đạp': {
        slug: 'thiet-bi-xe-dap',
        products: ['Xe đạp road Trek', 'Xe đạp Giant', 'Xe đạp Specialized', 'Xe đạp Cannondale', 'Xe đạp Scott', 'Helmet Giro', 'Bàn đạp PowerTap', 'Đèn xe đạp Cygolite', 'Khóa xe đạp Kryptonite', 'Giỏ xe đạp Wald']
      },
      'Thiết bị trượt băng & Trượt ván': {
        slug: 'thiet-bi-truot-bang-truot-van',
        products: ['Ván trượt Santa Cruz', 'Ván trượt Element', 'Ván trượt Toy Machine', 'Ván trượt Almost', 'Ván trượt Baker', 'Ván trượt Flip', 'Pads bảo vệ 187 Killer', 'Mũ bảo hiểm Pro-Tec', 'Giầy trượt ván etnies', 'Giầy trượt ván Vans']
      }
    }
  },
  'Đồ chơi & Trò chơi': {
    slug: 'do-choi-tro-choi',
    icon: '🎮',
    subcategories: {
      'Đồ chơi trẻ em': {
        slug: 'do-choi-tre-em',
        products: ['LEGO Classic Set', 'LEGO Technic Set', 'LEGO Ninjago Set', 'LEGO Friends Set', 'Playmobil City', 'Playmobil Family', 'Transformers Bumblebee', 'Hot Wheels Track', 'Barbie Dreamhouse', 'Action Man Figure']
      },
      'Trò chơi board': {
        slug: 'tro-choi-board',
        products: ['Catan Settlers', 'Ticket to Ride', 'Carcassonne', 'Pandemic', 'Agricola', 'Puerto Rico', 'Dominion', ' Stone Age', 'Splendor', ' 7 Wonders']
      },
      'Trò chơi video': {
        slug: 'tro-choi-video',
        products: ['PlayStation 5', 'Xbox Series X', 'Nintendo Switch', 'Gaming PC RTX 4090', 'Elden Ring', 'Final Fantasy VII Remake', 'Hogwarts Legacy', 'Cyberpunk 2077', 'Starfield', 'Dragon Age Inquisition']
      },
      'Tay cầm & Bộ điều khiển': {
        slug: 'tay-cam-bo-dieu-khien',
        products: ['PlayStation 5 DualSense', 'Xbox Series X Controller', 'Nintendo Switch Joy-Con', 'Nintendo Switch Pro', 'Scuf Controller Elite', 'Astro\'s Gaming Controller', 'PowerA Controller', ' 8BitDo Controller', 'Turtle Beach Recon', 'Steel Series Arctis Nova']
      },
      'Mô hình & Figure': {
        slug: 'mo-hinh-figure',
        products: ['Funko Pop Avengers', 'Nendoroid Series', 'S.H. Figuarts One Piece', 'Bandai HGUC Gundam', 'Hot Toys Iron Man', 'Revoltech Series', 'Figma Link Zelda', 'Scale Figure Saber', 'Good Smile Nendoroid', 'Medicom Mafex Batman']
      },
      'Đồ chơi xây dựng': {
        slug: 'do-choi-xay-dung',
        products: ['LEGO Architecture', 'LEGO Star Wars', 'LEGO Marvel', 'LEGO Harry Potter', 'LEGO Lord of the Rings', 'Mega Construx Pokémon', 'K\'NEX Building Sets', 'Magnetix Magnetic', 'Tinkertoys Wooden', 'Stickle Bricks']
      },
      'Búp bê & Phụ kiện': {
        slug: 'bup-be-phu-kien',
        products: ['Barbie Fashion Doll', 'American Girl Doll', 'Monster High Doll', 'Ever After High', 'Bratz Doll', 'Equestria Girls Pony', 'Baby Alive Doll', 'Cry Babies Magic Tears', 'Ty Beanie Babies', 'Squishmallow Collection']
      },
      'Trò chơi ngoài trời': {
        slug: 'tro-choi-ngoai-troi',
        products: ['Frisbee Discraft', 'Badminton Set', 'Tennis Racket Set', 'Kite Stunt Kite', 'Water Balloon', 'Beach Ball', 'Giant Jenga', 'Cornhole Game', 'Ladder Ball', 'Spikeball']
      },
      'Xe đồ chơi': {
        slug: 'xe-do-choi',
        products: ['RC Car Tamiya', 'RC Truck Traxxas', 'Drone DJI', 'RC Helicopter Syma', 'Hot Wheels Collection', 'Majorette Diecast', 'Matchbox Series', 'Dinoco Die-cast', 'Bburago Ferrari', 'Rastar License Car']
      },
      'Trò chơi xếp hình': {
        slug: 'tro-choi-xep-hinh',
        products: ['Rubik\'s Cube', 'Pyraminx Puzzle', 'Skewb Cube', 'Megaminx', 'Sudoku Puzzle', 'Hanayama Metal Puzzle', 'Tangram Set', 'IQ Logic Puzzle', 'Katamino Puzzle', 'ThinkFun Gravity Maze']
      }
    }
  },
  'Nhà cửa & Vật dụng': {
    slug: 'nha-cua-vat-dung',
    icon: '🔧',
    subcategories: {
      'Dụng cụ & Thiết bị cầm tay': {
        slug: 'dung-cu-thiet-bi-cam-tay',
        products: ['Mộng cầm tay Stanley', 'Mộng Bosch', 'Mộng DeWalt', 'Bộ tuốc nơ vít Stanley', 'Tuốc nơ vít makita', 'Khoan pin Bosch', 'Máy khoan Black & Decker', 'Lưỡi cắt Irwin', 'Tua vít Wera', 'Kìm tay Knipex']
      },
      'Máy khoan & Máy cắt': {
        slug: 'may-khoan-may-cat',
        products: ['Máy khoan pin Bosch', 'Máy khoan makita', 'Máy cắt Stanley', 'Máy cắt DeWalt', 'Máy cắt Black & Decker', 'Máy mài Hitachi', 'Máy bắn vít Panasonic', 'Máy tia cưa Makita', 'Máy cắt gỗ Bosch', 'Máy bắn đinh Pneumatic']
      },
      'Sơn & Vật liệu sơn': {
        slug: 'son-vat-lieu-son',
        products: ['Sơn Nội thất Sơn DominoPaint', 'Sơn Ngoài trời Jotun', 'Sơn Công nghiệp Nippon', 'Sơn Dầu Kansai', 'Sơn Epoxy Jotun', 'Sơn Nước Dulux', 'Sơn Polyester Comimex', 'Sơn Acryl Sơn Việt', 'Mầu sơn Motip', 'Sơn xịt Rust-Oleum']
      },
      'Xây dựng & Vật liệu': {
        slug: 'xay-dung-vat-lieu',
        products: ['Gạch Xi Măng Bình Minh', 'Gạch Viglacera', 'Gạch Đỏ Cộng Hòa', 'Xi Măng Portland Holcim', 'Xi Măng Hà Tiên', 'Xi Măng Thăng Long', 'Cát Lầu Chéo', 'Cát Đất Sạch', 'Sắt Thép Hòa Phát', 'Thép Mỹ Kỹ']
      },
      'Ốc vít & Đinh': {
        slug: 'oc-vit-dinh',
        products: ['Ốc vít Inox Stainless', 'Ốc vít Steel Sắt', 'Ốc vít Thép Boong Đầu', 'Đinh Thép Dạo', 'Đinh Vuông Truyền Thống', 'Đinh Ốc Sáo Cốc', 'Đinh Gỗ Tẻo Lỗi Đầu', 'Tắc Kê Ốc Phụ Kiện', 'Ốc Tường Nylon Plastic', 'Bullet Hót Phục Vụ']
      },
      'Khóa & Bản Lề': {
        slug: 'khoa-ban-le',
        products: ['Khóa Cửa Yale', 'Khóa Cửa Stanley', 'Khóa Cửa Hafele', 'Bản lề Cửa Selten', 'Bản lề cửa số Hettich', 'Bản lề ẩn Salice', 'Khóa Cửa Thông Minh Philips', 'Khóa Cửa Biometric Kaadas', 'Bản lề cửa tự đóng Geze', 'Khóa Cửa Sắt Đúc']
      },
      'Thang & Giàn giáo': {
        slug: 'thang-gian-giao',
        products: ['Thang Nhôm 3 bậc', 'Thang Nhôm 5 bậc', 'Thang Nhôm Tele', 'Thang Sợi Thủy Tinh', 'Giàn Giáo Chân Đế', 'Giàn Giáo Xe Đẩy', 'Thang Gập Multifungi', 'Thang Sơn Nhôm', 'Thang Dầu Kéo', 'Thang Máy Điện']
      },
      'Cảm biến & Điều khiển thông minh': {
        slug: 'cam-bien-dieu-khien-thong-minh',
        products: ['Công tắc cảm ứng Philips Hue', 'Công tắc Smart Home Tuya', 'Cảm biến chuyển động Aqara', 'Cảm biến ánh sáng tự động', 'Công tắc kiểm soát giọng nói', 'Hub điều khiển trung tâm SmartThings', 'Module Relay điều khiển', 'Relay tương tự Schneider', 'Timer tự động điện tử', 'Cảm biến cửa thông minh']
      },
      'Cồn bàn & Sàn gỗ': {
        slug: 'con-ban-san-go',
        products: ['Sàn gỗ tự nhiên Xoan Ta', 'Sàn gỗ xoanh Cẩm', 'Sàn gỗ Công nghiệp', 'Sàn gỗ Laminate', 'Sàn gỗ Vinyl tự dán', 'Gỗ Sồi Trắng', 'Gỗ Teak Lào', 'Gỗ Đinh Hương', 'Gỗ Sao Đen', 'Gỗ Dẻ Gai']
      }
    }
  }
};

/**
 * Generate mock product details similar to what crawlers would return
 */
function generateProductData(productName, categoryId, subcategoryId) {
  const prices = [
    99000, 199000, 299000, 499000, 799000, 999000, 1499000, 1999000, 2999000, 4999000,
    5999000, 7999000, 9999000, 12999000, 15999000, 19999000, 24999000, 29999000, 34999000, 39999000
  ];

  const brands = ['Samsung', 'Apple', 'Sony', 'LG', 'Dell', 'Hp', 'Asus', 'Lenovo', 'Canon', 'Nikon', 'Generic'];
  
  const price = prices[Math.floor(Math.random() * prices.length)];
  const originalPrice = price + Math.floor(Math.random() * 5000000);
  const discountPercent = Math.floor(((originalPrice - price) / originalPrice) * 100);
  const stock = Math.floor(Math.random() * 100) + 10;
  const rating = (Math.random() * 2 + 3).toFixed(1);
  const ratingCount = Math.floor(Math.random() * 500) + 10;
  
  // Create unique slug by combining product name with subcategory ID and a random suffix
  const baseSlug = productName.toLowerCase().replace(/\s+/g, '-').replace(/[^\w-]/g, '');
  const uniqueSuffix = Math.random().toString(36).substring(7);
  
  return {
    name: productName,
    slug: `${baseSlug}-${subcategoryId}-${uniqueSuffix}`,
    categoryId,
    brand: brands[Math.floor(Math.random() * brands.length)],
    description: `${productName} - Sản phẩm chính hãng, bảo hành chính thức. Mua hàng với giá tốt nhất.`,
    price,
    originalPrice,
    discountPercent,
    stock,
    rating: parseFloat(rating),
    ratingCount
  };
}

/**
 * Main database population function
 */
async function populateDatabase() {
  const client = await pool.connect();
  
  try {
    console.log('🚀 Starting database population...\n');

    // Clear existing data (optional - comment out to keep existing data)
    console.log('🧹 Clearing existing data...');
    await client.query('DELETE FROM products');
    await client.query('DELETE FROM categories');
    await client.query('ALTER SEQUENCE categories_id_seq RESTART WITH 1');
    console.log('✓ Cleared existing data\n');

    let categoryCount = 0;
    let subcategoryCount = 0;
    let productCount = 0;

    // Iterate through category hierarchy
    for (const [categoryName, categoryData] of Object.entries(categoryHierarchy)) {
      // Insert main category
      const categoryResult = await client.query(
        `INSERT INTO categories (name, slug, level, icon, priority, is_active) 
         VALUES ($1, $2, 0, $3, $4, true) 
         RETURNING id`,
        [categoryName, categoryData.slug, categoryData.icon, 100 - categoryCount * 10]
      );
      
      const categoryId = categoryResult.rows[0].id;
      categoryCount++;
      console.log(`📁 Created category: ${categoryName} (ID: ${categoryId})`);

      // Insert subcategories and products
      for (const [subcategoryName, subcategoryData] of Object.entries(categoryData.subcategories)) {
        // Insert subcategory
        const subcategoryResult = await client.query(
          `INSERT INTO categories (name, slug, parent_id, level, priority, is_active) 
           VALUES ($1, $2, $3, 1, $4, true) 
           RETURNING id`,
          [subcategoryName, subcategoryData.slug, categoryId, 90 - subcategoryCount * 5]
        );

        const subcategoryId = subcategoryResult.rows[0].id;
        subcategoryCount++;
        console.log(`  └─ Created subcategory: ${subcategoryName} (ID: ${subcategoryId})`);

        // Insert products for this subcategory
        const productNames = subcategoryData.products;
        
        for (const productName of productNames) {
          const productData = generateProductData(productName, subcategoryId, subcategoryId);
          
          await client.query(
            `INSERT INTO products (name, slug, category_id, brand, description, price, original_price, 
             discount_percent, stock, rating_avg, rating_count, popularity_score, is_active, is_featured)
             VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, true, false)`,
            [
              productData.name,
              productData.slug,
              subcategoryId,
              productData.brand,
              productData.description,
              productData.price,
              productData.originalPrice,
              productData.discountPercent,
              productData.stock,
              productData.rating,
              productData.ratingCount,
              Math.floor(Math.random() * 10000)
            ]
          );
          
          productCount++;
        }
        
        console.log(`     └─ Added ${productNames.length} products\n`);
      }
    }

    console.log('\n✅ Database population completed!');
    console.log(`📊 Summary:`);
    console.log(`   • Categories: ${categoryCount}`);
    console.log(`   • Subcategories: ${subcategoryCount}`);
    console.log(`   • Products: ${productCount}`);
    console.log(`   • Total: ${categoryCount + subcategoryCount + productCount} items`);

  } catch (error) {
    console.error('❌ Error populating database:', error);
    throw error;
  } finally {
    await client.release();
    await pool.end();
  }
}

// Run the population
populateDatabase().catch(console.error);
