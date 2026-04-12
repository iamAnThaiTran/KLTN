import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';

/**
 * useSearchPolling Hook
 * 
 * Handles async job polling for /api/analyze requests
 * 
 * Usage:
 * ```
 * const { data, loading, error } = useSearchPolling(jobId, token);
 * 
 * if (loading) return <div>Searching...</div>;
 * if (error) return <div>Error: {error}</div>;
 * if (data) return <ProductList products={data.products} />;
 * ```
 */

export const useSearchPolling = (jobId, token = null) => {
  // ── State ──
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  // ── Refs ──
  const intervalRef = useRef(null);
  const jobIdRef = useRef(jobId);
  const tokenRef = useRef(token);
  
  // ── Update refs ──
  jobIdRef.current = jobId;
  tokenRef.current = token;
  
  // ── Poll interval in ms ──
  const POLL_INTERVAL = 2500;
  
  /**
   * Poll job status from backend
   */
  const pollJobStatus = async () => {
    if (!jobIdRef.current) {
      console.warn('[useSearchPolling] No jobId provided');
      return;
    }
    
    try {
      const response = await axios.get(
        `${API_BASE_URL}/api/analyze/${jobIdRef.current}/status`,
        {
          headers: {
            ...(tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {}),
            'Content-Type': 'application/json',
          },
        }
      );
      
      const jobStatus = response.data;
      
      if (!jobStatus.success) {
        console.error('[useSearchPolling] Job status error:', jobStatus.error);
        setError(jobStatus.error || 'Unknown error');
        setLoading(false);
        // Stop polling on error
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        return;
      }
      
      console.log(`[useSearchPolling] Job ${jobIdRef.current} status: ${jobStatus.status}`);
      
      if (jobStatus.status === 'pending') {
        // Still processing, continue polling
        setLoading(true);
        return;
      }
      
      if (jobStatus.status === 'done') {
        // Job completed successfully
        console.log('[useSearchPolling] ✅ Job completed');
        setData(jobStatus.result);
        setLoading(false);
        setError(null);
        
        // Stop polling
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        return;
      }
      
      if (jobStatus.status === 'error') {
        // Job failed
        console.error('[useSearchPolling] ❌ Job error:', jobStatus.error);
        setError(jobStatus.error || 'Job processing error');
        setLoading(false);
        
        // Stop polling
        if (intervalRef.current) {
          clearInterval(intervalRef.current);
          intervalRef.current = null;
        }
        return;
      }
      
    } catch (err) {
      console.error('[useSearchPolling] Polling error:', err);
      setError(err.message || 'Failed to poll job status');
      setLoading(false);
      
      // Stop polling on network error
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    }
  };
  
  /**
   * Effect: Start polling when jobId changes
   */
  useEffect(() => {
    if (!jobId) {
      console.log('[useSearchPolling] No jobId, skipping polling');
      return;
    }
    
    console.log(`[useSearchPolling] 🔄 Starting polling for job: ${jobId}`);
    
    setLoading(true);
    setError(null);
    setData(null);
    
    // Poll immediately first time
    pollJobStatus();
    
    // Then set up interval for subsequent polls
    intervalRef.current = setInterval(() => {
      pollJobStatus();
    }, POLL_INTERVAL);
    
    // Cleanup on unmount or jobId change
    return () => {
      console.log('[useSearchPolling] 🛑 Cleaning up polling');
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
    
  }, [jobId]);
  
  return {
    data,
    loading,
    error,
  };
};

export default useSearchPolling;
