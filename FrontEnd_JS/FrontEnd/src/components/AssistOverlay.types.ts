/**
 * AssistOverlay.types.ts
 * TypeScript types for the AssistOverlay component and server responses
 */

/**
 * Single option in the assist overlay
 */
export interface AssistOption {
  key: string;
  label: string;
}

/**
 * Server response format for assist overlay
 * Sent when the backend requires intent clarification
 */
export interface AssistOverlayData {
  ui_mode: 'OVERLAY_ASSIST';
  title?: string;
  summary: string;
  question: string;
  options: AssistOption[];
  allow_skip?: boolean;
}

/**
 * Props for AssistOverlay component
 */
export interface AssistOverlayProps {
  isOpen?: boolean;
  data?: AssistOverlayData | null;
  onOptionSelect?: (optionKey: string) => void;
  onSkip?: () => void;
  onClose?: () => void;
}

/**
 * Extended API response that includes assist overlay data
 */
export interface AssistApiResponse {
  success: true;
  data: AssistOverlayData;
  message: string;
  timestamp: string;
}

/**
 * Example server response:
 * {
 *   "success": true,
 *   "data": {
 *     "ui_mode": "OVERLAY_ASSIST",
 *     "summary": "✔ Đã hiểu: mua áo mưa",
 *     "question": "Bạn đang tìm kiếm áo mưa cho mục đích gì?",
 *     "options": [
 *       { "key": "outdoor", "label": "Dã ngoại/Du lịch" },
 *       { "key": "work", "label": "Công việc" },
 *       { "key": "school", "label": "Học tập" }
 *     ],
 *     "allow_skip": true
 *   },
 *   "message": "Clarification needed",
 *   "timestamp": "2026-01-15T12:34:56.789Z"
 * }
 */
