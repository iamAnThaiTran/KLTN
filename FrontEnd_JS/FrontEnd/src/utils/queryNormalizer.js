/**
 * Query Normalizer
 * Convert raw search queries into humanized/normalized format
 * 
 * Example:
 * "tôi muốn mua một đôi nike jordan màu đỏ đẹp đẹp"
 * ↓ 
 * "Giày Nike Jordan đỏ"
 */

const CATEGORY_KEYWORDS = {
  'giày': 'Giày',
  'shoe': 'Giày',
  'shoes': 'Giày',
  'sneaker': 'Giày',
  'boot': 'Giày',
  'đồng hồ': 'Đồng hồ',
  'watch': 'Đồng hồ',
  'laptop': 'Laptop',
  'máy tính': 'Laptop',
  'tai nghe': 'Tai nghe',
  'headphone': 'Tai nghe',
  'bao cao su': 'Bao cao su',  // Add this category
  'máy cạo râu': 'Máy cạo râu',  // Add this category
};

const FILLER_WORDS = [
  'tôi', 'muốn', 'mua', 'một', 'cái', 'chiếc', 'đôi', 'bộ', 'tìm', 'tìm kiếm',
  'để', 'có', 'có thể', 'được', 'không', 'rất', 'đẹp', 'tốt', 'xấu', 'giá',
  'rẻ', 'mắc', 'tiền', 'tháng', 'năm', 'tuổi', 'lần', 'gì', 'gì gì', 'và',
  'hoặc', 'hay', 'cũng', 'nữa', 'thêm', 'với', 'ở', 'tại', 'từ', 'đến',
  'mới', 'cũ', 'là', 'em', 'tôi', 'bạn', 'anh', 'chị', 'cô', 'mr', 'ms',
  'trong', 'ngoài', 'trên', 'dưới', 'bên', 'cạnh', 'giữa', 'quanh'
];

export function normalizeQuery(rawQuery, isPart = false) {
  if (!rawQuery || typeof rawQuery !== 'string') {
    return '';
  }

  // Convert to lowercase for processing
  const lower = rawQuery.toLowerCase().trim();

  // Step 1: Extract category (only if NOT a continuation/part query)
  let detectedCategory = '';
  if (!isPart) {
    for (const [keyword, categoryName] of Object.entries(CATEGORY_KEYWORDS)) {
      if (lower.includes(keyword)) {
        detectedCategory = categoryName;
        break;
      }
    }
  }

  // Step 2: Remove filler words
  let normalized = lower;
  for (const filler of FILLER_WORDS) {
    // Use word boundaries for better matching
    const regex = new RegExp(`\\b${filler}\\b`, 'g');
    normalized = normalized.replace(regex, ' ');
  }

  // Step 3: Clean up extra spaces
  normalized = normalized
    .replace(/\s+/g, ' ')
    .trim();

  // Step 4: Build final result
  let result = '';
  
  if (detectedCategory && !isPart) {
    result = detectedCategory;
    
    // Add remaining keywords as details
    if (normalized.length > 0) {
      // Capitalize first letter
      const details = normalized.charAt(0).toUpperCase() + normalized.slice(1);
      result = `${result} ${details}`;
    }
  } else {
    // No category detected or it's a part query, just capitalize
    result = normalized.charAt(0).toUpperCase() + normalized.slice(1);
  }

  // Step 5: Limit length (max 60 chars)
  if (result.length > 60) {
    result = result.substring(0, 57) + '...';
  }

  return result || '(Tìm kiếm)';
}

/**
 * Check if a query is a "continuation" of the previous query
 * (e.g., "màu đỏ" after "giày" is a continuation)
 * 
 * Returns: boolean
 */
export function isQueryContinuation(currentQuery, previousQuery) {
  if (!previousQuery) return false;
  
  const current = currentQuery.toLowerCase().trim();
  const previous = previousQuery.toLowerCase().trim();
  
  // If current query is very short and previous had a category, it's likely a continuation
  const hasCategory = Object.keys(CATEGORY_KEYWORDS).some(k => previous.includes(k));
  const isShort = current.length < 15;
  const hasNoCategory = !Object.keys(CATEGORY_KEYWORDS).some(k => current.includes(k));
  
  return hasCategory && isShort && hasNoCategory;
}

/**
 * Get icon for category
 */
export function getCategoryIcon(categoryName) {
  const icons = {
    'Giày': '👟',
    'Đồng hồ': '⌚',
    'Laptop': '💻',
    'Tai nghe': '🎧',
    'Bao cao su': '🔞',
    'Máy cạo râu': '🪮',
    'dụng cụ': '🔧'
  };
  return icons[categoryName] || '🔍';
}
