import { useNavigate } from 'react-router-dom';

function ProductCard({ product }) {
  const navigate = useNavigate();

  const handleClick = () => {
    // Encode product data vào URL
    navigate(`/product/${encodeURIComponent(product.title)}`, {
      state: { product }
    });
  };

  return (
    <div
      onClick={handleClick}
      className="block bg-white border border-gray-200 rounded-lg p-3 hover:shadow-lg hover:border-indigo-300 transition-all cursor-pointer group"
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
  );
}

export default ProductCard;