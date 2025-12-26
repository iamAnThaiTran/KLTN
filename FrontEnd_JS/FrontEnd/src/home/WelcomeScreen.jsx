import { MessageCircle, Plus, Search, Trash2, Send, Sparkles } from 'lucide-react';
import ProductCard from '../common/ProductCard';
import { gamingGear, kitchen, laptop, phone, sport } from './mock_data';

function WelcomeScreen({ onPromptClick }) {
  const suggestedPrompts = [
    { icon: '🎮', title: 'Gợi ý gaming gear', subtitle: 'Tìm thiết bị chơi game phù hợp' },
    { icon: '💻', title: 'Laptop văn phòng', subtitle: 'Máy tính làm việc hiệu quả' },
    { icon: '📱', title: 'Điện thoại mới nhất', subtitle: 'Smartphone hot nhất 2024' },
    { icon: '🖥️', title: 'Màn hình & thiết bị PC', subtitle: 'Không gian làm việc hiện đại' },
    { icon: '🏋️', title: 'Thiết bị thể thao', subtitle: 'Rèn luyện sức khỏe mỗi ngày' },
    { icon: '🍳', title: 'Đồ gia dụng nhà bếp', subtitle: 'Nấu ăn tiện lợi và nhanh chóng' },
    { icon: '🛋️', title: 'Nội thất & trang trí', subtitle: 'Không gian sống phong cách' },
    { icon: '🚗', title: 'Phụ kiện ô tô', subtitle: 'Lái xe an toàn và tiện nghi' },
    { icon: '🧴', title: 'Mỹ phẩm & chăm sóc da', subtitle: 'Làm đẹp và chăm sóc bản thân' },
    { icon: '📚', title: 'Sách & học tập', subtitle: 'Tri thức và kỹ năng mới' }
  ];

  // Mock product base
  const baseProduct = {
    description: '15.12-29.12 Voucher 18% CHO ĐƠN TỪ 199K',
    price: 299000,
    rating: 4.8,
    image: 'https://img.lazcdn.com/g/ff/kf/S20b9405a7a0247b5ab3464cf57a806ecl.jpg_720x720q80.jpg_.webp'
  };

  // Tạo mock products cho từng ngành (12 items mỗi ngành để grid đầy đặn)
  const createMockProducts = (categoryTitle) => {
    return Array(12).fill(null).map((_, i) => ({
      ...baseProduct,
      title: `${categoryTitle} - Sản phẩm hot ${i + 1}`,
    }));
  };

  const categories = [
    { icon: '🎮', title: 'Gaming Gear Hot 🔥', products: gamingGear },
    { icon: '💻', title: 'Laptop Văn Phòng Hot 🔥', products: laptop },
    { icon: '📱', title: 'Điện Thoại Mới Nhất 🔥', products: phone },
    { icon: '🍳', title: 'Đồ gia dụng nhà bếp 🔥', products: kitchen },
    { icon: '🏋️', title: 'Thiết Bị Thể Thao Hot 🔥', products: sport },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-4xl mx-auto">
        {/* Mascot & Greeting */}
        <div className="text-center mb-12">
          <div className="inline-block mb-4 animate-bounce">
            <div className="w-24 h-24 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-4xl shadow-lg">
              🤖
            </div>
          </div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Chào, tôi có thể giúp gì không?
          </h1>
          <p className="text-gray-600">
            Hỏi tôi về bất kỳ sản phẩm nào bạn quan tâm
          </p>
        </div>
        
        {/* Suggested Prompts */}
        <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-12">
          {suggestedPrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => onPromptClick(prompt.title)}
              className="bg-gradient-to-br from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-xl p-6 text-left hover:shadow-lg hover:border-blue-400 transition-all group"
            >
              <div className="text-3xl mb-3 group-hover:scale-110 transition-transform">
                {prompt.icon}
              </div>
              <h3 className="font-semibold text-gray-900 mb-1">
                {prompt.title}
              </h3>
              <p className="text-sm text-gray-600">{prompt.subtitle}</p>
            </button>
          ))}
        </div>
        
        {/* Hot Products by Categories */}
        <div className="space-y-12">
          {categories.map((cat) => (
            <div key={cat.title} className="mb-8">
              <div className="flex items-center gap-2 mb-6">
                <Sparkles className="w-5 h-5 text-yellow-500" />
                <h2 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                  <span className="text-2xl">{cat.icon}</span> {cat.title}
                </h2>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-6">
                {cat.products.map((product, idx) => (
                  <ProductCard
                    key={idx}
                    product={product}
                    // onClick={() => onPromptClick(`Cho tôi xem thông tin về ${product.title}`)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default WelcomeScreen;