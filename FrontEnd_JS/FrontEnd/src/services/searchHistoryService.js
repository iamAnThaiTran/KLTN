/**
 * Search History Service
 * Handles fetching user's search history and recommendations from backend
 * 
 * Calls API Gateway which routes to microservices:
 * - Authenticated: API Gateway → User Service → Product Service
 * - Non-authenticated: API Gateway → Product Service
 */

const API_BASE = 'http://localhost:8000';

export class SearchHistoryService {
  /**
   * Get user's search history (actual search queries)
   * Source: Backend GET /api/user/search-history
   */
  static async getSearchHistory(token, limit = 20, days = 30) {
    try {
      const response = await fetch(
        `${API_BASE}/api/user/search-history?limit=${limit}&days=${days}`,
        {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          }
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[SearchHistoryService] Error fetching search history:', error);
      throw error;
    }
  }

  /**
   * Get user's search preferences and interests
   * Source: Backend GET /api/recommendations/preferences
   */
  static async getUserPreferences(token) {
    try {
      const response = await fetch(`${API_BASE}/api/recommendations/preferences`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[SearchHistoryService] Error fetching preferences:', error);
      throw error;
    }
  }

  /**
   * Get recommended products for homepage
   * 
   * Microservices Flow:
   * 1. Frontend calls: GET /api/recommendations/homepage (with Bearer token)
   * 2. API Gateway checks auth:
   *    - If authenticated: Routes to User Service + Product Service
   *      a. User Service: Builds criteria from search history
   *      b. Product Service: Queries products matching criteria
   *    - If not authenticated: Calls Product Service for trending
   * 3. Returns personalized or trending products
   * 
   * For authenticated users, returns personalized recommendations based on search history
   */
  static async getRecommendedProducts(token) {
    try {
      const response = await fetch(`${API_BASE}/api/recommendations/homepage`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[SearchHistoryService] Error fetching recommendations:', error);
      throw error;
    }
  }

  /**
   * Get public/trending recommendations
   * 
   * Microservices Flow:
   * 1. Frontend calls: GET /api/recommendations/homepage (without token)
   * 2. API Gateway detects no auth:
   *    - Routes directly to Product Service
   * 3. Product Service queries trending products
   * 4. Returns trending products
   * 
   * For non-authenticated users or as fallback
   * Returns trending and popular products
   */
  static async getPublicRecommendations() {
    try {
      const response = await fetch(`${API_BASE}/api/recommendations/homepage`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('[SearchHistoryService] Error fetching public recommendations:', error);
      throw error;
    }
  }
}

export default SearchHistoryService;
