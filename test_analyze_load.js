import http from 'k6/http';
import { check, group } from 'k6';
import { Rate, Trend, Counter } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const responseTime = new Trend('response_time');
const asyncJobsCreated = new Counter('async_jobs_created');
const syncResponsesReceived = new Counter('sync_responses');
const jobsPolled = new Counter('jobs_polled');

// Test options
export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp-up to 50 users
    { duration: '5m', target: 100 },  // Ramp-up to 100 users
    { duration: '10m', target: 100 }, // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp-down
  ],
  thresholds: {
    errors: ['rate<0.1'],             // error rate < 10%
    response_time: ['p(95)<2000'],    // 95th percentile < 2s
  },
};

// Test data: Products KHÔNG có trong DB (20%)
const unavailableProducts = [
  'laptop gaming RTX 4090',
  'iPhone 15 Pro Max 1TB',
  'MacBook Pro M4 Max 64GB',
  'Samsung Galaxy S25 Ultra',
  'Sony A1 camera',
  'DJI Phantom 8',
  'Asus ROG laptop i9',
  'iPad Pro 13 inch M4',
  'Google Pixel Fold',
  'Xiaomi Pad 8 Pro',
];

// Test data: Products CÓ trong DB (80%)
const availableProducts = [
  'áo thun nam',
  'quần jeans nữ',
  'giày thể thao',
  'túi xách nữ',
  'đồng hồ',
  'dép xỏ ngón',
  'áo khoác nam',
  'quần shorts nữ',
  'mũ lưỡi trai',
  'dây chuyền vàng',
  'vòng tay thời trang',
  'khăn choàng',
  'balo du lịch',
  'ví da nam',
  'giày cao gót nữ',
  'áo sơ mi nam',
  'quần legging nữ',
  'thắt lưng da',
  'tất cotton',
  'khẩu trang thời trang',
];

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const POLLING_INTERVAL = 1000; // 1 second
const POLLING_TIMEOUT = 30000; // 30 seconds max

// Store job IDs for polling simulation
const pendingJobs = {};

/**
 * Simulate polling for async job result
 */
function pollJobResult(jobId, conversationId, token) {
  const startTime = Date.now();
  let attempts = 0;

  while (Date.now() - startTime < POLLING_TIMEOUT && attempts < 30) {
    attempts++;
    jobsPolled.add(1);

    const pollRes = http.get(
      `${BASE_URL}/api/job/${jobId}`,
      {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'Content-Type': 'application/json',
        },
      }
    );

    const success = check(pollRes, {
      'poll status is 200': (r) => r.status === 200,
    });

    if (pollRes.status === 200) {
      const data = JSON.parse(pollRes.body);
      if (data.status === 'completed' || data.status === 'done') {
        return { success: true, data, attempts };
      }
    }

    // Wait before next poll (simulated)
    // In real k6, we don't actually sleep to avoid blocking
  }

  return { success: false, data: null, attempts };
}

/**
 * Main test function
 */
export default function () {
  // Determine if this should be a search for available or unavailable product
  // 20% unavailable, 80% available
  const isUnavailable = Math.random() < 0.2;

  const searchQuery = isUnavailable
    ? unavailableProducts[Math.floor(Math.random() * unavailableProducts.length)]
    : availableProducts[Math.floor(Math.random() * availableProducts.length)];

  const conversationId = `conv_${Math.random().toString(36).substring(7)}`;
  const token = __ENV.AUTH_TOKEN || null;

  group(`Analyze Search - ${isUnavailable ? 'Unavailable' : 'Available'} Product`, () => {
    // Step 1: Send analyze request
    const analyzeRes = http.post(
      `${BASE_URL}/api/analyze`,
      JSON.stringify({
        user_input: searchQuery,
        conversation_id: conversationId,
      }),
      {
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
          'Content-Type': 'application/json',
        },
      }
    );

    responseTime.add(analyzeRes.timings.duration);

    const success = check(analyzeRes, {
      'status is 200': (r) => r.status === 200,
      'response has success=true': (r) => {
        const body = JSON.parse(r.body);
        return body.success === true;
      },
      'has conversation_id': (r) => {
        const body = JSON.parse(r.body);
        return body.conversation_id !== undefined;
      },
    });

    if (!success) {
      errorRate.add(1);
      return;
    }

    const responseData = JSON.parse(analyzeRes.body);

    // Step 2: Handle async job vs sync response
    if (responseData.jobId) {
      asyncJobsCreated.add(1);
      console.log(`Job created: ${responseData.jobId}`);

      // Simulate polling (in real scenario, frontend would poll)
      const pollResult = pollJobResult(responseData.jobId, conversationId, token);

      check(pollResult, {
        'job polling completed successfully': (r) => r.success,
      });

      if (!pollResult.success) {
        errorRate.add(1);
      }
    } else {
      syncResponsesReceived.add(1);

      // Validate sync response structure
      check(responseData, {
        'has category': (r) => r.category !== undefined,
        'products exist or null': (r) =>
          r.products === undefined || r.products === null || Array.isArray(r.products),
        'has filters': (r) => r.filters !== undefined || r.filters === null,
      });
    }
  });
}

/**
 * Teardown - print summary
 */
export function teardown(data) {
  console.log('=== Load Test Summary ===');
  console.log(`Total async jobs created: ${asyncJobsCreated.value}`);
  console.log(`Total sync responses: ${syncResponsesReceived.value}`);
  console.log(`Total jobs polled: ${jobsPolled.value}`);
}
