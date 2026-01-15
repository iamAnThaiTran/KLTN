import { LazadaCrawler } from './src/crawlers/lazada.crawler.js';

async function test() {
  console.log('🧪 Testing Lazada Crawler...\n');
  
  const crawler = new LazadaCrawler();
  console.log('🕷️ Crawling for "laptop"...');
  
  const products = await crawler.crawl('laptop');
  
  console.log(`\n✅ Found ${products.length} products\n`);
  
  if (products.length > 0) {
    console.log('Sample products:');
    products.slice(0, 3).forEach((p, i) => {
      console.log(`\n${i + 1}. ${p.title}`);
      console.log(`   Price: ₫${p.price}`);
      console.log(`   Image: ${p.image}`);
      console.log(`   Link: ${p.link}`);
      console.log(`   Rating: ${p.rating}⭐ (${p.reviews} reviews)`);
      console.log(`   Discount: ${p.discount}%`);
    });
  }
  
  console.log('\n✨ Test completed!');
}

test().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});
