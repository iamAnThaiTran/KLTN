import React, { useState, useEffect } from 'react';
import { Lightbulb, TrendingUp, RefreshCw } from 'lucide-react';
import SearchHistoryService from '../services/searchHistoryService';
import { useAuth } from '../context/AuthContext';

const RecommendedProducts = ({ onProductClick }) => {
  const { user, token, isAuthenticated } = useAuth();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [recommendationType, setRecommendationType] = useState('personalized');
  const [topCategories, setTopCategories] = useState([]);
  const [topBrands, setTopBrands] = useState([]);

  useEffect(() => {
    fetchRecommendations();
  }, [isAuthenticated, token]);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError(null);
    
    try {
      if (isAuthenticated && token) {
        console.log('[RecommendedProducts] Fetching personalized recommendations for user:', user?.id)
        // Authenticated user: get personalized recommendations
        const data = await SearchHistoryService.getRecommendedProducts(token);
        
        if (data.status === 'success') {
          setProducts(data.recommended_products || []);
          setRecommendationType('personalized');
          setTopCategories(data.top_categories || []);
          setTopBrands(data.top_brands || []);
        } else if (data.status === 'unauthenticated') {
          // Fallback to public recommendations
          fetchPublicRecommendations();
        } else {
          setError('Failed to fetch recommendations');
          // Fallback to public recommendations on error
          fetchPublicRecommendations();
        }
      } else {
        // Non-authenticated user: get public/trending recommendations
        fetchPublicRecommendations();
      }
    } catch (err) {
      console.error('[RecommendedProducts] Error fetching recommendations:', err);
      setError('Unable to load recommendations');
      // Still try to fetch public recommendations as fallback
      fetchPublicRecommendations();
    }
  };

  const fetchPublicRecommendations = async () => {
    try {
      const data = await SearchHistoryService.getPublicRecommendations();
      
      if (data.status === 'success') {
        setProducts(data.products || []);
        setRecommendationType('trending');
        setTopCategories(data.popular_categories || []);
        setTopBrands(data.popular_brands || []);
      } else {
        setError('Unable to load trending products');
      }
    } catch (err) {
      console.error('[RecommendedProducts] Error fetching public recommendations:', err);
      setError('Unable to load trending products');
    }
  };

  const handleRefresh = () => {
    fetchRecommendations();
  };

  const handleProductClick = (product) => {
    if (onProductClick) {
      onProductClick(product);
    }
  };

  if (loading && products.length === 0) {
    return (
      <div style={{
        background: '#fff',
        borderRadius: 16,
        border: '1.5px solid #ede9fe',
        padding: 16,
        marginBottom: 32
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: 150,
          color: '#94a3b8'
        }}>
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 8
          }}>
            <RefreshCw size={24} style={{ animation: 'spin 1s linear infinite' }} />
            <span style={{ fontSize: 13 }}>Đang tải gợi ý...</span>
          </div>
        </div>
        <style>{`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  const headerText = recommendationType === 'personalized'
    ? 'Gợi ý dành riêng cho bạn'
    : '🔥 Sản phẩm phổ biến hôm nay';

  const headerIcon = recommendationType === 'personalized' ? <Lightbulb size={18} color="#8b5cf6" /> : <TrendingUp size={18} color="#ef4444" />;

  const subText = recommendationType === 'personalized'
    ? topCategories.length > 0
      ? `Dựa trên quan tâm của bạn: ${topCategories.join(', ')}`
      : 'Dựa trên lịch sử tìm kiếm của bạn'
    : 'Những sản phẩm được nhiều khách hàng tìm kiếm';

  return (
    <div style={{
      background: '#fff',
      borderRadius: 16,
      border: '1.5px solid #ede9fe',
      padding: 16,
      marginBottom: 32
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 14
      }}>
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8
        }}>
          {headerIcon}
          <h3 style={{
            fontWeight: 800,
            fontSize: 16,
            color: '#1e1b4b',
            margin: 0
          }}>
            {headerText}
          </h3>
        </div>
        <button
          onClick={handleRefresh}
          disabled={loading}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: '#6366f1',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            opacity: loading ? 0.5 : 1,
            transition: 'opacity 0.2s',
            fontSize: 18,
            padding: 4
          }}
          title="Làm mới gợi ý"
        >
          <RefreshCw size={16} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
        </button>
      </div>

      {/* Subtext */}
      <div style={{
        fontSize: 13,
        color: '#64748b',
        marginBottom: 14,
        lineHeight: 1.5
      }}>
        {subText}
      </div>

      {/* Error state */}
      {error && products.length === 0 && (
        <div style={{
          background: '#fee2e2',
          border: '1px solid #fca5a5',
          borderRadius: 10,
          padding: 12,
          color: '#991b1b',
          fontSize: 13,
          marginBottom: 12
        }}>
          ⚠️ {error}
        </div>
      )}

      {/* Products Grid */}
      {products.length > 0 ? (
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
          gap: 12
        }}>
          {products.map((product, index) => (
            <ProductCard
              key={product.id || product.sku_id || index}
              product={product}
              onClick={() => handleProductClick(product)}
            />
          ))}
        </div>
      ) : (
        <div style={{
          textAlign: 'center',
          padding: '24px 0',
          color: '#94a3b8'
        }}>
          <p style={{ fontSize: 13, margin: 0 }}>Không có gợi ý sản phẩm vào lúc này</p>
        </div>
      )}

      {/* Brand info if available */}
      {topBrands && topBrands.length > 0 && (
        <div style={{
          marginTop: 16,
          paddingTop: 12,
          borderTop: '1px solid #f0f0f8',
          fontSize: 12,
          color: '#64748b'
        }}>
          <span style={{ fontWeight: 600 }}>Các thương hiệu phổ biến:</span> {topBrands.slice(0, 5).join(', ')}
        </div>
      )}
    </div>
  );
};

// Product card component
function ProductCard({ product, onClick }) {
  const formatPrice = (price) => {
    if (typeof price === 'number') {
      return `₫${price.toLocaleString('vi-VN')}`;
    }
    return price || 'N/A';
  };

  const productImage = product.image_url || product.thumbnail || product.img || 'https://via.placeholder.com/140x120/f0f0f0/999?text=No+Image';
  const productName = product.name || product.product_name || product.title || 'Sản phẩm';
  const productPrice = product.price || product.selling_price || 'Liên hệ';

  return (
    <div
      onClick={onClick}
      style={{
        background: '#fff',
        borderRadius: 12,
        border: '1.5px solid #f0f0f8',
        padding: 10,
        cursor: 'pointer',
        transition: 'all 0.15s',
        width: '100%',
        boxSizing: 'border-box'
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#6366f1';
        e.currentTarget.style.boxShadow = '0 4px 16px rgba(99,102,241,0.15)';
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#f0f0f8';
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {/* Image */}
      <div style={{
        background: '#f8f9ff',
        borderRadius: 10,
        height: 90,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        marginBottom: 10,
        overflow: 'hidden'
      }}>
        <img
          src={productImage}
          alt={productName}
          style={{
            maxWidth: '100%',
            maxHeight: '100%',
            objectFit: 'contain'
          }}
          onError={(e) => {
            e.target.src = 'https://via.placeholder.com/140x120/f0f0f0/999?text=No+Image';
          }}
        />
      </div>

      {/* Name */}
      <div style={{
        fontSize: 12,
        fontWeight: 700,
        color: '#1e1b4b',
        marginBottom: 6,
        lineHeight: 1.3,
        display: '-webkit-box',
        WebkitLineClamp: 2,
        WebkitBoxOrient: 'vertical',
        overflow: 'hidden'
      }}>
        {productName}
      </div>

      {/* Price */}
      <div style={{
        fontSize: 12,
        fontWeight: 700,
        color: '#6366f1',
        marginBottom: 6
      }}>
        {formatPrice(productPrice)}
      </div>

      {/* Recommendation reason if available */}
      {product.recommendation_reason && (
        <div style={{
          fontSize: 10,
          color: '#94a3b8',
          lineHeight: 1.3,
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          overflow: 'hidden',
          fontStyle: 'italic'
        }}>
          💡 {product.recommendation_reason}
        </div>
      )}

      {/* Rating if available */}
      {product.rating && (
        <div style={{
          fontSize: 11,
          color: '#f59e0b',
          marginTop: 4
        }}>
          ⭐ {product.rating}
        </div>
      )}
    </div>
  );
}

export default RecommendedProducts;
