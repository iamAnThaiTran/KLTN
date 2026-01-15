import { useState, useEffect } from 'react';

/**
 * Custom hook to fetch category data with subcategories and products
 */
export function useCategoryProducts(categoryId) {
  const [subcategories, setSubcategories] = useState([]);
  const [products, setProducts] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!categoryId) return;

    const fetchData = async () => {
      try {
        setIsLoading(true);
        setError(null);

        // Fetch subcategories
        const subResponse = await fetch(
          `${process.env.REACT_APP_API_URL || 'http://localhost:3000/api'}/categories?parent_id=${categoryId}&level=1`
        );

        if (!subResponse.ok) {
          throw new Error(`HTTP error! status: ${subResponse.status}`);
        }

        const subData = await subResponse.json();
        const subs = subData.data || [];
        setSubcategories(subs);

        // Fetch products from all subcategories
        if (subs.length > 0) {
          const categoryIds = subs.map(s => s.id).join(',');
          const prodResponse = await fetch(
            `${process.env.REACT_APP_API_URL || 'http://localhost:3000/api'}/products?category_ids=${categoryIds}&limit=12&sort=-popularity_score`
          );

          if (!prodResponse.ok) {
            throw new Error(`HTTP error! status: ${prodResponse.status}`);
          }

          const prodData = await prodResponse.json();
          setProducts(prodData.data || []);
        }
      } catch (err) {
        console.error('Error fetching category data:', err);
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [categoryId]);

  return { subcategories, products, isLoading, error };
}
