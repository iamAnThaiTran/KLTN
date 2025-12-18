import express from "express";
import { crawlSite } from "./testPuppeteer.js";
import cors from 'cors';
import bodyParser from 'body-parser';
import { productNameHandler } from "./recomandetion/testPhi.js";


const app = express();
const PORT = process.env.PORT || 3000;
app.use(cors()); 
// app.use(bodyParser.json());

app.get("/crawl", async (req, res) => {
    const config = {
        url: "https://tiki.vn/search?q=iphone",
        product_selector: "a.product-item",
        name_selector: "h3.sc-68e86366-8.dDeapS",
        price_selector: "div.price-discount__price",
        product_link: "",
        next_button_selector: "a.arrow", // kiểm tra selector thực tế
        max_pages: 1, 
    };

    try {
        
const { q, message } = req.query;

    // Ưu tiên q nếu có; nếu không có thì suy từ message
    const productName = q ? String(q).trim() : await getProductNameFromMessage(message);

    if (!productName) {
      return res.status(400).json({ success: false, error: "Thiếu tên sản phẩm (?q= hoặc ?message=)" });
    }

        const data = await crawlSite(config);
        res.json({ success: true, data: data });
        // console.log(data);
    } catch (error) {
        res.status(500).json({ success: false, error: error.message });
    }
});



export async function getProductNameFromMessage(message) {
  const q = String(message || "").trim();
  if (!q) {
    throw new Error("Thiếu 'message' để suy tên sản phẩm.");
  }
  const { product_name } = await getRecommendProductName(q);
  const name = String(product_name || "").trim();
  if (!name) {
    throw new Error("Model không trả về tên sản phẩm hợp lệ.");
  }

  return name; 
}



app.get("/productname", productNameHandler);

app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});

