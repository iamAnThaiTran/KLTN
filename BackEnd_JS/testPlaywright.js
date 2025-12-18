import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

const shopeeConfig = {
    searchKeyword: "bột mì",
    baseUrl: "https://shopee.vn",
    maxPages: 3,
    sessionFile: './shopee-session.json', // Lưu session
    needLogin: true // Có cần đăng nhập không
};

export async function crawlShopeeWithLogin(config = shopeeConfig) {
    console.log('🚀 Khởi động Playwright với Login...');

    const browser = await chromium.launch({
        headless: false, // Phải false để đăng nhập thủ công
        args: [
            '--disable-blink-features=AutomationControlled',
            '--no-sandbox',
            '--disable-setuid-sandbox'
        ]
    });

    let context;
    const allProducts = [];

    try {
        // Kiểm tra xem có session cũ không
        if (fs.existsSync(config.sessionFile)) {
            console.log('📂 Tìm thấy session cũ, đang load...');
            const sessionData = JSON.parse(fs.readFileSync(config.sessionFile, 'utf-8'));
            
            // Tạo context từ session cũ
            context = await browser.newContext({
                storageState: sessionData,
                viewport: { width: 1920, height: 1080 },
                userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale: 'vi-VN',
                timezoneId: 'Asia/Ho_Chi_Minh'
            });
            console.log('✅ Đã load session thành công!');
        } else {
            console.log('🆕 Không có session, tạo mới...');
            context = await browser.newContext({
                viewport: { width: 1920, height: 1080 },
                userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                locale: 'vi-VN',
                timezoneId: 'Asia/Ho_Chi_Minh'
            });
        }

        const page = await context.newPage();

        // Bước 1: Kiểm tra xem đã đăng nhập chưa
        console.log('🔐 Kiểm tra trạng thái đăng nhập...');
        await page.goto(config.baseUrl, { waitUntil: 'domcontentloaded' });
        await sleep(3000);

        // Kiểm tra có nút đăng nhập không
        const loginButton = await page.$('a[class*="navbar__link--account"]');
        const isLoggedIn = !loginButton || !(await loginButton.textContent()).includes('Đăng nhập');

        if (!isLoggedIn && config.needLogin) {
            console.log('\n⚠️  CHƯA ĐĂNG NHẬP - Cần đăng nhập thủ công!');
            console.log('📌 Hướng dẫn:');
            console.log('   1. Trình duyệt sẽ mở ra');
            console.log('   2. Click "Đăng nhập" ở góc trên bên phải');
            console.log('   3. Đăng nhập bằng SĐT/Email hoặc QR Code');
            console.log('   4. Sau khi đăng nhập xong, quay lại terminal và nhấn ENTER');
            console.log('\n⏳ Đợi bạn đăng nhập...\n');

            // Đợi user đăng nhập thủ công
            await waitForEnter();

            // Lưu session sau khi đăng nhập
            console.log('💾 Đang lưu session...');
            const sessionData = await context.storageState();
            fs.writeFileSync(config.sessionFile, JSON.stringify(sessionData, null, 2));
            console.log('✅ Đã lưu session vào:', config.sessionFile);
            console.log('   Lần sau sẽ tự động đăng nhập!\n');
        } else {
            console.log('✅ Đã đăng nhập rồi!\n');
        }

        // Bước 2: Bắt đầu crawl
        console.log(`🔍 Tìm kiếm: "${config.searchKeyword}"`);
        const searchUrl = `${config.baseUrl}/search?keyword=${encodeURIComponent(config.searchKeyword)}`;
        await page.goto(searchUrl, { waitUntil: 'domcontentloaded' });
        await sleep(randomNumber(3000, 5000));

        // Scroll để load sản phẩm
        await smoothScroll(page, 1000);
        await sleep(randomNumber(2000, 3000));

        // Bước 3: Crawl từng trang
        let currentPage = 1;

        while (currentPage <= config.maxPages) {
            console.log(`\n📄 Đang crawl trang ${currentPage}/${config.maxPages}...`);

            // Kiểm tra có bị yêu cầu đăng nhập giữa chừng không
            const loginRequired = await page.$('div[class*="login"]');
            if (loginRequired) {
                console.log('⚠️  Shopee yêu cầu đăng nhập lại!');
                console.log('💡 Tips: Hãy chờ 5-10 phút rồi chạy lại');
                break;
            }

            // Đợi sản phẩm load
            try {
                await page.waitForSelector('div[data-sqe="item"]', { 
                    timeout: 10000,
                    state: 'visible'
                });
            } catch (error) {
                console.log('⚠️ Không tìm thấy sản phẩm');
                break;
            }

            await sleep(randomNumber(1000, 2000));

            // Lấy thông tin sản phẩm
            const products = await page.evaluate(() => {
                const items = document.querySelectorAll('div[data-sqe="item"]');
                const results = [];

                items.forEach((item) => {
                    try {
                        const linkElement = item.querySelector('a');
                        const productLink = linkElement?.href || '';

                        const imgElement = item.querySelector('img');
                        let imageUrl = '';
                        if (imgElement) {
                            imageUrl = imgElement.src || imgElement.dataset?.src || '';
                        }

                        const nameElement = item.querySelector('div[data-sqe="name"]');
                        const productName = nameElement?.innerText?.trim() || 'Không có tên';

                        let price = 'Không có giá';
                        const priceSelectors = ['span.Jz5Nh3', 'div.zp9xm9'];
                        
                        for (const selector of priceSelectors) {
                            const priceElement = item.querySelector(selector);
                            if (priceElement && priceElement.innerText) {
                                price = priceElement.innerText.trim();
                                break;
                            }
                        }

                        const ratingElement = item.querySelector('div[class*="rating"]');
                        const rating = ratingElement?.innerText?.trim() || '';

                        const soldElement = item.querySelector('div[class*="sold"]');
                        const sold = soldElement?.innerText?.trim() || '';

                        if (productLink && productName !== 'Không có tên') {
                            results.push({
                                title: productName,
                                price: price,
                                link: productLink,
                                image: imageUrl,
                                rating: rating,
                                sold: sold
                            });
                        }
                    } catch (error) {
                        console.error('Lỗi parse sản phẩm:', error);
                    }
                });

                return results;
            });

            console.log(`✅ Đã lấy ${products.length} sản phẩm`);
            allProducts.push(...products);

            // Hiển thị mẫu
            if (products.length > 0) {
                console.log(`📦 Sản phẩm đầu: ${products[0].title}`);
                console.log(`   Giá: ${products[0].price}`);
            }

            // Sang trang tiếp theo
            if (currentPage < config.maxPages) {
                const nextButton = await page.$('button.shopee-icon-button--right');
                
                if (!nextButton) {
                    console.log('🛑 Không có nút next');
                    break;
                }

                const isDisabled = await nextButton.evaluate(btn => {
                    return btn.disabled || btn.classList.contains('shopee-button-outline--disabled');
                });

                if (isDisabled) {
                    console.log('🛑 Hết trang');
                    break;
                }

                await nextButton.scrollIntoViewIfNeeded();
                await sleep(randomNumber(1000, 2000));

                console.log('👆 Chuyển trang...');
                await nextButton.click();
                await page.waitForLoadState('domcontentloaded');
                await sleep(randomNumber(4000, 6000));

                await smoothScroll(page, 1000);
                await sleep(randomNumber(2000, 3000));

                currentPage++;
            } else {
                break;
            }
        }

        console.log(`\n✨ Hoàn thành! Tổng: ${allProducts.length} sản phẩm`);

    } catch (error) {
        console.error('❌ Lỗi:', error.message);
    } finally {
        await browser.close();
    }

    return allProducts;
}

