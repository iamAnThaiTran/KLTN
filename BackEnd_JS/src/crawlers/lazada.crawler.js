import puppeteer from 'puppeteer';
import { logger } from '../utils/logger.js';

/**
 * Lazada Platform Crawler
 * Crawls product data from Lazada.vn
 */
export class LazadaCrawler {
    constructor() {
        this.baseUrl = 'https://www.lazada.vn/search?q=';
        this.config = {
            productSelector: 'div[data-qa-locator="product-item"]',
            nameSelector: 'div.RfADt a',
            priceSelector: 'div.aBrP0 span.ooOxS',
            imageSelector: 'img[type="product"]',
            discountSelector: 'span.IcOsH',
            soldSelector: 'span._1cEkb',
            ratingSelector: 'div.mdmmT',
            reviewSelector: 'span.qzqFw',
            timeout: 15000,
            maxPages: 2,
        };
    }

    /**
     * Crawl products from Lazada
     * @param {string} productName - Product to search
     * @returns {Promise<array>} - Array of product objects
     */
    async crawl(productName) {
        let browser = null;
        try {
            logger.info(`[Lazada] Starting crawl for: ${productName}`);

            browser = await puppeteer.launch({
                headless: true,
                args: ['--no-sandbox', '--disable-setuid-sandbox'],
            });

            const page = await browser.newPage();
            page.setDefaultTimeout(this.config.timeout);
            page.setDefaultNavigationTimeout(this.config.timeout);

            // Set user agent to avoid blocking
            await page.setUserAgent(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            );

            const url = `${this.baseUrl}${encodeURIComponent(productName)}`;
            logger.info(`[Lazada] Navigating to: ${url}`);

            await page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 });

            const products = await this.extractProducts(page, productName);

            await browser.close();
            logger.info(
                `[Lazada] Found ${products.length} products for "${productName}"`
            );

            return products;
        } catch (error) {
            logger.error('[Lazada] Crawl error:', error.message);
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
            await page
                .waitForSelector(this.config.productSelector, { timeout: 8000 })
                .catch(() => {
                    logger.warn(
                        '[Lazada] Product selector not found, trying alternative selectors'
                    );
                });

            const products = await page.evaluate(() => {
                const items = document.querySelectorAll('div[data-qa-locator="product-item"]');
                const result = [];

                items.forEach((item) => {
                    try {
                        // Get product link and title
                        const linkEl = item.querySelector('div.RfADt a');
                        const title = linkEl?.getAttribute('title')?.trim() || linkEl?.innerText?.trim() || 'N/A';
                        const link = linkEl?.href || '';

                        // Get price
                        const priceEl = item.querySelector('span.ooOxS');
                        let price = priceEl?.innerText?.trim() || 'N/A';

                        // Clean price string (remove currency and convert to number)
                        if (price !== 'N/A') {
                            price = price.replace(/[^\d,]/g, '').replace(',', '');
                        }

                        // Get image
                        const imageEl = item.querySelector('img[type="product"]');
                        const image = imageEl?.src || imageEl?.['data-src'] || '';

                        // Get discount
                        const discountEl = item.querySelector('span.IcOsH');
                        const discount = discountEl?.innerText?.match(/\d+/)?.[0] || '0';

                        // Get sold count
                        const soldEl = item.querySelector('span._1cEkb span');
                        const sold = soldEl?.innerText?.match(/\d+/)?.[0] || '0';

                        // Get rating
                        const ratingEl = item.querySelector('div.mdmmT');
                        const stars = ratingEl?.querySelectorAll('i._9-ogB.Dy1nx').length || 0;

                        // Get review count
                        const reviewEl = item.querySelector('span.qzqFw');
                        const reviews = reviewEl?.innerText?.match(/\d+/)?.[0] || '0';

                        if (title && title !== 'N/A' && link && price !== 'N/A') {
                            result.push({
                                title,
                                price: parseInt(price) || 0,
                                priceOriginal: parseInt(price) || 0,
                                discount: parseInt(discount) || 0,
                                link: link.startsWith('http') ? link : 'https:' + link,
                                image,
                                rating: Math.min(5, Math.max(0, stars)),
                                reviews: parseInt(reviews) || 0,
                                sold: parseInt(sold) || 0,
                                source: 'lazada',
                                platform: 'lazada'
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
            logger.error('[Lazada] Extract products error:', error.message);
            return [];
        }
    }
}

