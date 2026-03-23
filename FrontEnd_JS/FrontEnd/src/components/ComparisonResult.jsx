import React from 'react';
import { ArrowLeft, Download, Share2, ThumbsUp, ThumbsDown } from 'lucide-react';

/**
 * ComparisonResult Component
 * Displays detailed comparison results from LLM
 */
export default function ComparisonResult({ data, onBack }) {
  if (!data || !data.products) {
    return (
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        background: '#fff',
        borderRadius: 16,
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <div style={{ fontSize: 14, color: '#9ca3af' }}>No comparison data available</div>
      </div>
    );
  }

  const { products, summary, detailedComparison, recommendation } = data;

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: 'linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%)',
      borderRadius: 16,
      overflow: 'hidden',
      animation: 'slideIn 0.3s ease',
    }}>
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        .comparison-section {
          background: #fff;
          border-radius: 12px;
          padding: 20px;
          margin-bottom: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .comparison-title {
          font-size: 16px;
          font-weight: 700;
          color: #1f2937;
          margin-bottom: 12px;
        }
        .comparison-text {
          font-size: 14px;
          color: #4b5563;
          line-height: 1.6;
        }
      `}</style>

      {/* Header */}
      <div style={{
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        padding: '20px 24px',
        color: '#fff',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
      }}>
        <div>
          <div style={{ fontSize: 20, fontWeight: 700, marginBottom: 4 }}>
            Kết quả so sánh
          </div>
          <div style={{ fontSize: 12, opacity: 0.9 }}>
            {products.length} sản phẩm được so sánh
          </div>
        </div>
        <div style={{ fontSize: 32 }}>🔍</div>
      </div>

      {/* Content */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '24px',
      }}>
        {/* Products Overview */}
        <div style={{ marginBottom: 24 }}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: `repeat(${Math.min(products.length, 3)}, 1fr)`,
            gap: 16,
          }}>
            {products.map((product, idx) => (
              <ProductOverviewCard key={idx} product={product} />
            ))}
          </div>
        </div>

        {/* Summary */}
        <div className="comparison-section">
          <div className="comparison-title">📊 Tóm tắt</div>
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: 16,
            fontSize: 14,
          }}>
            <div>
              <div style={{ color: '#6b7280', fontSize: 12, marginBottom: 4 }}>Best for Comfort</div>
              <div style={{ fontWeight: 600, color: '#667eea' }}>{summary.bestForComfort}</div>
            </div>
            <div>
              <div style={{ color: '#6b7280', fontSize: 12, marginBottom: 4 }}>Best for Price</div>
              <div style={{ fontWeight: 600, color: '#667eea' }}>{summary.bestForPrice}</div>
            </div>
            <div style={{ gridColumn: '1 / -1' }}>
              <div style={{ color: '#6b7280', fontSize: 12, marginBottom: 4 }}>Overall Best</div>
              <div style={{ fontWeight: 600, color: '#667eea' }}>{summary.bestOverall}</div>
            </div>
          </div>
        </div>

        {/* Detailed Comparison */}
        <div className="comparison-section">
          <div className="comparison-title">🔬 So sánh chi tiết</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
            {/* Price */}
            <ComparisonDetail
              title="💰 Giá"
              content={detailedComparison.price}
            />
            {/* Design */}
            <ComparisonDetail
              title="🎨 Thiết kế"
              content={detailedComparison.design}
            />
            {/* Comfort */}
            <ComparisonDetail
              title="👟 Thoải mái"
              content={detailedComparison.comfort}
            />
            {/* Durability */}
            <ComparisonDetail
              title="💪 Độ bền"
              content={detailedComparison.durability}
            />
          </div>
        </div>

        {/* Recommendation */}
        <div style={{
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 30%, #f093fb 100%)',
          borderRadius: 12,
          padding: '20px',
          color: '#fff',
          marginBottom: 16,
          boxShadow: '0 8px 32px rgba(102, 126, 234, 0.3)',
        }}>
          <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 12 }}>
            💡 Gợi ý của chúng tôi
          </div>
          <div style={{
            fontSize: 14,
            lineHeight: 1.6,
            opacity: 0.95,
          }}>
            {recommendation}
          </div>
        </div>

        {/* Specs Comparison */}
        <SpecsComparison products={products} />
      </div>

      {/* Footer */}
      <div style={{
        padding: '16px 24px',
        background: '#fff',
        borderTop: '1px solid #e5e7eb',
        display: 'flex',
        gap: 12,
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <ActionButton icon={<ArrowLeft size={16} />} label="Back" onClick={onBack} />
        <ActionButton icon={<Download size={16} />} label="Download" onClick={() => alert('Download functionality coming soon')} />
        <ActionButton icon={<Share2 size={16} />} label="Share" onClick={() => alert('Share functionality coming soon')} />
      </div>
    </div>
  );
}

/**
 * ProductOverviewCard Component
 */
function ProductOverviewCard({ product }) {
  return (
    <div style={{
      background: '#fff',
      borderRadius: 12,
      overflow: 'hidden',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      transition: 'all 0.3s ease',
      cursor: 'pointer',
    }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-4px)';
        e.currentTarget.style.boxShadow = '0 12px 24px rgba(0,0,0,0.15)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
      }}
    >
      {/* Image */}
      <img
        src={product.image}
        alt={product.name}
        style={{
          width: '100%',
          height: 140,
          objectFit: 'cover',
          background: '#f3f4f6',
        }}
      />

      {/* Info */}
      <div style={{ padding: '16px' }}>
        <div style={{
          fontSize: 14,
          fontWeight: 600,
          color: '#1f2937',
          marginBottom: 8,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
        }}>
          {product.name}
        </div>
        <div style={{
          fontSize: 16,
          fontWeight: 700,
          color: '#667eea',
          marginBottom: 8,
        }}>
          {product.price}
        </div>
        <div style={{
          display: 'flex',
          gap: 4,
          alignItems: 'center',
          fontSize: 12,
          color: '#6b7280',
        }}>
          <span style={{ fontSize: 16 }}>⭐</span>
          <span>{product.rating}</span>
          <span style={{ color: '#d1d5db' }}>•</span>
          <span>{product.reviews} reviews</span>
        </div>
      </div>
    </div>
  );
}

/**
 * ComparisonDetail Component
 */
function ComparisonDetail({ title, content }) {
  return (
    <div>
      <div style={{
        fontSize: 14,
        fontWeight: 600,
        color: '#1f2937',
        marginBottom: 8,
      }}>
        {title}
      </div>
      <div style={{
        fontSize: 13,
        color: '#4b5563',
        lineHeight: 1.6,
        paddingLeft: 12,
        borderLeft: '3px solid #667eea',
      }}>
        {content}
      </div>
    </div>
  );
}

/**
 * SpecsComparison Component - Shows detailed specs table
 */
function SpecsComparison({ products }) {
  if (products.length === 0) return null;

  const specs = products[0].specs || {};
  const specKeys = Object.keys(specs);

  if (specKeys.length === 0) return null;

  return (
    <div className="comparison-section">
      <div className="comparison-title">📋 So sánh thông số kỹ thuật</div>
      <div style={{
        overflowX: 'auto',
      }}>
        <table style={{
          width: '100%',
          borderCollapse: 'collapse',
          fontSize: 13,
        }}>
          <tbody>
            <tr style={{ borderBottom: '1px solid #f3f4f6' }}>
              <td style={{
                padding: '10px 0',
                fontWeight: 600,
                color: '#6b7280',
                width: '30%',
              }}>Spec</td>
              {products.map((product, idx) => (
                <td key={idx} style={{
                  padding: '10px 12px',
                  fontWeight: 600,
                  color: '#1f2937',
                  borderLeft: '1px solid #f3f4f6',
                }}>
                  {product.name}
                </td>
              ))}
            </tr>
            {specKeys.map((key) => (
              <tr key={key} style={{ borderBottom: '1px solid #f3f4f6' }}>
                <td style={{
                  padding: '10px 0',
                  color: '#6b7280',
                  fontWeight: 500,
                  textTransform: 'capitalize',
                }}>
                  {key.replace(/_/g, ' ')}
                </td>
                {products.map((product, idx) => (
                  <td key={idx} style={{
                    padding: '10px 12px',
                    color: '#374151',
                    borderLeft: '1px solid #f3f4f6',
                  }}>
                    {product.specs[key]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/**
 * ActionButton Component
 */
function ActionButton({ icon, label, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 14px',
        border: '1px solid #e5e7eb',
        background: '#fff',
        borderRadius: 8,
        cursor: 'pointer',
        fontSize: 13,
        fontWeight: 500,
        color: '#6b7280',
        transition: 'all 0.2s',
        fontFamily: 'inherit',
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = '#667eea';
        e.currentTarget.style.color = '#667eea';
        e.currentTarget.style.background = '#f0f4ff';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = '#e5e7eb';
        e.currentTarget.style.color = '#6b7280';
        e.currentTarget.style.background = '#fff';
      }}
    >
      {icon}
      {label}
    </button>
  );
}
