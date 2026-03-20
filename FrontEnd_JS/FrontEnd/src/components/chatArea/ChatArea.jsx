import React from 'react';
import { Sparkles, CheckCircle2, Heart } from 'lucide-react';

// ─── Bot bubble ──────────────────────────────────────────────
const BotBubble = ({ msg, onQuickReply }) => (
  <div style={{ display: 'flex', gap: 12 }}>
    <div style={{
      width: 36, height: 36, borderRadius: '50%',
      background: 'linear-gradient(135deg,#6366f1,#8b5cf6)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0,
    }}>
      <Sparkles size={16} color="#fff" />
    </div>
    <div>
      <div style={{
        background: '#fff', borderRadius: '16px 16px 16px 4px',
        padding: '12px 16px', maxWidth: 520,
        boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #f0f0f8',
        whiteSpace: 'pre-wrap', color: '#1e1b4b', fontSize: 14, lineHeight: 1.6,
      }}>
        {msg.text}
      </div>
      {msg.quickReplies && (
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 9 }}>
          {msg.quickReplies.map((r, i) => (
            <button key={i} onClick={() => onQuickReply(r)}
              style={{ padding: '7px 15px', background: '#fff', border: '2px solid #c7d2fe', color: '#4f46e5', borderRadius: 20, fontSize: 13, fontWeight: 600, cursor: 'pointer', fontFamily: 'inherit' }}
              onMouseEnter={e => e.currentTarget.style.background = '#eef2ff'}
              onMouseLeave={e => e.currentTarget.style.background = '#fff'}
            >{r}</button>
          ))}
        </div>
      )}
    </div>
  </div>
);

// ─── User bubble ─────────────────────────────────────────────
const UserBubble = ({ msg }) => (
  <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
    <div style={{
      background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff',
      borderRadius: '16px 16px 4px 16px', padding: '12px 16px', maxWidth: 440,
      boxShadow: '0 3px 12px rgba(99,102,241,0.28)', fontSize: 14, lineHeight: 1.5,
    }}>
      {msg.text}
    </div>
  </div>
);

