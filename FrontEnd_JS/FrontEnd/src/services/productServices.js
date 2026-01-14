const BASE_URL =  'http://localhost:3000/api/v1';

import axios from 'axios';

export const getProductFromTiki = async (query) => {

  try {
    const res = await axios.get(`${BASE_URL}/products/search`, {
      params: { q: query },
    });
    if (res.data?.success === false) throw new Error('Search failed');
    // Return full response data including type, products, intentAnalysis
    const data = res.data?.data || { type: 'query', products: [] };
    console.log('API Response data:', data);
    return data;
  } catch (error) {
    console.error('Product search error:', error);
    return { type: 'query', products: [] };
  }
};

export const getRecomendProductName = async (query) => {
  try {
    const response = await axios.get(`${BASE_URL}/products/search`, {
      params: { q: query },
    });
    return response.data?.data || [];
  } catch (error) {
    console.error('Error fetching recommendations:', error);
    throw new Error(error?.message || "Lỗi gọi API search");
  }
};