/**
 * API Client with automatic token refresh on 401
 */

import { StorageService } from '../services/StorageService.js';

const API_BASE_URL = 'http://localhost:8000';

/**
 * Make an API request with automatic token refresh on 401
 */
export async function apiRequest(endpoint, options = {}) {
  let token = StorageService.getToken();
  
  console.log('📡 API Request:', endpoint, 'Token:', token ? '✓' : '✗');
  
  // Add auth header if token exists
  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  let response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  console.log('📊 Response status:', response.status);

  // If 401, try to refresh token
  if (response.status === 401) {
    console.log('🔄 Token expired, attempting to refresh...');
    const refreshed = await refreshToken();
    
    if (refreshed) {
      token = StorageService.getToken();
      headers['Authorization'] = `Bearer ${token}`;
      
      // Retry original request with new token
      response = await fetch(`${API_BASE_URL}${endpoint}`, {
        ...options,
        headers,
      });
    }
  }

  return response;
}

/**
 * Refresh the access token using /api/auth/refresh endpoint
 */
async function refreshToken() {
  try {
    const token = StorageService.getToken();
    if (!token) return false;

    const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      if (data.access_token) {
        StorageService.setToken(data.access_token);
        console.log('✅ Token refreshed successfully');
        return true;
      }
    }
    
    return false;
  } catch (error) {
    console.error('❌ Token refresh failed:', error);
    return false;
  }
}

export default apiRequest;
