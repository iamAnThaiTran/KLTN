import ProductCard from '../common/ProductCard';
import { gamingGear, kitchen, laptop, phone, sport } from './mock_data';

function WelcomeScreen({ onPromptClick }) {
  const suggestedPrompts = [
    { icon: '🎮', title: 'Gaming gear dưới 10tr' },
    { icon: '💻', title: 'Laptop văn phòng giá tốt' },
    { icon: '📱', title: 'Điện thoại mới 2024' },
    { icon: '🖥️', title: 'Màn hình 4K' },
    { icon: '🏋️', title: 'Thiết bị thể thao' },
    { icon: '🍳', title: 'Đồ gia dụng bếp' },
  ];

  const categories = [
    { icon: '🎮', title: 'Gaming Gear', products: gamingGear },
    { icon: '💻', title: 'Laptop', products: laptop },
    { icon: '📱', title: 'Điện Thoại', products: phone },
    { icon: '🍳', title: 'Gia dụng', products: kitchen },
    { icon: '🏋️', title: 'Thể thao', products: sport },
  ];

  return (
    <div className="flex-1 overflow-y-auto p-8">
      <div className="max-w-5xl mx-auto">
        {/* Welcome Section - Compact */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            Chào, bạn đang tìm gì?
          </h1>
          <p className="text-gray-600 text-sm">
            Mô tả sản phẩm bạn cần, AI sẽ giúp bạn tìm thứ tốt nhất
          </p>
        </div>
        
        {/* Suggested Prompts - Grid nhỏ hơn, 3 cột */}
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 mb-10">
          {suggestedPrompts.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => onPromptClick(prompt.title)}
              className="bg-white border border-gray-200 rounded-lg p-4 text-left hover:border-indigo-400 hover:shadow-md transition-all group"
            >
              <div className="text-2xl mb-2 group-hover:scale-110 transition-transform">
                {prompt.icon}
              </div>
              <h3 className="font-medium text-gray-900 text-sm">
                {prompt.title}
              </h3>
            </button>
          ))}
        </div>
        
        {/* Hot Products by Categories */}
        <div className="space-y-8">
          {categories.map((cat) => (
            <div key={cat.title} className="mb-6">
              <div className="flex items-center gap-2 mb-4">
                <h2 className="text-lg font-semibold text-gray-900">
                  <span className="text-xl">{cat.icon}</span> {cat.title}
                </h2>
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-5 gap-4">
                {cat.products.slice(0, 5).map((product, idx) => (
                  <ProductCard
                    key={idx}
                    product={product}
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