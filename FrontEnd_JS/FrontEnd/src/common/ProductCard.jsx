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
      className="block bg-white border border-gray-200 rounded-xl p-2 hover:shadow-lg hover:border-blue-300 transition-all cursor-pointer"
    >
      <img
        src={product.imageUrl ?? product.image}
        alt={product.title ?? 'Sản phẩm'}
        className="w-full h-40 object-cover rounded-lg mb-3"
      />
      <h3 className="font-semibold text-gray-900 mb-1 line-clamp-2">
        {product.title}
      </h3>
      <p className="text-sm text-gray-500 mb-2 line-clamp-2">
        {product.title}
      </p>
      <div className="flex items-center justify-between">
        <span className="text-lg font-semibold text-orange-600">
          ₫{(product.price ?? 0).toLocaleString('vi-VN')}
        </span>
      </div>
    </div>
  );
}

export default ProductCard;