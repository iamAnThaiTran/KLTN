import React, { useState, useEffect } from 'react';
import { X, Search, ChevronDown, Loader2 } from 'lucide-react';
import './SuggestionsPopup.css';

/**
 * SuggestionsPopup Component
 * 
 * Hiển thị popup gợi ý lọc khi user nhập tên sản phẩm
 * Gọi /api/analyze để lấy danh sách filters và hints
 * 
 * Features:
 * - Hiển thị clarifying hints (mũi tên tới hints)
 * - Hiển thị filter options dạng checkbox
 * - Lưu selected suggestions vào state
 * - Gọi callback khi confirm
 */
export default function SuggestionsPopup({ 
  isOpen, 
  onClose, 
  category, 
  onConfirm,
  conversationId 
}) {
  const [filters, setFilters] = useState([]);
  const [hints, setHints] = useState([]);
  const [selectedFilters, setSelectedFilters] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [expandedFilter, setExpandedFilter] = useState(null);
  const [error, setError] = useState(null);

  const API_BASE_URL = 'http://localhost:8000';

  // Load suggestions từ /api/analyze
  useEffect(() => {
    if (isOpen && category) {
      fetchAnalysis();
    }
  }, [isOpen, category]);

  const fetchAnalysis = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_input: category,
          conversation_id: conversationId
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('✅ Analysis response:', data);

      if (data.success) {
        setFilters(data.filters || []);
        setHints(data.clarifying_hints || []);
        
        // Auto-expand first filter
        if (data.filters && data.filters.length > 0) {
          setExpandedFilter(data.filters[0].attribute_name);
        }
      } else {
        setError(data.error || 'Không thể lấy gợi ý');
      }
    } catch (err) {
      console.error('Fetch analysis error:', err);
      setError(`Lỗi: ${err.message}`);
    } finally {
      setIsLoading(false);
    }
  };

  const handleFilterChange = (attributeName, attributeValue) => {
    setSelectedFilters(prev => {
      const newFilters = { ...prev };
      
      if (!newFilters[attributeName]) {
        newFilters[attributeName] = [];
      }

      const index = newFilters[attributeName].indexOf(attributeValue);
      if (index > -1) {
        newFilters[attributeName].splice(index, 1);
        if (newFilters[attributeName].length === 0) {
          delete newFilters[attributeName];
        }
      } else {
        newFilters[attributeName].push(attributeValue);
      }

      return newFilters;
    });
  };

  const handleConfirm = () => {
    // Gọi callback với selected filters
    onConfirm(selectedFilters);
    onClose();
  };

  const handleClearAll = () => {
    setSelectedFilters({});
  };

  if (!isOpen) return null;

  return (
    <div className="suggestions-popup-overlay" onClick={onClose}>
      <div 
        className="suggestions-popup-container" 
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="suggestions-popup-header">
          <h3>🔍 Gợi ý lọc cho "{category}"</h3>
          <button 
            className="suggestions-popup-close"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>

        {/* Content */}
        <div className="suggestions-popup-content">
          {isLoading ? (
            <div className="suggestions-loading">
              <Loader2 className="spinner" size={32} />
              <p>Đang tải gợi ý...</p>
            </div>
          ) : error ? (
            <div className="suggestions-error">
              <p>❌ {error}</p>
              <button 
                className="suggestions-retry-btn"
                onClick={fetchAnalysis}
              >
                Thử lại
              </button>
            </div>
          ) : (
            <>
              {/* Clarifying Hints */}
              {hints && hints.length > 0 && (
                <div className="suggestions-hints">
                  <p className="hints-label">💡 Hãy cho tôi biết:</p>
                  <div className="hints-list">
                    {hints.map((hint, idx) => (
                      <div key={idx} className="hint-item">
                        {hint}
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Filters */}
              {filters && filters.length > 0 ? (
                <div className="suggestions-filters">
                  <p className="filters-label">📋 Bộ lọc:</p>
                  <div className="filters-list">
                    {filters.map((filter) => (
                      <div key={filter.attribute_name} className="filter-group">
                        <button
                          className="filter-header"
                          onClick={() => 
                            setExpandedFilter(
                              expandedFilter === filter.attribute_name 
                                ? null 
                                : filter.attribute_name
                            )
                          }
                        >
                          <span>{filter.display_name}</span>
                          <ChevronDown 
                            size={18}
                            style={{
                              transform: expandedFilter === filter.attribute_name 
                                ? 'rotate(180deg)' 
                                : 'rotate(0deg)',
                              transition: 'transform 0.3s'
                            }}
                          />
                        </button>

                        {expandedFilter === filter.attribute_name && (
                          <div className="filter-options">
                            {filter.options && filter.options.length > 0 ? (
                              filter.options.map((option) => (
                                <label 
                                  key={option.attribute_value}
                                  className="filter-option"
                                >
                                  <input
                                    type="checkbox"
                                    checked={
                                      selectedFilters[filter.attribute_name]?.includes(
                                        option.attribute_value
                                      ) || false
                                    }
                                    onChange={() =>
                                      handleFilterChange(
                                        filter.attribute_name,
                                        option.attribute_value
                                      )
                                    }
                                  />
                                  <span className="option-text">
                                    {option.attribute_value}
                                    {option.product_count && (
                                      <span className="option-count">
                                        ({option.product_count})
                                      </span>
                                    )}
                                  </span>
                                </label>
                              ))
                            ) : (
                              <p className="no-options">Không có lựa chọn</p>
                            )}
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              ) : (
                <p className="no-filters">Không có bộ lọc khả dụng</p>
              )}
            </>
          )}
        </div>

        {/* Footer - Action Buttons */}
        <div className="suggestions-popup-footer">
          <button 
            className="suggestions-clear-btn"
            onClick={handleClearAll}
            disabled={isLoading || Object.keys(selectedFilters).length === 0}
          >
            Xóa lựa chọn
          </button>
          <button 
            className="suggestions-confirm-btn"
            onClick={handleConfirm}
            disabled={isLoading}
          >
            {isLoading ? (
              <>
                <Loader2 size={16} className="spinner" />
                Đang tải...
              </>
            ) : (
              <>
                <Search size={16} />
                Tìm kiếm
              </>
            )}
          </button>
        </div>

        {/* Selected Count Badge */}
        {Object.keys(selectedFilters).length > 0 && (
          <div className="selected-count">
            {Object.values(selectedFilters).reduce((acc, arr) => acc + arr.length, 0)} 
            {' '}lựa chọn
          </div>
        )}
      </div>
    </div>
  );
}
