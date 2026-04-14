import React, { useState, useEffect } from 'react';
import { ChevronRight, CheckCircle2, Circle, Loader } from 'lucide-react';
import { getUserFavorites } from '../utils/favoritesApi';

/**
 * ProductSelector Component
 * Allows users to select 2-3 products from favorites for comparison
 */
export default function ProductSelector({ user, onProductsSelected, onBack }) {
  const [favorites, setFavorites] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [question, setQuestion] = useState('');

  useEffect(() => {
    fetchFavorites();
  }, []);

  const fetchFavorites = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const userId = user?.user_id || user?.id;
      if (!userId) {
        throw new Error('User ID not found. Please login again.');
      }
      
      const response = await getUserFavorites(userId, { limit: 100, offset: 0 });
      setFavorites(response.favorites || []);
    } catch (err) {
      console.error('Error fetching favorites:', err);
      setError('Failed to load favorites. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const toggleProduct = (productId) => {
    if (selectedIds.includes(productId)) {
      setSelectedIds(selectedIds.filter(id => id !== productId));
    } else if (selectedIds.length < 3) {
      setSelectedIds([...selectedIds, productId]);
    }
  };

  const handleCompare = () => {
    if (selectedIds.length < 2) {
      alert('Please select at least 2 products to compare');
      return;
    }
    onProductsSelected(selectedIds, question);
  };

  const isValid = selectedIds.length >= 2;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#fff',
      borderRadius: 16,
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
      `}</style>

      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #f59e0b 0%, #fb923c 100%)',
        padding: '24px',
        color: '#fff',
      }}>
        <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 8 }}>
          So sánh sản phẩm
        </div>
        <div style={{ fontSize: 14, opacity: 0.9 }}>
          Chọn 2-3 sản phẩm từ yêu thích của bạn
        </div>
      </div>

      {/* Content */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
      }}>
        {loading && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            padding: '40px 20px',
            color: '#6b7280',
          }}>
            <Loader size={32} style={{ animation: 'spin 1s linear infinite' }} color="#f59e0b" />
            <span>Loading favorites...</span>
          </div>
        )}

        {error && (
          <div style={{
            padding: '16px',
            background: '#fef2f2',
            border: '1px solid #fecaca',
            borderRadius: 8,
            color: '#dc2626',
            fontSize: 14,
          }}>
            {error}
          </div>
        )}

        {!loading && favorites.length === 0 && (
          <div style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 12,
            padding: '40px 20px',
            color: '#9ca3af',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 32 }}>💔</div>
            <div>No favorites yet. Add some products to compare!</div>
          </div>
        )}

        {!loading && favorites.length > 0 && (
          <>
            {/* Product Selection */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
              {favorites.map((fav) => (
                <ProductCard
                  key={fav.product_id}
                  product={fav}
                  isSelected={selectedIds.includes(fav.product_id)}
                  onToggle={() => toggleProduct(fav.product_id)}
                  isDisabled={selectedIds.length >= 3 && !selectedIds.includes(fav.product_id)}
                />
              ))}
            </div>

            {/* Selected Count */}
            <div style={{
              padding: '12px 16px',
              background: '#f3f4f6',
              borderRadius: 8,
              fontSize: 14,
              color: '#6b7280',
              textAlign: 'center',
              marginTop: 8,
            }}>
              {selectedIds.length} / 3 products selected
            </div>

            {/* Question Input */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 16 }}>
              <label style={{ fontSize: 14, fontWeight: 600, color: '#374151' }}>
                Additional question (optional)
              </label>
              <textarea
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="E.g., Which one is best for running?"
                style={{
                  padding: '12px',
                  border: '1px solid #e5e7eb',
                  borderRadius: 8,
                  fontFamily: 'inherit',
                  fontSize: 14,
                  resize: 'vertical',
                  minHeight: '80px',
                  outline: 'none',
                  transition: 'border-color 0.2s',
                }}
                onFocus={(e) => e.currentTarget.style.borderColor = '#f59e0b'}
                onBlur={(e) => e.currentTarget.style.borderColor = '#e5e7eb'}
              />
            </div>
          </>
        )}
      </div>

      {/* Footer */}
      <div style={{
        padding: '16px 24px',
        background: '#f9fafb',
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        gap: 12,
      }}>
        <button
          onClick={onBack}
          style={{
            flex: 1,
            padding: '12px 16px',
            border: '1px solid #d1d5db',
            background: '#fff',
            borderRadius: 8,
            fontWeight: 600,
            cursor: 'pointer',
            transition: 'all 0.2s',
            fontFamily: 'inherit',
          }}
          onMouseEnter={(e) => e.currentTarget.style.background = '#f3f4f6'}
          onMouseLeave={(e) => e.currentTarget.style.background = '#fff'}
        >
          Back
        </button>
        <button
          onClick={handleCompare}
          disabled={!isValid}
          style={{
            flex: 1,
            padding: '12px 16px',
            background: isValid ? 'linear-gradient(135deg, #f59e0b 0%, #fb923c 100%)' : '#d1d5db',
            color: '#fff',
            border: 'none',
            borderRadius: 8,
            fontWeight: 600,
            cursor: isValid ? 'pointer' : 'not-allowed',
            transition: 'all 0.2s',
            fontFamily: 'inherit',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 8,
          }}
          onMouseEnter={(e) => {
            if (isValid) e.currentTarget.style.transform = 'translateY(-2px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)';
          }}
        >
          Compare {selectedIds.length > 0 && `(${selectedIds.length})`}
          <ChevronRight size={16} />
        </button>
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

/**
 * ProductCard Component - Individual product selection card
 */
function ProductCard({ product, isSelected, onToggle, isDisabled }) {
  return (
    <div
      onClick={() => !isDisabled && onToggle()}
      style={{
        padding: '16px',
        border: `2px solid ${isSelected ? '#f59e0b' : '#e5e7eb'}`,
        borderRadius: 12,
        cursor: isDisabled ? 'not-allowed' : 'pointer',
        display: 'flex',
        gap: 12,
        alignItems: 'center',
        transition: 'all 0.2s',
        background: isSelected ? '#fffbf0' : '#fff',
        opacity: isDisabled ? 0.6 : 1,
      }}
      onMouseEnter={(e) => {
        if (!isDisabled) {
          e.currentTarget.style.borderColor = '#f59e0b';
          e.currentTarget.style.background = '#fffbf0';
        }
      }}
      onMouseLeave={(e) => {
        if (!isSelected && !isDisabled) {
          e.currentTarget.style.borderColor = '#e5e7eb';
          e.currentTarget.style.background = '#fff';
        }
      }}
    >
      {/* Checkbox */}
      <div style={{ flexShrink: 0 }}>
        {isSelected ? (
          <CheckCircle2 size={24} color="#f59e0b" />
        ) : (
          <Circle size={24} color="#d1d5db" />
        )}
      </div>

      {/* Product Image */}
      <img
        src={product.product_image_url || 'https://via.placeholder.com/80/f0f0f0/999?text=Product'}
        alt={product.product_name}
        style={{
          width: 80,
          height: 80,
          borderRadius: 8,
          objectFit: 'cover',
          background: '#f3f4f6',
        }}
      />

      {/* Product Info */}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 14,
          fontWeight: 600,
          color: '#1f2937',
          marginBottom: 4,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {product.product_name}
        </div>
        <div style={{
          fontSize: 12,
          color: '#6b7280',
          marginBottom: 6,
        }}>
          {product.product_brand || 'Unknown Brand'}
        </div>
        <div style={{
          fontSize: 15,
          fontWeight: 700,
          color: '#f59e0b',
        }}>
          {product.product_price}
        </div>
      </div>
    </div>
  );
}
