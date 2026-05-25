/**
 * Load Test — /api/analyze
 *
 * Phân chia tải:
 *  - 20% nhóm A: query sản phẩm CHƯA có trong DB  → kỳ vọng status need_info hoặc empty
 *  - 80% nhóm B: query sản phẩm ĐÃ có trong DB    → kỳ vọng products array + jobId polling
 *
 * Chạy: k6 run analyze_load_test.js
 * Hoặc với env:  k6 run -e BASE_URL=http://localhost:8000 -e VUS=20 analyze_load_test.js
 *
 * Cài k6: https://k6.io/docs/get-started/installation/
 */

import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';
import { randomItem } from 'https://jslib.k6.io/k6-utils/1.4.0/index.js';

// ─── Cấu hình ───────────────────────────────────────────────
const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const VUS      = parseInt(__ENV.VUS  || '20');   // virtual users
const DURATION = __ENV.DURATION      || '2m';
const TOKEN    = __ENV.TOKEN         || '';       // Bearer token nếu cần

// Polling config cho async job
const POLL_INTERVAL_MS = 5000;  // poll mỗi 500ms
const POLL_TIMEOUT_MS  = 30000; // timeout sau 30s

// ─── Metrics tùy chỉnh ──────────────────────────────────────
const errorRate       = new Rate('analyze_error_rate');
const jobDuration     = new Trend('job_duration_ms',   true);  // true = display in ms
const analyzeLatency  = new Trend('analyze_latency_ms', true);
const pollCount       = new Counter('poll_count_total');
const productsFound   = new Counter('products_found_total');
const emptyResults    = new Counter('empty_results_total');
const groupAErrors    = new Rate('group_a_error_rate');
const groupBErrors    = new Rate('group_b_error_rate');

// ─── Kịch bản tải ───────────────────────────────────────────
export const options = {
  scenarios: {
    // 80% VUs — sản phẩm đã có trong DB
    group_b_existing: {
      executor:        'ramping-vus',
      startVUs:        0,
      stages: [
        { duration: '20s', target: Math.floor(VUS * 0.8) },
        { duration: DURATION, target: Math.floor(VUS * 0.8) },
        { duration: '10s', target: 0 },
      ],
      exec: 'existingProductsTest',
      tags: { group: 'B_existing' },
    },
    // // 20% VUs — sản phẩm chưa có trong DB
    // group_a_missing: {
    //   executor:        'ramping-vus',
    //   startVUs:        0,
    //   stages: [
    //     { duration: '20s', target: Math.floor(VUS * 0.2) },
    //     { duration: DURATION, target: Math.floor(VUS * 0.2) },
    //     { duration: '10s', target: 0 },
    //   ],
    //   exec: 'missingProductsTest',
    //   tags: { group: 'A_missing' },
    // },
  },

  thresholds: {
    // Tổng error rate < 5%
    'analyze_error_rate':   ['rate<0.05'],
    // p95 latency toàn bộ (bao gồm polling) < 35s
    'analyze_latency_ms':   ['p(95)<35000'],
    // Job duration p95 < 30s
    'job_duration_ms':      ['p(95)<30000'],
    // Error rate từng nhóm < 10%
    'group_a_error_rate':   ['rate<0.10'],
    'group_b_error_rate':   ['rate<0.05'],
    // HTTP request thành công
    'http_req_failed':      ['rate<0.05'],
  },
};

// ─── Query pools ─────────────────────────────────────────────
/**
 * NHÓM B (80%): Sản phẩm ĐÃ có trong DB.
 * Thay bằng các từ khóa thực tế trong hệ thống của bạn.
 */
const EXISTING_QUERIES = [
  // 'điện thoại samsung galaxy',
  // 'laptop dell xps',
  // 'tai nghe bluetooth sony',
  // 'máy tính bảng ipad',
  // 'tivi lg 55 inch oled',
  // 'tủ lạnh panasonic 300 lít',
  // 'máy giặt lg 9kg',
  // 'loa bluetooth jbl charge',
  // 'bàn phím cơ leopold',
  // 'chuột gaming logitech g pro',
  // 'màn hình dell 27 inch',
  // 'pin dự phòng anker 20000',
  // 'ổ cứng ssd samsung 1tb',
  // 'router wifi asus ax3000',
  // 'camera ip hikvision 4mp',
  'giày',
];

/**
 * NHÓM A (20%): Sản phẩm CHƯA có trong DB.
 * Dùng tên sản phẩm không tồn tại / rất hiếm để chắc chắn không có kết quả.
 */
const MISSING_QUERIES = [
  'điện thoại nokia 3310 mới 2025',
  'máy bay cá nhân mini giá rẻ',
  'robot hút bụi thần kinh nhân tạo',
  'xe đạp điện mặt trăng nasa',
  'kính thực tế ảo apple vision pro gen5',
  'máy in 3d kim cương tinh thể',
  'đồng hồ thông minh hải mã',
  'loa bluetooth từ trường siêu dẫn',
  'laptop hologram projection 2026',
  'máy lọc nước hàng không vũ trụ',
];

// ─── Helpers ─────────────────────────────────────────────────
function buildHeaders() {
  const h = { 'Content-Type': 'application/json' };
  if (TOKEN) h['Authorization'] = `Bearer ${TOKEN}`;
  return h;
}

/**
 * Gọi POST /api/analyze và trả về parsed response.
 * Nếu có jobId → poll đến khi xong hoặc timeout.
 * Trả về { ok, data, totalMs } — totalMs tính cả thời gian polling.
 */