// ─── Thinking dots ───────────────────────────────────────────
const ThinkingIndicator = () => (
  <div style={{ display: 'flex', gap: 12 }}>
    <div style={{ width: 36, height: 36, borderRadius: '50%', background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Sparkles size={16} color="#fff" />
    </div>
    <div style={{ background: '#fff', borderRadius: '16px 16px 16px 4px', padding: '13px 16px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)', border: '1px solid #f0f0f8', display: 'flex', gap: 5 }}>
      {[0, 150, 300].map(d => (
        <div key={d} style={{ width: 7, height: 7, borderRadius: '50%', background: '#a5b4fc', animation: `bounce 1.2s ease-in-out ${d}ms infinite` }} />
      ))}
    </div>
  </div>
);

// ─── Single product card ─────────────────────────────────────
const ProductCard = ({ product, index, isFavorited, onToggleFavorite, onOpen }) => {
  const productUrl   = product.product_url || product.link;
  const productImage = product.thumbnail   || product.image;
  const productPrice = product.price       || product.skus?.[0]?.price;

  return (
    <div className="product-card" onClick={() => onOpen(productUrl)}>
      {productImage && (
        <div style={{ background: '#f8f9ff', height: 128, display: 'flex', alignItems: 'center', justifyContent: 'center', overflow: 'hidden', position: 'relative' }}>
          <img src={productImage} alt={product.title} style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }} />
          {index === 0 && (
            <div style={{ position: 'absolute', top: 7, right: 7, background: 'linear-gradient(135deg,#f59e0b,#d97706)', color: '#fff', fontSize: 9.5, fontWeight: 700, padding: '2px 7px', borderRadius: 7 }}>TOP</div>
          )}
          <button
            onClick={e => { e.stopPropagation(); onToggleFavorite(); }}
            style={{ position: 'absolute', bottom: 6, right: 6, background: isFavorited ? '#e11d48' : 'rgba(255,255,255,0.9)', border: isFavorited ? 'none' : '1.5px solid #e2e8f0', color: isFavorited ? '#fff' : '#e11d48', borderRadius: '50%', width: 32, height: 32, display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer', transition: 'all 0.2s', boxShadow: isFavorited ? '0 2px 8px rgba(225,29,72,0.3)' : '0 2px 4px rgba(0,0,0,0.1)' }}
            onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.15)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
          >
            <Heart size={16} fill={isFavorited ? '#fff' : 'none'} />
          </button>
        </div>
      )}
      <div style={{ padding: '9px 11px' }}>
        <div style={{ fontSize: 11.5, fontWeight: 600, color: '#1e1b4b', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', marginBottom: 5 }}>
          {product.title}
        </div>
        {productPrice && (
          <div style={{ fontSize: 13, fontWeight: 700, color: '#e11d48' }}>
            {(productPrice / 1_000_000).toFixed(1)}tr
          </div>
        )}
        {product.brand && <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{product.brand}</div>}
      </div>
    </div>
  );
};

// ─── Products bubble — inline trong chat stream ──────────────
const ProductsBubble = ({ msg, favoriteProductIds, onToggleFavorite, onOpen }) => (
  <div style={{ animation: 'fadeIn 0.3s ease' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
      <CheckCircle2 size={15} color="#10b981" />
      <span style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b' }}>
        Tìm thấy {msg.productCount} sản phẩm
      </span>
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(148px,1fr))', gap: 12 }}>
      {msg.products.map((product, i) => (
        <ProductCard
          key={product.id || i}
          product={product}
          index={i}
          isFavorited={favoriteProductIds.has(product.id)}
          onToggleFavorite={() => onToggleFavorite(product)}
          onOpen={onOpen}
        />
      ))}
    </div>
  </div>
);

// ─── Skeleton (loading mới) ──────────────────────────────────
const SkeletonBubble = () => (
  <div style={{ animation: 'fadeIn 0.2s ease' }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
      <div style={{ width: 15, height: 15, borderRadius: '50%', background: '#a5b4fc', animation: 'bounce 1.2s ease-in-out infinite' }} />
      <span style={{ fontWeight: 700, fontSize: 14, color: '#94a3b8' }}>Đang tìm sản phẩm...</span>
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(148px,1fr))', gap: 12 }}>
      {[...Array(6)].map((_, i) => (
        <div key={i} style={{ background: '#fff', border: '1.5px solid #f0f0f8', borderRadius: 14, overflow: 'hidden' }}>
          <div style={{ height: 128, background: 'linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%)', backgroundSize: '200% 100%', animation: 'shimmer 1.5s infinite' }} />
          <div style={{ padding: '9px 11px' }}>
            <div style={{ height: 11, background: '#f1f5f9', borderRadius: 6, marginBottom: 7 }} />
            <div style={{ height: 11, background: '#f1f5f9', borderRadius: 6, width: '60%' }} />
          </div>
        </div>
      ))}
    </div>
  </div>
);

// ─── ChatArea ─────────────────────────────────────────────────
/**
 * Render toàn bộ conversation stream theo thứ tự.
 * messages có thể chứa:
 *   { type: 'user' }
 *   { type: 'bot' }
 *   { type: 'products', products, productCount, msgId }
 *
 * isThinking: hiện thinking dots + skeleton ở cuối
 */
const ChatArea = ({ messages, isThinking, onQuickReply, favoriteProductIds, onToggleFavorite, onOpen }) => {
  if (!messages.length && !isThinking) return null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20, marginBottom: 20 }}>
      {messages.map((msg, idx) => (
        <div key={msg.msgId || idx}>
          {msg.type === 'bot'      && <BotBubble      msg={msg} onQuickReply={onQuickReply} />}
          {msg.type === 'user'     && <UserBubble     msg={msg} />}
          {msg.type === 'products' && (
            <ProductsBubble
              msg={msg}
              favoriteProductIds={favoriteProductIds}
              onToggleFavorite={onToggleFavorite}
              onOpen={onOpen}
            />
          )}
        </div>
      ))}

      {/* Thinking: dots + skeleton cùng lúc */}
      {isThinking && (
        <>
          <ThinkingIndicator />
          <SkeletonBubble />
        </>
      )}
    </div>
  );
};

export default ChatArea;