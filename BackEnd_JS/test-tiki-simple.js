import { TikiCrawler } from './src/crawlers/tiki.crawler.js';

async function test() {
  console.log('🧪 Testing Tiki Crawler...\n');
  
  const crawler = new TikiCrawler();
  console.log('🕷️ Crawling for "laptop"...');
  
  const products = await crawler.crawl('laptop');
  
  console.log(`\n✅ Found ${products.length} products\n`);
  
  if (products.length > 0) {
    console.log('Sample products:');
    products.slice(0, 3).forEach((p, i) => {
      console.log(`\n${i + 1}. ${p.title}`);
      console.log(`   Price: ₫${p.price}`);
      console.log(`   Discount: ${p.discount}%`);
      console.log(`   Brand: ${p.brand}`);
      console.log(`   Rating: ${p.rating}⭐`);
      console.log(`   Sold: ${p.sold}`);
      console.log(`   Image: ${p.image}`);
      console.log(`   Link: ${p.link}`);
    });
  }
  
  console.log('\n✨ Test completed!');
  process.exit(0);
}

test().catch(err => {
  console.error('❌ Error:', err.message);
  process.exit(1);
});

