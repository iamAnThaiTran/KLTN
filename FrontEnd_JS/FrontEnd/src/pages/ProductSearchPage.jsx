import React from 'react';
import ProductSearchWithFilters from '../components/ProductSearchWithFilters';

/**
 * ProductSearchPage - Trang hiển thị ProductSearchWithFilters component
 * 
 * Điểm đặc biệt:
 * - Gọi endpoint /api/v1/crawl-products từ backend Python
 * - Hiển thị filters động không hardcode
 * - Support multiple categories
 * - Responsive design
 */
export default function ProductSearchPage() {
  return (
    <div>
      <ProductSearchWithFilters />
    </div>
  );
}
