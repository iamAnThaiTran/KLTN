/**
 * Comparison History API utilities
 * Handles all API calls related to comparison history management
 */

const API_BASE_URL = 'http://localhost:8000';

/**
 * Save a comparison result to history
 * @param {Object} data - Comparison data to save
 * @returns {Promise<Object>} Saved comparison record
 */
export const saveComparison = async (data) => {
  try {
    const response = await fetch(`${API_BASE_URL}/api/comparisons/save`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
      },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Comparison saved:', result);
    return result;
  } catch (error) {
    console.error('❌ Error saving comparison:', error);
    throw error;
  }
};

/**
 * Get comparison history for current user
 * @param {Object} params - Query parameters
 * @param {number} params.limit - Number of results
 * @param {number} params.offset - Pagination offset
 * @param {boolean} params.starred_only - Filter by starred only
 * @returns {Promise<Object>} List of comparisons
 */
export const getComparisonHistory = async ({
  limit = 10,
  offset = 0,
  starred_only = false,
} = {}) => {
  try {
    const params = new URLSearchParams({
      limit: limit.toString(),
      offset: offset.toString(),
      starred_only: starred_only.toString(),
    });

    const response = await fetch(
      `${API_BASE_URL}/api/comparisons/history?${params}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    console.log(`✅ Retrieved ${result.comparisons.length} comparisons`);
    return result;
  } catch (error) {
    console.error('❌ Error fetching comparison history:', error);
    throw error;
  }
};

/**
 * Get detailed view of a specific comparison
 * @param {number} comparisonId - ID of the comparison
 * @returns {Promise<Object>} Full comparison record
 */
export const getComparisonDetail = async (comparisonId) => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/comparisons/${comparisonId}`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Retrieved comparison detail:', result);
    return result;
  } catch (error) {
    console.error('❌ Error fetching comparison detail:', error);
    throw error;
  }
};

/**
 * Update comparison metadata (notes, starred status)
 * @param {number} comparisonId - ID of the comparison
 * @param {Object} updateData - Fields to update
 * @param {string} updateData.notes - User notes
 * @param {boolean} updateData.is_starred - Star status
 * @returns {Promise<Object>} Updated comparison
 */
export const updateComparison = async (comparisonId, updateData) => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/comparisons/${comparisonId}`,
      {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
        body: JSON.stringify(updateData),
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Comparison updated:', result);
    return result;
  } catch (error) {
    console.error('❌ Error updating comparison:', error);
    throw error;
  }
};

/**
 * Toggle star status of a comparison
 * @param {number} comparisonId - ID of the comparison
 * @param {boolean} isStarred - New star status
 * @returns {Promise<Object>} Updated comparison
 */
export const toggleComparisonStar = async (comparisonId, isStarred) => {
  return updateComparison(comparisonId, { is_starred: isStarred });
};

/**
 * Update comparison notes
 * @param {number} comparisonId - ID of the comparison
 * @param {string} notes - Notes text
 * @returns {Promise<Object>} Updated comparison
 */
export const updateComparisonNotes = async (comparisonId, notes) => {
  return updateComparison(comparisonId, { notes });
};

/**
 * Delete a comparison
 * @param {number} comparisonId - ID of the comparison to delete
 * @returns {Promise<Object>} Success message
 */
export const deleteComparison = async (comparisonId) => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/comparisons/${comparisonId}`,
      {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Comparison deleted');
    return result;
  } catch (error) {
    console.error('❌ Error deleting comparison:', error);
    throw error;
  }
};

/**
 * Get comparison statistics
 * @returns {Promise<Object>} Statistics object
 */
export const getComparisonStats = async () => {
  try {
    const response = await fetch(
      `${API_BASE_URL}/api/comparisons/stats/overview`,
      {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token') || ''}`,
        },
      }
    );

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const result = await response.json();
    console.log('✅ Retrieved comparison stats:', result);
    return result.data;
  } catch (error) {
    console.error('❌ Error fetching comparison stats:', error);
    throw error;
  }
};

export default {
  saveComparison,
  getComparisonHistory,
  getComparisonDetail,
  updateComparison,
  toggleComparisonStar,
  updateComparisonNotes,
  deleteComparison,
  getComparisonStats,
};
