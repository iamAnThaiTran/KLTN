/**
 * Global API Configuration
 * 
 * API Gateway maps port 80 (inside container) → port 8000 (on host)
 * So frontend should fetch from: http://localhost:8000
 */

export const API_BASE_URL = 'http://localhost:8000';
