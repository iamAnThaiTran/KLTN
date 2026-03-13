import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Mic, MicOff, ChevronRight, Search, Flame, Grid3X3, Lightbulb, SlidersHorizontal, Brain, ShoppingBag, Star } from 'lucide-react';
import { SharedHeader, LoginModal } from './SharedHeader';
import { useAuth } from '../context/AuthContext';

const CATEGORIES = [
  { icon: '👟', label: 'Giày đẹp' },
  { icon: '⌚', label: 'Đồng hồ thông minh' },
  { icon: '🎧', label: 'Tai nghe' },
  { icon: '📱', label: 'Điện thoại' },
  { icon: '🎒', label: 'Phụ kiện' },
  { icon: '🛍️', label: 'Acces..' },
];

const QUICK_SEARCHES = [
  { icon: '👟', label: 'Giày chạy bộ' },
  { icon: '🎧', label: 'Tai nghe bluetooth' },
  { icon: '🎁', label: 'Quà sinh nhật cho bạn gái' },
  { icon: '⌚', label: 'Đồng hồ thông minh' },
];

const POPULAR_PRODUCTS = [
  { name: 'Nike Air Force 1', price: '2.400.000đ', sales: null, img: 'https://via.placeholder.com/120x100/f0f0f0/999?text=Nike' },
  { name: 'AirPods Pro 2', price: '5.300.000đ', sales: '630 ches', img: 'https://via.placeholder.com/120x100/f0f0f0/999?text=AirPods' },
  { name: 'Xiaomi Redmi Watch 3', price: '1.890.000đ', sales: '410 ches', img: 'https://via.placeholder.com/120x100/f0f0f0/999?text=Watch' },
  { name: 'Song GaN 65W', price: '359.000đ', sales: '1670 ches', img: 'https://via.placeholder.com/120x100/f0f0f0/999?text=Charger' },
];

const EXAMPLE_QUERIES = [
  'Giày Nike chạy bộ dưới 2 triệu',
  'Sneaker trắng size 42',
  'Tai nghe chống ồn tốt',
  'Quà sinh nhật cho bạn gái dưới 500K',
];

const HOW_IT_WORKS = [
  { icon: <Search size={18} />, text: 'Tìm sản câu tìm nhiều sản', color: '#6366f1' },
  { icon: <SlidersHorizontal size={18} />, text: 'Gợi ý bộ lọc thông minh', color: '#0ea5e9' },
  { icon: <Brain size={18} />, text: 'Hiểu yêu cầu bằng ngôn ngữ tự nhiên', color: '#8b5cf6' },
];

