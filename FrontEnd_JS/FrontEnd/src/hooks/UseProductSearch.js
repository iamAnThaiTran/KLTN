import { useState, useCallback, useRef, useMemo, useEffect } from 'react';
import axios from 'axios';
import { API_BASE_URL } from '../config';
import { mergeFilters } from '../utils/storage';
import { useSearchPolling } from './useSearchPolling';

/**
 * Encapsulates all product-search state and API calls.
 *
 * BUG FIX: Previously, startSearch() called setActiveFilters([]) which caused
 * showSidebar to become false, hiding the product grid while the new request
 * was in flight.  Now we only clear filters AFTER a successful response that
 * returns new filter definitions.  Products remain visible until replaced.
 * 
 * ASYNC JOB FIX: Now uses async job pattern with useSearchPolling for /api/analyze
 */
 
export const useProductSearch = ({ token, onAddMessage }) => {
  // ── Stable refs ──
  const tokenRef      = useRef(token);
  const onAddMsgRef   = useRef(onAddMessage);
  tokenRef.current    = token;
  onAddMsgRef.current = onAddMessage;
 
  // ── Loading ──
  const [productsLoading, setProductsLoading] = useState(false);  const [jobId, setJobId] = useState(null);
  
  // ── Polling hook for async analyze job ──
  const { data: jobResult, loading: pollingLoading, error: pollingError } = useSearchPolling(jobId, token); 
  // ── Filter state (sidebar — chỉ áp dụng lên kết quả mới nhất) ──
  const [activeFilters,       setActiveFilters]       = useState([]);
  const [selectedFilters,     setSelectedFilters]     = useState({});
  const [extractedAttributes, setExtractedAttributes] = useState({});
  const [lastCategoryName,    setLastCategoryName]    = useState('');
  const [lastProductsMsgId,   setLastProductsMsgId]   = useState(null);
  const [productCount,        setProductCount]        = useState(null);
 
  // ── Conversation metadata ──
  const [conversationId,    setConversationId]    = useState(null);
  const [originalUserInput, setOriginalUserInput] = useState('');
 
  // ── Stable refs cho state trong callbacks ──
  const conversationIdRef    = useRef(conversationId);
  const lastCategoryNameRef  = useRef(lastCategoryName);
  const selectedFiltersRef   = useRef(selectedFilters);
  const extractedAttrRef     = useRef(extractedAttributes);
  const lastProductsMsgIdRef = useRef(lastProductsMsgId);
 
  conversationIdRef.current    = conversationId;
  lastCategoryNameRef.current  = lastCategoryName;
  selectedFiltersRef.current   = selectedFilters;
  extractedAttrRef.current     = extractedAttributes;
  lastProductsMsgIdRef.current = lastProductsMsgId;
 
  // ─────────────────────────────────────────────────────────────
  // appendProducts — thêm products message mới vào stream
  // ─────────────────────────────────────────────────────────────
  const appendProducts = useCallback((prods, filters, total) => {
    const msgId = `products_${Date.now()}`;
    const count = total ?? prods?.length ?? 0;
    onAddMsgRef.current({
      type: 'products',
      products: prods ?? [],
      productCount: count,
      filters,
      msgId,
      timestamp: new Date(),
    });
    setProductCount(count);
    setLastProductsMsgId(msgId);
    if (filters?.length) setActiveFilters(filters);
  }, []);
 
  // ─────────────────────────────────────────────────────────────
  // updateProducts — cập nhật IN-PLACE message đã có (khi filter)
  // ─────────────────────────────────────────────────────────────
  const updateProducts = useCallback((msgId, prods, filters, total) => {
    const count = total ?? prods?.length ?? 0;
    onAddMsgRef.current({
      type: 'update_products',
      msgId,
      products: prods ?? [],
      productCount: count,
      filters,
    });
    setProductCount(count);
    if (filters?.length) setActiveFilters(filters);
  }, []);
 
  // ─────────────────────────────────────────────────────────────
  // analyzeAndSearch - Async job pattern
  // ─────────────────────────────────────────────────────────────
  const analyzeAndSearch = useCallback(async (userInput) => {
    setProductsLoading(true);
    setOriginalUserInput(userInput);
 
    try {
      const res = await axios.post(`${API_BASE_URL}/api/analyze`, {
        user_input:      userInput,
        conversation_id: conversationIdRef.current,
      }, {
        headers: {
          ...(tokenRef.current ? { Authorization: `Bearer ${tokenRef.current}` } : {}),
          'Content-Type': 'application/json',
        },
      });
 
      const d = res.data;
      if (!d.success) {
        onAddMsgRef.current({ type: 'bot', text: `❌ ${d.error}`, timestamp: new Date() });
        setProductsLoading(false);
        return;
      }

      // Handle conversation metadata
      if (d.conversation_id) {
        setConversationId(d.conversation_id);
      }
      
      // Check if response contains jobId (async) or products (sync fallback)
      if (d.jobId) {
        console.log('[UseProductSearch] 📤 Job created:', d.jobId);
        // Start polling for results - lastCategoryName will be set when job completes
        setJobId(d.jobId);
        // Keep productsLoading true until polling completes
      } else if (d.category) {
        // Sync fallback or direct response
        setLastCategoryName(d.category);
        setSelectedFilters({});
        
        if (d.selected_attributes && Object.keys(d.selected_attributes).length > 0) {
          const extracted = {};
          Object.entries(d.selected_attributes).forEach(([attr, value]) => {
            if (value == null) return;
            extracted[attr] = Array.isArray(value) ? value.map(v => String(v)) : [String(value)];
          });
          setExtractedAttributes(extracted);
        } else {
          setExtractedAttributes({});
        }
        
        if (d.status === 'need_info' && d.question) {
          onAddMsgRef.current({
            type: 'bot',
            text: d.question,
            quickReplies: d.options?.map(o => o.label || o.value || o) ?? null,
            timestamp: new Date(),
          });
        } else if (d.products?.length) {
          appendProducts(d.products, d.filters, d.total);
        } else {
          onAddMsgRef.current({
            type: 'bot',
            text: `ℹ️ Hiện tại chưa có sản phẩm "${d.category}" trong kho.\n\nVui lòng thử mô tả khác.`,
            timestamp: new Date(),
          });
        }
        setProductsLoading(false);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Có lỗi xảy ra';
      onAddMsgRef.current({ type: 'bot', text: `❌ Lỗi: ${msg}`, timestamp: new Date() });
      onAddMsgRef.current({ type: 'bot', text: 'ℹ️ Vui lòng chắc chắn backend Python đang chạy trên http://localhost:8000', timestamp: new Date() });
      setProductsLoading(false);
    }
  }, [appendProducts]);
 
  // ─────────────────────────────────────────────────────────────
  // sendToBackend — quick-reply
  // ─────────────────────────────────────────────────────────────
  const sendToBackend = useCallback(async (userInput) => {
    try {
      const res = await axios.post(`${API_BASE_URL}/api/query`, {
        user_input:      userInput,
        conversation_id: conversationIdRef.current,
      });
      const d = res.data;
      if (d.conversation_id) setConversationId(d.conversation_id);
      if (d.status === 'results' && d.products?.length) {
        appendProducts(d.products, d.filters, d.total_found);
      } else if (d.question) {
        onAddMsgRef.current({
          type: 'bot',
          text: d.question,
          quickReplies: d.options?.map(o => o.label || o.value || o) ?? null,
          timestamp: new Date(),
        });
      }
    } catch (err) {
      onAddMsgRef.current({ type: 'bot', text: `❌ Lỗi: ${err.response?.data?.detail || err.message}`, timestamp: new Date() });
    }
  }, [appendProducts]);
 
  // ─────────────────────────────────────────────────────────────
  // searchWithFilters — sidebar "Áp dụng": UPDATE message hiện tại
  // ─────────────────────────────────────────────────────────────
  const searchWithFilters = useCallback(async (categoryName, selected, extracted) => {
    setProductsLoading(true);
    try {
      const finalFilters = mergeFilters(extracted, selected);
      const res = await fetch(`${API_BASE_URL}/api/v1/crawl-products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category_name: categoryName, selected_filters: finalFilters, page: 1, page_size: 20 }),
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || `HTTP ${res.status}`); }
      const data = await res.json();
      if (!data.products?.length) {
        onAddMsgRef.current({ type: 'bot', text: '🔍 Không tìm thấy sản phẩm nào phù hợp với bộ lọc này.', timestamp: new Date() });
        return;
      }
      if (lastProductsMsgIdRef.current) {
        updateProducts(lastProductsMsgIdRef.current, data.products, data.filters, data.total);
      } else {
        appendProducts(data.products, data.filters, data.total);
      }
    } catch (err) {
      onAddMsgRef.current({ type: 'bot', text: `❌ Lỗi: ${err.message}`, timestamp: new Date() });
    } finally {
      setProductsLoading(false);
    }
  }, [appendProducts, updateProducts]);
 
  // ── Filter handlers ──
  const toggleFilter = useCallback((key) =>
    setSelectedFilters(p => { const n = { ...p }; if (n[key]) delete n[key]; else n[key] = true; return n; }), []);
 
  const applyFilters = useCallback(() => {
    if (lastCategoryNameRef.current)
      searchWithFilters(lastCategoryNameRef.current, selectedFiltersRef.current, extractedAttrRef.current);
  }, [searchWithFilters]);
 
  const resetFilters = useCallback(() => {
    setSelectedFilters({});
    if (lastCategoryNameRef.current)
      searchWithFilters(lastCategoryNameRef.current, {}, extractedAttrRef.current);
  }, [searchWithFilters]);
 
  // ── snapshot ──
  const snapshot = useMemo(() => ({
    activeFilters, selectedFilters, extractedAttributes,
    conversationId, lastCategoryName, originalUserInput,
    productCount, lastProductsMsgId,
  }), [activeFilters, selectedFilters, extractedAttributes,
      conversationId, lastCategoryName, originalUserInput,
      productCount, lastProductsMsgId]);
 
  const hydrate = useCallback((saved) => {
    if (!saved) return;
    if (saved.activeFilters?.length)   setActiveFilters(saved.activeFilters);
    if (saved.selectedFilters)         setSelectedFilters(saved.selectedFilters);
    if (saved.extractedAttributes)     setExtractedAttributes(saved.extractedAttributes);
    if (saved.conversationId)          setConversationId(saved.conversationId);
    if (saved.lastCategoryName)        setLastCategoryName(saved.lastCategoryName);
    if (saved.originalUserInput)       setOriginalUserInput(saved.originalUserInput);
    if (saved.productCount    != null) setProductCount(saved.productCount);
    if (saved.lastProductsMsgId)       setLastProductsMsgId(saved.lastProductsMsgId);
  }, []);
  
  // ─────────────────────────────────────────────────────────────
  // Handle job completion - when polling returns results
  // ─────────────────────────────────────────────────────────────
  useEffect(() => {
    if (pollingError) {
      onAddMsgRef.current({ type: 'bot', text: `❌ Lỗi: ${pollingError}`, timestamp: new Date() });
      setProductsLoading(false);
      return;
    }
    
    if (jobResult && !pollingLoading) {
      console.log('[UseProductSearch] Job result received:', jobResult);
      setProductsLoading(false);
      
      // Update category name from result if available
      if (jobResult.category) {
        setLastCategoryName(jobResult.category);
      }
      
      if (jobResult.status === 'need_info' && jobResult.question) {
        onAddMsgRef.current({
          type: 'bot',
          text: jobResult.question,
          quickReplies: jobResult.options?.map(o => o.label || o.value || o) ?? null,
          timestamp: new Date(),
        });
      } else if (jobResult.products?.length) {
        appendProducts(jobResult.products, jobResult.filters, jobResult.total);
      } else if (jobResult.category) {
        onAddMsgRef.current({
          type: 'bot',
          text: `ℹ️ Hiện tại chưa có sản phẩm "${jobResult.category}" trong kho.\n\nVui lòng thử mô tả khác.`,
          timestamp: new Date(),
        });
      }
      
      setJobId(null); // Reset job ID after processing
    }
  }, [jobResult, pollingLoading, pollingError, appendProducts]);
 
  return {
    productsLoading,
    activeFilters, selectedFilters, productCount,
    conversationId, lastCategoryName, originalUserInput,
    analyzeAndSearch, sendToBackend,
    toggleFilter, applyFilters, resetFilters,
    snapshot, hydrate,
  };
};
 