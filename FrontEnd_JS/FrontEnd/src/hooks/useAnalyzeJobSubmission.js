import { useState, useCallback, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

/**
 * useAnalyzeJobSubmission Hook
 * 
 * Submits analyze request and returns jobId
 * Works with useSearchPolling for the polling part
 * 
 * Usage:
 * ```
 * const { submitAnalyze, jobId, submitting, submitError } = useAnalyzeJobSubmission(token);
 * 
 * const { data, loading, error } = useSearchPolling(jobId, token);
 * 
 * const handleSearch = async (userInput) => {
 *   await submitAnalyze(userInput, conversationId);
 * };
 * ```
 */

export const useAnalyzeJobSubmission = (token = null) => {
  // ── State ──
  const [jobId, setJobId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState(null);
  
  // ── Refs ──
  const tokenRef = useRef(token);
  tokenRef.current = token;
  
  /**
   * Submit analyze request and get jobId
   */
  const submitAnalyze = useCallback(async (userInput, conversationId = null) => {
    if (!userInput || !userInput.trim()) {
      console.warn('[useAnalyzeJobSubmission] Empty user input');
      setSubmitError('Vui lòng nhập từ khóa tìm kiếm');
      return null;
    }
    
    setSubmitting(true);
    setSubmitError(null);
    setJobId(null);
    
    try {
      console.log('[useAnalyzeJobSubmission] 📤 Submitting analyze request');
      
      const response = await axios.post(
        `${API_BASE_URL}/api/analyze`,
        {
          user_input: userInput,
          conversation_id: conversationId,
        },
        {
          headers: {
            ...(tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {}),
            'Content-Type': 'application/json',
          },
        }
      );
      
      const result = response.data;
      
      if (!result.success) {
        console.error('[useAnalyzeJobSubmission] Error:', result.error);
        setSubmitError(result.error || 'Failed to submit request');
        setSubmitting(false);
        return null;
      }
      
      console.log(`[useAnalyzeJobSubmission] ✅ Job created: ${result.jobId}`);
      setJobId(result.jobId);
      setSubmitting(false);
      
      return result.jobId;
      
    } catch (err) {
      console.error('[useAnalyzeJobSubmission] Submission error:', err);
      const errorMsg = err.response?.data?.detail || err.message || 'Failed to submit request';
      setSubmitError(errorMsg);
      setSubmitting(false);
      return null;
    }
  }, []);
  
  return {
    submitAnalyze,
    jobId,
    submitting,
    submitError,
    setJobId, // Allow manual reset if needed
  };
};

export default useAnalyzeJobSubmission;
