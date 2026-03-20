import React, { useState, useEffect, useRef, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Send, Sparkles, CheckCircle2, AlertCircle, ShoppingBag, Mic, MicOff, Volume2, User, Lock, Eye, EyeOff, LogOut, Heart, Clock, Tag, Gift, ChevronDown, ChevronRight, X, Search, SlidersHorizontal, Brain, Flame, RotateCcw } from 'lucide-react';
import axios from 'axios';
// import SuggestionsPopup from './SuggestionsPopup';  // ← TEMPORARILY DISABLED: Using sidebar filters instead
import { SharedHeader, LoginModal } from './SharedHeader';
import { useAuth } from '../context/AuthContext';
import FavoritesList from './FavoritesList';
import { addToFavorites, removeFromFavorites } from '../utils/favoritesApi';

const API_BASE_URL = 'http://localhost:8000';

// ─── DATA ────────────────────────────────────────────────────────────────────
const CATEGORIES = [
  { icon: '👟', label: 'Giày đẹp' },
  { icon: '⌚', label: 'Đồng hồ thông minh' },
  { icon: '🎧', label: 'Tai nghe' },
  { icon: '📱', label: 'Điện thoại' },
  { icon: '🎒', label: 'Phụ kiện' },
  { icon: '🛍️', label: 'Accessories' },
];
const QUICK_SEARCHES = [
  { icon: '👟', label: 'Giày chạy bộ' },
  { icon: '🎧', label: 'Tai nghe bluetooth' },
  { icon: '🎁', label: 'Quà sinh nhật cho bạn gái' },
  { icon: '⌚', label: 'Đồng hồ thông minh' },
];
const POPULAR_PRODUCTS = [
  { name: 'Nike Air Force 1', price: '2.400.000đ', sales: null },
  { name: 'AirPods Pro 2', price: '5.300.000đ', sales: '630 ches' },
  { name: 'Xiaomi Redmi Watch 3', price: '1.890.000đ', sales: '410 ches' },
  { name: 'Song GaN 65W', price: '359.000đ', sales: '1670 ches' },
];
const EXAMPLE_QUERIES = [
  'Giày Nike chạy bộ dưới 2 triệu',
  'Sneaker trắng size 42',
  'Tai nghe chống ồn tốt',
  'Quà sinh nhật cho bạn gái dưới 500K',
];

