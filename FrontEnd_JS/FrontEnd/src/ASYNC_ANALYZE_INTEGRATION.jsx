/**
 * INTEGRATION GUIDE: Using Async Analyze with Job Polling
 * 
 * This demonstrates how to use the new async analyze pattern with:
 * - useAnalyzeJobSubmission: Submit analyze request → get jobId
 * - useSearchPolling: Poll job status until done
 * 
 * Complete flow example component:
 */

import { useState } from 'react';
import { useSearchPolling } from '../hooks/useSearchPolling';
import { useAnalyzeJobSubmission } from '../hooks/useAnalyzeJobSubmission';

/**
 * Example: SearchForm Component with Async Job Pattern
 */
export const SearchFormWithAsyncJobs = ({ token, onProductsFound }) => {
  const [userInput, setUserInput] = useState('');
  const [conversationId, setConversationId] = useState(null);
  
  // Submission hook - creates job and returns jobId
  const { submitAnalyze, jobId, submitting: submittingJob, submitError } = useAnalyzeJobSubmission(token);
  
  // Polling hook - polls job status with 2500ms interval
  const { data: jobResult, loading: pollingLoading, error: pollingError } = useSearchPolling(jobId, token);
  
  // Handle form submission
  const handleSearch = async (e) => {
    e.preventDefault();
    
    // Submit analyze request
    const newJobId = await submitAnalyze(userInput, conversationId);
    
    if (newJobId) {
      console.log(`✅ Job created: ${newJobId}`);
      console.log('Now polling for results...');
    }
  };
  
  // Handle job completion
  const handleJobComplete = () => {
    if (jobResult) {
      // Update conversation for follow-ups
      setConversationId(jobResult.conversation_id);
      
      // Call parent handler with results
      if (onProductsFound) {
        onProductsFound(jobResult);
      }
      
      // Process different statuses
      if (jobResult.status === 'need_info') {
        console.log('📝 Needs clarification:', jobResult.question);
        console.log('Options:', jobResult.options);
      } else if (jobResult.status === 'no_results') {
        console.log('🔍 No products found:', jobResult.message);
      } else if (jobResult.products) {
        console.log(`✅ Found ${jobResult.products.length} products`);
        console.log('Filters available:', jobResult.filters);
      }
    }
  };
  
  // Determine overall loading state
  const isProcessing = submittingJob || pollingLoading;
  const hasError = submitError || pollingError;
  
  // Call handler when job completes
  React.useEffect(() => {
    if (jobResult && !pollingLoading) {
      handleJobComplete();
    }
  }, [jobResult, pollingLoading]);
  
  return (
    <div className="search-form-async">
      <form onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Tìm kiếm sản phẩm..."
          value={userInput}
          onChange={(e) => setUserInput(e.target.value)}
          disabled={isProcessing}
        />
        <button type="submit" disabled={isProcessing}>
          {isProcessing ? '⏳ Đang tìm...' : '🔍 Tìm kiếm'}
        </button>
      </form>
      
      {/* Status display */}
      {jobId && (
        <div className="job-status">
          <p>Job ID: {jobId}</p>
          {isProcessing && <p>⏳ Đang xử lý...</p>}
          {jobResult && !pollingLoading && (
            <div className="result-summary">
              <p>Status: {jobResult.status}</p>
              {jobResult.products && (
                <p>✅ Tìm thấy {jobResult.products.length} sản phẩm</p>
              )}
            </div>
          )}
        </div>
      )}
      
      {/* Error display */}
      {hasError && (
        <div className="error-message">
          <p>❌ {hasError}</p>
        </div>
      )}
    </div>
  );
};

/**
 * BACKEND FLOW (for reference):
 * 
 * 1. Frontend: POST /api/analyze
 *    Request: { user_input: "giày thể thao", conversation_id: "..." }
 *    Response: { success: true, jobId: "uuid-xxx", status: "pending" }
 *    ↓
 * 
 * 2. Backend: Creates job in Redis
 *    Key: "analyze_job:uuid-xxx"
 *    Status: pending
 *    Starts background task with asyncio.create_task()
 *    ↓
 * 
 * 3. Background Task: Processes analyze (same logic as before)
 *    - Creates/fetches session
 *    - Reconstructs intent if needed
 *    - Runs orchestrator
 *    - Fetches filters from DB
 *    - Updates Redis with result
 *    ↓
 * 
 * 4. Frontend: Polls GET /api/analyze/:jobId/status every 2500ms
 *    Request: GET /api/analyze/uuid-xxx/status
 *    Response (pending): { success: true, status: "pending", ... }
 *    Response (done): { success: true, status: "done", result: {...} }
 *    Response (error): { success: false, status: "error", error: "..." }
 *    ↓
 * 
 * 5. Frontend: Clears interval when status is done/error
 *    Displays results to user
 * 
 * 
 * KEY BENEFITS:
 * ✅ API responds immediately (< 100ms)
 * ✅ Frontend stays responsive during processing
 * ✅ Can show progress/loading state
 * ✅ Multiple requests don't block each other
 * ✅ User can navigate/interact while waiting
 * ✅ Scales better under load
 */

export default SearchFormWithAsyncJobs;
