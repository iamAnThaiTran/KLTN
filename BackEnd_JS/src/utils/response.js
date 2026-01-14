/**
 * Response utility functions
 * Standardized API response format
 */

/**
 * Send success response
 * @param {object} res - Express response object
 * @param {any} data - Response data
 * @param {string} message - Success message (optional)
 * @param {number} statusCode - HTTP status code (default: 200)
 */
export function successResponse(res, data, message = 'Success', statusCode = 200) {
  return res.status(statusCode).json({
    success: true,
    data,
    message,
    timestamp: new Date().toISOString()
  });
}

/**
 * Send error response
 * @param {object} res - Express response object
 * @param {string} message - Error message
 * @param {number} statusCode - HTTP status code (default: 400)
 * @param {any} error - Error details (optional)
 */
export function errorResponse(res, message = 'Error', statusCode = 400, error = null) {
  return res.status(statusCode).json({
    success: false,
    message,
    error: error ? error.toString() : null,
    timestamp: new Date().toISOString()
  });
}

/**
 * Send paginated response
 * @param {object} res - Express response object
 * @param {array} data - Response data array
 * @param {number} page - Current page
 * @param {number} limit - Items per page
 * @param {number} total - Total items count
 * @param {string} message - Success message (optional)
 */
export function paginatedResponse(res, data, page, limit, total, message = 'Success') {
  return res.status(200).json({
    success: true,
    data,
    pagination: {
      page,
      limit,
      total,
      pages: Math.ceil(total / limit)
    },
    message,
    timestamp: new Date().toISOString()
  });
}
