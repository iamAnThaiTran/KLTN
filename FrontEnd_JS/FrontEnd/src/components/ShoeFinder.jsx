import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Send, Sparkles, CheckCircle2, AlertCircle, ShoppingBag, Mic, MicOff, Volume2, User, Lock, Eye, EyeOff, LogOut, Heart, Clock, Tag, Gift, ChevronDown, ChevronRight, X, Search, SlidersHorizontal, Brain, Flame } from 'lucide-react';
import axios from 'axios';
import SuggestionsPopup from './SuggestionsPopup';
import { SharedHeader, LoginModal } from './SharedHeader';
import { useAuth } from '../context/AuthContext';

const API_BASE_URL = 'http://localhost:8000';

// ─── DATA ───────────────────────────────────────────────────────────────────
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

// ─── USER QUICK ACTIONS (chat view) ──────────────────────────────────────────
const UserQuickActions = ({ onAction }) => (
  <div style={{ display:'flex', gap:8, paddingBottom:10, flexWrap:'wrap' }}>
    {[{icon:<Heart size={14}/>,label:'Sản phẩm yêu thích',color:'#e11d48',bg:'#fff1f2',border:'#fecdd3'},{icon:<Clock size={14}/>,label:'Tìm kiếm gần đây',color:'#6366f1',bg:'#eef2ff',border:'#c7d2fe'},{icon:<Tag size={14}/>,label:'Ưu đãi hôm nay',color:'#d97706',bg:'#fffbeb',border:'#fde68a'},{icon:<Gift size={14}/>,label:'Gợi ý cho bạn',color:'#059669',bg:'#ecfdf5',border:'#a7f3d0'}].map((a,i)=>(
      <button key={i} onClick={()=>onAction(a.label)} style={{ display:'flex', alignItems:'center', gap:6, padding:'6px 14px', borderRadius:20, border:`1.5px solid ${a.border}`, background:a.bg, color:a.color, fontSize:13, fontWeight:600, cursor:'pointer', transition:'all 0.15s', fontFamily:'inherit' }}
        onMouseEnter={e=>{e.currentTarget.style.transform='translateY(-1px)';e.currentTarget.style.boxShadow=`0 3px 10px ${a.border}`;}}
        onMouseLeave={e=>{e.currentTarget.style.transform='none';e.currentTarget.style.boxShadow='none';}}
      >{a.icon}{a.label}</button>
    ))}
  </div>
);

