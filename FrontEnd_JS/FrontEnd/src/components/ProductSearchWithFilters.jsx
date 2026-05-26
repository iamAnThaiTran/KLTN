import React, { useState, useCallback } from 'react';
import { Search, Loader2, X, ChevronDown } from 'lucide-react';
import SuggestionsPopup from './SuggestionsPopup';
import './ProductSearchWithFilters.css';

const API_BASE_URL = 'http://localhost:8000';

/**
 * ProductSearchWithFilters Component
 * 
 * Dynamic component gọi backend Python endpoint: POST /api/v1/crawl-products
 * Hiển thị filters tự động dựa trên response từ backend
 * 
 * Features:
 * - Không hardcode filters/attributes
 * - Support multiple categories
 * - Dynamic filter display
 * - Multiple select per filter
 * - Pagination support
 */
export default function ProductSearchWithFilters() {
  // State
  const [categoryName, setCategoryName] = useState('');
  const [selectedFilters, setSelectedFilters] = useState({});
  const [products, setProducts] = useState([]);
  const [filters, setFilters] = useState([]); // Dynamic filters từ API
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [hasSearched, setHasSearched] = useState(false);

  // State quản lý UI
  const [expandedFilters, setExpandedFilters] = useState({}); // Track which filters are expanded
  const [showSuggestions, setShowSuggestions] = useState(false); // Popup gợi ý
  const [conversationId, setConversationId] = useState(null);

  /**
   * Gọi API crawl-products
   * @param {string} category - Category name (e.g., "giày")
   * @param {object} filters - Selected filters {attribute_name: [values]}
   * @param {number} page - Page number
   * @param {string} userInput - Original user input for attribute extraction
   */
  const searchProducts = useCallback(async (category, filters = {}, page = 1, userInput = '') => {
    if (!category.trim()) {
      setError('Vui lòng nhập tên loại sản phẩm');
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/api/v1/crawl-products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_name: category,
          user_input: userInput || category,  // ✅ NEW: Pass original user input for attribute extraction
          selected_filters: filters,
          page: page,
          page_size: pageSize
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('API Response:', data);

      setProducts(data.products || []);
      setFilters(data.filters || []);
      setTotal(data.total || 0);
      setTotalPages(data.total_pages || 0);
      setCurrentPage(page);
      setHasSearched(true);

      // 🎯 Auto pre-tick filters dựa trên selected_attributes từ backend
      if (data.selected_attributes && Object.keys(data.selected_attributes).length > 0) {
        console.log('Auto-selecting attributes:', data.selected_attributes);
        
        // Chuyển selected_attributes thành selectedFilters format
        // selected_attributes: { brand: 'Nike', size: '40' }
        // selectedFilters: { brand: ['Nike'], size: ['40'] }
        const autoSelectedFilters = {};
        Object.entries(data.selected_attributes).forEach(([attr, value]) => {
          if (value === null || value === undefined) return; // Skip null/undefined
          
          // Xử lý các loại value khác nhau
          if (Array.isArray(value)) {
            autoSelectedFilters[attr] = value.map(v => String(v));
          } else if (typeof value === 'object') {
            // Nếu là object (ví dụ: gia: { min: 100, max: 1000 }), skip
            console.log(`Skipping object value for ${attr}:`, value);
            return;
          } else {
            autoSelectedFilters[attr] = [String(value)];
          }
        });
        
        console.log('Auto-selected filters:', autoSelectedFilters);
        setSelectedFilters(autoSelectedFilters);
      }

      // Reset expanded filters khi có data mới
      const newExpandedState = {};
      (data.filters || []).forEach((filter, idx) => {
        newExpandedState[filter.attribute_name] = idx === 0; // Mở filter đầu tiên
      });
      setExpandedFilters(newExpandedState);
    } catch (err) {
      console.error('Search error:', err);
      setError(`Lỗi: ${err.message}`);
      setProducts([]);
      setFilters([]);
    } finally {
      setIsLoading(false);
    }
  }, [pageSize]);

  /**
   * Handle search button click
   */
  const handleSearch = () => {
    if (!categoryName.trim()) {
      setError('Vui lòng nhập tên loại sản phẩm');
      return;
    }
    
    // Show suggestions popup trước
    setShowSuggestions(true);
    
    // Generate new conversation ID
    if (!conversationId) {
      setConversationId(`conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`);
    }
  };

  /**
   * Handle suggestions popup confirm
   */
  const handleSuggestionsConfirm = (suggestedFilters) => {
    setCurrentPage(1);
    setSelectedFilters(suggestedFilters);
    // Tìm kiếm với các filters đã chọn từ gợi ý + pass user input
    searchProducts(categoryName, suggestedFilters, 1, categoryName);
  };

  /**
   * Handle filter selection
   * @param {string} attributeName - Tên attribute (e.g., "size", "color")
   * @param {string} attributeValue - Giá trị được chọn (e.g., "42", "Đen")
   */
  const handleFilterChange = (attributeName, attributeValue) => {
    setSelectedFilters(prev => {
      const newFilters = { ...prev };
      
      if (!newFilters[attributeName]) {
        newFilters[attributeName] = [];
      }

      const index = newFilters[attributeName].indexOf(attributeValue);
      if (index > -1) {
        // Remove if already selected
        newFilters[attributeName].splice(index, 1);
        if (newFilters[attributeName].length === 0) {
          delete newFilters[attributeName];
        }
      } else {
        // Add if not selected
        newFilters[attributeName].push(attributeValue);
      }

      return newFilters;
    });
  };

  /**
   * Apply filters - gọi API với selected filters
   */
  const handleApplyFilters = () => {
    setCurrentPage(1);
    searchProducts(categoryName, selectedFilters, 1, categoryName);
  };

  /**
   * Clear all filters
   */
  const handleClearFilters = () => {
    setSelectedFilters({});
    searchProducts(categoryName, {}, 1, categoryName);
  };

  /**
   * Toggle filter expansion
   */
  const toggleFilterExpansion = (attributeName) => {
    setExpandedFilters(prev => ({
      ...prev,
      [attributeName]: !prev[attributeName]
    }));
  };

  /**
   * Handle pagination
   */
  const handlePageChange = (newPage) => {
    searchProducts(categoryName, selectedFilters, newPage, categoryName);
  };

  return (
    <div className="product-search-with-filters">
      {/* Search Header */}
      <div className="search-header">
        <h1 className="page-title">🛍️ Tìm Kiếm Sản Phẩm</h1>
        <div className="search-container">
          <input
            type="text"
            placeholder="Nhập loại sản phẩm (ví dụ: giày, áo, quần...)"
            value={categoryName}
            onChange={(e) => setCategoryName(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            className="search-input"
            autoFocus
          />
          <button 
            onClick={handleSearch}
            disabled={isLoading}
            className="search-button"
          >
            {isLoading ? (
              <Loader2 className="spinner" size={20} />
            ) : (
              <Search size={20} />
            )}
            <span className="button-text">Tìm kiếm</span>
          </button>
        </div>
        {error && (
          <div className="error-message">
            ❌ {error}
          </div>
        )}
      </div>

      {hasSearched && (
        <div className="search-results-container">
          {/* Sidebar Filters */}
          <aside className="filters-sidebar">
            <div className="filters-header">
              <h3>
                🔽 Bộ lọc
                {filters.length > 0 && <span className="filter-count-badge">{filters.length}</span>}
              </h3>
              {Object.keys(selectedFilters).length > 0 && (
                <button 
                  onClick={handleClearFilters}
                  className="clear-filters-btn"
                  title="Xóa tất cả filter"
                >
                  <X size={18} />
                </button>
              )}
            </div>

            {/* Dynamic Filters */}
            {filters.length > 0 ? (
              <div className="filters-list">
                {filters.map((filter) => (
                  <div 
                    key={filter.attribute_name}
                    className="filter-group"
                  >
                    {/* Filter Group Header */}
                    <button
                      className="filter-group-header"
                      onClick={() => toggleFilterExpansion(filter.attribute_name)}
                    >
                      <span className="filter-name">
                        {filter.display_name || filter.attribute_name}
                      </span>
                      <ChevronDown 
                        size={18}
                        className={`chevron ${expandedFilters[filter.attribute_name] ? 'expanded' : ''}`}
                      />
                    </button>

                    {/* Filter Options */}
                    {expandedFilters[filter.attribute_name] && (
                      <div className="filter-options">
                        {filter.options && filter.options.length > 0 ? (
                          filter.options
                            .filter(option => option.attribute_value && option.attribute_value !== 'None' && option.attribute_value !== 'null')
                            .map((option, idx) => (
                            <div 
                              key={`${filter.attribute_name}-${option.attribute_value}-${idx}`}
                              className="filter-option-wrapper"
                            >
                              <label 
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
                                  className="filter-checkbox"
                                />
                                <span className="filter-label">
                                  {option.attribute_value}
                                </span>
                                <span className="filter-count">
                                  ({option.product_count})
                                </span>
                              </label>
                              {/* Quick filter button - tìm ngay khi click */}
                              <button
                                onClick={() => {
                                  const newFilters = {
                                    [filter.attribute_name]: [option.attribute_value]
                                  };
                                  setCurrentPage(1);
                                  setSelectedFilters(newFilters);
                                  searchProducts(categoryName, newFilters, 1, categoryName);
                                }}
                                className="quick-filter-btn"
                                title={`Tìm kiếm ngay với ${option.attribute_value}`}
                                disabled={isLoading}
                              >
                                ⚡
                              </button>
                            </div>
                          ))
                        ) : (
                          <p className="no-options">Không có tùy chọn</p>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className="no-filters">Không có bộ lọc nào</p>
            )}

            {/* Apply Button */}
            {Object.keys(selectedFilters).length > 0 && (
              <button
                onClick={handleApplyFilters}
                disabled={isLoading}
                className="apply-filters-btn"
              >
                {isLoading ? <Loader2 className="spinner" /> : 'Áp dụng'}
              </button>
            )}
          </aside>

          {/* Products Grid */}
          <main className="products-section">
            {isLoading && (
              <div className="loading-container">
                <div className="loading-spinner">
                  <Loader2 className="spinner" size={48} />
                </div>
                <p className="loading-text">⏳ Đang tải sản phẩm và bộ lọc...</p>
              </div>
            )}

            {!isLoading && products.length > 0 && (
              <>
                <div className="products-info">
                  <div className="results-header">
                    <h2 className="results-title">
                      ✅ Tìm thấy <strong>{total}</strong> sản phẩm
                    </h2>
                    {Object.keys(selectedFilters).length > 0 && (
                      <button 
                        onClick={handleClearFilters}
                        className="clear-filters-link"
                      >
                        ✕ Xóa bộ lọc
                      </button>
                    )}
                  </div>
                  
                  {Object.keys(selectedFilters).length > 0 && (
                    <div className="filter-tags">
                      {Object.entries(selectedFilters).map(([attr, values]) => (
                        <span key={attr} className="filter-tag">
                          <strong>{attr}:</strong> {values.join(', ')}
                        </span>
                      ))}
                    </div>
                  )}
                </div>

                <div className="products-grid">
                  {products.map((product) => (
                    <div 
                      key={`${product.id}`}
                      className="product-card"
                    >
                      {/* Product Image */}
                      <div className="product-image-wrapper">
                        {product.thumbnail ? (
                          <img
                            src={product.thumbnail}
                            alt={product.title}
                            className="product-image"
                          />
                        ) : (
                          <div className="product-image-placeholder">
                            📦
                          </div>
                        )}
                      </div>

                      {/* Product Info */}
                      <div className="product-info">
                        <h4 className="product-title">
                          {product.title}
                        </h4>
                        
                        {product.brand && (
                          <p className="product-brand">
                            Brand: {product.brand}
                          </p>
                        )}

                        {/* Price Range */}
                        {product.min_price && (
                          <div className="product-price-range">
                            {product.min_price === product.max_price ? (
                              <span className="product-price">
                                {new Intl.NumberFormat('vi-VN', {
                                  style: 'currency',
                                  currency: 'VND'
                                }).format(product.min_price)}
                              </span>
                            ) : (
                              <>
                                <span className="price-from">
                                  {new Intl.NumberFormat('vi-VN', {
                                    style: 'currency',
                                    currency: 'VND'
                                  }).format(product.min_price)}
                                </span>
                                <span className="price-separator"> - </span>
                                <span className="price-to">
                                  {new Intl.NumberFormat('vi-VN', {
                                    style: 'currency',
                                    currency: 'VND'
                                  }).format(product.max_price)}
                                </span>
                              </>
                            )}
                          </div>
                        )}

                        {/* SKU Attributes */}
                        {product.skus && product.skus.length > 0 && (
                          <div className="product-attributes">
                            {product.skus.slice(0, 1).map((sku, idx) => (
                              <div key={idx} className="sku-info">
                                {sku.attributes && Object.keys(sku.attributes).length > 0 && (
                                  <div className="attributes-list">
                                    {Object.entries(sku.attributes).map(([attrName, attrValue]) => (
                                      <span key={attrName} className="attribute-badge">
                                        {attrName}: {attrValue}
                                      </span>
                                    ))}
                                  </div>
                                )}
                                <p className="sku-stock">
                                  Stock: {sku.stock} | {sku.is_available ? '✅ Có sẵn' : '❌ Hết'}
                                </p>
                              </div>
                            ))}
                            {product.skus.length > 1 && (
                              <p className="more-variants">
                                +{product.skus.length - 1} phiên bản khác
                              </p>
                            )}
                          </div>
                        )}

                        <p className="available-count">
                          Số lượng khả dụng: {product.available_count || 0}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Pagination */}
                {totalPages > 1 && (
                  <div className="pagination">
                    <button
                      onClick={() => handlePageChange(currentPage - 1)}
                      disabled={currentPage === 1 || isLoading}
                      className="pagination-btn"
                    >
                      Trang trước
                    </button>
                    
                    <div className="pagination-info">
                      Trang {currentPage} / {totalPages}
                    </div>
                    
                    <button
                      onClick={() => handlePageChange(currentPage + 1)}
                      disabled={currentPage === totalPages || isLoading}
                      className="pagination-btn"
                    >
                      Trang sau
                    </button>
                  </div>
                )}
              </>
            )}

            {!isLoading && products.length === 0 && hasSearched && (
              <div className="no-products">
                <p className="no-products-icon">🔍</p>
                <p className="no-products-text">Không tìm thấy sản phẩm nào</p>
                <p className="no-products-hint">Hãy thử với tên loại sản phẩm khác</p>
              </div>
            )}
          </main>
        </div>
      )}

      {/* Suggestions Popup */}
      <SuggestionsPopup
        isOpen={showSuggestions}
        onClose={() => setShowSuggestions(false)}
        category={categoryName}
        onConfirm={handleSuggestionsConfirm}
        conversationId={conversationId}
      />
    </div>
  );
}
