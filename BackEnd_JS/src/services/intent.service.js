import fetch from 'node-fetch';
import { logger } from '../utils/logger.js';

/**
 * Intent Analysis Service
 * Sử dụng SLM để phân tích ý định người dùng
 * KHÔNG search DB, chỉ quyết định: "đủ rõ chưa?" + "thiếu gì?"
 */
class IntentService {
  constructor() {
    this.ollamaHost = process.env.OLLAMA_HOST || 'http://localhost:11434';
    this.ollamaUrl = `${this.ollamaHost}/api/chat`;
    this.modelName = process.env.INTENT_MODEL || 'qwen2.5';
  }

  /**
   * System prompt cho Intent Analysis
   */
  getSystemPrompt() {
    return `
Bạn là Intent Analysis SLM cho hệ thống gợi ý sản phẩm e-commerce.

NHIỆM VỤ CỦA BẠN:
1. Phân tích query và lịch sử tìm kiếm của user
2. Quyết định intent đã đủ rõ để search DB chưa
3. Trích xuất các ràng buộc có cấu trúc (structured constraints)
4. Xác định thông tin còn thiếu (nếu có)
5. Trả về CHỈ JSON hợp lệ theo schema quy định

QUY TẮC VỀ INTENT STATUS:
- "clear": User đã chỉ định rõ LOẠI SẢN PHẨM (category). Có thể thiếu các chi tiết khác (usage, brand, price) nhưng vẫn có thể search.
- "unclear": CHỈ khi user chưa nêu rõ LOẠI SẢN PHẨM hoặc query quá mơ hồ. VÍ DỤ:
  - "bao cao su" → CLEAR (rõ category, có thể search)
  - "sản phẩm tốt" → UNCLEAR (quá mơ hồ, không rõ category)
  - "laptop 5 triệu" → CLEAR (rõ category: laptop)
  - "tôi muốn mua gì đó" → UNCLEAR (không rõ cụ thể)

QUY TẮC CHUNG:
- KHÔNG bao giờ trả về text tự nhiên ngoài JSON
- KHÔNG bao giờ gợi ý sản phẩm cụ thể
- Dùng tiếng Việt cho tất cả giá trị text
- Nếu thiếu chi tiết nhưng category rõ → VẪN là "clear", search DB trước
- CHỈ đánh dấu "unclear" nếu THỰC SỰ không rõ user muốn gì

SCHEMA BẮT BUỘC:
{
  "intent_status": "clear | unclear",
  "intent_summary": "Tóm tắt ý định user bằng tiếng Việt",
  "extracted_constraints": {
    "category": "loại sản phẩm nếu rõ, null nếu không",
    "price_min": số hoặc null,
    "price_max": số hoặc null,
    "usage": "mục đích sử dụng nếu rõ, null nếu không",
    "brand": "thương hiệu nếu rõ, null nếu không",
    "priority": ["yếu tố ưu tiên nếu có"]
  },
  "missing_constraints": ["danh sách ràng buộc còn thiếu"],
  "follow_up_questions": [
    {
      "key": "usage",
      "question": "Câu hỏi làm rõ",
      "options": ["tùy chọn 1", "tùy chọn 2"]
    }
  ],
  "ui_state": "SEARCH_RESULT | INTENT_CLARIFICATION"
}
`.trim();
  }

  /**
   * Tạo user prompt động
   */
  buildUserPrompt(query, searchHistory = [], availableFilters = {}) {
    return `
User query:
"${query}"

Lịch sử tìm kiếm:
${searchHistory.length > 0 ? searchHistory.map((h, i) => `${i + 1}. "${h}"`).join('\n') : 'Chưa có'}

Bộ lọc khả dụng:
${JSON.stringify(availableFilters, null, 2)}

Hãy phân tích và trả về JSON theo schema đã định.
`.trim();
  }