function callAnalyze(userInput, conversationId = null) {
  const startMs = Date.now();
  const payload = JSON.stringify({
    user_input: userInput,
    ...(conversationId ? { conversation_id: conversationId } : {}),
  });

  const res = http.post(`${BASE_URL}/api/analyze`, payload, {
    headers: buildHeaders(),
    timeout: '35s',
  });

  const analyzeMs = Date.now() - startMs;
  analyzeLatency.add(analyzeMs);

  if (res.status !== 200) {
    return { ok: false, data: null, totalMs: analyzeMs, status: res.status };
  }

  let data;
  try { data = JSON.parse(res.body); } catch {
    return { ok: false, data: null, totalMs: analyzeMs, status: res.status };
  }

  if (!data.success) {
    return { ok: false, data, totalMs: analyzeMs, status: res.status };
  }

  // ── Async job path: có jobId → poll ──────────────────────
  if (data.jobId) {
    const jobStart = Date.now();
    let elapsed    = 0;
    let jobData    = null;

    while (elapsed < POLL_TIMEOUT_MS) {
      sleep(POLL_INTERVAL_MS / 1000); // k6 sleep nhận giây
      elapsed = Date.now() - jobStart;

      const pollRes = http.get(`${BASE_URL}/api/jobs/${data.jobId}`, {
        headers: buildHeaders(),
        timeout: '10s',
      });
      pollCount.add(1);

      if (pollRes.status !== 200) continue;

      let pollData;
      try { pollData = JSON.parse(pollRes.body); } catch { continue; }

      // Kiểm tra trạng thái job
      const status = pollData.status || pollData.state || '';

// Backend của bạn trả data trong result
const resultData = pollData.result || pollData;

// Detect completed job
if (
    status === 'completed' ||
    status === 'done' ||
    resultData.products ||
    resultData.question ||
    resultData.filters ||
    resultData.category
) {
    jobData = resultData;
    break;
}
    }

    const jobMs = Date.now() - jobStart;
    jobDuration.add(jobMs);

    if (!jobData) {
      // Timeout khi polling
      return { ok: false, data: null, totalMs: Date.now() - startMs, status: 408 };
    }

    return { ok: true, data: jobData, totalMs: Date.now() - startMs, status: 200 };
  }

  // ── Sync path: kết quả trả về ngay ──────────────────────
  return { ok: true, data, totalMs: analyzeMs, status: 200 };
}

// ─── Scenario: Nhóm B — sản phẩm đã có (80%) ────────────────
export function existingProductsTest() {
  const query = randomItem(EXISTING_QUERIES);

  group('B — sản phẩm đã có trong DB', () => {
    const { ok, data, totalMs, status } = callAnalyze(query);

    const passed = check({ ok, data, status }, {
      'B: HTTP 200':             ({ status }) => status === 200,
      'B: success = true':       ({ ok })     => ok === true,
      'B: có products hoặc question': ({ data }) =>
        data && (
          (Array.isArray(data.products) && data.products.length > 0) ||
          (data.status === 'need_info' && !!data.question)
        ),
      'B: latency < 35s':        () => totalMs < 35000,
    });

    // Metrics
    errorRate.add(!passed);
    groupBErrors.add(!passed);

    if (ok && data) {
      if (data.products?.length) {
        productsFound.add(data.products.length);
      } else if (!data.question) {
        emptyResults.add(1);
      }
    }
  });

  sleep(Math.random() * 2 + 1); // 1-3s think time
}

// ─── Scenario: Nhóm A — sản phẩm chưa có (20%) ──────────────
export function missingProductsTest() {
  const query = randomItem(MISSING_QUERIES);

  group('A — sản phẩm chưa có trong DB', () => {
    const { ok, data, totalMs, status } = callAnalyze(query);

    const passed = check({ ok, data, status }, {
      'A: HTTP 200':                ({ status }) => status === 200,
      'A: success = true':          ({ ok })     => ok === true,
      'A: trả về empty hoặc question': ({ data }) =>
        data && (
          // Không tìm thấy sản phẩm — đây là kết quả ĐÚNG cho nhóm A
          (data.products && data.products.length === 0) ||
          (data.status === 'need_info'  && !!data.question) ||
          (data.status === 'not_found') ||
          // Backend báo không có trong kho
          (typeof data.message === 'string' && data.message.includes('chưa có'))
        ),
      'A: latency < 35s':           () => totalMs < 35000,
    });

    errorRate.add(!passed);
    groupAErrors.add(!passed);

    if (ok && data) {
      if (!data.products?.length) emptyResults.add(1);
    }
  });

  sleep(Math.random() * 3 + 1); // 1-4s think time (query phức tạp hơn)
}

// ─── Setup / Teardown ────────────────────────────────────────
export function setup() {
  console.log(`=== Load Test /api/analyze ===`);
  console.log(`Base URL : ${BASE_URL}`);
  console.log(`VUs      : ${VUS} (${Math.floor(VUS * 0.8)} nhóm B + ${Math.floor(VUS * 0.2)} nhóm A)`);
  console.log(`VUs      : ${VUS} (${Math.floor(VUS * 0.8)} nhóm B)`);
  console.log(`Duration : ${DURATION}`);
  console.log(`Nhóm A queries : ${MISSING_QUERIES.length}`);
  console.log(`Nhóm B queries : ${EXISTING_QUERIES.length}`);

  // Smoke test — kiểm tra backend có sẵn không
  const ping = http.get(`${BASE_URL}/health`, { timeout: '5s' });
  if (ping.status !== 200) {
    console.warn(`⚠ /health trả về ${ping.status} — backend có thể chưa sẵn sàng`);
  }
  return {};
}

export function teardown() {
  console.log('=== Test hoàn thành ===');
}