import { chromium } from 'playwright';
import fs from 'fs';

(async () => {
  // 🔧 QUAN TRỌNG: Thay đường dẫn này bằng Chrome profile của bạn
  // Cách tìm: Vào chrome://version/ và copy "Profile Path"
  const userDataDir = 'C:\Users\Admin\AppData\Local\Google\Chrome\User Data';
  const profileName = 'Profile 1'; // hoặc 'Profile 1', 'Profile 2'...

  console.log('⚠️  LƯU Ý: Đóng hết Chrome trước khi chạy script!');
  console.log('📂 Đang dùng profile:', userDataDir);

  const context = await chromium.launchPersistentContext(userDataDir, {
    headless: false,
    channel: 'chrome', // Dùng Chrome thay vì Chromium
    slowMo: 500,
    viewport: { width: 1280, height: 800 },
    args: [
      `--profile-directory=${profileName}`,
      '--disable-blink-features=AutomationControlled' // Ẩn dấu hiệu bot
    ]
  });

  const page = context.pages()[0] || await context.newPage();

  try {
    // 1️⃣ Mở trang sản phẩm
    console.log('🔄 Đang mở trang sản phẩm...');
    await page.goto('https://tiki.vn/acecook-mi-lau-thai-tom-mi-an-lien-lau-thai-tom-mi-lau-thai-huong-vi-tom-mi-the-gioi-mi-acecook-81g-goi-p278137714.html?spid=278137716', { 
      waitUntil: 'domcontentloaded',
      timeout: 30000 
    });
    console.log('✅ Trang đã load (đã đăng nhập sẵn)');
    
    await page.waitForTimeout(3000);

    // 2️⃣ Click "Mua ngay"
    console.log('🔍 Tìm nút "Mua ngay"...');
    const buyNowButton = await page.locator('button:has-text("Mua ngay")').first();
    await buyNowButton.waitFor({ state: 'visible', timeout: 10000 });
    
    await buyNowButton.click();
    console.log('🛒 Đã click "Mua ngay"');

    // 3️⃣ Dừng lại
    console.log('⛔ DỪNG - Không thanh toán');
    await page.waitForTimeout(30000);
    
  } catch (error) {
    console.error('❌ Lỗi:', error.message);
    await page.screenshot({ path: 'error_screenshot.png' });
    await page.waitForTimeout(15000);
  }

  console.log('✅ Hoàn tất!');
})();