  /**
   * Phân tích ý định người dùng
   * @param {string} query - Câu hỏi của user
   * @param {string[]} searchHistory - Lịch sử tìm kiếm
   * @param {object} availableFilters - Các bộ lọc có sẵn
   * @returns {Promise<object>} - Intent analysis result
   */
  async analyzeIntent(query, searchHistory = [], availableFilters = {}) {
    try {
      logger.info(`[IntentService] Analyzing intent: "${query}"`);

      const messages = [
        { role: 'system', content: this.getSystemPrompt() },
        { 
          role: 'user', 
          content: this.buildUserPrompt(query, searchHistory, availableFilters) 
        }
      ];

      const payload = {
        model: this.modelName,
        format: 'json',
        temperature: 0.1,
        top_p: 0.3,
        seed: 42,
        stream: false,
        messages
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
      const rawOutput = String(data?.message?.content || '').trim();

      logger.info(`[IntentService] Raw output: ${rawOutput.substring(0, 200)}...`);

      // Parse JSON nghiêm ngặt
      let result;
      try {
        result = JSON.parse(rawOutput);
      } catch (parseError) {
        logger.error('[IntentService] JSON parse failed, attempting fallback');
        result = this.extractJSONFallback(rawOutput);
      }

      // Validate schema
      const validated = this.validateIntentResult(result);
      
      logger.info(`[IntentService] Intent status: ${validated.intent_status}`);
      logger.info(`[IntentService] UI state: ${validated.ui_state}`);

      return validated;

    } catch (error) {
      logger.error('[IntentService] Error analyzing intent:', error);
      // Fallback: treat as unclear intent
      return {
        intent_status: 'unclear',
        intent_summary: query,
        extracted_constraints: {},
        missing_constraints: ['category', 'budget', 'usage'],
        follow_up_questions: [
          {
            key: 'category',
            question: 'Bạn đang tìm loại sản phẩm gì?',
            options: ['laptop', 'điện thoại', 'tai nghe', 'màn hình']
          }
        ],
        ui_state: 'INTENT_CLARIFICATION',
        error: error.message
      };
    }
  }

  /**
   * Fallback extraction khi JSON parse thất bại
   */
  extractJSONFallback(text) {
    const jsonMatch = text.match(/\{[\s\S]*\}/);
    if (jsonMatch) {
      try {
        return JSON.parse(jsonMatch[0]);
      } catch {
        // Nếu vẫn fail, return default
      }
    }

    return {
      intent_status: 'unclear',
      intent_summary: 'Không thể phân tích được ý định',
      extracted_constraints: {},
      missing_constraints: ['category'],
      follow_up_questions: [],
      ui_state: 'INTENT_CLARIFICATION'
    };
  }

  /**
   * Validate và normalize kết quả
   */
  validateIntentResult(result) {
    const validated = {
      intent_status: result.intent_status || 'unclear',
      intent_summary: result.intent_summary || '',
      extracted_constraints: result.extracted_constraints || {},
      missing_constraints: Array.isArray(result.missing_constraints) 
        ? result.missing_constraints 
        : [],
      follow_up_questions: Array.isArray(result.follow_up_questions)
        ? result.follow_up_questions
        : [],
      ui_state: result.ui_state || 'INTENT_CLARIFICATION'
    };

    // Auto-correct ui_state based on intent_status
    if (validated.intent_status === 'clear' && validated.ui_state !== 'SEARCH_RESULT') {
      validated.ui_state = 'SEARCH_RESULT';
    }
    if (validated.intent_status === 'unclear' && validated.ui_state !== 'INTENT_CLARIFICATION') {
      validated.ui_state = 'INTENT_CLARIFICATION';
    }

    return validated;
  }

  /**
   * Tạo search query từ extracted constraints
   * Hàm này được gọi KHI intent_status = "clear"
   */
  buildSearchQuery(constraints) {
    const parts = [];

    if (constraints.category) {
      parts.push(constraints.category);
    }

    if (constraints.usage) {
      parts.push(constraints.usage);
    }

    if (constraints.brand) {
      parts.push(constraints.brand);
    }

    if (constraints.priority && constraints.priority.length > 0) {
      parts.push(...constraints.priority);
    }

    return parts.join(' ');
  }

  /**
   * Tạo database filters từ constraints
   */
  buildDatabaseFilters(constraints) {
    const filters = {};

    if (constraints.price_min !== null && constraints.price_min !== undefined) {
      filters.price_min = constraints.price_min;
    }

    if (constraints.price_max !== null && constraints.price_max !== undefined) {
      filters.price_max = constraints.price_max;
    }

    if (constraints.category) {
      filters.category = constraints.category;
    }

    if (constraints.brand) {
      filters.brand = constraints.brand;
    }

    if (constraints.usage) {
      filters.usage = constraints.usage;
    }

    return filters;
  }
}

export const intentService = new IntentService();