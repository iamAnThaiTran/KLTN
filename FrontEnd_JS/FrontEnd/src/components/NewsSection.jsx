// components/NewsSection.jsx
import React from 'react';

const NewsSection = ({ 
  articles: propArticles = [], 
  title = "TIN TỨC", 
  maxHeight = "400px",      
  maxItems = 4,             
  className = "" 
}) => {
  // Mock data tạm thời (dùng khi chưa có dữ liệu thật)
  const mockArticles = [
    {
      thumbnail: "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400",
      title: "Xiaomi Redmi Note 14 5G ra mắt: Pin 6000mAh, giá chỉ từ 5.6 triệu",
      excerpt: "Dòng máy tầm trung mới nhất với camera 108MP và màn hình AMOLED 120Hz, đang gây sốt tại thị trường Việt Nam.",
      link: "/tin-tuc/xiaomi-redmi-note-14-5g",
      date: "15/01/2026"
    },
    {
      thumbnail: "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?w=400",
      title: "Bếp từ Bosch PMB65EW2 VN giảm sốc còn 6 triệu đồng",
      excerpt: "Sản phẩm nhập khẩu Đức chính hãng, công nghệ nấu nướng thông minh, bảo hành 2 năm.",
      link: "/tin-tuc/bosch-pmb65ew2",
      date: "14/01/2026"
    },
    {
      thumbnail: "https://images.unsplash.com/photo-1503376780353-7e6692767b70?w=400",
      title: "Xe máy điện VinFast Feliz S mới: Giá cạnh tranh, pin lithium-ion",
      excerpt: "Thiết kế thời thượng, phạm vi di chuyển lên đến 90km/lần sạc, phù hợp di chuyển đô thị.",
      link: "/tin-tuc/vinfast-feliz-s",
      date: "13/01/2026"
    },
    {
      thumbnail: "https://images.unsplash.com/photo-1581093450021-4a7360e9a6b5?w=400",
      title: "TV Sony Mini LED 65 inch giảm giá kỷ lục còn 22 triệu",
      excerpt: "Công nghệ XR Cognitive Processor, hình ảnh sắc nét, âm thanh Dolby Atmos sống động.",
      link: "/tin-tuc/sony-mini-led-65-inch",
      date: "12/01/2026"
    },
    {
      thumbnail: "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=400",
      title: "iPhone Air 'sắp tới' chỉ từ 7 triệu, người dùng Việt chờ đón",
      excerpt: "Tin đồn về mẫu iPhone mỏng nhẹ nhất từ trước đến nay, dự kiến ra mắt cuối 2026.",
      link: "/tin-tuc/iphone-air-2026",
      date: "10/01/2026"
    }
  ];

  // Ưu tiên props articles, nếu rỗng thì dùng mock
  const articles = propArticles.length > 0 ? propArticles : mockArticles;

  const displayedArticles = maxItems === Infinity 
    ? articles 
    : articles.slice(0, maxItems);

  return (
    <div className={`bg-white border border-gray-200 rounded-lg overflow-hidden ${className}`}>
      {/* Header */}
      <div className="bg-gray-50 px-5 py-4 border-b border-gray-200">
        <h2 className="text-xl font-bold text-gray-800 text-center md:text-left">
          {title}
        </h2>
      </div>

      {/* Danh sách tin tức */}
      <div 
        className="divide-y divide-gray-100"
        style={{ maxHeight, overflowY: maxHeight ? 'auto' : 'visible' }}
      >
        {displayedArticles.length === 0 ? (
          <div className="px-5 py-8 text-center text-gray-500">
            Chưa có tin tức nào
          </div>
        ) : (
          displayedArticles.map((article, index) => (
            <a
              key={index}
              href={article.link || '#'}
              className="flex items-start p-4 hover:bg-gray-50 transition-colors duration-150 group"
            >
              {/* Thumbnail */}
              <div className="flex-shrink-0 mr-4">
                <img
                  src={article.thumbnail}
                  alt={article.title}
                  className="w-28 h-20 md:w-32 md:h-24 object-cover rounded-md border border-gray-200"
                  loading="lazy"
                />
              </div>

              {/* Nội dung */}
              <div className="flex-1 min-w-0">
                <h3 className="text-base md:text-lg font-semibold text-blue-600 group-hover:text-blue-800 line-clamp-2">
                  {article.title}
                </h3>
                <p className="mt-1 text-sm text-gray-600 line-clamp-2 md:line-clamp-3">
                  {article.excerpt}
                </p>
                {article.date && (
                  <p className="mt-1 text-xs text-gray-500">
                    {article.date}
                  </p>
                )}
              </div>
            </a>
          ))
        )}
      </div>

      {/* Footer - Xem thêm */}
      {articles.length > maxItems && maxItems !== Infinity && (
        <div className="px-5 py-3 bg-gray-50 border-t border-gray-200 text-center">
          <button className="text-blue-600 hover:text-blue-800 font-medium text-sm">
            Xem thêm tin tức →
          </button>
        </div>
      )}
    </div>
  );
};

export default NewsSection;