// Helper functions
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

function randomNumber(min, max) {
    return Math.floor(Math.random() * (max - min + 1)) + min;
}

async function smoothScroll(page, distance) {
    await page.evaluate((dist) => {
        return new Promise((resolve) => {
            let totalHeight = 0;
            const step = 100;
            const delay = 100;

            const timer = setInterval(() => {
                window.scrollBy(0, step);
                totalHeight += step;

                if (totalHeight >= dist) {
                    clearInterval(timer);
                    resolve();
                }
            }, delay);
        });
    }, distance);
}

// Đợi user nhấn Enter
function waitForEnter() {
    return new Promise((resolve) => {
        process.stdin.once('data', () => {
            resolve();
        });
    });
}

// Chạy thử
if (import.meta.url === `file://${process.argv[1]}`) {
    console.log('🎯 Shopee Crawler với Login\n');
    
    crawlShopeeWithLogin()
        .then(products => {
            console.log('\n📊 KẾT QUẢ CUỐI CÙNG:');
            console.log(`📦 Tổng: ${products.length} sản phẩm`);
            
            if (products.length > 0) {
                console.log('\n🔝 Top 5 sản phẩm:');
                products.slice(0, 5).forEach((p, i) => {
                    console.log(`${i+1}. ${p.title}`);
                    console.log(`   💰 ${p.price} | ⭐ ${p.rating} | 📈 ${p.sold}`);
                });
            }
            
            // Lưu kết quả
            fs.writeFileSync('shopee_products.json', JSON.stringify(products, null, 2));
            console.log('\n💾 Đã lưu kết quả vào: shopee_products.json');
        })
        .catch(console.error);
}