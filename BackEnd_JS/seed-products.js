/**
 * Seed database with realistic mock product data
 * Run: npm run seed-products
 * 
 * This populates the database with realistic product data
 * for testing before implementing live crawlers
 */

import { pool } from './src/config/database.js';
import { logger } from './src/utils/logger.js';

const MOCK_PRODUCTS = [
  // Laptops
  {
    name: 'Dell XPS 13 Plus (9330) - Intel Core i7 13th Gen',
    price: 24990000,
    original_price: 27990000,
    discount_percent: 11,
    brand: 'Dell',
    category_id: 1,
    image: 'https://images.unsplash.com/photo-1588872657840-790ff3bde08c?w=400',
    description: 'Laptop mỏng nhẹ cao cấp với màn hình FHD+ 13.4 inch, chip Intel Core i7, RAM 16GB'
  },
  {
    name: 'MacBook Air M2 13 inch 2022 - Silver',
    price: 22990000,
    original_price: 24990000,
    discount_percent: 8,
    brand: 'Apple',
    category_id: 1,
    image: 'https://images.unsplash.com/photo-1517336714731-489689fd1ca8?w=400',
    description: 'Laptop Apple cao cấp với chip M2, RAM 8GB, SSD 256GB'
  },
  {
    name: 'ASUS ROG G15 Advantage Edition - AMD Ryzen 9',
    price: 28990000,
    original_price: 32990000,
    discount_percent: 12,
    brand: 'ASUS',
    category_id: 1,
    image: 'https://images.unsplash.com/photo-1544303749-e5fbb8e8f0f3?w=400',
    description: 'Gaming laptop với màn hình 165Hz, AMD Ryzen 9, RTX 3060'
  },
  {
    name: 'Lenovo ThinkPad X1 Carbon Gen 10 - Intel Core i7',
    price: 25990000,
    original_price: 28990000,
    discount_percent: 10,
    brand: 'Lenovo',
    category_id: 1,
    image: 'https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=400',
    description: 'Laptop business cao cấp, chuyên nghiệp, bền bỉ'
  },
  {
    name: 'HP Pavilion 15 - Intel Core i5 12th Gen',
    price: 15990000,
    original_price: 17990000,
    discount_percent: 11,
    brand: 'HP',
    category_id: 1,
    image: 'https://images.unsplash.com/photo-1588872657840-790ff3bde08c?w=400',
    description: 'Laptop giá rẻ, hiệu năng tốt cho học tập và công việc'
  },
  
  // Smartphones
  {
    name: 'iPhone 15 Pro Max 256GB - Deep Purple',
    price: 29990000,
    original_price: 32990000,
    discount_percent: 9,
    brand: 'Apple',
    category_id: 2,
    image: 'https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=400',
    description: 'Điện thoại cao cấp Apple với chip A17 Pro, camera 48MP'
  },
  {
    name: 'Samsung Galaxy S24 Ultra 512GB - Titanium Black',
    price: 27990000,
    original_price: 29990000,
    discount_percent: 7,
    brand: 'Samsung',
    category_id: 2,
    image: 'https://images.unsplash.com/photo-1511264372407-330f63602d72?w=400',
    description: 'Flagship Samsung với màn hình 120Hz, S Pen, camera 200MP'
  },
  {
    name: 'Xiaomi 14 Ultra 512GB - Black',
    price: 18990000,
    original_price: 20990000,
    discount_percent: 10,
    brand: 'Xiaomi',
    category_id: 2,
    image: 'https://images.unsplash.com/photo-1516589178587-c52646b8c231?w=400',
    description: 'Điện thoại giá tốt với camera chất lượng cao'
  },
  {
    name: 'Google Pixel 8 Pro 256GB - Obsidian',
    price: 21990000,
    original_price: 23990000,
    discount_percent: 8,
    brand: 'Google',
    category_id: 2,
    image: 'https://images.unsplash.com/photo-1607317352960-3a63bda34f6b?w=400',
    description: 'Smartphone Google với AI tích hợp, camera xuất sắc'
  },
  {
    name: 'OnePlus 12 256GB - Silky Black',
    price: 12990000,
    original_price: 14990000,
    discount_percent: 13,
    brand: 'OnePlus',
    category_id: 2,
    image: 'https://images.unsplash.com/photo-1511491356471-a0d1d9b39f1d?w=400',
    description: 'Smartphone hiệu năng cao, giá hợp lý'
  },

  // Tablets
  {
    name: 'iPad Pro 12.9 inch M2 256GB - Silver',
    price: 21990000,
    original_price: 23990000,
    discount_percent: 8,
    brand: 'Apple',
    category_id: 3,
    image: 'https://images.unsplash.com/photo-1544716278-ca5e3af4abd8?w=400',
    description: 'Tablet cao cấp với chip M2, Liquid Retina XDR'
  },
  {
    name: 'Samsung Galaxy Tab S10 Pro 12.4 inch 256GB',
    price: 18990000,
    original_price: 20990000,
    discount_percent: 10,
    brand: 'Samsung',
    category_id: 3,
    image: 'https://images.unsplash.com/photo-1561070791-2526d30994b5?w=400',
    description: 'Tablet Samsung với màn hình AMOLED, S Pen'
  },

  // Headphones
  {
    name: 'Sony WH-1000XM5 Wireless Headphones',
    price: 6990000,
    original_price: 7990000,
    discount_percent: 13,
    brand: 'Sony',
    category_id: 4,
    image: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400',
    description: 'Tai nghe chống ồn tốt nhất, âm thanh xuất sắc'
  },
  {
    name: 'Apple AirPods Pro (2nd gen)',
    price: 5990000,
    original_price: 6990000,
    discount_percent: 14,
    brand: 'Apple',
    category_id: 4,
    image: 'https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=400',
    description: 'Tai nghe Apple không dây, chống ồn chủ động'
  },
  {
    name: 'JBL Tune 770NC Wireless Headphones',
    price: 2990000,
    original_price: 3490000,
    discount_percent: 14,
    brand: 'JBL',
    category_id: 4,
    image: 'https://images.unsplash.com/photo-1484704849700-f032a568e944?w=400',
    description: 'Tai nghe không dây giá rẻ, chất lượng tốt'
  },

  // Speakers
  {
    name: 'Bose SoundLink Max Bluetooth Speaker',
    price: 3490000,
    original_price: 3990000,
    discount_percent: 13,
    brand: 'Bose',
    category_id: 5,
    image: 'https://images.unsplash.com/photo-1545127398-14699f92334b?w=400',
    description: 'Loa di động Bluetooth, chất lượng âm thanh cao'
  },
  {
    name: 'JBL Xtreme 3 Portable Bluetooth Speaker',
    price: 2990000,
    original_price: 3490000,
    discount_percent: 14,
    brand: 'JBL',
    category_id: 5,
    image: 'https://images.unsplash.com/photo-1589003077984-894fdbb6d075?w=400',
    description: 'Loa chống nước, âm thanh to rõ'
  },

  // Cameras
  {
    name: 'Canon EOS R5 Mark II Mirrorless Camera',
    price: 59990000,
    original_price: 65990000,
    discount_percent: 9,
    brand: 'Canon',
    category_id: 6,
    image: 'https://images.unsplash.com/photo-1611532736597-de2d4265fba3?w=400',
    description: 'Máy ảnh mirrorless chuyên nghiệp, quay 8K'
  },
  {
    name: 'Sony A6700 APS-C Mirrorless Camera',
    price: 34990000,
    original_price: 37990000,
    discount_percent: 8,
    brand: 'Sony',
    category_id: 6,
    image: 'https://images.unsplash.com/photo-1604933762023-7213af7ff5a7?w=400',
    description: 'Máy ảnh Sony nhỏ gọn, hiệu năng cao'
  },

  // Smartwatches
  {
    name: 'Apple Watch Series 9 45mm - Midnight',
    price: 10990000,
    original_price: 11990000,
    discount_percent: 8,
    brand: 'Apple',
    category_id: 7,
    image: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400',
    description: 'Smartwatch Apple, theo dõi sức khỏe, thanh toán'
  },
  {
    name: 'Samsung Galaxy Watch 6 Classic 47mm',
    price: 7990000,
    original_price: 8990000,
    discount_percent: 11,
    brand: 'Samsung',
    category_id: 7,
    image: 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=400',
    description: 'Smartwatch Samsung, thiết kế thanh lịch'
  },

  // Gaming
  {
    name: 'Xbox Series X 1TB',
    price: 9990000,
    original_price: 10990000,
    discount_percent: 9,
    brand: 'Microsoft',
    category_id: 8,
    image: 'https://images.unsplash.com/photo-1538481143235-5d8a0874d6fe?w=400',
    description: 'Console chơi game Xbox hiệu năng cao'
  },
  {
    name: 'PlayStation 5 Disc Edition',
    price: 10990000,
    original_price: 11990000,
    discount_percent: 8,
    brand: 'Sony',
    category_id: 8,
    image: 'https://images.unsplash.com/photo-1538481143235-5d8a0874d6fe?w=400',
    description: 'Console PlayStation 5 có đĩa game'
  }
];

