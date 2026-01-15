import React, { useState, useEffect } from 'react';
import CategoryProductList from '../components/CategoryProductList';
import { useNavigate } from 'react-router-dom';

/**
 * Homepage Category List Section
 * 
 * Displays multiple CategoryProductList components
 * for all main categories on the homepage
 */
export default function HomeCategorySection() {
  const [categories, setCategories] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchMainCategories();
  }, []);

  const fetchMainCategories = async () => {
    try {
      setIsLoading(true);
      const response = await fetch(
        `${import.meta.env.VITE_API_URL}/categories?level=0&limit=10`
      );

      if (!response.ok) throw new Error('Failed to fetch categories');
      
      const data = await response.json();
      setCategories(data.data || []);
    } catch (error) {
      console.error('Error fetching categories:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewMore = (categoryId, categoryName) => {
    navigate(`/category/${categoryId}`, { 
      state: { categoryName } 
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <p className="text-gray-600">Đang tải danh mục...</p>
      </div>
    );
  }

  return (
    <div className="bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        {categories.map((category) => (
          <CategoryProductList
            key={category.id}
            categoryId={category.id}
            categoryName={category.name}
            onViewMore={handleViewMore}
          />
        ))}
      </div>
    </div>
  );
}
