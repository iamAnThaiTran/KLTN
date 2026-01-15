// CategoryProductList.types.ts

/**
 * Category data structure
 */
export interface Category {
  id: number;
  name: string;
  slug: string;
  parent_id?: number | null;
  level: 0 | 1 | 2; // 0=main, 1=sub, 2=brand
  icon?: string;
  keywords?: string[];
  description?: string;
  priority?: number;
  is_active: boolean;
  created_at?: string;
  updated_at?: string;
}

/**
 * Product data structure
 */
export interface Product {
  id: number;
  name: string;
  slug: string;
  category_id: number;
  brand?: string;
  description?: string;
  price: number;
  original_price?: number;
  discount_percent?: number;
  stock?: number;
  sku?: string;
  images?: string[];
  attributes?: Record<string, any>;
  
  // Metrics
  view_count?: number;
  sale_count?: number;
  rating_avg?: number;
  rating_count?: number;
  popularity_score?: number;
  
  // Status
  is_active: boolean;
  is_featured?: boolean;
  created_at?: string;
  updated_at?: string;
}

/**
 * API Response format
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T[];
  message?: string;
  error?: string;
  pagination?: {
    total: number;
    page: number;
    limit: number;
    pages: number;
  };
}

/**
 * CategoryProductList component props
 */
export interface CategoryProductListProps {
  /** Main category ID (level 0) */
  categoryId: number;
  
  /** Display name of the category */
  categoryName: string;
  
  /** Callback when "View More" button is clicked */
  onViewMore?: (categoryId: number, categoryName: string) => void;
  
  /** Custom class names */
  className?: string;
  
  /** Number of products to display (default: 12) */
  productsLimit?: number;
}

/**
 * useCategoryProducts hook return type
 */
export interface UseCategoryProductsReturn {
  subcategories: Category[];
  products: Product[];
  isLoading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

/**
 * Subcategory tile props
 */
export interface SubcategoryTileProps {
  id: number;
  name: string;
  icon?: string;
  onClick: (id: number, name: string) => void;
}

/**
 * Product card props
 */
export interface ProductCardProps {
  product: Product;
  onClick: (product: Product) => void;
}

/**
 * Fetch options for API calls
 */
export interface FetchOptions {
  parentId?: number;
  level?: 0 | 1 | 2;
  limit?: number;
  offset?: number;
  sort?: string;
  categoryIds?: number[];
}
