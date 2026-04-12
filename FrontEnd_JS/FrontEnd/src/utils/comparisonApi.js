/**
 * Product Comparison API
 * Handles all product comparison related API calls
 */

import apiRequest from './apiClient.js';

const API_BASE_URL =  'http://localhost:8000';

/**
 * Compare two or three products with a question
 * @param {Array<number>} productIds - Array of 2-3 product IDs
 * @param {string} question - Specific question or comparison criteria
 * @returns {Promise<Object>} Comparison results from LLM with snapshot_a, snapshot_b, comparison text
 */
export async function compareProducts(productIds, question = '') {
  try {
    if (!Array.isArray(productIds) || productIds.length < 2 || productIds.length > 4) {
      throw new Error('Vui lòng chọn 2-4 sản phẩm để so sánh');
    }

    console.log('🔍 Đang so sánh sản phẩm:', productIds);

    // Call real backend API
    try {
      const response = await fetch(`${API_BASE_URL}/api/compare_products`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          product_ids: productIds,
          question: question || '',
        }),
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();

      console.log('✅ So sánh thành công:', data);

      // Check if response has the new format from backend
      if (data.status === 'success' && data.comparison) {
        return data; // Return full response with snapshot_a, snapshot_b, comparison markdown
      }

      // Fallback to old mock format if needed
      return data;
    } catch (apiError) {
      console.warn('⚠️ API không khả dụng, sử dụng mock data:', apiError);
      // Fallback to mock data in development
      return await mockComparisonResponse(productIds, question);
    }
  } catch (error) {
    console.error('[Comparison API] Error comparing products:', error);
    throw error;
  }
}

/**
 * Mock comparison response (to be replaced with real API call)
 * @param {Array<number>} productIds - Product IDs
 * @param {string} question - Question
 * @returns {Promise<Object>} Mock comparison data
 */
async function mockComparisonResponse(productIds, question) {
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 800));

  // Mock product data
  const mockProducts = {
    1: {
      id: 1,
      name: 'Nike Air Force 1',
      price: '2.400.000đ',
      rating: 4.5,
      reviews: 245,
      image: 'https://via.placeholder.com/150/f0f0f0/999?text=Nike',
      specs: {
        material: 'Leather + Canvas',
        weight: '345g',
        colors: '8 màu',
        sizes: '37-46',
      },
      pros: ['Nhẹ và thoải mái', 'Thiết kế kinh điển', 'Bền lâu'],
      cons: ['Giá cao', 'Cần tỏa mồ hôi ban đầu'],
    },
    2: {
      id: 2,
      name: 'Adidas Stan Smith',
      price: '1.890.000đ',
      rating: 4.3,
      reviews: 189,
      image: 'https://via.placeholder.com/150/f0f0f0/999?text=Adidas',
      specs: {
        material: 'Leather',
        weight: '320g',
        colors: '5 màu',
        sizes: '37-46',
      },
      pros: ['Giá hợp lý', 'Thiết kế đơn giản', 'Thoải mái'],
      cons: ['Bề mặt dễ bẩn', 'Ít tùy chọn màu'],
    },
    3: {
      id: 3,
      name: 'Vans Old Skool',
      price: '1.600.000đ',
      rating: 4.4,
      reviews: 312,
      image: 'https://via.placeholder.com/150/f0f0f0/999?text=Vans',
      specs: {
        material: 'Canvas + Suede',
        weight: '380g',
        colors: '12 màu',
        sizes: '37-45',
      },
      pros: ['Rẻ nhất', 'Nhiều màu lựa chọn', 'Phổ biến'],
      cons: ['Nặng hơn', 'Chất liệu kém bền'],
    },
  };

  // Get selected products
  const selectedProducts = productIds
    .map(id => mockProducts[id] || mockProducts[1])
    .slice(0, 3);

  return {
    success: true,
    question: question || 'General comparison',
    products: selectedProducts,
    summary: {
      bestForComfort: selectedProducts[0].name,
      bestForPrice: selectedProducts[1].name,
      bestOverall: selectedProducts[0].name,
    },
    detailedComparison: {
      price: `${selectedProducts[0].name} is more expensive at ${selectedProducts[0].price}, while ${selectedProducts[1].name} offers better value at ${selectedProducts[1].price}. Overall, ${selectedProducts[1].name} provides the best price-to-quality ratio.`,
      design: `${selectedProducts[0].name} features a classic design with modern touches. ${selectedProducts[1].name} maintains a minimalist aesthetic. ${selectedProducts[2] ? selectedProducts[2].name + ' offers trendy styling.' : ''}`,
      comfort: `All three options provide excellent comfort. ${selectedProducts[0].name} is particularly suitable for extended walking. ${selectedProducts[1].name} breaks in quickly and is immediately comfortable.`,
      durability: `${selectedProducts[0].name} uses premium materials for long-term durability. ${selectedProducts[1].name} has solid construction quality. Both are reliable choices for daily wear.`,
    },
    recommendation: `Based on your preferences, ${selectedProducts[0].name} is recommended for those seeking premium quality and style. For budget-conscious shoppers, ${selectedProducts[1].name} is an excellent choice.`,
    timestamp: new Date().toISOString(),
  };
}

export default {
  compareProducts,
};
