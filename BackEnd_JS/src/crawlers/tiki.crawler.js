import puppeteer from 'puppeteer';
import { logger } from '../utils/logger.js';

/**
 * Tiki Platform Crawler
 * Crawls product data from Tiki.vn
 */
export class TikiCrawler {
  constructor() {
    this.baseUrl = 'https://tiki.vn/search?q=';
    this.config = {
      productSelector: 'a.product-item',
      nameSelector: 'h3.dDeapS',
      priceSelector: 'div.price-discount__price',
      discountSelector: 'div.price-discount__percent',
      imageSelector: 'img.hFEtiz',
      brandSelector: 'span',
      soldSelector: 'span.quantity',
      timeout: 15000,
      maxPages: 3,
    };
  }

  /**
   * Crawl products from Tiki
   * @param {string} productName - Product to search
   * @returns {Promise<array>} - Array of product objects
   */
  async crawl(productName) {
    let browser = null;
    try {
      logger.info(`[Tiki] Starting crawl for: ${productName}`);
      
      browser = await puppeteer.launch({ 
        headless: true,
        args: ['--no-sandbox', '--disable-setuid-sandbox']
      });
      
      const page = await browser.newPage();
      page.setDefaultTimeout(this.config.timeout);
      page.setDefaultNavigationTimeout(this.config.timeout);

      // Set user agent to avoid blocking
      await page.setUserAgent(
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
      );
      
      const url = `${this.baseUrl}${encodeURIComponent(productName)}`;
      logger.info(`[Tiki] Navigating to: ${url}`);
      
      await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });
      
      const products = await this.extractProducts(page, productName);
      
      await browser.close();
      logger.info(`[Tiki] Found ${products.length} products for "${productName}"`);
      
      return products;
    } catch (error) {
      logger.error('[Tiki] Crawl error:', error.message);
      if (browser) await browser.close();
      return [];
    }
  }

  /**
   * Extract product data from page
   * @private
   */
  async extractProducts(page, searchQuery) {
    try {
      // Wait for products to load
      await page.waitForSelector('a.product-item', { timeout: 8000 }).catch(() => {
        logger.warn('[Tiki] Product items not found, trying alternative selectors');
      });
      
      const products = await page.evaluate(() => {
        // Get all product items
        const items = document.querySelectorAll('a.product-item');
        
        const result = [];
        
        items.forEach((item) => {
          try {
            // Get product link
            const link = item.href || '';

            // Get product title
            const titleEl = item.querySelector('h3.dDeapS');
            const title = titleEl?.innerText?.trim() || 'N/A';

            // Get price
            const priceEl = item.querySelector('div.price-discount__price');
            let price = priceEl?.innerText?.trim() || 'N/A';

            // Clean price string (remove ₫ and convert to number)
            if (price !== 'N/A') {
              price = price.replace(/[^\d]/g, '');
            }

            // Get discount
            const discountEl = item.querySelector('div.price-discount__percent');
            let discount = discountEl?.innerText?.trim() || '0';
            // Remove % sign
            discount = discount.replace(/[^\d]/g, '');

            // Get brand
            const brandEl = item.querySelector('div.cUhrxa span');
            const brand = brandEl?.innerText?.trim() || 'Unknown';

            // Get image from picture > img or directly from img
            let image = '';
            const pictureImg = item.querySelector('picture img');
            const directImg = item.querySelector('img.hFEtiz');
            
            if (pictureImg) {
              // Extract first image URL from srcset or use src
              const srcset = pictureImg.getAttribute('srcset');
              if (srcset) {
                // srcset format: "url1 1x, url2 2x" - take first URL
                image = srcset.split(',')[0].split(' ')[0].trim();
              } else {
                image = pictureImg.src || '';
              }
            } else if (directImg) {
              const srcset = directImg.getAttribute('srcset');
              if (srcset) {
                image = srcset.split(',')[0].split(' ')[0].trim();
              } else {
                image = directImg.src || '';
              }
            }

            // Get sold count
            const soldEl = item.querySelector('span.quantity.has-border');
            let sold = soldEl?.innerText?.match(/\d+/)?.[0] || '0';

            // Count stars for rating (count filled yellow stars)
            const starContainer = item.querySelector('div.eTeHeN');
            let rating = 0;
            if (starContainer) {
              // Count the number of filled yellow star SVGs
              const filledStars = starContainer.querySelectorAll('svg path[fill="#FFC400"]').length / 6; // Each star has 6 path elements
              rating = Math.round(filledStars);
            }

            if (title && title !== 'N/A' && link && price !== 'N/A') {
              result.push({
                title,
                price: parseInt(price) || 0,
                priceOriginal: parseInt(price) || 0,
                discount: parseInt(discount) || 0,
                brand,
                link,
                image,
                rating: Math.min(5, Math.max(0, rating)),
                reviews: 0, // Tiki doesn't show review count in this layout
                sold: parseInt(sold) || 0,
                source: 'tiki',
                platform: 'tiki'
              });
            }
          } catch (err) {
            // Skip problematic items
          }
        });
        
        return result;
      });
      
      return products;
    } catch (error) {
      logger.error('[Tiki] Extract products error:', error.message);
      return [];
    }
  }
}
