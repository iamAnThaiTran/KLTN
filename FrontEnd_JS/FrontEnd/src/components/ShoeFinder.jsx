import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';

import { SharedHeader, LoginModal } from './SharedHeader';
import ProductComparison from './ProductComparison';
import { useAuth } from '../context/AuthContext';
import { addToFavorites, removeFromFavorites } from '../utils/favoritesApi';

import { useProductSearch } from '../hooks/UseProductSearch';
import { useSpeech }        from '../hooks/UseSpeech';
import { saveSearchState, restoreSearchState, clearSearchState } from '../utils/storage';
import FilterSidebar from './filter/FilterSideBar';
import ChatArea from './chatArea/ChatArea';
import InputBar from './search/InputBar';
import UserQuickActions from '../layout/Userquickaction';
import FavoritesList from './FavoritesList';

const GLOBAL_STYLES = `
  @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
  @keyframes bounce  { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-6px)} }
  @keyframes fadeIn  { from{opacity:0} to{opacity:1} }
  .product-card {
    background:#fff; border:1.5px solid #f0f0f8; border-radius:14px;
    overflow:hidden; cursor:pointer; transition:all 0.18s;
  }
  .product-card:hover {
    border-color:#6366f1; transform:translateY(-3px);
    box-shadow:0 8px 24px rgba(99,102,241,0.16);
  }
`;
 
