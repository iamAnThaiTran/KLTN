import { useNavigate } from 'react-router-dom';
import { Loader2 } from 'lucide-react';

export default function ProductGrid({ products, isLoading, isHidden }) {
  const navigate = useNavigate();

  const handleProductClick = (product) => {
    navigate(`/product/${encodeURIComponent(product.title)}`, {
      state: { product }
    });
  };

  if (isHidden) {
    return null;
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="flex flex-col items-center gap-3">
          <Loader2 className="w-8 h-8 text-indigo-600 animate-spin" />
          <p className="text-gray-600 text-sm">Đang tìm kiếm sản phẩm...</p>
        </div>
      </div>
    );
  }

  if (!products || products.length === 0) {
    return (
      <div className="flex items-center justify-center h-96">
        <p className="text-gray-500 text-center">
          Không tìm thấy sản phẩm nào. Hãy thử tìm kiếm khác.
        </p>
      </div>
    );
  }

  return (
    <div className="px-6 pb-12">
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
        {products.map((product) => (
          <div
            key={product.id || product.title}
            onClick={() => handleProductClick(product)}
            className="bg-white border border-gray-200 rounded-lg p-3 hover:shadow-lg hover:border-indigo-300 transition-all cursor-pointer group"
          >
            <img
              src={product.imageUrl ?? product.image}
              alt={product.title ?? 'Sản phẩm'}
              className="w-full h-40 object-cover rounded-lg mb-3 group-hover:scale-105 transition-transform"
            />
            <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2 text-sm">
              {product.title}
            </h3>
            <p className="text-xs text-gray-500 mb-3 line-clamp-1">
              {product.brand ?? 'Không rõ'}
            </p>
            <div className="flex items-center justify-between">
              <span className="text-base font-bold text-indigo-600">
                ₫{(product.price ?? 0).toLocaleString('vi-VN')}
              </span>
            </div>
            {product.rating && (
              <div className="text-xs text-gray-500 mt-2">
                ⭐ {product.rating}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
