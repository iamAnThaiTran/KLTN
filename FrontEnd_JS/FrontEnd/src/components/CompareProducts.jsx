import React, { useState, useEffect } from 'react';
import { ArrowLeft, Trash2, Loader, Check } from 'lucide-react';
import { getUserFavorites, compareProducts } from '../utils/favoritesApi';
import ComparisonResultFromApi from './ComparisonResultFromApi';
import ComparisonHistoryModal from './ComparisonHistoryModal';

/**
 * CompareProducts Component
 * Allows user to select products from favorites to compare
 */
export default function CompareProducts({ token, user, onBack }) {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selected, setSelected] = useState(new Set());
  const [comparing, setComparing] = useState(false);
  const [comparisonData, setComparisonData] = useState(null);
  const [showResult, setShowResult] = useState(false);
  const [showHistory, setShowHistory] = useState(false);

  // Fetch favorites on mount
  useEffect(() => {
    fetchFavorites();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const fetchFavorites = async () => {
    try {
      setLoading(true);
      setError(null);
      console.log('📥 Fetching favorites for comparison...');
      
      const userId = user?.user_id || user?.id;
      if (!userId) {
        throw new Error('User ID not found. Please login again.');
      }
      
      const response = await getUserFavorites(userId, { limit: 100, offset: 0 });
      console.log('✅ Favorites fetched:', response);
      setFavorites(response.favorites || []);
    } catch (err) {
      console.error('❌ Error fetching favorites:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleSelect = (productId) => {
    const newSelected = new Set(selected);
    if (newSelected.has(productId)) {
      newSelected.delete(productId);
    } else {
      if (newSelected.size < 4) {
        newSelected.add(productId);
      } else {
        alert('Bạn chỉ có thể so sánh tối đa 4 sản phẩm');
        return;
      }
    }
    setSelected(newSelected);
  };

  const handleCompare = () => {
    if (selected.size < 2) {
      alert('Vui lòng chọn ít nhất 2 sản phẩm để so sánh');
      return;
    }
    console.log('🔍 Comparing products:', Array.from(selected));
    
    // Convert Set to Array and send to server
    const productIds = Array.from(selected);
    
    setComparing(true);
    setError(null);
    
    compareProducts(productIds)
      .then(response => {
        console.log('✅ Comparison response:', response);
        setComparisonData(response);
        setShowResult(true);
        setSelected(new Set()); // Clear selection
      })
      .catch(err => {
        console.error('❌ Comparison error:', err);
        setError(err.message);
        alert(`❌ Lỗi: ${err.message}`);
      })
      .finally(() => {
        setComparing(false);
      });
  };

  // Handle back from comparison result
  const handleBackFromResult = () => {
    setShowResult(false);
    setComparisonData(null);
  };

  // Handle selecting a comparison from history
  const handleSelectFromHistory = (historicalComparison) => {
    setComparisonData(historicalComparison);
    setShowResult(true);
    setShowHistory(false);
  };

  const isSelected = (productId) => selected.has(productId);

  // If showing history, display the history modal
  if (showHistory) {
    return (
      <ComparisonHistoryModal
        user={user}
        onBack={() => setShowHistory(false)}
        onSelectComparison={handleSelectFromHistory}
      />
    );
  }

  // If showing result, display the comparison
  if (showResult && comparisonData) {
    return (
      <ComparisonResultFromApi
        data={comparisonData}
        onBack={handleBackFromResult}
        onOpenHistory={() => setShowHistory(true)}
      />
    );
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#fff',
        borderRadius: 12,
        overflow: 'hidden',
        animation: 'slideIn 0.3s ease',
      }}
    >
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
        .compare-item {
          animation: fadeIn 0.3s ease;
        }
      `}</style>

      {/* Header */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '16px 20px',
          borderBottom: '1px solid #f0f0f8',
          background: 'linear-gradient(135deg, #f59e0b, #d97706)',
        }}
      >
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
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.3)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.2)')}
          >
            <ArrowLeft size={18} />
          </button>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: '#fff' }}>
              🔍 So sánh sản phẩm
            </div>
            <div style={{ fontSize: 12, color: 'rgba(255,255,255,0.8)', marginTop: 2 }}>
              Chọn {selected.size}/4 sản phẩm
            </div>
          </div>
        </div>
        {selected.size > 0 && (
          <button
            onClick={handleCompare}
            disabled={selected.size < 2 || comparing}
            style={{
              background: selected.size < 2 || comparing ? 'rgba(255,255,255,0.3)' : 'rgba(255,255,255,0.95)',
              border: 'none',
              color: selected.size < 2 || comparing ? 'rgba(255,255,255,0.5)' : '#d97706',
              padding: '8px 16px',
              borderRadius: 6,
              cursor: selected.size < 2 || comparing ? 'not-allowed' : 'pointer',
              fontSize: 12,
              fontWeight: 600,
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) =>
              selected.size >= 2 && !comparing && (e.currentTarget.style.background = 'rgba(255,255,255,1)')
            }
            onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.95)')}
          >
            {comparing ? (
              <>
                <Loader size={12} style={{ animation: 'spin 1s linear infinite', marginRight: 4, display: 'inline' }} />
                Đang so sánh...
              </>
            ) : (
              <>So sánh ({selected.size})</>
            )}
          </button>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
        {loading ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: '#94a3b8',
              flexDirection: 'column',
              gap: 12,
            }}
          >
            <Loader size={32} style={{ animation: 'spin 1s linear infinite' }} />
            <div>Đang tải sản phẩm yêu thích...</div>
          </div>
        ) : error ? (
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: '#e11d48',
              flexDirection: 'column',
              gap: 12,
              textAlign: 'center',
            }}
          >
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
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              height: '100%',
              color: '#94a3b8',
              flexDirection: 'column',
              gap: 12,
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: 48 }}>📦</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#475569' }}>
                Chưa có sản phẩm yêu thích
              </div>
              <div style={{ fontSize: 13, marginTop: 4 }}>
                Hãy thêm sản phẩm yêu thích trước khi so sánh
              </div>
            </div>
          </div>
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
              gap: 12,
            }}
          >
            {favorites.map((fav) => {
              const product = fav.product;
              if (!product) return null;

              const productUrl = product.product_url;
              const productImage = product.thumbnail;
              const productPrice = product.min_price || product.skus?.[0]?.price;
              const isChecked = isSelected(fav.product_id);

              return (
                <div
                  key={fav.id}
                  className="compare-item"
                  onClick={() => toggleSelect(fav.product_id)}
                  style={{
                    background: isChecked ? '#f0f9ff' : '#f8f9ff',
                    borderRadius: 10,
                    overflow: 'hidden',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    border: isChecked ? '2px solid #f59e0b' : '1px solid #e2e8f0',
                    position: 'relative',
                  }}
                  onMouseEnter={(e) => {
                    if (!isChecked) {
                      e.currentTarget.style.boxShadow = '0 8px 16px rgba(245,158,11,0.15)';
                      e.currentTarget.style.transform = 'translateY(-2px)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (!isChecked) {
                      e.currentTarget.style.boxShadow = 'none';
                      e.currentTarget.style.transform = 'translateY(0)';
                    }
                  }}
                >
                  {/* Image */}
                  {productImage && (
                    <div
                      style={{
                        height: 120,
                        background: '#fff',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        overflow: 'hidden',
                        position: 'relative',
                      }}
                    >
                      <img
                        src={productImage}
                        alt={product.title}
                        style={{
                          maxWidth: '100%',
                          maxHeight: '100%',
                          objectFit: 'contain',
                        }}
                      />
                      {/* Checkbox */}
                      <div
                        style={{
                          position: 'absolute',
                          top: 8,
                          right: 8,
                          width: 24,
                          height: 24,
                          borderRadius: 4,
                          background: isChecked ? '#f59e0b' : 'rgba(255,255,255,0.8)',
                          border: '2px solid ' + (isChecked ? '#f59e0b' : '#d1d5db'),
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          transition: 'all 0.2s',
                          zIndex: 10,
                        }}
                      >
                        {isChecked && <Check size={14} color="#fff" strokeWidth={3} />}
                      </div>
                    </div>
                  )}

                  {/* Product Info */}
                  <div style={{ padding: '10px 10px' }}>
                    <div
                      style={{
                        fontSize: 11,
                        fontWeight: 600,
                        color: '#1e1b4b',
                        lineHeight: 1.4,
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                      }}
                    >
                      {product.title}
                    </div>
                    {productPrice && (
                      <div
                        style={{
                          fontSize: 12,
                          fontWeight: 700,
                          color: '#f59e0b',
                          marginTop: 4,
                        }}
                      >
                        {typeof productPrice === 'number'
                          ? (productPrice / 1000000).toFixed(1) + 'tr'
                          : productPrice}
                      </div>
                    )}
                    {product.brand && (
                      <div
                        style={{
                          fontSize: 10,
                          color: '#94a3b8',
                          marginTop: 2,
                        }}
                      >
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
