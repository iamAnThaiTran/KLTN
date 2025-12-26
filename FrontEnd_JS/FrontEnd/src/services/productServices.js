const BASE_URL =  'http://localhost:3000';
// function getProductFromChat() = async => {

// }


import axios from 'axios';

export const getProductFromTiki = async (query) => {
  try {
    const res = await axios.get(`${BASE_URL}/crawl`, {
      params: { q: query },
    });
    if (!res.data?.success) throw new Error('Crawl thất bại');
    return res.data.data;
  } catch (error) {
    console.error('getProductFromTiki error:', error);
    return [];
  }
};


export const getRecomendProductName = async (query) => {
  try {
    const response = await axios.get(`${BASE_URL}/productname`, {
      params: { q: query },
    });
    return response.data;
  } catch (error) {
    console.error(error);
    throw new Error(error?.message || "Lỗi gọi API /productname");
  }
};