async function seedDatabase() {
  try {
    console.log('\n🌱 Starting database seeding with realistic product data...\n');
    
    // Check database connection
    const testQuery = await pool.query('SELECT NOW()');
    logger.info('✅ Database connected');
    console.log(`📅 Server time: ${testQuery.rows[0].now}\n`);
    
    // Truncate products table
    await pool.query('TRUNCATE products RESTART IDENTITY CASCADE');
    console.log('🗑️  Cleaned existing products\n');
    
    // Insert products
    let insertedCount = 0;
    
    for (const product of MOCK_PRODUCTS) {
      try {
        const slug = product.name.toLowerCase()
          .replace(/[^a-z0-9]+/g, '-')
          .replace(/^-|-$/g, '');
        
        const sql = `
          INSERT INTO products (name, slug, brand, category_id, description, price, original_price, discount_percent, images, rating_avg, rating_count, is_active)
          VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, true)
          RETURNING id;
        `;
        
        const values = [
          product.name,
          slug,
          product.brand,
          product.category_id || 1,
          product.description,
          product.price,
          product.original_price,
          product.discount_percent,
          product.image ? [product.image] : [],
          Math.random() * 2 + 3.5, // Random rating 3.5-5.5
          Math.floor(Math.random() * 1000) // Random reviews 0-1000
        ];
        
        const result = await pool.query(sql, values);
        if (result.rows.length > 0) {
          insertedCount++;
          console.log(`✅ [${insertedCount}] ${product.name}`);
        }
      } catch (error) {
        console.error(`❌ Failed to insert ${product.name}:`, error.message);
      }
    }
    
    console.log(`\n✨ Seeding completed!\n`);
    console.log(`📊 Statistics:`);
    console.log(`   - Products inserted: ${insertedCount}`);
    console.log(`   - Timestamp: ${new Date().toISOString()}\n`);
    
    console.log('✨ Database is ready for testing!\n');
    
    process.exit(0);
  } catch (error) {
    logger.error('❌ Seeding failed:', error);
    console.error('\n❌ Error:', error.message, '\n');
    process.exit(1);
  }
}

seedDatabase();
