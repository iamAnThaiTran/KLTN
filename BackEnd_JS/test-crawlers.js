import { LazadaCrawler } from './src/crawlers/lazada.crawler.js';
import { TikiCrawler } from './src/crawlers/tiki.crawler.js';
import { pool } from './src/config/database.js';
import { logger } from './src/utils/logger.js';

// Fetch all categories from database dynamically
async function getCategoriesToCrawl() {
  try {
    const result = await pool.query(
      'SELECT DISTINCT name FROM categories WHERE parent_id IS NULL ORDER BY name'
    );
    return result.rows.map(row => row.name);
  } catch (error) {
    logger.warn('Failed to fetch categories from database, using defaults:', error.message);
    // Fallback to hardcoded list if database fails
    return ['laptop', 'điện thoại', 'máy tính bảng', 'tai nghe'];
  }
}

async function getCategoryIdByName(categoryName) {
  try {
    const result = await pool.query(
      'SELECT id FROM categories WHERE name ILIKE $1 LIMIT 1',
      [`%${categoryName}%`]
    );
    return result.rows.length > 0 ? result.rows[0].id : null;
  } catch (error) {
    logger.warn(`Failed to get category ID for "${categoryName}":`, error.message);
    return null;
  }
}

async function saveProductsToDb(products, category) {
  let saved = 0;
  const categoryId = await getCategoryIdByName(category);
  
  for (const product of products) {
    try {
      const slug = (product.title || '').toLowerCase().replace(/\s+/g, '-');
      
      const sql = `
        INSERT INTO products (name, slug, brand, price, original_price, discount_percent, images, rating_avg, rating_count, link, platform, category_id, is_active)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, true)
        ON CONFLICT (slug) DO UPDATE SET 
          price = $4,
          original_price = $5,
          discount_percent = $6,
          rating_avg = $8,
          rating_count = $9,
          link = $10,
          platform = $11,
          category_id = $12,
          updated_at = CURRENT_TIMESTAMP
        RETURNING id;
      `;
      
      const values = [
        product.title,
        slug,
        product.brand || 'Unknown',
        product.price || 0,
        product.priceOriginal || product.price || 0,
        product.discount || 0,
        product.image ? [product.image] : [],
        product.rating || 0,
        product.reviews || 0,
        product.link || '',
        product.platform || product.source || 'unknown',
        categoryId
      ];
      
      await pool.query(sql, values);
      saved++;
    } catch (error) {
      logger.warn(`Failed to save product ${product.title}:`, error.message);
    }
  }
  
  return saved;
}

async function testCrawlers() {
  logger.info('🕷️ Starting crawler test...\n');
  
  const lazada = new LazadaCrawler();
  const tiki = new TikiCrawler();
  
  // Fetch categories from database
  const categoriesToCrawl = await getCategoriesToCrawl();
  logger.info(`📂 Found ${categoriesToCrawl.length} categories in database`);
  logger.info(`Categories: ${categoriesToCrawl.join(', ')}\n`);
  
  for (const product of categoriesToCrawl) {
    try {
      logger.info(`\n📦 Crawling for: "${product}"`);
      logger.info('=====================================');
      
      // Crawl Lazada
      logger.info(`🕷️ Lazada crawler...`);
      const lazadaProducts = await lazada.crawl(product);
      logger.info(`✅ Lazada: Found ${lazadaProducts.length} products`);
      if (lazadaProducts.length > 0) {
        const savedLzd = await saveProductsToDb(lazadaProducts, product);
        logger.info(`💾 Saved ${savedLzd} Lazada products to database`);
      }
      
      // Wait before next crawl
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      // Crawl Tiki
      logger.info(`🕷️ Tiki crawler...`);
      const tikiProducts = await tiki.crawl(product);
      logger.info(`✅ Tiki: Found ${tikiProducts.length} products`);
      if (tikiProducts.length > 0) {
        const savedTiki = await saveProductsToDb(tikiProducts, product);
        logger.info(`💾 Saved ${savedTiki} Tiki products to database`);
      }
      
      // Wait before next category
      await new Promise(resolve => setTimeout(resolve, 2000));
      
    } catch (error) {
      logger.error(`❌ Error crawling "${product}":`, error.message);
    }
  }
  
  // Get stats
  try {
    const result = await pool.query('SELECT COUNT(*) as total FROM products WHERE is_active = true');
    const total = result.rows[0].total;
    logger.info(`\n✨ Database now has ${total} active products`);
  } catch (error) {
    logger.error('Failed to get product count:', error);
  }

  // Display products by category
  logger.info('\n\n📂 Retrieving Products by Category:\n');
  try {
    const categoryResult = await pool.query(`
      SELECT brand, COUNT(*) as count 
      FROM products 
      WHERE is_active = true 
      GROUP BY brand 
      ORDER BY count DESC 
      LIMIT 10
    `);
    
    logger.info('📊 Top Brands/Categories:');
    categoryResult.rows.forEach((row, index) => {
      logger.info(`  ${index + 1}. ${row.brand}: ${row.count} products`);
    });
  } catch (error) {
    logger.error('Failed to get category stats:', error);
  }

  // Display sample products
  logger.info('\n\n📋 Sample Products from Database:\n');
  try {
    const sampleResult = await pool.query(`
      SELECT 
        p.id, 
        p.name, 
        p.brand, 
        p.price, 
        p.original_price, 
        p.discount_percent, 
        p.rating_avg, 
        p.rating_count,
        p.link,
        p.platform,
        c.name as category_name
      FROM products p
      LEFT JOIN categories c ON p.category_id = c.id
      WHERE p.is_active = true 
      ORDER BY p.id DESC 
      LIMIT 5
    `);
    
    sampleResult.rows.forEach((product, index) => {
      logger.info(`${index + 1}. ${product.name}`);
      logger.info(`   Category: ${product.category_name || 'Uncategorized'}`);
      logger.info(`   Brand: ${product.brand}`);
      logger.info(`   Price: ₫${product.price} (Original: ₫${product.original_price})`);
      logger.info(`   Discount: ${product.discount_percent}%`);
      logger.info(`   Rating: ${product.rating_avg}/5 (${product.rating_count} reviews)`);
      logger.info(`   Platform: ${product.platform}`);
      logger.info(`   Link: ${product.link || 'N/A'}`);
      logger.info('');
    });
  } catch (error) {
    logger.error('Failed to get sample products:', error);
  }
  
  await pool.end();
  logger.info('\n✅ Crawler test completed!');
  process.exit(0);
}

testCrawlers().catch(error => {
  logger.error('Fatal error:', error);
  process.exit(1);
});