// ─── MAIN APP ─────────────────────────────────────────────────────────────────
const ShoeFinder = () => {
  const [searchParams] = useSearchParams();
  const { user, showLoginModal, setShowLoginModal } = useAuth();
  const [view, setView] = useState('landing'); // 'landing' | 'chat'
  const [messages, setMessages] = useState([]);
  const [currentInput, setCurrentInput] = useState('');
  const [conversationState, setConversationState] = useState({ conversationId: null, isLoading: false });
  const [isThinking, setIsThinking] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isBrowserSupported, setIsBrowserSupported] = useState(true);
  const [lastCategoryName, setLastCategoryName] = useState('');
  const [selectedFilters, setSelectedFilters] = useState({});
  const [clarifyingHints, setClarifyingHints] = useState([]);
  const [showSuggestionsPopup, setShowSuggestionsPopup] = useState(false);
  const [suggestionsPopupFilters, setSuggestionsPopupFilters] = useState([]);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) { setIsBrowserSupported(false); return; }
    const r = new SR();
    r.continuous = true; r.interimResults = true; r.lang = 'vi-VN';
    r.onstart = () => { setIsListening(true); setTranscript(''); };
    r.onresult = (e) => {
      let interim='', final='';
      for (let i=e.resultIndex;i<e.results.length;i++) {
        const t=e.results[i][0].transcript;
        if(e.results[i].isFinal) final+=t+' '; else interim+=t;
      }
      setTranscript(interim);
      if(final) setCurrentInput(p=>(p+' '+final).trim());
    };
    r.onerror = () => setIsListening(false);
    r.onend = () => { setIsListening(false); setTranscript(''); };
    recognitionRef.current = r;
    return () => recognitionRef.current?.abort();
  }, []);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior:'smooth' }); }, [messages]);

  const addBot = (text, quickReplies=null) => setMessages(p=>[...p,{type:'bot',text,quickReplies,timestamp:new Date()}]);
  const addUser = (text) => setMessages(p=>[...p,{type:'user',text,timestamp:new Date()}]);

  const startSearch = (query) => {
    setView('chat');
    setMessages([]);
    setTimeout(() => {
      addUser(query);
      analyzeAndSearch(query);
    }, 50);
  };

  // Auto-start search when URL has query parameter
  useEffect(() => {
    const query = searchParams.get('q');
    if (query) {
      startSearch(query);
    }
  }, [searchParams]);

  const analyzeAndSearch = async (userInput) => {
    setIsThinking(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/analyze`, { user_input: userInput, conversation_id: conversationState.conversationId });
      const d = res.data;
      if (!d.success) { addBot(`❌ ${d.error}`); setIsThinking(false); return; }
      setConversationState(p=>({...p, conversationId: d.conversation_id}));
      setLastCategoryName(d.category);
      setSelectedFilters({});
      setClarifyingHints(d.clarifying_hints||[]);
      setSuggestionsPopupFilters(d.filters||[]);
      setMessages(p=>[...p,{type:'loading',timestamp:new Date()}]);
      if (d.products?.length) {
        setMessages(p=>p.filter(m=>m.type!=='loading'));
        if (d.filters?.length) setMessages(p=>[...p,{type:'filters',text:'Bạn có thể lọc sản phẩm theo các tiêu chí dưới đây:',filters:d.filters,timestamp:new Date()}]);
        setMessages(p=>[...p,{type:'results',text:`🎯 Tìm thấy ${d.total||d.products.length} sản phẩm!`,products:d.products,timestamp:new Date()}]);
      } else {
        setMessages(p=>p.filter(m=>m.type!=='loading'));
        addBot(`ℹ️ Hiện tại chưa có sản phẩm "${d.category}" trong kho.\n\nVui lòng chọn các tiêu chí tìm kiếm để giúp tôi tìm kiếm chính xác hơn.`);
      }
      setShowSuggestionsPopup(true);
    } catch (err) {
      const msg = err.response?.data?.detail || err.message || 'Có lỗi xảy ra';
      setMessages(p=>p.filter(m=>m.type!=='loading'));
      addBot(`❌ Lỗi: ${msg}`);
      addBot('Lưu ý: Vui lòng chắc chắn backend Python đang chạy trên http://localhost:8000');
    } finally {
      setIsThinking(false);
    }
  };

  const sendToBackend = async (userInput) => {
    setIsThinking(true);
    try {
      const res = await axios.post(`${API_BASE_URL}/api/query`, { user_input: userInput, conversation_id: conversationState.conversationId });
      const d = res.data;
      if (d.conversation_id) setConversationState(p=>({...p,conversationId:d.conversation_id}));
      if (d.clarifying_hints) setClarifyingHints(d.clarifying_hints);
      if (d.status==='results'&&d.products?.length) {
        if (d.filters?.length) setMessages(p=>[...p,{type:'filters',text:'Bạn có thể lọc sản phẩm theo các tiêu chí dưới đây:',filters:d.filters,timestamp:new Date()}]);
        setMessages(p=>[...p,{type:'results',text:`🎯 Tìm thấy ${d.total_found||d.products.length} sản phẩm!`,products:d.products,timestamp:new Date()}]);
      } else if (d.question) {
        addBot(d.question, d.options?d.options.map(o=>o.label||o.value||o):null);
      }
    } catch (err) {
      addBot(`❌ Lỗi: ${err.response?.data?.detail||err.message}`);
    } finally {
      setIsThinking(false);
    }
  };

  const searchProductsWithFilters = async (categoryName, filters={}) => {
    setConversationState(p=>({...p,isLoading:true}));
    setClarifyingHints([]);
    try {
      setMessages(p=>[...p,{type:'loading',timestamp:new Date()}]);
      let fo = filters;
      if (Object.keys(filters).some(k=>k.includes(':'))) {
        fo = {};
        Object.keys(filters).forEach(k=>{const[a,v]=k.split(':');if(!fo[a])fo[a]=[];fo[a].push(v);});
      }
      const res = await fetch(`${API_BASE_URL}/api/v1/crawl-products`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({category_name:categoryName,selected_filters:fo,page:1,page_size:20})});
      if (!res.ok) { const e=await res.json(); throw new Error(e.detail||`HTTP ${res.status}`); }
      const data = await res.json();
      setMessages(p=>p.filter(m=>m.type!=='loading'));
      if (!data.products?.length) { addBot('🔍 Không tìm thấy sản phẩm nào phù hợp'); return; }
      const rm={type:'results',text:`🎯 Tìm thấy ${data.total||data.products.length} sản phẩm!`,products:data.products,timestamp:new Date()};
      const fm=data.filters?.length?{type:'filters',text:'Bạn có thể lọc sản phẩm theo các tiêu chí dưới đây:',filters:data.filters,timestamp:new Date()}:null;
      setMessages(p=>{const cl=p.filter(m=>m.type!=='results'&&m.type!=='filters');return[...cl,...(fm?[fm]:[]),rm];});
    } catch (err) {
      setMessages(p=>p.filter(m=>m.type!=='loading'));
      addBot(`❌ Lỗi: ${err.message}`);
    } finally {
      setConversationState(p=>({...p,isLoading:false}));
    }
  };

  const handleSend = () => {
    if (!currentInput.trim()||isThinking) return;
    addUser(currentInput);
    analyzeAndSearch(currentInput);
    setCurrentInput('');
  };

  return (
    <div style={{ height:'100vh', width:'100vw', display:'flex', flexDirection:'column', overflow:'hidden' }}>
      <SharedHeader onLogoClick={()=>setView('landing')} />

      {/* {view === 'landing' ? (
        <LandingPage onSearch={startSearch} user={user} onLoginClick={()=>setShowLoginModal(true)} />
      ) : ( */}
        <>
          {/* Chat messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4" style={{ background:'linear-gradient(160deg,#f5f7ff,#f0f4ff)', flex:1, overflowY:'auto', padding:'24px' }}>
            {/* Back to home */}
            <div style={{ marginBottom:8 }}>
              <button onClick={()=>setView('landing')} style={{ display:'flex', alignItems:'center', gap:6, color:'#6366f1', fontSize:13, fontWeight:600, background:'none', border:'none', cursor:'pointer', padding:0, fontFamily:'inherit' }}>
                ← Về trang chủ
              </button>
            </div>

            <div style={{ display:'flex', flexDirection:'column', gap:16 }}>
              {messages.map((msg, idx) => (
                <div key={idx}>
                  {msg.type==='bot' && (
                    <div style={{ display:'flex', gap:12 }}>
                      <div style={{ width:38, height:38, borderRadius:'50%', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                        <Sparkles size={17} color="#fff" />
                      </div>
                      <div>
                        <div style={{ background:'#fff', borderRadius:'18px 18px 18px 4px', padding:'13px 17px', maxWidth:560, boxShadow:'0 2px 10px rgba(0,0,0,0.06)', border:'1px solid #f0f0f8', whiteSpace:'pre-wrap', color:'#1e1b4b', fontSize:14.5, lineHeight:1.6 }}>{msg.text}</div>
                        {msg.quickReplies && (
                          <div style={{ display:'flex', flexWrap:'wrap', gap:8, marginTop:10 }}>
                            {msg.quickReplies.map((r,i)=>(
                              <button key={i} onClick={()=>{addUser(r);sendToBackend(r);}} style={{ padding:'8px 16px', background:'#fff', border:'2px solid #c7d2fe', color:'#4f46e5', borderRadius:20, fontSize:13, fontWeight:600, cursor:'pointer', transition:'all 0.15s', fontFamily:'inherit' }}
                                onMouseEnter={e=>e.currentTarget.style.background='#eef2ff'}
                                onMouseLeave={e=>e.currentTarget.style.background='#fff'}
                              >{r}</button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  )}

                  {msg.type==='user' && (
                    <div style={{ display:'flex', justifyContent:'flex-end' }}>
                      <div style={{ background:'linear-gradient(135deg,#6366f1,#8b5cf6)', color:'#fff', borderRadius:'18px 18px 4px 18px', padding:'13px 17px', maxWidth:480, boxShadow:'0 3px 14px rgba(99,102,241,0.3)', fontSize:14.5, lineHeight:1.5 }}>{msg.text}</div>
                    </div>
                  )}

                  {msg.type==='filters' && msg.filters && (
                    <div style={{ display:'flex', gap:12 }}>
                      <div style={{ width:38, height:38, borderRadius:'50%', background:'linear-gradient(135deg,#8b5cf6,#ec4899)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                        <Sparkles size={17} color="#fff" />
                      </div>
                      <div style={{ flex:1 }}>
                        <div style={{ background:'#faf5ff', borderRadius:'18px 18px 18px 4px', padding:'16px', border:'1px solid #e9d5ff', maxWidth:640 }}>
                          <div style={{ fontWeight:700, color:'#6b21a8', marginBottom:12, fontSize:14 }}>{msg.text}</div>
                          <div style={{ display:'flex', flexDirection:'column', gap:10, maxHeight:320, overflowY:'auto' }}>
                            {msg.filters.map((filter,fi)=>(
                              <div key={fi} style={{ border:'1px solid #e9d5ff', borderRadius:10, padding:'10px 12px', background:'#fff' }}>
                                <p style={{ fontWeight:700, fontSize:13, color:'#6b21a8', margin:'0 0 8px' }}>{filter.display_name||filter.attribute_name}</p>
                                <div style={{ display:'flex', flexWrap:'wrap', gap:7 }}>
                                  {filter.options?.map((opt,oi)=>{
                                    const k=`${filter.attribute_name}:${opt.attribute_value}`;
                                    const sel=selectedFilters[k];
                                    return (
                                      <button key={oi} onClick={()=>setSelectedFilters(p=>{const n={...p};if(n[k])delete n[k];else n[k]=true;return n;})}
                                        style={{ padding:'6px 12px', fontSize:12, borderRadius:20, fontWeight:600, border:sel?'2px solid #7c3aed':'1.5px solid #ddd6fe', background:sel?'linear-gradient(135deg,#7c3aed,#8b5cf6)':'#fff', color:sel?'#fff':'#6b21a8', cursor:'pointer', transition:'all 0.15s', fontFamily:'inherit', boxShadow:sel?'0 2px 8px rgba(124,58,237,0.3)':'none' }}>
                                        {opt.attribute_value} ({opt.product_count})
                                      </button>
                                    );
                                  })}
                                </div>
                              </div>
                            ))}
                          </div>
                          <div style={{ marginTop:12, display:'flex', gap:8 }}>
                            {Object.keys(selectedFilters).length>0 ? (
                              <>
                                <button onClick={()=>lastCategoryName&&searchProductsWithFilters(lastCategoryName,selectedFilters)}
                                  style={{ flex:1, padding:'10px', background:'linear-gradient(135deg,#7c3aed,#8b5cf6)', color:'#fff', border:'none', borderRadius:10, fontSize:13, fontWeight:700, cursor:'pointer', fontFamily:'inherit' }}>
                                  🔍 Lọc sản phẩm ({Object.keys(selectedFilters).length})
                                </button>
                                <button onClick={()=>{setSelectedFilters({});lastCategoryName&&searchProductsWithFilters(lastCategoryName,{});}}
                                  style={{ padding:'10px 16px', background:'#f1f5f9', color:'#64748b', border:'none', borderRadius:10, fontSize:13, fontWeight:600, cursor:'pointer', fontFamily:'inherit' }}>
                                  ✕ Xóa
                                </button>
                              </>
                            ) : <div style={{ fontSize:12, color:'#9333ea', fontStyle:'italic' }}>Chọn các tiêu chí trên để lọc sản phẩm</div>}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}

                  {msg.type==='results' && (
                    <div>
                      <div style={{ display:'flex', gap:12, marginBottom:14 }}>
                        <div style={{ width:38, height:38, borderRadius:'50%', background:'linear-gradient(135deg,#10b981,#059669)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                          <CheckCircle2 size={17} color="#fff" />
                        </div>
                        <div style={{ background:'#f0fdf4', border:'1px solid #bbf7d0', borderRadius:'18px 18px 18px 4px', padding:'12px 17px', color:'#15803d', fontWeight:700, fontSize:14 }}>{msg.text}</div>
                      </div>
                      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(148px,1fr))', gap:12, paddingLeft:50 }}>
                        {msg.products.map((product,i)=>(
                          <div key={product.id||i}
                            style={{ background:'#fff', border:'1.5px solid #f0f0f8', borderRadius:14, overflow:'hidden', cursor:'pointer', transition:'all 0.18s' }}
                            onMouseEnter={e=>{e.currentTarget.style.borderColor='#6366f1';e.currentTarget.style.transform='translateY(-3px)';e.currentTarget.style.boxShadow='0 8px 24px rgba(99,102,241,0.18)';}}
                            onMouseLeave={e=>{e.currentTarget.style.borderColor='#f0f0f8';e.currentTarget.style.transform='none';e.currentTarget.style.boxShadow='none';}}
                            onClick={()=>{
                              if(product.product_url){
                                fetch('http://localhost:8000/api/open-product',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({product_url:product.product_url})})
                                  .then(r=>r.json()).then(d=>{if(d.success)addBot('🎬 Đã bắt đầu tự động mở sản phẩm trong Chrome...');else window.open(product.product_url,'_blank');})
                                  .catch(()=>window.open(product.product_url,'_blank'));
                              }
                            }}>
                            {product.thumbnail && (
                              <div style={{ background:'#f8f9ff', height:128, display:'flex', alignItems:'center', justifyContent:'center', overflow:'hidden', position:'relative' }}>
                                <img src={product.thumbnail} alt={product.title} style={{ maxWidth:'100%', maxHeight:'100%', objectFit:'contain' }} />
                                {i===0&&<div style={{ position:'absolute', top:7, right:7, background:'linear-gradient(135deg,#f59e0b,#d97706)', color:'#fff', fontSize:9.5, fontWeight:700, padding:'2px 7px', borderRadius:7 }}>TOP</div>}
                              </div>
                            )}
                            <div style={{ padding:'9px 11px' }}>
                              <div style={{ fontSize:11.5, fontWeight:600, color:'#1e1b4b', lineHeight:1.4, display:'-webkit-box', WebkitLineClamp:2, WebkitBoxOrient:'vertical', overflow:'hidden', marginBottom:5 }}>{product.title}</div>
                              {product.min_price&&<div style={{ fontSize:13, fontWeight:700, color:'#e11d48' }}>{(product.min_price/1000000).toFixed(1)}tr</div>}
                              {product.brand&&<div style={{ fontSize:11, color:'#94a3b8', marginTop:2 }}>{product.brand}</div>}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {msg.type==='loading' && (
                    <div>
                      <div style={{ display:'flex', gap:12, marginBottom:14 }}>
                        <div style={{ width:38, height:38, borderRadius:'50%', background:'#e2e8f0' }} />
                        <div style={{ height:44, width:180, background:'#f1f5f9', borderRadius:12 }} />
                      </div>
                      <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill,minmax(148px,1fr))', gap:12, paddingLeft:50 }}>
                        {[...Array(12)].map((_,i)=>(
                          <div key={i} style={{ background:'#fff', border:'1.5px solid #f0f0f8', borderRadius:14, overflow:'hidden' }}>
                            <div style={{ height:128, background:'linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%)', backgroundSize:'200% 100%', animation:'shimmer 1.5s infinite' }} />
                            <div style={{ padding:'9px 11px' }}>
                              <div style={{ height:11, background:'#f1f5f9', borderRadius:6, marginBottom:7 }} />
                              <div style={{ height:11, background:'#f1f5f9', borderRadius:6, width:'60%' }} />
                            </div>
                          </div>
                        ))}
                      </div>
                      <style>{'@keyframes shimmer{0%{background-position:200% 0}100%{background-position:-200% 0}}'}</style>
                    </div>
                  )}
                </div>
              ))}

              {isThinking && (
                <div style={{ display:'flex', gap:12 }}>
                  <div style={{ width:38, height:38, borderRadius:'50%', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', display:'flex', alignItems:'center', justifyContent:'center' }}>
                    <Sparkles size={17} color="#fff" />
                  </div>
                  <div style={{ background:'#fff', borderRadius:'18px 18px 18px 4px', padding:'14px 18px', boxShadow:'0 2px 10px rgba(0,0,0,0.06)', border:'1px solid #f0f0f8', display:'flex', gap:5 }}>
                    {[0,150,300].map(d=><div key={d} style={{ width:8, height:8, borderRadius:'50%', background:'#a5b4fc', animation:`bounce 1.2s ease-in-out ${d}ms infinite` }} />)}
                    <style>{'@keyframes bounce{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}'}</style>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Chat input */}
          <div style={{ borderTop:'1px solid #eff0f8', background:'#fff', padding:'14px 20px', flexShrink:0, boxShadow:'0 -4px 20px rgba(99,102,241,0.07)' }}>
            {isListening && transcript && (
              <div style={{ marginBottom:10, padding:'10px 14px', background:'#eef2ff', border:'1px solid #c7d2fe', borderRadius:10, display:'flex', alignItems:'center', gap:8 }}>
                <Volume2 size={14} color="#6366f1" />
                <span style={{ fontSize:13, color:'#4f46e5' }}>Đang nghe: <strong>{transcript}</strong></span>
              </div>
            )}
            {user && <UserQuickActions onAction={(a)=>{addUser(`📌 ${a}`);addBot(`Tính năng "${a}" đang được phát triển. Bạn muốn tìm kiếm sản phẩm gì?`);}} />}
            <div style={{ display:'flex', gap:10, alignItems:'center' }}>
              <input type="text" value={currentInput} onChange={e=>setCurrentInput(e.target.value)} onKeyDown={e=>e.key==='Enter'&&handleSend()}
                placeholder="Nhập câu trả lời của bạn hoặc nói vào micro..."
                disabled={isThinking}
                style={{ flex:1, padding:'13px 20px', border:'2px solid #e8eaf6', borderRadius:28, fontSize:14.5, color:'#1e1b4b', outline:'none', background:'#f8f9ff', transition:'all 0.2s', fontFamily:'inherit' }}
                onFocus={e=>{e.target.style.borderColor='#6366f1';e.target.style.background='#fff';}}
                onBlur={e=>{e.target.style.borderColor='#e8eaf6';e.target.style.background='#f8f9ff';}}
              />
              {isBrowserSupported && (
                <button onClick={()=>{if(!recognitionRef.current)return;if(isListening){recognitionRef.current.stop();}else{try{recognitionRef.current.start();}catch(e){console.error(e);}}}}
                  disabled={isThinking}
                  style={{ width:46, height:46, borderRadius:'50%', border:'none', cursor:'pointer', background:isListening?'linear-gradient(135deg,#ef4444,#dc2626)':'#f1f5f9', color:isListening?'#fff':'#64748b', display:'flex', alignItems:'center', justifyContent:'center', transition:'all 0.2s', flexShrink:0, boxShadow:isListening?'0 4px 16px rgba(239,68,68,0.4)':'none' }}>
                  {isListening?<MicOff size={18}/>:<Mic size={18}/>}
                </button>
              )}
              <button onClick={handleSend} disabled={!currentInput.trim()||isThinking}
                style={{ width:46, height:46, borderRadius:'50%', border:'none', cursor:'pointer', background:'linear-gradient(135deg,#6366f1,#8b5cf6)', color:'#fff', display:'flex', alignItems:'center', justifyContent:'center', transition:'all 0.2s', flexShrink:0, opacity:(!currentInput.trim()||isThinking)?0.45:1 }}>
                <Send size={18}/>
              </button>
            </div>
            {!user && (
              <p style={{ margin:'8px 0 0', fontSize:12, color:'#94a3b8', textAlign:'center' }}>
                <button onClick={()=>setShowLoginModal(true)} style={{ color:'#6366f1', fontWeight:600, background:'none', border:'none', cursor:'pointer', fontSize:12, padding:0, fontFamily:'inherit' }}>Đăng nhập</button>
                {' '}để lưu yêu thích & nhận gợi ý cá nhân hoá
              </p>
            )}
          </div>

          <SuggestionsPopup isOpen={showSuggestionsPopup} onClose={()=>setShowSuggestionsPopup(false)} category={lastCategoryName} filters={suggestionsPopupFilters} hints={clarifyingHints} onConfirm={(f)=>{setShowSuggestionsPopup(false);searchProductsWithFilters(lastCategoryName,f);}} conversationId={conversationState.conversationId} />
        </>
      

      <LoginModal isOpen={showLoginModal} onClose={() => setShowLoginModal(false)} />
    </div>
  );
};

export default ShoeFinder;