export default function LandingPage() {
  const navigate = useNavigate();
  const { showLoginModal, setShowLoginModal } = useAuth();
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isBrowserSupported, setIsBrowserSupported] = useState(true);
  const inputRef = useRef(null);
  const recognitionRef = useRef(null);

  // Initialize speech recognition
  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      setIsBrowserSupported(false);
      return;
    }
    
    const r = new SR();
    r.continuous = false;
    r.interimResults = true;
    r.lang = 'vi-VN';
    
    r.onstart = () => {
      setIsListening(true);
      setTranscript('');
    };
    
    r.onresult = (e) => {
      let interim = '';
      let final = '';
      
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const t = e.results[i][0].transcript;
        if (e.results[i].isFinal) {
          final += t + ' ';
        } else {
          interim += t;
        }
      }
      
      setTranscript(interim);
      if (final) {
        setInput(p => (p + ' ' + final).trim());
      }
    };
    
    r.onerror = (e) => {
      console.error('Speech recognition error:', e.error);
      setIsListening(false);
    };
    
    r.onend = () => {
      setIsListening(false);
      setTranscript('');
    };
    
    recognitionRef.current = r;
    return () => recognitionRef.current?.abort();
  }, []);

  const handleMicClick = () => {
    if (!recognitionRef.current) return;
    
    if (isListening) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.error('Error starting speech recognition:', e);
      }
    }
  };

  const handleSubmit = () => {
    if (input.trim()) {
      navigate(`/search?q=${encodeURIComponent(input.trim())}`);
    }
  };

  const handleKey = (e) => {
    if (e.key === 'Enter') handleSubmit();
  };

  const handleQuick = (label) => {
    navigate(`/search?q=${encodeURIComponent(label)}`);
  };

  return (
    <div style={{
      minHeight: '100vh',
      background: 'linear-gradient(160deg, #eef2ff 0%, #f0f7ff 40%, #f8f0ff 100%)',
      fontFamily: "'Be Vietnam Pro', 'Segoe UI', sans-serif",
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Be+Vietnam+Pro:wght@400;500;600;700;800&display=swap');

        @keyframes fadeUp { from{opacity:0;transform:translateY(18px)} to{opacity:1;transform:translateY(0)} }
        @keyframes fadeIn { from{opacity:0} to{opacity:1} }
        @keyframes shimmer { 0%{background-position:200% 0} 100%{background-position:-200% 0} }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.6} }

        .landing-root * { box-sizing: border-box; }

        .search-bar {
          width: 100%;
          padding: 16px 60px 16px 20px;
          border: 2px solid #e0e7ff;
          border-radius: 14px;
          font-size: 15px;
          color: #1e1b4b;
          background: #fff;
          outline: none;
          transition: border-color 0.2s, box-shadow 0.2s;
          font-family: inherit;
        }
        .search-bar:focus {
          border-color: #6366f1;
          box-shadow: 0 0 0 4px rgba(99,102,241,0.1);
        }
        .search-bar::placeholder { color: #a5b4c8; font-size: 14px; }

        .quick-chip {
          display: inline-flex; align-items: center; gap: 7px;
          padding: 8px 16px; border-radius: 20px;
          background: #fff; border: 1.5px solid #e0e7ff;
          color: #4f46e5; font-size: 13px; font-weight: 600;
          cursor: pointer; transition: all 0.15s; white-space: nowrap;
          font-family: inherit;
        }
        .quick-chip:hover { background: #eef2ff; border-color: #6366f1; transform: translateY(-1px); box-shadow: 0 3px 10px rgba(99,102,241,0.15); }

        .category-card {
          display: flex; flex-direction: column; align-items: center; gap: 10px;
          padding: 16px 8px; background: #fff; border-radius: 14px;
          border: 1.5px solid #ede9fe; cursor: pointer;
          transition: all 0.15s; text-align: center;
        }
        .category-card:hover { border-color: #6366f1; box-shadow: 0 4px 14px rgba(99,102,241,0.15); transform: translateY(-2px); }
        .category-icon {
          width: 58px; height: 58px; border-radius: 50%;
          background: linear-gradient(135deg, #eef2ff, #e0e7ff);
          display: flex; align-items: center; justify-content: center; font-size: 26px;
        }
        .category-label { font-size: 12px; font-weight: 600; color: #374151; }

        .product-card {
          background: #fff; border-radius: 14px; border: 1.5px solid #f0f0f8;
          padding: 12px; cursor: pointer; transition: all 0.15s; flex-shrink: 0;
          width: 148px;
        }
        .product-card:hover { border-color: #6366f1; box-shadow: 0 4px 16px rgba(99,102,241,0.15); transform: translateY(-2px); }

        .sidebar-card {
          background: #fff; border-radius: 16px; border: 1.5px solid #ede9fe;
          padding: 20px; box-shadow: 0 2px 12px rgba(99,102,241,0.06);
        }

        .stagger-1 { animation: fadeUp 0.5s ease 0.05s both; }
        .stagger-2 { animation: fadeUp 0.5s ease 0.15s both; }
        .stagger-3 { animation: fadeUp 0.5s ease 0.25s both; }
        .stagger-4 { animation: fadeUp 0.5s ease 0.35s both; }
        .stagger-5 { animation: fadeUp 0.5s ease 0.45s both; }
        .stagger-6 { animation: fadeUp 0.5s ease 0.55s both; }
      `}</style>

      <div className="landing-root">
        {/* ── Header ── */}
        <SharedHeader />

        {/* ── Body ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 24, maxWidth: 1100, margin: '0 auto', padding: '32px 24px' }}>

          {/* LEFT COLUMN */}
          <div>
            {/* Hero */}
            <div className="stagger-1" style={{ marginBottom: 28 }}>
              <div style={{ fontSize: 15, color: '#6366f1', fontWeight: 600, marginBottom: 8 }}>Xin chào! 👋</div>
              <h1 style={{ fontSize: 'clamp(22px,3vw,32px)', fontWeight: 800, color: '#1e1b4b', lineHeight: 1.25, margin: '0 0 10px', letterSpacing: '-0.5px' }}>
                Hôm nay bạn muốn mua gì?<br />
                <span style={{ background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
                  Tôi sẽ tìm kiếm sản phẩm phù hợp nhất.
                </span>
              </h1>
              <p style={{ color: '#64748b', fontSize: 14, margin: 0 }}>Bạn đang tìm loại sản phẩm gì?</p>
            </div>

            {/* Search bar */}
            <div className="stagger-2" style={{ position: 'relative', marginBottom: 14 }}>
              <input
                ref={inputRef}
                className="search-bar"
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={handleKey}
                placeholder="(Ví dụ: giày chạy bộ, quà sinh nhật, vòng đeo tay huawei band 11, ...)"
              />
              {isBrowserSupported && (
                <button onClick={handleMicClick} title={isListening ? 'Nhấn để dừng' : 'Nhấn để nói'} style={{
                  position: 'absolute', right: 50, top: '50%', transform: 'translateY(-50%)',
                  width: 38, height: 38, borderRadius: '50%', border: 'none',
                  background: isListening ? 'linear-gradient(135deg,#ef4444,#dc2626)' : '#f1f5f9',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  cursor: 'pointer', transition: 'all 0.2s',
                  color: isListening ? '#fff' : '#64748b',
                  boxShadow: isListening ? '0 4px 16px rgba(239,68,68,0.4)' : 'none'
                }}>
                  {isListening ? <MicOff size={18} /> : <Mic size={18} />}
                </button>
              )}
              <button onClick={handleSubmit} title="Tìm kiếm" style={{
                position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                width: 38, height: 38, borderRadius: '50%', border: 'none',
                background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                cursor: 'pointer', transition: 'opacity 0.2s', color: '#fff'
              }}>
                <Search size={18} />
              </button>
              {isListening && transcript && (
                <div style={{
                  position: 'absolute', left: 20, right: 60, top: '50%', transform: 'translateY(-50%)',
                  color: '#6366f1', fontSize: 13, fontStyle: 'italic', fontWeight: 500,
                  animation: 'pulse 1s infinite'
                }}>
                  🎤 {transcript}
                </div>
              )}
            </div>

            {/* Quick chips */}
            <div className="stagger-2" style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 36 }}>
              {QUICK_SEARCHES.map((q, i) => (
                <button key={i} className="quick-chip" onClick={() => handleQuick(q.label)}>
                  <span>{q.icon}</span> {q.label}
                </button>
              ))}
            </div>

            {/* Popular categories */}
            <div className="stagger-3" style={{ marginBottom: 32 }}>
              <div style={{ fontWeight: 800, fontSize: 16, color: '#1e1b4b', marginBottom: 14 }}>Danh mục phổ biến</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6,1fr)', gap: 10 }}>
                {CATEGORIES.map((cat, i) => (
                  <div key={i} className="category-card" onClick={() => handleQuick(cat.label)}>
                    <div className="category-icon">{cat.icon}</div>
                    <span className="category-label">{cat.label}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Popular products */}
            <div className="stagger-4">
              <div style={{ fontWeight: 800, fontSize: 16, color: '#1e1b4b', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 8 }}>
                🔥 Sản phẩm phổ biến hôm nay
              </div>
              <div style={{ background: '#fff', borderRadius: 16, border: '1.5px solid #ede9fe', padding: 16 }}>
                <div style={{ display: 'flex', gap: 12, overflowX: 'auto', paddingBottom: 4 }}>
                  {POPULAR_PRODUCTS.map((p, i) => (
                    <div key={i} className="product-card" onClick={() => handleQuick(p.name)}>
                      <div style={{ background: '#f8f9ff', borderRadius: 10, height: 90, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 10, overflow: 'hidden' }}>
                        <img src={p.img} alt={p.name} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
                      </div>
                      <div style={{ fontSize: 12, fontWeight: 700, color: '#1e1b4b', lineHeight: 1.3, marginBottom: 5 }}>{p.name}</div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexWrap: 'wrap' }}>
                        <span style={{ fontSize: 13, fontWeight: 700, color: '#f59e0b' }}>🔥</span>
                        <span style={{ fontSize: 12, fontWeight: 700, color: '#1e1b4b' }}>{p.price}</span>
                        {p.sales && <span style={{ fontSize: 10, color: '#94a3b8' }}>{p.sales}</span>}
                      </div>
                    </div>
                  ))}
                  <div style={{ display: 'flex', alignItems: 'center', paddingLeft: 4, flexShrink: 0 }}>
                    <div style={{ width: 32, height: 32, borderRadius: '50%', background: '#eef2ff', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
                      <ChevronRight size={16} color="#6366f1" />
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* RIGHT SIDEBAR */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            {/* Example queries */}
            <div className="sidebar-card stagger-2">
              <div style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b', marginBottom: 12 }}>Ví dụ bạn có thể hỏi:</div>
              <ul style={{ margin: 0, padding: '0 0 0 18px', display: 'flex', flexDirection: 'column', gap: 8 }}>
                {EXAMPLE_QUERIES.map((q, i) => (
                  <li key={i} style={{ fontSize: 13, color: '#4f46e5', lineHeight: 1.4 }}>{q}</li>
                ))}
              </ul>
            </div>

            {/* Popular today info */}
            <div className="sidebar-card stagger-3">
              <div style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b', marginBottom: 14, display: 'flex', alignItems: 'center', gap: 7 }}>
                🔥 Sản phẩm phổ biến hôm nay
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {[
                  { icon: <Search size={15} />, text: 'Nhập yêu cầu tìm kiếm', color: '#6366f1' },
                  { icon: <SlidersHorizontal size={15} />, text: 'Gợi ý bộ lọc thông minh', color: '#0ea5e9' },
                  { icon: <Brain size={15} />, text: 'Hiểu yêu cầu bằng ngôn ngữ tự nhiên', color: '#8b5cf6' },
                ].map((item, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                    <div style={{ width: 30, height: 30, borderRadius: 8, background: `${item.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: item.color }}>
                      {item.icon}
                    </div>
                    <span style={{ fontSize: 13, color: '#475569', lineHeight: 1.5, paddingTop: 5 }}>{item.text}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* How it works */}
            <div className="sidebar-card stagger-4">
              <div style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b', marginBottom: 14 }}>Cách hệ thống hoạt động</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {HOW_IT_WORKS.map((item, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'flex-start', gap: 10 }}>
                    <div style={{ width: 30, height: 30, borderRadius: 8, background: `${item.color}15`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, color: item.color }}>
                      {item.icon}
                    </div>
                    <span style={{ fontSize: 13, color: '#475569', lineHeight: 1.5, paddingTop: 5 }}>{item.text}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>

      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />
    </div>
  );
}