const ShoeFinder = () => {
  const [searchParams] = useSearchParams();
  const navigate       = useNavigate();
  const { user, showLoginModal, setShowLoginModal, token } = useAuth();
 
  const currentQuery  = searchParams.get('q');
  const savedState    = restoreSearchState();
  const shouldRestore = savedState && currentQuery === savedState.originalUserInput;
  const lastAutoStartedQueryRef = useRef(null);
 
  // ── Messages (bot + user + products — tất cả trong 1 stream) ──
  const [messages,     setMessages]     = useState(shouldRestore ? savedState.messages : []);
  const [currentInput, setCurrentInput] = useState('');
  const [isThinking,   setIsThinking]   = useState(false);
 
  // ── Favorites ──
  const [showFavoritesList,  setShowFavoritesList]  = useState(false);
  const [favoriteProductIds, setFavoriteProductIds] = useState(new Set());
  const [showComparison, setShowComparison] = useState(false);
 
  const messagesEndRef = useRef(null);
 
  // ── addMessage: xử lý cả append mới lẫn update in-place ──
  const addMessage = useCallback((msg) => {
    if (msg.type === 'update_products') {
      // Tìm products message theo msgId và update tại chỗ
      setMessages(prev => prev.map(m =>
        m.msgId === msg.msgId
          ? { ...m, products: msg.products, productCount: msg.productCount, filters: msg.filters }
          : m
      ));
    } else {
      setMessages(prev => [...prev, msg]);
    }
  }, []);
 
  // ── Product search hook ──
  const search = useProductSearch({ token, onAddMessage: addMessage });
 
  // ── Speech hook ──
  const speech = useSpeech({
    onFinalTranscript: (final) => setCurrentInput(p => (p + ' ' + final).trim()),
  });
 
  // ── Auto-scroll ──
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);
 
  // ── Persist state ──
  useEffect(() => {
    saveSearchState({ messages, ...search.snapshot });
  }, [messages, search.snapshot]);
 
  // ── Hydrate ──
  useEffect(() => {
    if (shouldRestore) search.hydrate(savedState);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
 
  // ── Auto-start từ URL ──
  const startSearch = useCallback((query) => {
    setMessages(prev => [...prev, { type: 'user', text: query, timestamp: new Date() }]);
    search.analyzeAndSearch(query);
  }, [search]);
 
  useEffect(() => {
    if (currentQuery && currentQuery !== lastAutoStartedQueryRef.current && !shouldRestore) {
      lastAutoStartedQueryRef.current = currentQuery;
      startSearch(currentQuery);
    }
  }, [currentQuery, shouldRestore, startSearch]);
 
  // ── Send ──
  const handleSend = () => {
    if (!currentInput.trim() || isThinking || search.productsLoading) return;
    setMessages(prev => [...prev, { type: 'user', text: currentInput, timestamp: new Date() }]);
    search.analyzeAndSearch(currentInput);
    setCurrentInput('');
  };
 
  const handleLogoClick = () => { clearSearchState(); navigate('/'); };
 
  // ── Favorites toggle ──
  const handleToggleFavorite = async (product) => {
    if (!user || !token) { alert('Vui lòng đăng nhập để sử dụng tính năng này'); return; }
    try {
      if (favoriteProductIds.has(product.id)) {
        await removeFromFavorites(product.id, token);
        setFavoriteProductIds(prev => { const s = new Set(prev); s.delete(product.id); return s; });
      } else {
        await addToFavorites(product.id, token);
        setFavoriteProductIds(prev => new Set(prev).add(product.id));
      }
    } catch (err) { alert('Lỗi: ' + err.message); }
  };
 
  // ── Open product ──
  const handleOpenProduct = (productUrl) => {
    if (!productUrl) return;
    fetch('http://localhost:8000/api/open-product', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ product_url: productUrl }),
    })
      .then(r => r.json())
      .then(d => { if (!d.success) window.open(productUrl, '_blank'); })
      .catch(() => window.open(productUrl, '_blank'));
  };
 
  // Sidebar hiện khi có filter definitions
  const showSidebar = search.activeFilters.length > 0;
 
  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <style>{GLOBAL_STYLES}</style>
      <SharedHeader onLogoClick={handleLogoClick} onCompareClick={() => setShowComparison(true)} />
 
      {showFavoritesList ? (
        <div style={{ flex: 1, overflow: 'hidden', background: 'linear-gradient(160deg,#f5f7ff,#f0f4ff)', padding: 16 }}>
          <FavoritesList token={token} user={user} onBack={() => setShowFavoritesList(false)} onProductClick={handleOpenProduct} />
        </div>
      ) : (
        <div style={{ flex: 1, display: 'flex', overflow: 'hidden', background: 'linear-gradient(160deg,#f5f7ff,#f0f4ff)' }}>
 
          {showSidebar && (
            <FilterSidebar
              filters={search.activeFilters}
              selectedFilters={search.selectedFilters}
              onToggle={search.toggleFilter}
              onApply={search.applyFilters}
              onReset={search.resetFilters}
              resultCount={search.productCount}
              isLoading={search.productsLoading}
            />
          )}
 
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
 
            <div style={{ padding: '12px 20px 0', flexShrink: 0 }}>
              <button onClick={handleLogoClick}
                style={{ display: 'flex', alignItems: 'center', gap: 5, color: '#6366f1', fontSize: 13, fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', padding: 0, fontFamily: 'inherit' }}>
                ← Về trang chủ
              </button>
            </div>
 
            {/* Scrollable chat stream */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '14px 40px 20px', display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
              <div style={{ width: '100%', maxWidth: 680 }}>
 
                {/* TẤT CẢ messages (user + bot + products) trong 1 stream duy nhất */}
                <ChatArea
                  messages={messages}
                  isThinking={search.productsLoading}
                  onQuickReply={(r) => {
                    setMessages(prev => [...prev, { type: 'user', text: r, timestamp: new Date() }]);
                    search.sendToBackend(r);
                  }}
                  favoriteProductIds={favoriteProductIds}
                  onToggleFavorite={handleToggleFavorite}
                  onOpen={handleOpenProduct}
                />
 
                <div ref={messagesEndRef} />
              </div>
            </div>
 
            <InputBar
              value={currentInput}
              onChange={e => setCurrentInput(e.target.value)}
              onSend={handleSend}
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              isThinking={search.productsLoading}
              isListening={speech.isListening}
              transcript={speech.transcript}
              isBrowserSupported={speech.isBrowserSupported}
              onToggleMic={speech.toggle}
            >
              {user && (
                <UserQuickActions
                  onFavoritesClick={() => setShowFavoritesList(true)}
                  onAction={(a) => {
                    setMessages(prev => [...prev, { type: 'user', text: `📌 ${a}`, timestamp: new Date() }]);
                    addMessage({ type: 'bot', text: `Tính năng "${a}" đang được phát triển. Bạn muốn tìm kiếm sản phẩm gì?`, timestamp: new Date() });
                  }}
                />
              )}
              {!user && (
                <p style={{ margin: '0 0 8px', fontSize: 12, color: '#94a3b8', textAlign: 'center' }}>
                  <button onClick={() => setShowLoginModal(true)}
                    style={{ color: '#6366f1', fontWeight: 600, background: 'none', border: 'none', cursor: 'pointer', fontSize: 12, padding: 0, fontFamily: 'inherit' }}>
                    Đăng nhập
                  </button>
                  {' '}để lưu yêu thích &amp; nhận gợi ý cá nhân hoá
                </p>
              )}
            </InputBar>
          </div>
        </div>
      )}
 
      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />






      {showComparison && <ProductComparison onClose={() => setShowComparison(false)} />}
    </div>
  );
};
 
export default ShoeFinder;