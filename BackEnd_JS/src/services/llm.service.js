 import fetch from 'node-fetch';
import { logger } from '../utils/logger.js';

/**
 * LLM Service - UPDATED
 * Chỉ dùng cho các task enhancement, KHÔNG dùng cho intent analysis
 * 
 * PHÂN BIỆT:
 * - IntentService: Phân tích ý định, quyết định search hay clarify
 * - LLMService: Enhance kết quả (explain, summarize, compare)
 */
class LLMService {
  constructor() {
    this.ollamaHost = process.env.OLLAMA_HOST || 'http://localhost:11434';
    this.ollamaUrl = `${this.ollamaHost}/api/chat`;
    this.modelName = process.env.LLM_MODEL || 'qwen2.5';
  }

  /**
   * Call Ollama API
   */
  async callOllama(messages, options = {}) {
    try {
      const payload = {
        model: this.modelName,
        temperature: options.temperature || 0.3,
        top_p: options.top_p || 0.5,
        stream: false,
        messages,
        ...options
      };

      const response = await fetch(this.ollamaUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Ollama API error: ${errorText}`);
      }

      const data = await response.json();
      return String(data?.message?.content || '').trim();

    } catch (error) {
      logger.error('[LLMService] API call failed:', error);
      throw error;
    }
  }

  /**
   * Generate product recommendation explanation
   * Giải thích tại sao sản phẩm phù hợp với query
   * 
   * @param {object} product - Product data
   * @param {string} userQuery - Original user query
   * @param {object} constraints - Extracted constraints
   * @returns {Promise<string>} - Explanation
   */
  async generateRecommendationReason(product, userQuery, constraints = {}) {
    try {
      logger.info(`[LLMService] Generating reason for: ${product.title}`);

      const systemPrompt = `
Bạn là trợ lý gợi ý sản phẩm. Nhiệm vụ: giải thích ngắn gọn (2-3 câu) 
tại sao sản phẩm này phù hợp với nhu cầu của khách hàng.

Quy tắc:
- Viết bằng tiếng Việt tự nhiên
- Tập trung vào điểm mạnh liên quan đến nhu cầu
- Không quá dài dòng
- Không dùng từ ngữ marketing phóng đại
`.trim();

      const userPrompt = `
Nhu cầu khách hàng: "${userQuery}"

Ràng buộc:
${JSON.stringify(constraints, null, 2)}

Sản phẩm:
- Tên: ${product.title}
- Giá: ${product.price.toLocaleString('vi-VN')} VNĐ
- Cấu hình: ${JSON.stringify(product.specs, null, 2)}
- Đánh giá: ${product.rating}/5
- Tags: ${product.tags?.join(', ') || 'N/A'}

Hãy giải thích ngắn gọn tại sao sản phẩm này phù hợp.
`.trim();

      const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ];

      const explanation = await this.callOllama(messages, {
        temperature: 0.5,
        max_tokens: 150
      });

      logger.info(`[LLMService] Generated explanation`);
      return explanation;

    } catch (error) {
      logger.error('[LLMService] Error generating explanation:', error);
      return `Sản phẩm phù hợp với yêu cầu "${userQuery}" của bạn.`;
    }
  }

  /**
   * Summarize product reviews
   * Tóm tắt đánh giá của người dùng
   * 
   * @param {array} reviews - Array of review texts
   * @returns {Promise<string>} - Summary
   */
  async summarizeReviews(reviews) {
    try {
      if (!reviews || reviews.length === 0) {
        return 'Chưa có đánh giá';
      }

      logger.info(`[LLMService] Summarizing ${reviews.length} reviews`);

      const systemPrompt = `
Bạn là trợ lý tóm tắt đánh giá sản phẩm.
Nhiệm vụ: tóm tắt ngắn gọn (3-4 câu) nội dung chính từ các đánh giá.

Tập trung vào:
- Điểm mạnh được nhắc nhiều
- Điểm yếu (nếu có)
- Đánh giá tổng quan

Viết bằng tiếng Việt, ngắn gọn, khách quan.
`.trim();

      const reviewTexts = reviews
        .slice(0, 20) // Limit to 20 reviews
        .map((r, i) => `${i + 1}. ${r}`)
        .join('\n');

      const userPrompt = `
Đây là các đánh giá của khách hàng:

${reviewTexts}

Hãy tóm tắt nội dung chính.
`.trim();

      const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ];

      const summary = await this.callOllama(messages, {
        temperature: 0.3,
        max_tokens: 200
      });

      return summary;

    } catch (error) {
      logger.error('[LLMService] Error summarizing reviews:', error);
      return 'Không thể tóm tắt đánh giá';
    }
  }

  /**
   * Compare products
   * So sánh nhiều sản phẩm và đưa ra nhận xét
   * 
   * @param {array} products - Array of products to compare
   * @param {string} userQuery - Original query
   * @returns {Promise<string>} - Comparison text
   */
  async compareProducts(products, userQuery = '') {
    try {
      if (!products || products.length < 2) {
        return 'Cần ít nhất 2 sản phẩm để so sánh';
      }

      logger.info(`[LLMService] Comparing ${products.length} products`);

      const systemPrompt = `
Bạn là trợ lý so sánh sản phẩm.
Nhiệm vụ: so sánh các sản phẩm dựa trên nhu cầu của khách hàng.

Cấu trúc output:
1. Tổng quan ngắn gọn
2. So sánh các điểm chính (giá, cấu hình, điểm mạnh/yếu)
3. Gợi ý cho từng trường hợp sử dụng

Viết bằng tiếng Việt, súc tích, dễ hiểu.
`.trim();

      const productsInfo = products
        .slice(0, 5) // Max 5 products
        .map((p, i) => `
${i + 1}. ${p.title}
   - Giá: ${p.price.toLocaleString('vi-VN')} VNĐ
   - Cấu hình: ${JSON.stringify(p.specs)}
   - Đánh giá: ${p.rating}/5
        `.trim())
        .join('\n\n');

      const userPrompt = `
Nhu cầu: "${userQuery}"

Các sản phẩm cần so sánh:
${productsInfo}

Hãy so sánh và đưa ra nhận xét.
`.trim();

      const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ];

      const comparison = await this.callOllama(messages, {
        temperature: 0.4,
        max_tokens: 400
      });

      return comparison;

    } catch (error) {
      logger.error('[LLMService] Error comparing products:', error);
      return 'Không thể so sánh sản phẩm';
    }
  }

  /**
   * Extract product specifications from description
   * Parse thông số kỹ thuật từ text tự do
   * 
   * @param {string} description - Product description
   * @returns {Promise<object>} - Structured specs
   */
  async extractSpecs(description) {
    try {
      logger.info('[LLMService] Extracting specs from description');

      const systemPrompt = `
Trích xuất thông số kỹ thuật từ mô tả sản phẩm.
Trả về JSON với các trường: cpu, ram, storage, screen, gpu, battery, os.
Nếu không tìm thấy thông tin, để giá trị null.
`.trim();

      const userPrompt = `
Mô tả sản phẩm:
${description}

Trích xuất thông số kỹ thuật.
`.trim();

      const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ];

      const result = await this.callOllama(messages, {
        format: 'json',
        temperature: 0.1
      });

      const specs = JSON.parse(result);
      return specs;

    } catch (error) {
      logger.error('[LLMService] Error extracting specs:', error);
      return {};
    }
  }

  /**
   * Generate product description
   * Tạo mô tả sản phẩm từ specs
   * 
   * @param {object} specs - Product specifications
   * @param {string} productName - Product name
   * @returns {Promise<string>} - Description
   */
  async generateDescription(specs, productName) {
    try {
      logger.info('[LLMService] Generating product description');

      const systemPrompt = `
Viết mô tả sản phẩm ngắn gọn (2-3 câu) từ thông số kỹ thuật.
Tập trung vào điểm nổi bật, viết theo phong cách tự nhiên.
Không dùng từ ngữ marketing phóng đại.
`.trim();

      const userPrompt = `
Sản phẩm: ${productName}
Thông số: ${JSON.stringify(specs, null, 2)}

Viết mô tả ngắn gọn.
`.trim();

      const messages = [
        { role: 'system', content: systemPrompt },
        { role: 'user', content: userPrompt }
      ];

      const description = await this.callOllama(messages, {
        temperature: 0.5,
        max_tokens: 150
      });

      return description;

    } catch (error) {
      logger.error('[LLMService] Error generating description:', error);
      return '';
    }
  }
}

export const llmService = new LLMService();