import React, { useState, useRef, useEffect } from 'react';
import { ShoppingBag, ChevronDown, LogOut, Heart, Clock, Tag, User, AlertCircle, X, Loader } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { GoogleLogin } from '@react-oauth/google';
import { SearchHistoryModal } from './SearchHistoryModal';

export const LoginModal = ({ isOpen, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { googleLogin } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (!isOpen) {
      setError('');
    }
  }, [isOpen]);

  const handleGoogleSuccess = async (credentialResponse) => {
    setError('');
    setLoading(true);

    try {
      console.log('🔐 Handling Google success...');
      const result = await googleLogin(credentialResponse.credential);
      
      console.log('📊 Result:', result);
      
      if (result.success) {
        console.log('✅ Login successful, closing modal...');
        onClose();
        console.log('⏳ Navigating...', result.user?.role === 'admin' ? '/admin/dashboard' : '/');
        
        // Add small delay to ensure state updates
        setTimeout(() => {
          if (result.user?.role === 'admin') {
            navigate('/admin/dashboard');
          } else {
            navigate('/');
          }
        }, 100);
      } else {
        console.error('❌ Login failed:', result.message);
        setError(result.message || 'Đăng nhập thất bại');
      }
    } catch (err) {
      console.error('❌ Error:', err);
      setError('Lỗi: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleError = () => {
    setError('Google login failed. Vui lòng thử lại.');
  };

  if (!isOpen) return null;

  return (
    <div style={{ position:'fixed', inset:0, zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', background:'rgba(15,23,42,0.55)', backdropFilter:'blur(6px)' }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <style>{`
        @keyframes modalSlide { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
      `}</style>
      <div style={{ background:'#fff', borderRadius:20, width:'100%', maxWidth:380, boxShadow:'0 24px 64px rgba(0,0,0,0.18)', animation:'modalSlide 0.25s ease', overflow:'hidden' }}>
        <div style={{ background:'linear-gradient(135deg,#6366f1,#8b5cf6)', padding:'22px 24px 0', position:'relative' }}>
          <button onClick={onClose} style={{ position:'absolute', top:14, right:14, background:'rgba(255,255,255,0.2)', border:'none', borderRadius:8, padding:'5px', cursor:'pointer', display:'flex' }}>
            <X size={16} color="#fff" />
          </button>
          <div style={{ display:'flex', alignItems:'center', gap:10, marginBottom:16 }}>
            <div style={{ width:36, height:36, borderRadius:10, background:'rgba(255,255,255,0.2)', display:'flex', alignItems:'center', justifyContent:'center' }}>
              <User size={18} color="#fff" />
            </div>
            <div>
              <div style={{ color:'#fff', fontWeight:700, fontSize:16 }}>Tài khoản RCM</div>
              <div style={{ color:'rgba(255,255,255,0.7)', fontSize:12 }}>Lưu yêu thích & nhận gợi ý cá nhân</div>
            </div>
          </div>
        </div>
        <div style={{ padding:'24px' }}>
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            {error && <div style={{ padding:'9px 13px', background:'#fef2f2', border:'1px solid #fecaca', borderRadius:8, color:'#dc2626', fontSize:13, display:'flex', alignItems:'center', gap:7 }}><AlertCircle size={14}/>{error}</div>}
            
            {loading ? (
              <div style={{ display:'flex', alignItems:'center', justifyContent:'center', gap:8, padding:'16px' }}>
                <Loader size={18} style={{ animation:'spin 1s linear infinite' }} color="#6366f1" />
                <span style={{ color:'#6366f1', fontWeight:500 }}>Đang xác thực...</span>
              </div>
            ) : (
              <div style={{ display:'flex', justifyContent:'center' }}>
                <GoogleLogin
                  onSuccess={handleGoogleSuccess}
                  onError={handleGoogleError}
                  text="signin_with"
                />
              </div>
            )}
            
            <div style={{ textAlign:'center', fontSize:12, color:'#94a3b8', marginTop:8 }}>
              Chúng tôi chỉ sử dụng Google để xác thực
            </div>
          </div>
        </div>
      </div>
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

// ─── USER DROPDOWN ────────────────────────────────────────────────────────────
const UserMenu = ({ user, onLogout, onSearchHistoryClick }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  // Safely get user name with fallbacks
  const getUserName = () => {
    return user?.full_name || user?.name || user?.email?.split('@')[0] || 'User';
  };

  const getUserInitial = () => {
    const name = getUserName();
    return (name && name[0]) ? name[0].toUpperCase() : 'U';
  };

  useEffect(() => {
    const h = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', h);
    return () => document.removeEventListener('mousedown', h);
  }, []);

  return (
    <div ref={ref} style={{ position:'relative' }}>
      <button onClick={()=>setOpen(!open)} style={{ display:'flex', alignItems:'center', gap:8, background:'rgba(255,255,255,0.15)', border:'none', cursor:'pointer', borderRadius:20, padding:'6px 12px 6px 8px', transition:'background 0.2s', fontFamily:'inherit' }}
        onMouseEnter={e=>e.currentTarget.style.background='rgba(255,255,255,0.25)'}
        onMouseLeave={e=>e.currentTarget.style.background='rgba(255,255,255,0.15)'}
      >
        <div style={{ width:28, height:28, borderRadius:'50%', background:'rgba(255,255,255,0.3)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:700, color:'#fff' }}>{getUserInitial()}</div>
        <span style={{ color:'#fff', fontSize:14, fontWeight:500 }}>{getUserName()}</span>
        <ChevronDown size={14} color="rgba(255,255,255,0.8)" style={{ transform:open?'rotate(180deg)':'none', transition:'transform 0.2s' }} />
      </button>
      {open && (
        <div style={{ position:'absolute', top:'calc(100% + 8px)', right:0, background:'#fff', borderRadius:14, minWidth:180, boxShadow:'0 12px 40px rgba(0,0,0,0.15)', border:'1px solid #f0f0f8', overflow:'hidden', zIndex:200 }}>
          <div style={{ padding:'12px 16px', borderBottom:'1px solid #f5f5f8' }}>
            <div style={{ fontWeight:700, fontSize:14, color:'#1e1b4b' }}>{getUserName()}</div>
            <div style={{ fontSize:12, color:'#94a3b8', marginTop:2 }}>{user?.email}</div>
          </div>
          {[{icon:<Heart size={15}/>,label:'Sản phẩm yêu thích',color:'#e11d48',action:'favorites'},{icon:<Clock size={15}/>,label:'Lịch sử tìm kiếm',color:'#6366f1',action:'history'},{icon:<Tag size={15}/>,label:'So sánh sản phẩm',color:'#f59e0b',action:'offers'}].map((item,i)=>(
            <button key={i} onClick={()=>{
              setOpen(false);
              if(item.action === 'history') {
                onSearchHistoryClick();
              }
            }} style={{ width:'100%', padding:'10px 16px', border:'none', background:'none', display:'flex', alignItems:'center', gap:10, cursor:'pointer', color:'#374151', fontSize:14, textAlign:'left', fontFamily:'inherit' }}
              onMouseEnter={e=>e.currentTarget.style.background='#f8f9ff'}
              onMouseLeave={e=>e.currentTarget.style.background='none'}
            ><span style={{ color:item.color }}>{item.icon}</span>{item.label}</button>
          ))}
          <div style={{ borderTop:'1px solid #f5f5f8' }}>
            <button onClick={()=>{onLogout();setOpen(false);}} style={{ width:'100%', padding:'10px 16px', border:'none', background:'none', display:'flex', alignItems:'center', gap:10, cursor:'pointer', color:'#ef4444', fontSize:14, fontFamily:'inherit' }}
              onMouseEnter={e=>e.currentTarget.style.background='#fff5f5'}
              onMouseLeave={e=>e.currentTarget.style.background='none'}
            ><LogOut size={15}/>Đăng xuất</button>
          </div>
        </div>
      )}
    </div>
  );
};

// ─── SHARED HEADER ────────────────────────────────────────────────────────────
export const SharedHeader = ({ onLogoClick, onQuerySelect }) => {
  const { user, setShowLoginModal, logout, token } = useAuth();
  const navigate = useNavigate();
  const [showSearchHistoryModal, setShowSearchHistoryModal] = useState(false);

  const handleLogoClick = () => {
    navigate('/');
    if (onLogoClick) onLogoClick();
  };

  return (
    <>
      <div style={{ background:'linear-gradient(135deg,#4f46e5,#6366f1,#7c3aed)', padding:'0 28px', display:'flex', alignItems:'center', justifyContent:'space-between', height:60, boxShadow:'0 2px 20px rgba(79,70,229,0.3)', flexShrink:0 }}>
        <div style={{ display:'flex', alignItems:'center', gap:10, cursor:'pointer' }} onClick={handleLogoClick}>
          <div style={{ width:34, height:34, borderRadius:10, background:'rgba(255,255,255,0.2)', display:'flex', alignItems:'center', justifyContent:'center' }}>
            <ShoppingBag size={18} color="#fff" />
          </div>
          <div>
            <div style={{ color:'#fff', fontWeight:800, fontSize:16, letterSpacing:'-0.3px', lineHeight:1 }}>RCM</div>
            <div style={{ color:'rgba(255,255,255,0.65)', fontSize:11 }}>Trợ lý tìm sản phẩm</div>
          </div>
        </div>
        {user ? <UserMenu user={user} onLogout={logout} onSearchHistoryClick={() => setShowSearchHistoryModal(true)} /> : (
          <button onClick={() => setShowLoginModal(true)} style={{ display:'flex', alignItems:'center', gap:7, padding:'7px 18px', borderRadius:20, border:'1.5px solid rgba(255,255,255,0.4)', background:'rgba(255,255,255,0.12)', color:'#fff', fontSize:13, fontWeight:600, cursor:'pointer', transition:'all 0.2s', fontFamily:'inherit' }}
            onMouseEnter={e=>e.currentTarget.style.background='rgba(255,255,255,0.22)'}
            onMouseLeave={e=>e.currentTarget.style.background='rgba(255,255,255,0.12)'}
          >👤 Đăng nhập</button>
        )}
      </div>
      
      {/* Search History Modal */}
      <SearchHistoryModal 
        isOpen={showSearchHistoryModal} 
        onClose={() => setShowSearchHistoryModal(false)}
        token={token}
        onQuerySelect={onQuerySelect}
      />
    </>
  );
};
