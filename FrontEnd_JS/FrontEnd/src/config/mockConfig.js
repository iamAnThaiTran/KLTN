/**
 * Mock Data Configuration
 * 
 * This file controls whether the application uses mock data or real server data.
 * 
 * USAGE:
 * - Set ENABLE_MOCK_DATA = true to use mock data for testing UI without server
 * - Set ENABLE_MOCK_DATA = false to use real server APIs
 * 
 * SUPPORTED FEATURES:
 * - Mock product search results
 * - Mock authentication (login/register)
 * - Mock search API responses
 * - Mock product fetching
 * 
 * When mock mode is enabled, all API calls will be intercepted and return mock data
 * with realistic network delays to simulate actual server behavior.
 */

export const MOCK_CONFIG = {
  // Toggle mock mode on/off
  ENABLE_MOCK_DATA: true,
  
  // Simulate network delays (in milliseconds)
  MOCK_NETWORK_DELAY: 500,
  
  // Log mock API calls to console
  LOG_MOCK_CALLS: true,
  
  // Mock data for different scenarios
  MOCK_SCENARIOS: {
    // Scenario: User searches for laptops
    LAPTOP_SEARCH: [
      'laptop', 'máy tính xách tay', 'notebook', 'computer', 
      'dell', 'hp', 'asus', 'lenovo', 'macbook'
    ],
    
    // Scenario: User searches for phones
    PHONE_SEARCH: [
      'iphone', 'phone', 'điện thoại', 'smartphone', 'galaxy',
      'pixel', 'android', 'ios', 'mobile'
    ],
    
    // Scenario: User searches for audio
    AUDIO_SEARCH: [
      'headphones', 'earbuds', 'tai nghe', 'speaker', 'audio',
      'sony', 'beats', 'bose', 'airpods'
    ],
    
    // Scenario: User searches for TV
    TV_SEARCH: [
      'tv', 'television', 'tivi', 'smart tv', '4k',
      'oled', 'qled', 'samsung', 'lg'
    ]
  }
};

/**
 * Quick Reference:
 * 
 * To use mock data in your component:
 * 
 * import { ENABLE_MOCK_DATA, mockGetProductFromTiki } from '@/services/mockDataService';
 * 
 * Then in your API call:
 * if (ENABLE_MOCK_DATA) {
 *   const products = await mockGetProductFromTiki(query);
 * } else {
 *   const products = await getProductFromTiki(query);
 * }
 * 
 * Or better, the services already handle this automatically!
 * Just use the regular API calls - they'll use mock data when enabled.
 */