// ─── FILTER SIDEBAR ───────────────────────────────────────────────────────────
/*
  Thay thế hoàn toàn filter bubble trong chat.
  Layout: sidebar trái cố định 256px + nội dung chat/sản phẩm bên phải.
  - Không hiển thị số lượng sản phẩm trên mỗi option
  - Chip style gọn, collapse/expand theo group
  - Nút "Áp dụng" chỉ hiện khi có filter được chọn
*/
const FilterSidebar = ({ filters, selectedFilters, onToggle, onApply, onReset, resultCount, isLoading }) => {
  const [openGroups, setOpenGroups] = useState({});

  // Mở hết tất cả groups khi filters thay đổi
  useEffect(() => {
    if (filters?.length) {
      const init = {};
      filters.forEach((_, i) => { init[i] = true; });
      setOpenGroups(init);
    }
  }, [filters]);

  const activeCount = Object.keys(selectedFilters).length;
  const toggleGroup = (i) => setOpenGroups(p => ({ ...p, [i]: !p[i] }));

  return (
    <div style={{
      width: 256, flexShrink: 0,
      borderRight: '1px solid #ebe9f8',
      background: '#fafafa',
      display: 'flex', flexDirection: 'column',
      height: '100%',
    }}>
      <style>{`
        @keyframes sidebarIn { from{opacity:0;transform:translateX(-10px)} to{opacity:1;transform:translateX(0)} }
        .filter-sidebar { animation: sidebarIn 0.3s ease; }
        .fchip {
          padding: 5px 12px; border-radius: 16px; font-size: 12.5px; font-weight: 500;
          border: 1.5px solid #e2e8f0; background: #fff; color: #475569;
          cursor: pointer; transition: all 0.14s; white-space: nowrap; font-family: inherit;
          line-height: 1.4;
        }
        .fchip:hover { border-color: #6366f1; color: #6366f1; background: #eef2ff; }
        .fchip.on {
          border-color: #6366f1; background: #6366f1; color: #fff;
          box-shadow: 0 2px 6px rgba(99,102,241,0.28);
        }
        .group-toggle {
          width: 100%; display: flex; align-items: center; justify-content: space-between;
          padding: 11px 16px; background: none; border: none; cursor: pointer;
          font-family: inherit; border-bottom: 1px solid #f0f0f8;
        }
        .group-toggle:hover { background: #f5f3ff; }
        .apply-btn {
          width: 100%; padding: 11px; border-radius: 10px; border: none;
          background: linear-gradient(135deg, #6366f1, #8b5cf6);
          color: #fff; font-weight: 700; font-size: 14px; cursor: pointer;
          font-family: inherit; transition: box-shadow 0.2s;
          box-shadow: 0 4px 14px rgba(99,102,241,0.3);
        }
        .apply-btn:hover { box-shadow: 0 6px 20px rgba(99,102,241,0.45); }
        .reset-btn {
          display: flex; align-items: center; gap: 4px;
          color: #94a3b8; font-size: 12px; background: none; border: none;
          cursor: pointer; font-family: inherit; padding: 0;
        }
        .reset-btn:hover { color: #6366f1; }
      `}</style>

      <div className="filter-sidebar" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* ── Sidebar header ── */}
        <div style={{
          padding: '14px 16px 12px',
          borderBottom: '1px solid #ebe9f8',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <SlidersHorizontal size={15} color="#6366f1" />
            <span style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b' }}>Bộ lọc</span>
            {activeCount > 0 && (
              <span style={{
                background: '#6366f1', color: '#fff',
                borderRadius: 10, padding: '1px 7px',
                fontSize: 11, fontWeight: 700, lineHeight: 1.6,
              }}>{activeCount}</span>
            )}
          </div>
          {activeCount > 0 && (
            <button className="reset-btn" onClick={onReset}>
              <RotateCcw size={11} /> Xóa tất cả
            </button>
          )}
        </div>

        {/* ── Result count pill ── */}
        {resultCount != null && (
          <div style={{ padding: '10px 16px', flexShrink: 0 }}>
            <div style={{
              background: 'linear-gradient(135deg,#eef2ff,#f0f7ff)',
              border: '1px solid #e0e7ff', borderRadius: 8,
              padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <CheckCircle2 size={13} color="#6366f1" />
              <span style={{ fontSize: 13, color: '#4f46e5', fontWeight: 600 }}>
                {isLoading ? 'Đang tìm...' : `${resultCount} sản phẩm`}
              </span>
            </div>
          </div>
        )}

        {/* ── Filter groups (scrollable) ── */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0 8px' }}>
          {filters.map((filter, fi) => {
            const isOpen = openGroups[fi] !== false;
            return (
              <div key={fi} style={{ borderBottom: '1px solid #f0f0f8' }}>
                {/* Group header */}
                <button className="group-toggle" onClick={() => toggleGroup(fi)}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>
                    {filter.display_name || filter.attribute_name}
                  </span>
                  <ChevronDown
                    size={14} color="#9ca3af"
                    style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}
                  />
                </button>

                {/* Chips */}
                {isOpen && (
                  <div style={{ padding: '8px 14px 12px', display: 'flex', flexWrap: 'wrap', gap: 7 }}>
                    {filter.options?.map((opt, oi) => {
                      const key = `${filter.attribute_name}:${opt.attribute_value}`;
                      const active = !!selectedFilters[key];
                      return (
                        <button
                          key={oi}
                          className={`fchip${active ? ' on' : ''}`}
                          onClick={() => onToggle(key)}
                        >
                          {opt.attribute_value}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* ── Apply button ── */}
        <div style={{ padding: '12px 16px', borderTop: '1px solid #ebe9f8', flexShrink: 0 }}>
          {activeCount > 0 ? (
            <button className="apply-btn" onClick={onApply}>
              Áp dụng ({activeCount} tiêu chí)
            </button>
          ) : (
            <p style={{ margin: 0, fontSize: 12, color: '#b0b7c3', textAlign: 'center', fontStyle: 'italic' }}>
              Chọn tiêu chí để lọc sản phẩm
            </p>
          )}
        </div>
      </div>
    </div>
  );
};

// ─── USER QUICK ACTIONS ───────────────────────────────────────────────────────
const UserQuickActions = ({ onAction, onFavoritesClick }) => (
  <div style={{ display: 'flex', gap: 8, paddingBottom: 10, flexWrap: 'wrap' }}>
    {[
      { icon: <Heart size={14} />, label: 'Sản phẩm yêu thích', color: '#e11d48', bg: '#fff1f2', border: '#fecdd3', onClick: onFavoritesClick },
      { icon: <Clock size={14} />, label: 'Tìm kiếm gần đây',   color: '#6366f1', bg: '#eef2ff', border: '#c7d2fe', onClick: () => onAction('Tìm kiếm gần đây') },
      { icon: <Tag  size={14} />, label: 'Ưu đãi hôm nay',      color: '#d97706', bg: '#fffbeb', border: '#fde68a', onClick: () => onAction('Ưu đãi hôm nay') },
      { icon: <Gift size={14} />, label: 'Gợi ý cho bạn',       color: '#059669', bg: '#ecfdf5', border: '#a7f3d0', onClick: () => onAction('Gợi ý cho bạn') },
    ].map((a, i) => (
      <button key={i} onClick={a.onClick}
        style={{ display:'flex', alignItems:'center', gap:6, padding:'6px 14px', borderRadius:20, border:`1.5px solid ${a.border}`, background:a.bg, color:a.color, fontSize:13, fontWeight:600, cursor:'pointer', transition:'all 0.15s', fontFamily:'inherit' }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = `0 3px 10px ${a.border}`; }}
        onMouseLeave={e => { e.currentTarget.style.transform = 'none'; e.currentTarget.style.boxShadow = 'none'; }}
      >{a.icon}{a.label}</button>
    ))}
  </div>
);

// ─── MAIN COMPONENT ───────────────────────────────────────────────────────────
const ShoeFinder = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { user, showLoginModal, setShowLoginModal, token } = useAuth();

  // ── Helper: Save to sessionStorage ──
  const saveSearchState = (state) => {
    try {
      sessionStorage.setItem('shoeFinderSearchState', JSON.stringify(state));
    } catch (e) {
      console.warn('[SessionStorage] Failed to save search state:', e);
    }
  };

  const restoreSearchState = () => {
    try {
      const saved = sessionStorage.getItem('shoeFinderSearchState');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      console.warn('[SessionStorage] Failed to restore search state:', e);
      return null;
    }
  };

  const clearSearchState = () => {
    try {
      sessionStorage.removeItem('shoeFinderSearchState');
    } catch (e) {
      console.warn('[SessionStorage] Failed to clear search state:', e);
    }
  };

  // ── Restore state from sessionStorage if available ──
  const currentQuery = searchParams.get('q');
  const savedState = restoreSearchState();
  
  // Only restore if URL query matches saved state (prevents mix-up when searching different terms)
  const shouldRestore = savedState && currentQuery === savedState.originalUserInput;
  const lastAutoStartedQueryRef = useRef(null);  // Track which query we've auto-started for

  // ── Chat messages (bot/user bubbles only — NO filters/results in messages) ──
  const [messages, setMessages] = useState(shouldRestore ? savedState.messages : []);
  const [currentInput, setCurrentInput] = useState('');
  const [conversationState, setConversationState] = useState(shouldRestore ? savedState.conversationState : { conversationId: null, isLoading: false });
  const [isThinking, setIsThinking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isBrowserSupported, setIsBrowserSupported] = useState(true);

  // ── Filter & product state (lifted out of messages) ──
  const [activeFilters, setActiveFilters]     = useState(shouldRestore ? savedState.activeFilters : []);
  const [selectedFilters, setSelectedFilters] = useState(shouldRestore ? savedState.selectedFilters : {});
  const [products, setProducts]               = useState(shouldRestore ? savedState.products : null);
  const [productCount, setProductCount]       = useState(shouldRestore ? savedState.productCount : null);
  const [productsLoading, setProductsLoading] = useState(false);
  
  // ── Favorites state ──
  const [showFavoritesList, setShowFavoritesList] = useState(false);
  const [favoriteProductIds, setFavoriteProductIds] = useState(new Set());
  const [lastCategoryName, setLastCategoryName] = useState(shouldRestore ? savedState.lastCategoryName : '');
  const [extractedAttributes, setExtractedAttributes] = useState(shouldRestore ? savedState.extractedAttributes : {});
  const [originalUserInput, setOriginalUserInput] = useState(shouldRestore ? savedState.originalUserInput : '');

  // ── Suggestions popup ── (TEMPORARILY DISABLED)
  // const [clarifyingHints, setClarifyingHints]             = useState([]);
  // const [showSuggestionsPopup, setShowSuggestionsPopup]   = useState(false);
  // const [suggestionsPopupFilters, setSuggestionsPopupFilters] = useState([]);

  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  // ── Auto-save state to sessionStorage whenever search-related state changes ──
  useEffect(() => {
    const stateToSave = {
      messages,
      conversationState,
      activeFilters,
      selectedFilters,
      products,
      productCount,
      lastCategoryName,
      extractedAttributes,
      originalUserInput,
    };
    saveSearchState(stateToSave);
  }, [messages, conversationState, activeFilters, selectedFilters, products, productCount, lastCategoryName, extractedAttributes, originalUserInput]);

  // ── Clear session state when navigating home ──
  const handleLogoClick = () => {
    clearSearchState();
    navigate('/');
  };

  // Speech recognition setup
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setIsBrowserSupported(false); return; }
    const r = new SR();
    r.continuous = true; r.interimResults = true; r.lang = 'vi-VN';
    r.onstart  = () => { setIsListening(true); setTranscript(''); };
    r.onresult = (e) => {
      let interim = '', final = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) final += t + ' '; else interim += t;
      }
      setTranscript(interim);
      if (final) setCurrentInput(p => (p + ' ' + final).trim());
    };
    r.onerror = () => setIsListening(false);
    r.onend   = () => { setIsListening(false); setTranscript(''); };
    recognitionRef.current = r;
    return () => recognitionRef.current?.abort();
  }, []);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, products]);

  // ── Helpers ──
  const addBot  = (text, quickReplies = null) => setMessages(p => [...p, { type:'bot',  text, quickReplies, timestamp: new Date() }]);
  const addUser = (text)                      => setMessages(p => [...p, { type:'user', text, timestamp: new Date() }]);

  const applyProductResults = (prods, filters, total) => {
    // Add products as a message in the chat stream so they become part of conversation history
    setMessages(p => [...p, { 
      type: 'products', 
      products: prods ?? [], 
      productCount: total ?? prods?.length ?? 0,
      filters: filters,
      timestamp: new Date() 
    }]);
    // Also update sidebar filter state
    if (filters?.length) setActiveFilters(filters);
    // Keep products in state for sidebar to reference
    setProducts(prods ?? []);
    setProductCount(total ?? prods?.length ?? 0);
  };

  // Helper: Merge extracted (from search) + selected (from user filters) attributes
  // extracted: {brand: ["Nike"], color: ["Đen"]}
  // selected: {size: ["40"]}
  // result: {brand: ["Nike"], color: ["Đen"], size: ["40"]}
  const mergeFilters = (extracted = {}, selected = {}) => {
    const merged = { ...extracted };
    Object.entries(selected).forEach(([attr, values]) => {
      if (merged[attr]) {
        console.warn(`[Filter] Overriding extracted ${attr} with user-selected values`);
      }
      merged[attr] = values;
    });
    return merged;
  };

  // ── Memoized API calls and handlers ──
  const analyzeAndSearch = useCallback(async (userInput) => {
    setIsThinking(true);
    setProductsLoading(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/analyze`, {
        user_input: userInput,
        conversation_id: conversationState.conversationId,
      }, {
        headers: {
          'Authorization': token ? `Bearer ${token}` : undefined,
          'Content-Type': 'application/json'
        }
      });
      const d = res.data;
      if (!d.success) { 
        setMessages(p => [...p, { type:'bot', text:`❌ ${d.error}`, quickReplies: null, timestamp: new Date() }]); 
        return; 
      }

      setConversationState(p => ({ ...p, conversationId: d.conversation_id }));
      setLastCategoryName(d.category);
      setSelectedFilters({});
      
      // Capture extracted attributes from backend (e.g., {brand: "Nike"} from input)
      // Convert to array format: {brand: ["Nike"]}
      if (d.selected_attributes && Object.keys(d.selected_attributes).length > 0) {
        const extracted = {};
        Object.entries(d.selected_attributes).forEach(([attr, value]) => {
          if (value === null || value === undefined) return;
          extracted[attr] = Array.isArray(value) ? value.map(v => String(v)) : [String(value)];
        });
        setExtractedAttributes(extracted);
        console.log('[Filter] Extracted attributes from search:', extracted);
      } else {
        setExtractedAttributes({});
      }
      
      // Handle question/clarification from backend
      if (d.status === 'need_info' && d.question) {
        setMessages(p => [...p, { type:'bot', text: d.question, quickReplies: d.options ? d.options.map(o => o.label || o.value || o) : null, timestamp: new Date() }]);
        // Keep previous products/results visible - don't clear them when asking clarifying questions
      } else if (d.products?.length) {
        applyProductResults(d.products, d.filters, d.total);
      } else {
        setMessages(p => [...p, { type:'bot', text:`ℹ️ Hiện tại chưa có sản phẩm "${d.category}" trong kho.\n\nVui lòng thử mô tả khác.`, quickReplies: null, timestamp: new Date() }]);
        // Keep previous products visible - don't clear them when backend has no results
      }
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Có lỗi xảy ra';
      setMessages(p => [...p, { type:'bot', text:`❌ Lỗi: ${msg}`, quickReplies: null, timestamp: new Date() }, { type:'bot', text:'Vui lòng chắc chắn backend Python đang chạy trên http://localhost:8000', quickReplies: null, timestamp: new Date() }]);
    } finally {
      setIsThinking(false);
      setProductsLoading(false);
    }
  }, [conversationState.conversationId, token]);

  const startSearch = useCallback((query) => {
    // Keep previous messages - just append the new search query to continue conversation
    setMessages(p => [...p, { type:'user', text: query, timestamp: new Date() }]);
    // Don't clear products - keep them visible while loading new results for conversation feel
    setActiveFilters([]);
    setSelectedFilters({});
    setExtractedAttributes({});
    setOriginalUserInput(query);
    setProductCount(null);
    setTimeout(() => { 
      analyzeAndSearch(query); 
    }, 50);
  }, [analyzeAndSearch]);

  const sendToBackend = async (userInput) => {
    setIsThinking(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/query`, {
        user_input: userInput,
        conversation_id: conversationState.conversationId,
      });
      const d = res.data;
      if (d.conversation_id) setConversationState(p => ({ ...p, conversationId: d.conversation_id }));
      // if (d.clarifying_hints) setClarifyingHints(d.clarifying_hints);  // Disabled: popup disabled
      if (d.status === 'results' && d.products?.length) {
        applyProductResults(d.products, d.filters, d.total_found);
      } else if (d.question) {
        addBot(d.question, d.options ? d.options.map(o => o.label || o.value || o) : null);
      }
    } catch (err) {
      addBot(`❌ Lỗi: ${err.response?.data?.detail || err.message}`);
    } finally { setIsThinking(false); }
  };

  const searchProductsWithFilters = async (categoryName, filters = {}, extracted = {}) => {
    setProductsLoading(true);
    // Don't clear products - keep them visible while loading new results for conversation feel
    try {
      // Convert "attr:val" keys → { attr: [val] }
      let selectedFilters = filters;
      if (Object.keys(filters).some(k => k.includes(':'))) {
        selectedFilters = {};
        Object.keys(filters).forEach(k => {
          const [a, v] = k.split(':');
          if (!selectedFilters[a]) selectedFilters[a] = [];
          selectedFilters[a].push(v);
        });
      }
      
      // MERGE: extracted attributes (from user input) + user-selected filters
      const finalFilters = mergeFilters(extracted, selectedFilters);
      
      console.log('[Filter] Final merged filters:', finalFilters);
      
      const res = await fetch(`${API_BASE_URL}/api/v1/crawl-products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ category_name: categoryName, selected_filters: finalFilters, page: 1, page_size: 20 }),
      });
      if (!res.ok) { const e = await res.json(); throw new Error(e.detail || `HTTP ${res.status}`); }
      const data = await res.json();
      if (!data.products?.length) {
        addBot('🔍 Không tìm thấy sản phẩm nào phù hợp với bộ lọc này.');
        // Keep previous products visible - don't clear them
        return;
      }
      applyProductResults(data.products, data.filters, data.total);
    } catch (err) {
      addBot(`❌ Lỗi: ${err.message}`);
      // Keep previous products visible on error
    } finally { setProductsLoading(false); }
  };

  const handleSend = () => {
    if (!currentInput.trim() || isThinking) return;
    addUser(currentInput);
    analyzeAndSearch(currentInput);
    setCurrentInput('');
  };

  // Filter sidebar handlers
  const handleFilterToggle = (key) =>
    setSelectedFilters(p => { const n = { ...p }; if (n[key]) delete n[key]; else n[key] = true; return n; });

  const handleFilterApply = () => {
    if (lastCategoryName) searchProductsWithFilters(lastCategoryName, selectedFilters, extractedAttributes);
  };

  const handleFilterReset = () => {
    setSelectedFilters({});
    // Keep extractedAttributes when resetting user-selected filters
    // This preserves the original search context (e.g., brand Nike)
    if (lastCategoryName) searchProductsWithFilters(lastCategoryName, {}, extractedAttributes);
  };

  // Show sidebar when we have filter definitions
  const showSidebar = activeFilters.length > 0 && products !== null;

  // Auto-start from URL query param (only if NOT restored from session)
  // Use ref to track which query we've auto-started for, preventing duplicate API calls
  useEffect(() => {
    const shouldAutoStart = currentQuery && 
                          currentQuery !== lastAutoStartedQueryRef.current && 
                          !shouldRestore;  // Don't auto-start if restoring from cache
    if (shouldAutoStart) {
      lastAutoStartedQueryRef.current = currentQuery;
      startSearch(currentQuery);
    }
  }, [currentQuery, shouldRestore, startSearch]);

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <style>{`
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
        @keyframes bounce  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
        @keyframes fadeIn  { from{opacity:0} to{opacity:1} }
        .product-card { background:#fff; border:1.5px solid #f0f0f8; border-radius:14px; overflow:hidden; cursor:pointer; transition:all 0.18s; }
        .product-card:hover { border-color:#6366f1; transform:translateY(-3px); box-shadow:0 8px 24px rgba(99,102,241,0.16); }
      `}</style>

      <SharedHeader onLogoClick={handleLogoClick} />

      <>
        {/* ════ FAVORITES LIST VIEW ════ */}
        {showFavoritesList ? (
          <div style={{ flex: 1, overflow: 'hidden', background: 'linear-gradient(160deg,#f5f7ff,#f0f4ff)', padding: 16 }}>
            <FavoritesList 
              token={token}
              user={user}
              onBack={() => setShowFavoritesList(false)}
              onProductClick={(url) => {
                if (url) {
                  fetch('http://localhost:8000/api/open-product', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ product_url: url }),
                  })
                    .then(r => r.json())
                    .then(d => { if (!d.success) window.open(url, '_blank'); })
                    .catch(() => window.open(url, '_blank'));
                }
              }}
            />
          </div>
        ) : (
          <div style={{ flex: 1, display: 'flex', overflow: 'hidden', background: 'linear-gradient(160deg,#f5f7ff,#f0f4ff)' }}>

            {/* ── Filter sidebar (only when results available) ── */}
            {showSidebar && (
              <FilterSidebar
                filters={activeFilters}
                selectedFilters={selectedFilters}
                onToggle={handleFilterToggle}
                onApply={handleFilterApply}
                onReset={handleFilterReset}
                resultCount={productCount}
                isLoading={productsLoading}
              />
            )}

            {/* ── Main column ── */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

            {/* Back link */}
            <div style={{ padding: '12px 20px 0', flexShrink: 0 }}>
              <button
                onClick={handleLogoClick}
                style={{ display:'flex', alignItems:'center', gap:5, color:'#6366f1', fontSize:13, fontWeight:600, background:'none', border:'none', cursor:'pointer', padding:0, fontFamily:'inherit' }}
              >
                ← Về trang chủ
              </button>
            </div>

            {/* Scrollable area: chat bubbles + products */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '14px 40px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{ width: '100%', maxWidth: 680 }}>

              {/* ── Chat bubbles (bot / user only) ── */}
              {messages.length > 0 && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 14, marginBottom: 20 }}>
                  {messages.map((msg, idx) => (
                    <div key={idx}>

                      {msg.type === 'bot' && (
                        <div style={{ display:'flex', gap:12 }}>
                          <div style={{ width:36, height:36, borderRadius:'50%', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                            <Sparkles size={16} color="#fff" />
                          </div>
                          <div>
                            <div style={{ background:'#fff', borderRadius:'16px 16px 16px 4px', padding:'12px 16px', maxWidth:520, boxShadow:'0 2px 8px rgba(0,0,0,0.06)', border:'1px solid #f0f0f8', whiteSpace:'pre-wrap', color:'#1e1b4b', fontSize:14, lineHeight:1.6 }}>
                              {msg.text}
                            </div>
                            {msg.quickReplies && (
                              <div style={{ display:'flex', flexWrap:'wrap', gap:8, marginTop:9 }}>
                                {msg.quickReplies.map((r, i) => (
                                  <button key={i}
                                    onClick={() => { addUser(r); sendToBackend(r); }}
                                    style={{ padding:'7px 15px', background:'#fff', border:'2px solid #c7d2fe', color:'#4f46e5', borderRadius:20, fontSize:13, fontWeight:600, cursor:'pointer', fontFamily:'inherit' }}
                                    onMouseEnter={e => e.currentTarget.style.background = '#eef2ff'}
                                    onMouseLeave={e => e.currentTarget.style.background = '#fff'}
                                  >{r}</button>
                                ))}
                              </div>
                            )}
                          </div>
                        </div>
                      )}

                      {msg.type === 'user' && (
                        <div style={{ display:'flex', justifyContent:'flex-end' }}>
                          <div style={{ background:'linear-gradient(135deg,#6366f1,#8b5cf6)', color:'#fff', borderRadius:'16px 16px 4px 16px', padding:'12px 16px', maxWidth:440, boxShadow:'0 3px 12px rgba(99,102,241,0.28)', fontSize:14, lineHeight:1.5 }}>
                            {msg.text}
                          </div>
                        </div>
                      )}

                    </div>
                  ))}

                  {/* Thinking indicator */}
                  {isThinking && (
                    <div style={{ display:'flex', gap:12 }}>
                      <div style={{ width:36, height:36, borderRadius:'50%', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                        <Sparkles size={16} color="#fff" />
                      </div>
                      <div style={{ background:'#fff', borderRadius:'16px 16px 16px 4px', padding:'13px 16px', boxShadow:'0 2px 8px rgba(0,0,0,0.06)', border:'1px solid #f0f0f8', display:'flex', gap:5 }}>
                        {[0, 150, 300].map(d => (
                          <div key={d} style={{ width:7, height:7, borderRadius:'50%', background:'#a5b4fc', animation:`bounce 1.2s ease-in-out ${d}ms infinite` }} />
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* ── Product grid (always show if products exist, even while loading) ── */}
              {/* Show skeleton while loading NEW results */}
              {productsLoading && (
                <div style={{ animation:'fadeIn 0.2s ease', marginBottom: 20, opacity: 0.6 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
                    <div style={{ width: 15, height: 15, borderRadius: '50%', background: '#a5b4fc', animation: 'bounce 1.2s ease-in-out infinite' }} />
                    <span style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b' }}>
                      Đang tìm kết quả mới...
                    </span>
                  </div>
                  <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(148px,1fr))', gap:12 }}>
                    {[...Array(6)].map((_, i) => (
                      <div key={i} style={{ background:'#fff', border:'1.5px solid #f0f0f8', borderRadius:14, overflow:'hidden' }}>
                        <div style={{ height:128, background:'linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%)', backgroundSize:'200% 100%', animation:'shimmer 1.5s infinite' }} />
                        <div style={{ padding:'9px 11px' }}>
                          <div style={{ height:11, background:'#f1f5f9', borderRadius:6, marginBottom:7 }} />
                          <div style={{ height:11, background:'#f1f5f9', borderRadius:6, width:'60%' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Show existing/new products */}
              {products && products.length > 0 && (
                <div style={{ animation:'fadeIn 0.3s ease' }}>
                  <div style={{ display:'flex', alignItems:'center', gap:8, marginBottom:14 }}>
                    <CheckCircle2 size={15} color="#10b981" />
                    <span style={{ fontWeight:700, fontSize:14, color:'#1e1b4b' }}>
                      Tìm thấy {productCount} sản phẩm
                    </span>
                  </div>
                  <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(148px,1fr))', gap:12 }}>
                    {products.map((product, i) => {
                      // Handle both backend response formats
                      const productUrl = product.product_url || product.link;
                      const productImage = product.thumbnail || product.image;
                      const productPrice = product.price || product.skus?.[0]?.price;
                      const isFavorited = favoriteProductIds.has(product.id);
                      
                      const toggleFavorite = async (e) => {
                        e.stopPropagation();
                        if (!user || !token) {
                          alert('Vui lòng đăng nhập để sử dụng tính năng này');
                          return;
                        }
                        
                        try {
                          if (isFavorited) {
                            await removeFromFavorites(product.id, token);
                            setFavoriteProductIds(prev => {
                              const newSet = new Set(prev);
                              newSet.delete(product.id);
                              return newSet;
                            });
                          } else {
                            await addToFavorites(product.id, token);
                            setFavoriteProductIds(prev => new Set(prev).add(product.id));
                          }
                        } catch (err) {
                          console.error('Error toggling favorite:', err);
                          alert('Lỗi: ' + err.message);
                        }
                      };
                      
                      return (
                        <div
                          key={product.id || i}
                          className="product-card"
                          onClick={() => {
                            if (productUrl) {
                              fetch('http://localhost:8000/api/open-product', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ product_url: productUrl }),
                              })
                                .then(r => r.json())
                                .then(d => { if (d.success) addBot('🎬 Đang mở sản phẩm trong Chrome...'); else window.open(productUrl, '_blank'); })
                                .catch(() => window.open(productUrl, '_blank'));
                            }
                          }}
                        >
                          {productImage && (
                            <div style={{ background:'#f8f9ff', height:128, display:'flex', alignItems:'center', justifyContent:'center', overflow:'hidden', position:'relative' }}>
                              <img src={productImage} alt={product.title} style={{ maxWidth:'100%', maxHeight:'100%', objectFit:'contain' }} />
                              {i === 0 && (
                                <div style={{ position:'absolute', top:7, right:7, background:'linear-gradient(135deg,#f59e0b,#d97706)', color:'#fff', fontSize:9.5, fontWeight:700, padding:'2px 7px', borderRadius:7 }}>
                                  TOP
                                </div>
                              )}
                              {/* Favorite Button */}
                              <button
                                onClick={toggleFavorite}
                                style={{
                                  position: 'absolute',
                                  bottom: 6,
                                  right: 6,
                                  background: isFavorited ? '#e11d48' : 'rgba(255,255,255,0.9)',
                                  border: isFavorited ? 'none' : '1.5px solid #e2e8f0',
                                  color: isFavorited ? '#fff' : '#e11d48',
                                  borderRadius: '50%',
                                  width: 32,
                                  height: 32,
                                  display: 'flex',
                                  alignItems: 'center',
                                  justifyContent: 'center',
                                  cursor: 'pointer',
                                  transition: 'all 0.2s',
                                  boxShadow: isFavorited ? '0 2px 8px rgba(225,29,72,0.3)' : '0 2px 4px rgba(0,0,0,0.1)',
                                }}
                                onMouseEnter={e => {
                                  e.currentTarget.style.transform = 'scale(1.15)';
                                }}
                                onMouseLeave={e => {
                                  e.currentTarget.style.transform = 'scale(1)';
                                }}
                              >
                                <Heart size={16} fill={isFavorited ? '#fff' : 'none'} />
                              </button>
                            </div>
                          )}
                          <div style={{ padding:'9px 11px' }}>
                            <div style={{ fontSize:11.5, fontWeight:600, color:'#1e1b4b', lineHeight:1.4, display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden', marginBottom:5 }}>
                              {product.title}
                            </div>
                            {productPrice && (
                              <div style={{ fontSize:13, fontWeight:700, color:'#e11d48' }}>
                                {(productPrice / 1000000).toFixed(1)}tr
                              </div>
                            )}
                            {product.brand && (
                              <div style={{ fontSize:11, color:'#94a3b8', marginTop:2 }}>{product.brand}</div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
              </div>
            </div>

            {/* ════ INPUT BAR ════ */}
        <div style={{ borderTop:'1px solid #eff0f8', background:'#fff', padding:'14px 40px', flexShrink:0, boxShadow:'0 -4px 20px rgba(99,102,241,0.07)', display: 'flex', justifyContent: 'center' }}>
          <div style={{ width: '100%' }}>
          {isListening && transcript && (
            <div style={{ marginBottom:10, padding:'10px 14px', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:10, display:'flex', alignItems:'center', gap:8 }}>
              <Volume2 size={14} color="#6366f1" />
              <span style={{ fontSize:13, color:'#4f46e5' }}>Đang nghe: <strong>{transcript}</strong></span>
            </div>
          )}

          {user && (
            <UserQuickActions 
              onAction={a => { addUser(`📌 ${a}`); addBot(`Tính năng "${a}" đang được phát triển. Bạn muốn tìm kiếm sản phẩm gì?`); }} 
              onFavoritesClick={() => setShowFavoritesList(true)}
            />
          )}

          <div style={{ display:'flex', gap:10, alignItems:'center' }}>
            <input
              type="text" value={currentInput}
              onChange={e => setCurrentInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="Nhập câu trả lời của bạn hoặc nói vào micro..."
              disabled={isThinking}
              style={{ flex:1, padding:'13px 20px', border:'2px solid #e8eaf6', borderRadius:28, fontSize:14.5, color:'#1e1b4b', outline:'none', background:'#f8f9ff', transition:'all 0.2s', fontFamily:'inherit' }}
              onFocus={e => { e.target.style.borderColor = '#6366f1'; e.target.style.background = '#fff'; }}
              onBlur={e  => { e.target.style.borderColor = '#e8eaf6'; e.target.style.background = '#f8f9ff'; }}
            />
            {isBrowserSupported && (
              <button
                onClick={() => {
                  if (!recognitionRef.current) return;
                  if (isListening) recognitionRef.current.stop();
                  else try { recognitionRef.current.start(); } catch (e) { console.error(e); }
                }}
                disabled={isThinking}
                style={{ width:46, height:46, borderRadius:'50%', border:'none', cursor:'pointer', background:isListening?'linear-gradient(135deg,#ef4444,#dc2626)':'#f1f5f9', color:isListening?'#fff':'#64748b', display:'flex', alignItems:'center', justifyContent:'center', transition:'all 0.2s', flexShrink:0, boxShadow:isListening?'0 4px 16px rgba(239,68,68,0.4)':'none' }}
              >
                {isListening ? <MicOff size={18} /> : <Mic size={18} />}
              </button>
            )}
            <button
              onClick={handleSend}
              disabled={!currentInput.trim() || isThinking}
              style={{ width:46, height:46, borderRadius:'50%', border:'none', cursor:'pointer', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', transition:'all 0.2s', flexShrink:0, opacity:(!currentInput.trim()||isThinking)?0.45:1 }}
            >
              <Send size={18} />
            </button>
          </div>

          {!user && (
            <p style={{ margin:'8px 0 0', fontSize:12, color:'#94a3b8', textAlign:'center' }}>
              <button onClick={() => setShowLoginModal(true)} style={{ color:'#6366f1', fontWeight:600, background:'none', border:'none', cursor:'pointer', fontSize:12, padding:0, fontFamily:'inherit' }}>
                Đăng nhập
              </button>
              {' '}để lưu yêu thích & nhận gợi ý cá nhân hoá
            </p>
          )}
          </div>
        </div>
          </div>

          
          </div>
        )}
      </>

      {/* TEMPORARILY DISABLED: Using sidebar filters instead of popup
        <SuggestionsPopup
          isOpen={showSuggestionsPopup}
          onClose={() => setShowSuggestionsPopup(false)}
          category={lastCategoryName}
          filters={suggestionsPopupFilters}
          hints={clarifyingHints}
          onConfirm={f => { setShowSuggestionsPopup(false); searchProductsWithFilters(lastCategoryName, f); }}
          conversationId={conversationState.conversationId}
        />
        */}


      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />
    </div>
  );
};

export default ShoeFinder;