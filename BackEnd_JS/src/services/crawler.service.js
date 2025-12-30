import { LazadaCrawler } from '../crawlers/lazada.crawler.js';
import { TikiCrawler } from '../crawlers/tiki.crawler.js';
import { ShopeeCrawler } from '../crawlers/shopee.crawler.js';
import { logger } from '../utils/logger.js';

class CrawlerService {
  constructor() {
    this.crawlers = {
      lazada: new LazadaCrawler(),
      tiki: new TikiCrawler(),
      shopee: new ShopeeCrawler()
    };
  }
  
  async crawlAll(productName) {
    const results = await Promise.allSettled([
      this.crawlers.lazada.crawl(productName),
      this.crawlers.tiki.crawl(productName),
      this.crawlers.shopee.crawl(productName)
    ]);
    
    const products = [];
    
    results.forEach((result, index) => {
      const platform = ['lazada', 'tiki', 'shopee'][index];
      
      if (result.status === 'fulfilled') {
        products.push(...result.value);
        logger.info(`✅ ${platform}: ${result.value.length} products`);
      } else {
        logger.error(`❌ ${platform} failed:`, result.reason);
      }
    });
    
    return products;
  }
  
  async crawlPlatform(platform, productName) {
    if (!this.crawlers[platform]) {
      throw new Error(`Unknown platform: ${platform}`);
    }
    
    return await this.crawlers[platform].crawl(productName);
  }
}

export const crawlerService = new CrawlerService();