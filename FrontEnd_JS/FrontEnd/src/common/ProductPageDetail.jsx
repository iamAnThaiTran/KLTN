import { useLocation, useNavigate } from 'react-router-dom';
import { Shield, Truck, RefreshCw, Headphones, Star } from 'lucide-react';
import shopeeLogo from '../assets/shopee.png';
import lazadaLogo from '../assets/lazada.png';
import tikiLogo from '../assets/tiki.png';


function ProductDetailPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const product = location.state?.product;

  // Nếu không có product (người dùng refresh page), redirect về trang chủ
  if (!product) {
    navigate('/');
    return null;
  }

  const url = product?.link?.startsWith('http')
    ? product.link
    : `https://${product.link}`;

  const getSellerName = (link) => {
    if (!link) return 'Cửa hàng';
    if (link.includes('shopee')) return 'Shopee';
    if (link.includes('lazada')) return 'Lazada';
    if (link.includes('tiki')) return 'Tiki';
    if (link.includes('sendo')) return 'Sendo';
    return 'Cửa hàng';
  };

  const getSellerLogo = (link) => {
    if (!link) return null;
    const lowerLink = link.toLowerCase();
    if (lowerLink.includes('shopee')) return shopeeLogo;
    if (lowerLink.includes('lazada')) return lazadaLogo;
    if (lowerLink.includes('tiki')) return tikiLogo;
    return null;
  };


  const seller = getSellerName(product.link);
  const sellerLogo = getSellerLogo(product.link);

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white shadow-sm sticky top-0 z-10">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="text-gray-600 hover:text-gray-900 font-medium"
          >
            ← Quay lại
          </button>
          <div className="h-6 w-px bg-gray-300"></div>
          <h1 className="text-lg font-semibold text-gray-900">Chi tiết sản phẩm</h1>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-7xl mx-auto px-4 py-6">
        <div className="bg-white rounded-xl shadow-sm overflow-hidden">
          <div className="grid md:grid-cols-2 gap-8 p-6">
            {/* Product Image */}
            <div className="flex items-center justify-center bg-gray-50 rounded-xl p-8">
              <img
                src={product.imageUrl ?? product.image}
                alt={product.title}
                className="max-w-full h-auto max-h-96 object-contain"
              />
            </div>

            {/* Product Info */}
            <div className="flex flex-col">
              <h2 className="text-2xl font-bold text-gray-900 mb-4">
                {product.title}
              </h2>

              <div className="mb-6">
                <div className="flex items-baseline gap-3 mb-2">
                  <span className="text-3xl font-bold text-orange-600">
                    ₫{(product.price ?? 0).toLocaleString('vi-VN')}
                  </span>
                </div>
                <p className="text-sm text-gray-500">Giá tại {seller}</p>
              </div>

              {/* Trust Value */}
              {product.trust_value && (
                <div className="flex items-center gap-2 mb-6 p-3 bg-green-50 rounded-lg">
                  <Shield className="w-5 h-5 text-green-600" />
                  <span className="text-sm text-green-700">
                    Độ tin cậy: {product.trust_value}/10
                  </span>
                </div>
              )}

              {/* Seller Info Card */}
              <div className="border-2 border-yellow-400 rounded-xl p-4 mb-6 bg-yellow-50">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center gap-2">
                  {sellerLogo ? (
                    <img src={sellerLogo} alt={seller} className="w-6 h-6 object-contain" />
                  ) : (
                    <span className="text-2xl">🏪</span>
                  )}
                  <span>Gian hàng: {seller}</span>

                </h3>

                <div className="space-y-2 mb-4 text-sm text-gray-600">
                  <div className="flex items-center gap-2">
                    <Shield className="w-4 h-4 text-red-500" />
                    <span>Giao hàng toàn quốc</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Truck className="w-4 h-4 text-red-500" />
                    <span>Được kiểm tra hàng</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <RefreshCw className="w-4 h-4 text-red-500" />
                    <span>Thanh toán khi nhận hàng</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Headphones className="w-4 h-4 text-red-500" />
                    <span>Chất lượng, Uy tín</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Star className="w-4 h-4 text-red-500" />
                    <span>7 ngày đổi trả dễ dàng</span>
                  </div>
                </div>

                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block w-full bg-red-600 hover:bg-red-700 text-white font-semibold py-3 px-6 rounded-lg text-center transition-colors"
                >
                  ĐẾN NƠI BÁN
                </a>
              </div>

              {/* Store buttons */}
              <div className="space-y-3">
                <div className="text-sm font-semibold text-gray-700 mb-2">
                  SO SÁNH GIÁ TẠI:
                </div>

                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:border-orange-400 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    
                      <img src={shopeeLogo} alt={seller} className="w-6 h-6 object-contain" />
                   
                    <span className="font-medium text-gray-700 group-hover:text-orange-600">
                      Shopee
                    </span>
                  </div>
                  <span className="text-sm text-white bg-orange-500 px-4 py-1 rounded">
                    Xem giá
                  </span>
                </a>

                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:border-blue-400 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    
                      <img src={lazadaLogo} alt={seller} className="w-6 h-6 object-contain" />
                    

                    <span className="font-medium text-gray-700 group-hover:text-blue-600">
                      Lazada
                    </span>
                  </div>
                  <span className="text-sm text-white bg-blue-500 px-4 py-1 rounded">
                    Xem giá
                  </span>
                </a>

                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center justify-between p-3 border border-gray-200 rounded-lg hover:border-blue-400 transition-colors group"
                >
                  <div className="flex items-center gap-3">
                    
                      <img src={tikiLogo} alt={seller} className="w-6 h-6 object-contain" />
                    

                    <span className="font-medium text-gray-700 group-hover:text-blue-600">
                      Tiki
                    </span>
                  </div>
                  <span className="text-sm text-white bg-blue-600 px-4 py-1 rounded">
                    Xem giá
                  </span>
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default ProductDetailPage;