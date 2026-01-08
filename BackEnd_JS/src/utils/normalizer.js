import { logger } from './logger.js';

/**
 * Normalize product name into a standardized cache key
 * Removes special characters, converts to lowercase, handles duplicates
 * 
 * @param {string} productName - Original product name
 * @returns {string} - Normalized product key
 */
export function normalizeProductKey(productName) {
  try {
    // TODO: Implementation steps:
    // 1. Convert to lowercase
    // 2. Trim whitespace
    // 3. Remove special characters (keep only alphanumeric and hyphens)
    // 4. Replace spaces with hyphens
    // 5. Remove duplicate hyphens
    // 6. Return normalized key
    
    const normalized = productName
      .toLowerCase()
      .trim()
      .replace(/[^\w\s-]/g, '') // Remove special characters
      .replace(/\s+/g, '-')      // Replace spaces with hyphens
      .replace(/-+/g, '-')       // Remove duplicate hyphens
      .replace(/^-+|-+$/g, '');  // Remove leading/trailing hyphens
    
    logger.info(`Normalized: "${productName}" -> "${normalized}"`);
    return normalized;
  } catch (error) {
    logger.error(`Error normalizing product key: ${productName}`, error);
    return productName.toLowerCase().trim();
  }
}

/**
 * Normalize product title for consistent display
 * 
 * @param {string} title - Product title
 * @returns {string} - Normalized title
 */
export function normalizeTitle(title) {
  try {
    // TODO: Implementation:
    // 1. Trim whitespace
    // 2. Remove extra spaces between words
    // 3. Capitalize first letter of each word (title case)
    // 4. Remove duplicate punctuation
    
    return title
      .trim()
      .replace(/\s+/g, ' ')           // Remove extra spaces
      .replace(/\.{2,}/g, '.')        // Remove duplicate dots
      .replace(/,{2,}/g, ',');        // Remove duplicate commas
  } catch (error) {
    logger.error(`Error normalizing title: ${title}`, error);
    return title.trim();
  }
}

/**
 * Normalize price string to number
 * Handles various formats: "1,000.00", "1.000,00", "$100", etc.
 * 
 * @param {string|number} price - Price value
 * @returns {number} - Normalized price as number
 */
export function normalizePrice(price) {
  try {
    // TODO: Implementation:
    // 1. Handle if already a number
    // 2. Remove currency symbols ($, €, ₫, etc.)
    // 3. Detect thousand separator vs decimal separator
    // 4. Convert to float number
    // 5. Return -1 or null if invalid
    
    if (typeof price === 'number') return price;
    
    // Remove currency symbols
    let cleaned = String(price).replace(/[^\d.,]/g, '');
    
    // TODO: Detect format (1,000.00 vs 1.000,00)
    // For now assume: if last separator is comma, use comma as decimal
    const lastCommaIndex = cleaned.lastIndexOf(',');
    const lastDotIndex = cleaned.lastIndexOf('.');
    
    if (lastCommaIndex > lastDotIndex) {
      // European format: 1.000,00
      cleaned = cleaned.replace(/\./g, '').replace(',', '.');
    } else {
      // US format: 1,000.00
      cleaned = cleaned.replace(/,/g, '');
    }
    
    const normalized = parseFloat(cleaned);
    return isNaN(normalized) ? -1 : normalized;
  } catch (error) {
    logger.error(`Error normalizing price: ${price}`, error);
    return -1;
  }
}

/**
 * Normalize URL for consistent comparison
 * 
 * @param {string} url - Product URL
 * @returns {string} - Normalized URL
 */
export function normalizeUrl(url) {
  try {
    // TODO: Implementation:
    // 1. Remove protocol (https://, http://)
    // 2. Remove trailing slashes
    // 3. Remove query parameters
    // 4. Remove hash fragments
    // 5. Convert to lowercase
    
    return url
      .toLowerCase()
      .replace(/^https?:\/\//, '')   // Remove protocol
      .replace(/\/$/, '')             // Remove trailing slash
      .split(/[?#]/)[0];              // Remove query params and hash
  } catch (error) {
    logger.error(`Error normalizing URL: ${url}`, error);
    return url;
  }
}

/**
 * Normalize text for search/comparison
 * Removes accents and special characters
 * 
 * @param {string} text - Text to normalize
 * @returns {string} - Normalized text
 */
export function normalizeText(text) {
  try {
    // TODO: Implementation:
    // 1. Normalize Unicode (NFD)
    // 2. Remove accents and diacritics
    // 3. Convert to lowercase
    // 4. Remove extra whitespace
    
    return text
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '') // Remove accents
      .toLowerCase()
      .trim()
      .replace(/\s+/g, ' ');
  } catch (error) {
    logger.error(`Error normalizing text: ${text}`, error);
    return text.toLowerCase().trim();
  }
}
