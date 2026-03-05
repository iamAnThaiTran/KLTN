import React, { useState, useRef, useEffect } from 'react';
import { ShoppingBag, ChevronDown, LogOut, Heart, Clock, Tag, User, Lock, Eye, EyeOff, AlertCircle, X } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

// ─── LOGIN MODAL ─────────────────────────────────────────────────────────────
export const LoginModal = ({ isOpen, onClose }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [name, setName] = useState('');
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [tab, setTab] = useState('login');
  const { login, register } = useAuth();

  useEffect(() => {
    if (!isOpen) {
      setError('');
      setEmail('');
      setPassword('');
      setName('');
      setShowPw(false);
    }
  }, [isOpen]);

  const handleSubmit = async () => {
    if (tab === 'login') {
      if (!email || !password) {
        setError('Vui lòng điền đầy đủ thông tin');
        return;
      }
    } else {
      if (!name || !email || !password) {
        setError('Vui lòng điền đầy đủ thông tin');
        return;
      }
    }
    
    setLoading(true);
    setError('');
    
    try {
      let result;
      if (tab === 'login') {
        result = await login(email, password);
      } else {
        result = await register(email, password, name);
      }
      
      setLoading(false);
      if (result.success) {
        onClose();
      } else {
        setError(result.message || 'Thao tác thất bại');
      }
    } catch (err) {
      setLoading(false);
      setError('Lỗi: ' + err.message);
    }
  };

  if (!isOpen) return null;

  return (
    <div style={{ position:'fixed', inset:0, zIndex:1000, display:'flex', alignItems:'center', justifyContent:'center', background:'rgba(15,23,42,0.55)', backdropFilter:'blur(6px)' }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <style>{`
        @keyframes modalSlide { from{opacity:0;transform:translateY(20px)} to{opacity:1;transform:translateY(0)} }
        .login-inp { width:100%; padding:11px 14px 11px 40px; border:1.5px solid #e2e8f0; border-radius:10px; font-size:14px; color:#1e293b; outline:none; transition:all 0.2s; box-sizing:border-box; background:#f8fafc; font-family:inherit; }
        .login-inp:focus { border-color:#6366f1; background:#fff; box-shadow:0 0 0 3px rgba(99,102,241,0.12); }
        .login-inp::placeholder { color:#94a3b8; }
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
          <div style={{ display:'flex' }}>
            {['login','register'].map(t => (
              <button key={t} onClick={() => setTab(t)} style={{ flex:1, padding:'10px', border:'none', background:'none', cursor:'pointer', color:tab===t?'#fff':'rgba(255,255,255,0.55)', fontWeight:tab===t?700:500, fontSize:14, borderBottom:tab===t?'2px solid #fff':'2px solid transparent', transition:'all 0.2s', fontFamily:'inherit' }}>
                {t==='login'?'Đăng nhập':'Đăng ký'}
              </button>
            ))}
          </div>
        </div>
        <div style={{ padding:'24px' }}>
          <div style={{ display:'flex', flexDirection:'column', gap:12 }}>
            {tab==='register' && (
              <div style={{ position:'relative' }}>
                <User size={15} color="#94a3b8" style={{ position:'absolute', left:13, top:'50%', transform:'translateY(-50%)' }} />
                <input className="login-inp" type="text" placeholder="Họ và tên" value={name} onChange={e=>setName(e.target.value)} />
              </div>
            )}
            <div style={{ position:'relative' }}>
              <svg style={{ position:'absolute', left:13, top:'50%', transform:'translateY(-50%)' }} width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#94a3b8" strokeWidth="2"><path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/></svg>
              <input className="login-inp" type="email" placeholder="Email của bạn" value={email} onChange={e=>setEmail(e.target.value)} onKeyDown={e=>e.key==='Enter'&&handleSubmit()} />
            </div>
            <div style={{ position:'relative' }}>
              <Lock size={15} color="#94a3b8" style={{ position:'absolute', left:13, top:'50%', transform:'translateY(-50%)' }} />
              <input className="login-inp" style={{ paddingRight:40 }} type={showPw?'text':'password'} placeholder="Mật khẩu" value={password} onChange={e=>setPassword(e.target.value)} onKeyDown={e=>e.key==='Enter'&&handleSubmit()} />
              <button onClick={()=>setShowPw(!showPw)} style={{ position:'absolute', right:12, top:'50%', transform:'translateY(-50%)', background:'none', border:'none', cursor:'pointer', padding:0, display:'flex' }}>
                {showPw?<EyeOff size={15} color="#94a3b8"/>:<Eye size={15} color="#94a3b8"/>}
              </button>
            </div>
            {error && <div style={{ padding:'9px 13px', background:'#fef2f2', border:'1px solid #fecaca', borderRadius:8, color:'#dc2626', fontSize:13, display:'flex', alignItems:'center', gap:7 }}><AlertCircle size={14}/>{error}</div>}
            <button onClick={handleSubmit} disabled={loading} style={{ width:'100%', padding:'12px', borderRadius:10, border:'none', cursor:'pointer', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', color:'#fff', fontSize:14, fontWeight:700, transition:'all 0.2s', marginTop:4, fontFamily:'inherit', opacity:loading?0.7:1 }}>
              {loading ? 'Đang xử lý...' : tab==='login'?'Đăng nhập':'Tạo tài khoản'}
            </button>
            {tab==='login'&&<div style={{ textAlign:'center', fontSize:13, color:'#6366f1', cursor:'pointer', fontWeight:500 }}>Quên mật khẩu?</div>}
          </div>
        </div>
      </div>
    </div>
  );
};

// ─── USER DROPDOWN ────────────────────────────────────────────────────────────
const UserMenu = ({ user, onLogout }) => {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

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
        <div style={{ width:28, height:28, borderRadius:'50%', background:'rgba(255,255,255,0.3)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:13, fontWeight:700, color:'#fff' }}>{user.name[0].toUpperCase()}</div>
        <span style={{ color:'#fff', fontSize:14, fontWeight:500 }}>{user.name}</span>
        <ChevronDown size={14} color="rgba(255,255,255,0.8)" style={{ transform:open?'rotate(180deg)':'none', transition:'transform 0.2s' }} />
      </button>
      {open && (
        <div style={{ position:'absolute', top:'calc(100% + 8px)', right:0, background:'#fff', borderRadius:14, minWidth:180, boxShadow:'0 12px 40px rgba(0,0,0,0.15)', border:'1px solid #f0f0f8', overflow:'hidden', zIndex:200 }}>
          <div style={{ padding:'12px 16px', borderBottom:'1px solid #f5f5f8' }}>
            <div style={{ fontWeight:700, fontSize:14, color:'#1e1b4b' }}>{user.name}</div>
            <div style={{ fontSize:12, color:'#94a3b8', marginTop:2 }}>{user.email}</div>
          </div>
          {[{icon:<Heart size={15}/>,label:'Sản phẩm yêu thích',color:'#e11d48'},{icon:<Clock size={15}/>,label:'Lịch sử tìm kiếm',color:'#6366f1'},{icon:<Tag size={15}/>,label:'Ưu đãi của tôi',color:'#f59e0b'}].map((item,i)=>(
            <button key={i} style={{ width:'100%', padding:'10px 16px', border:'none', background:'none', display:'flex', alignItems:'center', gap:10, cursor:'pointer', color:'#374151', fontSize:14, textAlign:'left', fontFamily:'inherit' }}
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
export const SharedHeader = ({ onLogoClick }) => {
  const { user, setShowLoginModal, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogoClick = () => {
    navigate('/');
    if (onLogoClick) onLogoClick();
  };

  return (
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
      {user ? <UserMenu user={user} onLogout={logout} /> : (
        <button onClick={() => setShowLoginModal(true)} style={{ display:'flex', alignItems:'center', gap:7, padding:'7px 18px', borderRadius:20, border:'1.5px solid rgba(255,255,255,0.4)', background:'rgba(255,255,255,0.12)', color:'#fff', fontSize:13, fontWeight:600, cursor:'pointer', transition:'all 0.2s', fontFamily:'inherit' }}
          onMouseEnter={e=>e.currentTarget.style.background='rgba(255,255,255,0.22)'}
          onMouseLeave={e=>e.currentTarget.style.background='rgba(255,255,255,0.12)'}
        >👤 Đăng nhập</button>
      )}
    </div>
  );
};
