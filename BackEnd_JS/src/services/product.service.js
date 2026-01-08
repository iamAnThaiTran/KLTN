import { prisma } from '../config/database.js';
import { crawlerService } from './crawler.service.js';
import { rankingService } from './ranking.service.js';
import { cacheService } from './cache.service.js';
import { normalizeProductKey } from '../utils/normalizer.js';
import { logger } from '../utils/logger.js';
import { llmService } from './llm.service.js';

class ProductService {
  async search({ query, message, forceRefresh, userId }) {
    // 1. Get product name
    const productName = query || await llmService.extractProductName(message);
    const productKey = normalizeProductKey(productName);
    
    // 2. Check cache
    if (!forceRefresh) {
      const cached = await cacheService.get(productKey);
      if (cached) {
        logger.info(`Cache hit for: ${productKey}`);
        
        // Track search
        if (userId) {
          await this.trackSearch(userId, productName, productKey);
        }
        
        return {
          data: cached,
          cached: true,
          timestamp: new Date()
        };
      }
    }
    
    // 3. Crawl fresh data
    logger.info(`Crawling fresh data for: ${productKey}`);
    const products = await crawlerService.crawlAll(productName);
    
    // 4. Save to database
    const savedProducts = await this.saveProducts(products, productKey);
    
    // 5. Rank products
    const rankedProducts = rankingService.rank(savedProducts);
    
    // 6. Cache results
    await cacheService.set(productKey, rankedProducts);
    
    // 7. Track search
    if (userId) {
      await this.trackSearch(userId, productName, productKey);
    }
    
    return {
      data: rankedProducts,
      cached: false,
      timestamp: new Date()
    };
  }
  
  async saveProducts(products, productKey) {
    const saved = [];
    
    for (const product of products) {
      const savedProduct = await prisma.product.upsert({
        where: { link: product.link },
        update: {
          price: product.price,
          title: product.title,
          image: product.image,
          trust_value: product.trust_value,
          updated_at: new Date()
        },
        create: {
          ...product,
          product_key: productKey
        }
      });
      
      saved.push(savedProduct);
    }
    
    return saved;
  }
  
  async trackSearch(userId, query, productKey) {
    await prisma.searchHistory.create({
      data: { user_id: userId, query, product_key: productKey }
    });
  }
  
  async getById(id) {
    return await prisma.product.findUnique({
      where: { id },
      include: { price_history: { orderBy: { recorded_at: 'desc' }, take: 30 } }
    });
  }
  
  async compare(productIds) {
    const products = await prisma.product.findMany({
      where: { id: { in: productIds } }
    });
    
    return rankingService.compare(products);
  }
}

export const productService = new ProductService();