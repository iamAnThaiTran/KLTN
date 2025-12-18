
// recommend.module.js
import fetch from "node-fetch";

// Cho phép override host qua biến môi trường, mặc định localhost:11434
const OLLAMA_HOST = process.env.OLLAMA_HOST || "http://localhost:11434";
const OLLAMA_CHAT_URL = `${OLLAMA_HOST}/api/chat`;

// Mặc định dùng model nhẹ, đa ngôn ngữ, tiếng Việt ổn
// Bạn có thể set: MODEL_NAME=qwen3:4b hoặc qwen2.5:3b ở biến môi trường
const MODEL_NAME = process.env.MODEL_NAME || "qwen2.5";

// System prompt: ràng buộc chặt chẽ output JSON
const SYSTEM_PROMPT = `
Bạn là trợ lý gợi ý sản phẩm. Bạn là trợ lý tiếng Việt. Chỉ tạo tên sản phẩm bằng TIẾNG VIỆT THUẦN, không dùng ký tự Trung, không dùng tiếng Anh. Nếu đầu vào đa ngữ, vẫn trả về tiếng Việt.
Định dạng: chỉ một tên ngắn gọn, không có câu giải thích. Trả về DUY NHẤT JSON hợp lệ:
{"product_name":"<tên sản phẩm tiếng Việt ngắn gọn, cụ thể>"}
- KHÔNG giải thích.
- KHÔNG thêm trường khác.
- KHÔNG lặp lại schema mẫu.
- Nếu không đủ thông tin, vẫn suy luận tên cụ thể, ngắn gọn, sát nhu cầu.
- Ngôn ngữ trả về là tiếng Việt tự nhiên.
`.trim();

// Few-shot để mô hình học theo mẫu Input/Output
const FEWSHOT = `
Ví dụ:
Input: "cần màn hình 27 inch, IPS, 2K, 75Hz"
Output:
{"product_name":"Màn hình 27'' IPS 2K 75Hz – ProView 27Q"}

Input: "tai nghe chống ồn, pin lâu, có mic học online"
Output:
{"product_name":"Tai nghe Bluetooth ANC pin 40h có mic – StudyPro S1"}

Input: "tôi cần mua đồ tên là xx"
Output:
{"product_name":"xx"}


`.trim();

function buildUserContent(userText) {
  return `
${FEWSHOT}

Input: "${userText}"
Output:
{"product_name":"<điền duy nhất tên sản phẩm phù hợp>"}
`.trim();
}

/**
 * Hàm core: gọi Ollama để lấy tên sản phẩm.
 * @param {string} query - mô tả nhu cầu của khách hàng
 * @returns {Promise<{product_name: string}>}
 */
export async function getRecommendProductName(query) {
  const messages = [
    { role: "system", content: SYSTEM_PROMPT },
    { role: "user", content: buildUserContent(query) },
  ];

  const payload = {
    model: MODEL_NAME,
    format: "json",
    temperature: 0,
    top_p: 0.1,
    seed: 42,
    stream: false,
    messages,
  };

  const r = await fetch(OLLAMA_CHAT_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!r.ok) {
    const text = await r.text();
    throw new Error(`Lỗi gọi Ollama: ${text}`);
  }

  const data = await r.json();
  const out = String(data?.message?.content || "").trim();

  // Parse JSON nghiêm ngặt, fallback nếu cần
  let result;
  try {
    result = JSON.parse(out);
  } catch {
    const m = out.match(/"product_name"\s*:\s*"([^"]+)"/);
    result = m ? { product_name: m[1] } : { product_name: "" };
  }

  const name = String(result.product_name || "").trim();
  if (!name) {
    throw new Error(`Model không trả về 'product_name' hợp lệ. raw="${out}"`);
  }

  return { product_name: name };
}

/**
 * (Tuỳ chọn) Export sẵn một Express handler GET /productname?q=...
 * Để bạn chỉ cần app.get("/productname", productNameHandler)
 */
export async function productNameHandler(req, res) {
  try {
    const q = String(req.query?.q || "").trim();
    if (!q) {
      return res.status(400).json({ error: "Thiếu query param 'q'" });
    }
    const result = await getRecommendProductName(q);
    return res.json(result); // { product_name }
  } catch (error) {
    console.error(error);
    return res.status(500).json({ error: error.message });
  }
}