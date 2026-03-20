import React from 'react';
import { CheckCircle2, Heart } from 'lucide-react';

/* ─── Skeleton ──────────────────────────────────────────────── */
const SkeletonGrid = () => (
  <div style={{ animation: 'fadeIn 0.2s ease', marginBottom: 20, opacity: 0.6 }}>
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
      <div style={{
        width: 15, height: 15, borderRadius: '50%', background: '#a5b4fc',
        animation: 'bounce 1.2s ease-in-out infinite',
      }} />
      <span style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b' }}>
        Đang tìm kết quả mới...
      </span>
    </div>
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(148px,1fr))', gap: 12 }}>
      {[...Array(6)].map((_, i) => (
        <div key={i} style={{ background: '#fff', border: '1.5px solid #f0f0f8', borderRadius: 14, overflow: 'hidden' }}>
          <div style={{
            height: 128,
            background: 'linear-gradient(90deg,#f1f5f9 25%,#e2e8f0 50%,#f1f5f9 75%)',
            backgroundSize: '200% 100%', animation: 'shimmer 1.5s infinite',
          }} />
          <div style={{ padding: '9px 11px' }}>
            <div style={{ height: 11, background: '#f1f5f9', borderRadius: 6, marginBottom: 7 }} />
            <div style={{ height: 11, background: '#f1f5f9', borderRadius: 6, width: '60%' }} />
          </div>
        </div>
      ))}
    </div>
  </div>
);

/* ─── Single product card ───────────────────────────────────── */
const ProductCard = ({ product, index, isFavorited, onToggleFavorite, onOpen }) => {
  const productUrl   = product.product_url || product.link;
  const productImage = product.thumbnail   || product.image;
  const productPrice = product.price       || product.skus?.[0]?.price;

  return (
    <div
      className="product-card"
      onClick={() => onOpen(productUrl)}
    >
      {productImage && (
        <div style={{
          background: '#f8f9ff', height: 128,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          overflow: 'hidden', position: 'relative',
        }}>
          <img
            src={productImage}
            alt={product.title}
            style={{ maxWidth: '100%', maxHeight: '100%', objectFit: 'contain' }}
          />

          {index === 0 && (
            <div style={{
              position: 'absolute', top: 7, right: 7,
              background: 'linear-gradient(135deg,#f59e0b,#d97706)',
              color: '#fff', fontSize: 9.5, fontWeight: 700,
              padding: '2px 7px', borderRadius: 7,
            }}>TOP</div>
          )}

          <button
            onClick={(e) => { e.stopPropagation(); onToggleFavorite(); }}
            style={{
              position: 'absolute', bottom: 6, right: 6,
              background:    isFavorited ? '#e11d48' : 'rgba(255,255,255,0.9)',
              border:        isFavorited ? 'none' : '1.5px solid #e2e8f0',
              color:         isFavorited ? '#fff' : '#e11d48',
              borderRadius:  '50%', width: 32, height: 32,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              cursor: 'pointer', transition: 'all 0.2s',
              boxShadow: isFavorited ? '0 2px 8px rgba(225,29,72,0.3)' : '0 2px 4px rgba(0,0,0,0.1)',
            }}
            onMouseEnter={e => e.currentTarget.style.transform = 'scale(1.15)'}
            onMouseLeave={e => e.currentTarget.style.transform = 'scale(1)'}
          >
            <Heart size={16} fill={isFavorited ? '#fff' : 'none'} />
          </button>
        </div>
      )}

      <div style={{ padding: '9px 11px' }}>
        <div style={{
          fontSize: 11.5, fontWeight: 600, color: '#1e1b4b', lineHeight: 1.4,
          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical',
          overflow: 'hidden', marginBottom: 5,
        }}>
          {product.title}
        </div>
        {productPrice && (
          <div style={{ fontSize: 13, fontWeight: 700, color: '#e11d48' }}>
            {(productPrice / 1_000_000).toFixed(1)}tr
          </div>
        )}
        {product.brand && (
          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 2 }}>{product.brand}</div>
        )}
      </div>
    </div>
  );
};

/* ─── Grid ──────────────────────────────────────────────────── */
const ProductGrid = ({ products, productCount, productsLoading, favoriteProductIds, onToggleFavorite, onOpen }) => {
  const hasProducts = products && products.length > 0;

  return (
    <>
      {/* Show loading skeleton (old products remain visible below) */}
      {productsLoading && <SkeletonGrid />}

      {/* Always show products if we have them (even while loading new ones) */}
      {hasProducts && (
        <div style={{ animation: 'fadeIn 0.3s ease', opacity: productsLoading ? 0.6 : 1, transition: 'opacity 0.2s' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 14 }}>
            <CheckCircle2 size={15} color="#10b981" />
            <span style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b' }}>
              Tìm thấy {productCount} sản phẩm
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(148px,1fr))', gap: 12, pointerEvents: productsLoading ? 'none' : 'auto' }}>
            {products.map((product, i) => (
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
      )}
    </>
  );
};

export default ProductGrid;