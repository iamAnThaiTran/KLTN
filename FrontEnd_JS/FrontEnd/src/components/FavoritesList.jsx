import React, { useState, useEffect } from 'react';
import { Heart, ArrowLeft, Trash2, Loader } from 'lucide-react';
import { getUserFavorites, removeFromFavorites, clearAllFavorites } from '../utils/favoritesApi';

/**
 * FavoritesList Component
 * Displays user's favorite products in a grid layout
 */
export default function FavoritesList({ token, user, onBack, onProductClick }) {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [totalCount, setTotalCount] = useState(0);
  const [deletingId, setDeletingId] = useState(null);
  const [isClearing, setIsClearing] = useState(false);

  // Fetch favorites on mount
  useEffect(() => {
    if (token && user) {
      fetchFavorites();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, user]);

  const fetchFavorites = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getUserFavorites(token, { limit: 100, offset: 0 });
      setFavorites(response.favorites || []);
      setTotalCount(response.total || 0);
    } catch (err) {
      console.error('Error fetching favorites:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async (productId) => {
    try {
      setDeletingId(productId);
      await removeFromFavorites(productId, token);
      setFavorites(favorites.filter(fav => fav.product_id !== productId));
      setTotalCount(totalCount - 1);
    } catch (err) {
      alert('Lỗi khi xóa sản phẩm yêu thích: ' + err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const handleClearAll = async () => {
    if (!window.confirm('Bạn chắn chắn muốn xóa tất cả sản phẩm yêu thích?')) return;

    try {
      setIsClearing(true);
      await clearAllFavorites(token);
      setFavorites([]);
      setTotalCount(0);
    } catch (err) {
      alert('Lỗi khi xóa tất cả: ' + err.message);
    } finally {
      setIsClearing(false);
    }
  };

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#fff',
      borderRadius: 12,
      overflow: 'hidden',
      animation: 'slideIn 0.3s ease',
    }}>
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .favorite-item {
          animation: fadeIn 0.3s ease;
        }
      `}</style>

      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 20px',
        borderBottom: '1px solid #f0f0f8',
        background: 'linear-gradient(135deg, #e11d48, #be123c)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={onBack}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: '#fff',
              borderRadius: '50%',
              width: 36,
              height: 36,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.3)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>
              ❤️ Sản phẩm yêu thích
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)', marginTop: 2 }}>
              {totalCount} sản phẩm
            </div>
          </div>
        </div>
        {favorites.length > 0 && (
          <button
            onClick={handleClearAll}
            disabled={isClearing}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: '1px solid rgba(255,255,255,0.3)',
              color: '#fff',
              padding: '8px 12px',
              borderRadius: 6,
              cursor: isClearing ? 'not-allowed' : 'pointer',
              fontSize: 12,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              transition: 'all 0.2s',
              opacity: isClearing ? 0.6 : 1,
            }}
            onMouseEnter={e => !isClearing && (e.currentTarget.style.background = 'rgba(255,255,255,0.3)')}
            onMouseLeave={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.2)')}
          >
            <Trash2 size={14} />
            Xóa tất cả
          </button>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {loading ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#94a3b8',
            flexDirection: 'column',
            gap: 12,
          }}>
            <Loader size={32} style={{ animation: 'spin 1s linear infinite' }} />
            <div>Đang tải sản phẩm yêu thích...</div>
          </div>
        ) : error ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#e11d48',
            flexDirection: 'column',
            gap: 12,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 24 }}>⚠️</div>
            <div>{error}</div>
            <button
              onClick={fetchFavorites}
              style={{
                padding: '8px 16px',
                background: '#e11d48',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600,
                marginTop: 8,
              }}
            >
              Thử lại
            </button>
          </div>
        ) : favorites.length === 0 ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#94a3b8',
            flexDirection: 'column',
            gap: 12,
            textAlign: 'center',
          }}>
            <Heart size={48} style={{ opacity: 0.5 }} />
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#475569' }}>
                Chưa có sản phẩm yêu thích
              </div>
              <div style={{ fontSize: 13, marginTop: 4 }}>
                Hãy thêm sản phẩm yêu thích của bạn
              </div>
            </div>
          </div>
        ) : (
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
            gap: 12,
          }}>
            {favorites.map((fav) => {
              const product = fav.product;
              if (!product) return null;

              const productUrl = product.product_url;
              const productImage = product.thumbnail;
              const productPrice = product.min_price || product.skus?.[0]?.price;

              return (
                <div
                  key={fav.id}
                  className="favorite-item"
                  style={{
                    background: '#f8f9ff',
                    borderRadius: 10,
                    overflow: 'hidden',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    border: '1px solid #e2e8f0',
                    position: 'relative',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.boxShadow = '0 8px 16px rgba(99,102,241,0.15)';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.boxShadow = 'none';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                  onClick={() => {
                    if (productUrl && onProductClick) {
                      onProductClick(productUrl);
                    } else if (productUrl) {
                      window.open(productUrl, '_blank');
                    }
                  }}
                >
                  {/* Image */}
                  {productImage && (
                    <div style={{
                      height: 120,
                      background: '#fff',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      overflow: 'hidden',
                    }}>
                      <img
                        src={productImage}
                        alt={product.title}
                        style={{
                          maxWidth: '100%',
                          maxHeight: '100%',
                          objectFit: 'contain',
                        }}
                      />
                    </div>
                  )}

                  {/* Remove Button */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRemove(fav.product_id);
                    }}
                    disabled={deletingId === fav.product_id}
                    style={{
                      position: 'absolute',
                      top: 8,
                      right: 8,
                      background: '#e11d48',
                      border: 'none',
                      color: '#fff',
                      borderRadius: '50%',
                      width: 28,
                      height: 28,
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      cursor: deletingId === fav.product_id ? 'not-allowed' : 'pointer',
                      transition: 'all 0.2s',
                      opacity: deletingId === fav.product_id ? 0.6 : 1,
                      zIndex: 10,
                    }}
                    onMouseEnter={e => !deletingId && (e.currentTarget.style.transform = 'scale(1.1)')}
                    onMouseLeave={e => (e.currentTarget.style.transform = 'scale(1)')}
                  >
                    <Heart size={14} fill="#fff" />
                  </button>

                  {/* Product Info */}
                  <div style={{ padding: '10px 10px' }}>
                    <div style={{
                      fontSize: 11,
                      fontWeight: 600,
                      color: '#1e1b4b',
                      lineHeight: 1.4,
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                      overflow: 'hidden',
                    }}>
                      {product.title}
                    </div>
                    {productPrice && (
                      <div style={{
                        fontSize: 12,
                        fontWeight: 700,
                        color: '#e11d48',
                        marginTop: 4,
                      }}>
                        {typeof productPrice === 'number'
                          ? (productPrice / 1000000).toFixed(1) + 'tr'
                          : productPrice}
                      </div>
                    )}
                    {product.brand && (
                      <div style={{
                        fontSize: 10,
                        color: '#94a3b8',
                        marginTop: 2,
                      }}>
                        {product.brand}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
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
