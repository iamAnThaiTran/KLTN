import puppeteer from "puppeteer";

const config = {
  url: "https://www.lazada.vn/catalog/?q=b%E1%BB%99t+m%C3%AC",
  product_selector: 'div[data-qa-locator="product-item"]',
  name_selector: ".RfADt a",
  price_selector: ".aBrP0 .ooOxS",
  next_button_selector: "li.ant-pagination-next a",
  max_pages: 2,
};

export async function lazadaCrawlSite(config) {
  const browser = await puppeteer.launch({ headless: true });
  const page = await browser.newPage();
  
  // Thêm user-agent để tránh bị render khác
  await page.setUserAgent("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36");

  await page.goto(config.url, { waitUntil: "networkidle2" });

  const response = [];

  // Hàm scroll mượt hơn để trigger lazy-load ảnh tốt
  async function autoScroll(page) {
  await page.evaluate(async () => {
    await new Promise((resolve) => {
      let totalHeight = 0;
      const distance = 800;
      const timer = setInterval(() => {
        const scrollHeight = document.body.scrollHeight;
        window.scrollBy(0, distance);
        totalHeight += distance;
        if (totalHeight >= scrollHeight - window.innerHeight) {
          clearInterval(timer);
          resolve();
        }
      }, 2000); // delay giữa các scroll để ảnh load
    });
  });
  await page.waitForTimeout(3000); // chờ lâu hơn để ảnh lazy load
}
  let pageIndex = 1;
  while (pageIndex <= config.max_pages) {
    await autoScroll(page); // scroll đầy đủ trang

    await page.waitForSelector(config.product_selector, { timeout: 15000 });
    const products = await page.$$(config.product_selector);

    console.log(`Trang ${pageIndex} có ${products.length} sản phẩm`);

    for (let product of products) {
      const titleElement = await product.$(config.name_selector);
      const title = titleElement
        ? await page.evaluate(el => el.innerText.trim(), titleElement)
        : "Không có tên";

      const priceElement = await product.$(config.price_selector);
      const price = priceElement
        ? await page.evaluate(el => el.innerText.trim(), priceElement)
        : "Không có giá";

      const link = await page.evaluate(el => {
        const a = el.querySelector("a");
        return a ? a.href : "Không có link";
      }, product);

      let image = "Không có ảnh";
      const imgElement = await product.$("img");
      if (imgElement) {
        const dataSrc = await page.evaluate(img => img.getAttribute("data-src"), imgElement);
        const srcset = await page.evaluate(img => img.getAttribute("srcset"), imgElement);
        const src = await page.evaluate(img => img.src, imgElement); // src thường là placeholder cuối cùng

        if (dataSrc && dataSrc.startsWith("https://")) {
          image = dataSrc;
        } else if (srcset && srcset.trim()) {
          // Lấy URL đầu tiên trong srcset (thường chất lượng tốt nhất hoặc mặc định)
          const parts = srcset.split(",");
          const firstSrc = parts[0].trim().split(" ")[0];
          if (firstSrc.startsWith("https://")) {
            image = firstSrc;
          }
        } else if (src && src.startsWith("https://") && !src.includes("placeholder") && src.length > 50) {
          // src dài và không chứa placeholder mới là ảnh thật
          image = src;
        }
      }

      response.push({ title, price, link, image });
    }

    // Chuyển trang
    const nextButton = await page.$(config.next_button_selector);
    if (!nextButton || pageIndex >= config.max_pages) break;

    await Promise.all([
      nextButton.click(),
      page.waitForNavigation({ waitUntil: "networkidle0" }),
    ]);
    await page.waitForTimeout(1000);
    pageIndex++;
  }

  await browser.close();
  console.log(JSON.stringify(response, null, 2));
  return response.filter(item => {
    return item.image != "Không có ảnh"
  });
}

// run test
lazadaCrawlSite(config);