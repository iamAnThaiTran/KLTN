import puppeteer from "puppeteer";

const config = {
    url: "https://tiki.vn/search?q=b%E1%BB%99t%20m%C3%AC",
    product_selector: "a.product-item",
    name_selector: "h3.sc-68e86366-8.dDeapS",
    price_selector: "div.price-discount__price",
    product_link: "",
    next_button_selector: "a.arrow", // kiểm tra selector thực tế
    max_pages: 2, // thêm giới hạn số trang
};

export async function crawlSite(config) {
    const browser = await puppeteer.launch({ headless: true });
    const page = await browser.newPage();
    await page.goto(config.url, { waitUntil: "networkidle2" });
    const response = [];

    let pageIndex = 1;
    while (pageIndex <= config.max_pages) {
        await page.waitForSelector(config.product_selector);
        const products = await page.$$(config.product_selector);

        console.log(`Trang ${pageIndex} có ${products.length} sản phẩm`);

        for (let product of products) {
            const titleElement = await product.$(config.name_selector);
            const priceElement = await product.$(config.price_selector);
            const imgElement = await product.$("img");

            // console.log("imgElement tồn tại?", !!imgElement);

            let image = "Không có ảnh";

            if (imgElement) {
                const srcset = await page.evaluate(
                    (img) => img.srcset,
                    imgElement
                );
                const src = await page.evaluate((img) => img.src, imgElement);
                const alt = await page.evaluate((img) => img.alt, imgElement);

                // console.log("srcset:", srcset);
                // console.log("src:", src);
                // console.log("alt:", alt);

                if (srcset && srcset.trim() !== "") {
                    const firstUrl = srcset.split(",")[0].trim().split(" ")[0];
                    image = firstUrl;
                } else if (src && src.startsWith("http")) {
                    image = src;
                }

                // console.log("Link ảnh lấy được:", image);
            } else {
                console.log("Không tìm thấy thẻ <img> nào trong product này");
            }
            const title = titleElement
                ? await page.evaluate((el) => el.innerText, titleElement)
                : "Không có tên";
            const price = priceElement
                ? await page.evaluate((el) => el.innerText, priceElement)
                : "Không có giá";

            const link = await page.evaluate((el) => el.href, product);

            // console.log(`Tên: ${title}`);
            // console.log(`Giá: ${price}`);
            // console.log(`Link: ${link}`);
            // console.log(`ImageElement: ${image}`);
            // console.log("-".repeat(40));

            response.push({
                title: title,
                price: price,
                link: link,
                image: image, 
            });
        }

        const nextButton = await page.$(config.next_button_selector);
        if (!nextButton) break;

        const isDisabled = await page.evaluate((el) => el.disabled, nextButton);
        if (isDisabled) break;

        await nextButton.click();
        await new Promise((resolve) => setTimeout(resolve, 2000));
        pageIndex++;
    }

    await browser.close();
    return response;
}
