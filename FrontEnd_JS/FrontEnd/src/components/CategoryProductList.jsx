import React, { useState, useEffect } from 'react';
import { ChevronRight, Loader2 } from 'lucide-react';
import './CategoryProductList.css';

/**
 * CategoryProductList Component
 * 
 * Displays a main category with:
 * - Part 1: Category title with "View More" button
 * - Part 2: Related subcategories
 * - Part 3: ~12 featured products
 */
export default function CategoryProductList({ categoryId, categoryName, onViewMore }) {
  const [subcategories, setSubcategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchCategoryData();
  }, [categoryId]);

  const fetchCategoryData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      // Fetch category with its products and subcategories
      const categoryResponse = await fetch(
        `${import.meta.env.VITE_API_URL}/categories/${categoryId}`
      );
      if (!categoryResponse.ok) throw new Error('Failed to fetch category');
      const categoryData = await categoryResponse.json();
      
      if (categoryData.data) {
        setSubcategories(categoryData.data.subcategories || []);
        setProducts(categoryData.data.products || []);
      }
    } catch (err) {
      console.error('Error fetching category data:', err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubcategoryClick = (subcategoryId, subcategoryName) => {
    if (onViewMore) {
      onViewMore(subcategoryId, subcategoryName);
    }
  };

  const handleProductClick = (product) => {
    window.location.href = `/product/${product.slug}`;
  };

  if (error) {
    return (
      <div className="category-list error">
        <p>Lỗi tải dữ liệu: {error}</p>
      </div>
    );
  }

  return (
    <div className="category-list">
      {/* PART 1: Category Header */}
      <div className="category-header">
        <h2 className="category-title">{categoryName}</h2>
        <button 
          className="view-more-btn"
          onClick={() => onViewMore && onViewMore(categoryId, categoryName)}
        >
          XEM THÊM <ChevronRight size={16} />
        </button>
      </div>

      {isLoading ? (
        <div className="loading-container">
          <Loader2 className="spinner" />
          <p>Đang tải...</p>
        </div>
      ) : (
        <>
          {/* PART 2: Subcategories */}
          {subcategories.length > 0 && (
            <div className="subcategories-section">
              <div className="subcategories-grid">
                {subcategories.map((subcategory) => (
                  <button
                    key={subcategory.id}
                    className="subcategory-tile"
                    onClick={() => 
                      handleSubcategoryClick(subcategory.id, subcategory.name)
                    }
                    title={subcategory.name}
                  >
                    <div className="subcategory-icon">
                      {subcategory.icon || '📦'}
                    </div>
                    <p className="subcategory-name">{subcategory.name}</p>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* PART 3: Products */}
          {products.length > 0 ? (
            <div className="products-section">
              <div className="products-grid">
                {products.map((product) => (
                  <div
                    key={product.id}
                    className="product-card"
                    onClick={() => handleProductClick(product)}
                  >
                    <div className="product-image-container">
                      <img
                        src={product.images?.[0] || '/placeholder.jpg'}
                        alt={product.name}
                        className="product-image"
                      />
                      {product.discount_percent > 0 && (
                        <div className="discount-badge">
                          -{product.discount_percent}%
                        </div>
                      )}
                    </div>
                    <div className="product-info">
                      <h4 className="product-name">{product.name}</h4>
                      <div className="product-pricing">
                        <span className="product-price">
                          {new Intl.NumberFormat('vi-VN', {
                            style: 'currency',
                            currency: 'VND'
                          }).format(product.price)}
                        </span>
                        {product.original_price > product.price && (
                          <span className="product-original-price">
                            {new Intl.NumberFormat('vi-VN', {
                              style: 'currency',
                              currency: 'VND'
                            }).format(product.original_price)}
                          </span>
                        )}
                      </div>
                      {product.rating_count > 0 && (
                        <div className="product-rating">
                          <span className="stars">⭐ {product.rating_avg}</span>
                          <span className="review-count">
                            ({product.rating_count})
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="no-products">
              <p>Không có sản phẩm trong danh mục này</p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
