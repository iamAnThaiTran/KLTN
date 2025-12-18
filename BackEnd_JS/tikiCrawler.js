
// tikiCrawler.js
import puppeteer from 'puppeteer';

const DEFAULT_CFG = {
  container_selector: '[data-view-id="product_list"]',
  item_selector: 'a[data-view-id="product_list_item"]',
  fallback_item_selector: 'a.product-item',
  max_items: 200,
  max_scroll_rounds: 12,
  scroll_pause_ms: 1200,
  navigation_timeout_ms: 30000,
};

function buildSearchUrl(q) {
  const keyword = encodeURIComponent(q || '');
  return `https://tiki.vn/search?q=${keyword}`;
}

async function autoScroll(page, rounds = 8, pause = 1000) {
  for (let i = 0; i < rounds; i++) {
    await page.evaluate(() => window.scrollBy(0, document.body.scrollHeight));
    await page.waitForTimeout(pause);
  }
}

function parsePriceVND(str) {
  if (!str) return null;
  const digits = str.replace(/[^\d]/g, '');
  if (!digits) return null;
  return Number(digits);
}

async function extractProducts(page, cfg) {
  const items = await page.$$(
    `${cfg.container_selector} ${cfg.item_selector}, ${cfg.container_selector} ${cfg.fallback_item_selector}`
  );
  const products = [];

  for (const el of items) {
    const data = await page.evaluate((node) => {
      const link = node.getAttribute('href') || '';
      const titleEl =
        node.querySelector('h3') ||
        node.querySelector('[data-title]') ||
        node.querySelector('[class*="title"]');

      const priceEl =
        node.querySelector('.price-discount__price') ||
        node.querySelector('[class*="price"]') ||
        node.querySelector('[data-price]');

      const imageEl = node.querySelector('img') || node.querySelector('picture img');

      const title = titleEl ? (titleEl.textContent || '').trim() : '';
      const priceRaw = priceEl ? (priceEl.textContent || '').trim() : '';
      const image =
        imageEl ? (imageEl.getAttribute('src') || imageEl.getAttribute('data-src') || '').trim() : '';

      const absoluteLink = link.startsWith('http') ? link : `https://tiki.vn${link}`;

      return { title, priceRaw, link: absoluteLink, image };
    }, el);

    if (data?.title || data?.link) products.push(data);
  }

  return products;
}

/**
 * Crawl Tiki search page with infinite scroll.
 * @param {Object} params { q, maxItems, maxScrollRounds }
 * @returns {Array<{name, price, priceRaw, url, image}>}
 */
export async function crawlTikiSearch({ q, maxItems, maxScrollRounds } = {}) {
  const cfg = {
    ...DEFAULT_CFG,
    max_items: maxItems || DEFAULT_CFG.max_items,
    max_scroll_rounds: maxScrollRounds || DEFAULT_CFG.max_scroll_rounds,
  };

  const url = buildSearchUrl(q);

  const browser = await puppeteer.launch({
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  try {
    const page = await browser.newPage();
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    );
    await page.setViewport({ width: 1366, height: 900 });
    page.setDefaultNavigationTimeout(cfg.navigation_timeout_ms);

    await page.goto(url, { waitUntil: 'networkidle2' });
    await page.waitForSelector(cfg.container_selector, { timeout: 15000 }).catch(() => {});

    let allProducts = [];
    let lastCount = 0;

    for (let round = 1; round <= cfg.max_scroll_rounds; round++) {
      await autoScroll(page, 1, cfg.scroll_pause_ms);

      await page
        .waitForFunction(
          (sel) => document.querySelectorAll(sel).length > 0,
          {},
          `${cfg.container_selector} ${cfg.item_selector}, ${cfg.container_selector} ${cfg.fallback_item_selector}`
        )
        .catch(() => {});

      const products = await extractProducts(page, cfg);

      const map = new Map();
      [...allProducts, ...products].forEach((p) => {
        const key = (p.link || '') + '|' + (p.title || '');
        if (!map.has(key)) map.set(key, p);
      });
      allProducts = [...map.values()];

      if (allProducts.length === lastCount) break;
      lastCount = allProducts.length;

      if (allProducts.length >= cfg.max_items) break;
    }

    const normalized = allProducts.map((p, idx) => ({
      id: p.link || String(idx),
      name: p.title || 'Không có tên',
      price: parsePriceVND(p.priceRaw),
      priceRaw: p.priceRaw,
      url: p.link,
      image: p.image || null,
    }));

    return normalized;
  } finally {
    await browser.close();
  }
}
