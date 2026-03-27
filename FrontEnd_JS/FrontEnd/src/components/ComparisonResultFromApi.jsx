import React, { useState } from 'react';
import { ArrowLeft, Download, Share2, Copy, Check, Save, Clock } from 'lucide-react';
import { saveComparison } from '../utils/comparisonHistoryApi';

/**
 * ComparisonResultFromApi Component
 * Displays comparison results directly from backend API response
 * Handles markdown comparison text and product snapshots
 */
export default function ComparisonResultFromApi({ data, onBack, onOpenHistory }) {
  const [copied, setCopied] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  if (!data || !data.comparison) {
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

  const { comparison, snapshot_a, snapshot_b } = data;

  const handleCopy = () => {
    navigator.clipboard.writeText(comparison);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    const element = document.createElement('a');
    const file = new Blob([comparison], { type: 'text/markdown' });
    element.href = URL.createObjectURL(file);
    element.download = `comparison-${new Date().getTime()}.md`;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
  };

  const handleSaveComparison = async () => {
    try {
      setSaving(true);
      
      // Get product IDs from snapshots or use placeholder
      const product1Id = snapshot_a?.product_id || snapshot_a?.id || 1;
      const product2Id = snapshot_b?.product_id || snapshot_b?.id || 2;
      const product1Name = snapshot_a?.name || snapshot_a?.title || 'Product 1';
      const product2Name = snapshot_b?.name || snapshot_b?.title || 'Product 2';
      
      const saveData = {
        product_id_1: product1Id,
        product_id_2: product2Id,
        product_name_1: product1Name,
        product_name_2: product2Name,
        snapshot_a: snapshot_a,
        snapshot_b: snapshot_b,
        comparison_result: comparison,
        summary_json: data.summary || null,
        api_request: { product_ids: [product1Id, product2Id] },
        notes: null,
        comparison_type: 'detailed',
        llm_model: 'gpt-4',
      };
      
      await saveComparison(saveData);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      console.log('✅ Comparison saved successfully');
    } catch (error) {
      console.error('❌ Error saving comparison:', error);
      alert(`Lỗi khi lưu: ${error.message}`);
    } finally {
      setSaving(false);
    }
  };

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
        .comparison-content {
          background: #fff;
          border-radius: 12px;
          padding: 24px;
          margin-bottom: 16px;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }
        .comparison-content h1, 
        .comparison-content h2, 
        .comparison-content h3 {
          color: #1f2937;
          margin-top: 16px;
          margin-bottom: 12px;
        }
        .comparison-content h1 {
          font-size: 24px;
          font-weight: 700;
        }
        .comparison-content h2 {
          font-size: 18px;
          font-weight: 700;
          border-bottom: 2px solid #f59e0b;
          padding-bottom: 8px;
        }
        .comparison-content h3 {
          font-size: 16px;
          font-weight: 600;
          color: #2d3748;
        }
        .comparison-content p, 
        .comparison-content li {
          font-size: 14px;
          color: #4b5563;
          line-height: 1.7;
          margin-bottom: 8px;
        }
        .comparison-content ul, 
        .comparison-content ol {
          margin-left: 20px;
          margin-bottom: 12px;
        }
        .comparison-content li {
          margin-bottom: 6px;
        }
        .comparison-content strong {
          color: #1f2937;
          font-weight: 600;
        }
        .comparison-content em {
          color: #667eea;
          font-style: italic;
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
            {snapshot_a?.name && snapshot_b?.name ? '2 sản phẩm được so sánh' : 'Phân tích chi tiết'}
          </div>
        </div>
        <div style={{ fontSize: 32 }}>🔍</div>
      </div>

      {/* Products Overview Row */}
      {snapshot_a && snapshot_b && (
        <div style={{
          padding: '24px',
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: 16,
        }}>
          <ProductCard product={snapshot_a} label="Sản phẩm A" />
          <ProductCard product={snapshot_b} label="Sản phẩm B" />
        </div>
      )}

      {/* Comparison Content */}
      <div style={{
        flex: 1,
        overflowY: 'auto',
        padding: '0 24px 24px 24px',
      }}>
        <div className="comparison-content">
          <MarkdownRenderer content={comparison} />
        </div>
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
        flexWrap: 'wrap',
      }}>
        <ActionButton 
          icon={<ArrowLeft size={16} />} 
          label="Quay lại" 
          onClick={onBack} 
        />
        <ActionButton 
          icon={saved ? <Check size={16} /> : <Save size={16} />} 
          label={saved ? "Đã lưu" : "Lưu"} 
          onClick={handleSaveComparison}
          disabled={saving || saved}
          loading={saving}
        />
        {onOpenHistory && (
          <ActionButton 
            icon={<Clock size={16} />} 
            label="Lịch sử" 
            onClick={onOpenHistory}
          />
        )}
        <ActionButton 
          icon={copied ? <Check size={16} /> : <Copy size={16} />} 
          label={copied ? "Đã copy" : "Copy"} 
          onClick={handleCopy}
          disabled={copied}
        />
        <ActionButton 
          icon={<Download size={16} />} 
          label="Tải xuống" 
          onClick={handleDownload} 
        />
        <ActionButton 
          icon={<Share2 size={16} />} 
          label="Chia sẻ" 
          onClick={() => {
            if (navigator.share) {
              navigator.share({
                title: 'So sánh sản phẩm',
                text: comparison,
              });
            } else {
              alert('Chức năng chia sẻ không được hỗ trợ trên trình duyệt này');
            }
          }}
        />
      </div>
    </div>
  );
}

/**
 * MarkdownRenderer Component - Simple markdown to HTML renderer
 */
function MarkdownRenderer({ content }) {
  if (!content) return null;

  // Split content by lines and process
  const lines = content.split('\n');
  const elements = [];
  let currentList = [];
  let listType = null;

  const flushList = () => {
    if (currentList.length > 0) {
      if (listType === 'ul') {
        elements.push(
          <ul key={`list-${elements.length}`} style={{ marginLeft: 20, marginBottom: 12 }}>
            {currentList.map((item, i) => (
              <li key={i} style={{ marginBottom: 6 }}>{item}</li>
            ))}
          </ul>
        );
      } else if (listType === 'ol') {
        elements.push(
          <ol key={`list-${elements.length}`} style={{ marginLeft: 20, marginBottom: 12 }}>
            {currentList.map((item, i) => (
              <li key={i} style={{ marginBottom: 6 }}>{item}</li>
            ))}
          </ol>
        );
      }
      currentList = [];
      listType = null;
    }
  };

  lines.forEach((line, idx) => {
    const trimmed = line.trim();

    // Handle headings
    if (trimmed.startsWith('# ')) {
      flushList();
      elements.push(
        <h1 key={idx} style={{ fontSize: 24, fontWeight: 700, marginTop: 16, marginBottom: 12 }}>
          {trimmed.substring(2)}
        </h1>
      );
      return;
    }
    if (trimmed.startsWith('## ')) {
      flushList();
      elements.push(
        <h2 key={idx} style={{ 
          fontSize: 18, 
          fontWeight: 700, 
          marginTop: 16, 
          marginBottom: 12,
          borderBottom: '2px solid #f59e0b',
          paddingBottom: 8,
        }}>
          {trimmed.substring(3)}
        </h2>
      );
      return;
    }
    if (trimmed.startsWith('### ')) {
      flushList();
      elements.push(
        <h3 key={idx} style={{ 
          fontSize: 16, 
          fontWeight: 600, 
          marginTop: 12, 
          marginBottom: 8,
          color: '#2d3748',
        }}>
          {trimmed.substring(4)}
        </h3>
      );
      return;
    }

    // Handle unordered lists
    if (trimmed.startsWith('- ')) {
      if (listType !== 'ul') {
        flushList();
        listType = 'ul';
      }
      currentList.push(<RichText text={trimmed.substring(2)} />);
      return;
    }

    // Handle ordered lists
    if (/^\d+\. /.test(trimmed)) {
      if (listType !== 'ol') {
        flushList();
        listType = 'ol';
      }
      const match = trimmed.match(/^\d+\.\s*(.*)/);
      if (match) {
        currentList.push(<RichText text={match[1]} />);
      }
      return;
    }

    // Skip empty lines if in list
    if (trimmed === '' && listType) {
      return;
    }

    // Handle paragraphs
    if (trimmed !== '') {
      flushList();
      elements.push(
        <p key={idx} style={{ 
          fontSize: 14, 
          color: '#4b5563', 
          lineHeight: 1.7, 
          marginBottom: 12,
        }}>
          <RichText text={trimmed} />
        </p>
      );
      return;
    }

    // Handle empty lines
    if (trimmed === '') {
      flushList();
      elements.push(<div key={idx} style={{ height: 8 }} />);
    }
  });

  flushList();

  return <>{elements}</>;
}

/**
 * RichText Component - Renders text with bold, italic, links
 */
function RichText({ text }) {
  if (!text) return null;

  const parts = [];
  let lastIdx = 0;
  const patterns = [
    { regex: /\*\*(.*?)\*\*/g, style: { fontWeight: 600, color: '#1f2937' }, tag: 'strong' },
    { regex: /\*(.*?)\*/g, style: { fontStyle: 'italic', color: '#667eea' }, tag: 'em' },
    { regex: /\[(.*?)\]\((.*?)\)/g, style: { color: '#667eea', textDecoration: 'underline', cursor: 'pointer' }, tag: 'a' },
  ];

  // Process bold first
  const boldRegex = /\*\*(.*?)\*\*/g;
  const italicRegex = /\*(.*?)\*/g;
  const linkRegex = /\[(.*?)\]\((.*?)\)/g;

  let regex = /(.*?)(?:\*\*(.*?)\*\*|\*(.*?)\*|\[(.*?)\]\((.*?)\))/;
  let result;
  let currentText = text;
  let offset = 0;

  return (
    <>
      {currentText.split(/(\*\*.*?\*\*|\*.*?\*|\[.*?\]\(.*?\))/g).map((segment, i) => {
        if (!segment) return null;

        // Bold
        if (segment.startsWith('**') && segment.endsWith('**')) {
          return <strong key={i} style={{ fontWeight: 600, color: '#1f2937' }}>
            {segment.substring(2, segment.length - 2)}
          </strong>;
        }

        // Italic
        if (segment.startsWith('*') && segment.endsWith('*') && !segment.startsWith('**')) {
          return <em key={i} style={{ fontStyle: 'italic', color: '#667eea' }}>
            {segment.substring(1, segment.length - 1)}
          </em>;
        }

        // Link
        const linkMatch = segment.match(/\[(.*?)\]\((.*?)\)/);
        if (linkMatch) {
          return (
            <a 
              key={i}
              href={linkMatch[2]}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#667eea', textDecoration: 'underline', cursor: 'pointer' }}
            >
              {linkMatch[1]}
            </a>
          );
        }

        // Normal text
        return <span key={i}>{segment}</span>;
      })}
    </>
  );
}

/**
 * ProductCard Component - Displays product info from snapshot
 */function ProductCard({ product, label }) {
  if (!product) return null;

  return (
    <div style={{
      background: '#fff',
      borderRadius: 12,
      overflow: 'hidden',
      boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      transition: 'all 0.3s ease',
      cursor: 'pointer',
      border: '2px solid transparent',
    }}
      onMouseEnter={(e) => {
        e.currentTarget.style.transform = 'translateY(-4px)';
        e.currentTarget.style.boxShadow = '0 12px 24px rgba(0,0,0,0.15)';
        e.currentTarget.style.borderColor = '#f59e0b';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.transform = 'translateY(0)';
        e.currentTarget.style.boxShadow = '0 2px 8px rgba(0,0,0,0.08)';
        e.currentTarget.style.borderColor = 'transparent';
      }}
    >
      {/* Image */}
      {product.thumbnail && (
        <div style={{
          height: 140,
          background: '#f3f4f6',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          overflow: 'hidden',
        }}>
          <img
            src={product.thumbnail}
            alt={product.name}
            style={{
              maxWidth: '100%',
              maxHeight: '100%',
              objectFit: 'contain',
            }}
          />
        </div>
      )}

      {/* Info */}
      <div style={{ padding: '16px' }}>
        <div style={{
          fontSize: 11,
          fontWeight: 600,
          color: '#6b7280',
          marginBottom: 6,
          textTransform: 'uppercase',
          letterSpacing: 0.5,
        }}>
          {label}
        </div>
        <div style={{
          fontSize: 13,
          fontWeight: 600,
          color: '#1f2937',
          marginBottom: 8,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
          minHeight: 36,
        }}>
          {product.name}
        </div>
        <div style={{
          fontSize: 16,
          fontWeight: 700,
          color: '#f59e0b',
          marginBottom: 8,
        }}>
          {typeof product.price === 'number' 
            ? (product.price / 1000).toLocaleString('vi-VN') + 'đ'
            : product.price
          }
        </div>
        <div style={{
          display: 'flex',
          gap: 12,
          alignItems: 'center',
          fontSize: 12,
          color: '#6b7280',
        }}>
          {product.rating_avg && (
            <>
              <span style={{ fontSize: 16 }}>⭐</span>
              <span>{product.rating_avg} ({product.rating_count} reviews)</span>
            </>
          )}
        </div>
        {product.brand && (
          <div style={{
            fontSize: 11,
            color: '#94a3b8',
            marginTop: 8,
            paddingTop: 8,
            borderTop: '1px solid #e5e7eb',
          }}>
            <strong style={{ color: '#6b7280' }}>Brand:</strong> {product.brand}
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * ActionButton Component
 */
function ActionButton({ icon, label, onClick, disabled = false, loading = false }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '8px 14px',
        border: '1px solid #e5e7eb',
        background: disabled ? '#f3f4f6' : '#fff',
        borderRadius: 8,
        cursor: disabled ? 'not-allowed' : 'pointer',
        fontSize: 13,
        fontWeight: 500,
        color: disabled ? '#9ca3af' : '#6b7280',
        transition: 'all 0.2s',
        fontFamily: 'inherit',
        opacity: disabled ? 0.6 : 1,
      }}
      onMouseEnter={(e) => {
        if (!disabled) {
          e.currentTarget.style.borderColor = '#667eea';
          e.currentTarget.style.color = '#667eea';
          e.currentTarget.style.background = '#f0f4ff';
        }
      }}
      onMouseLeave={(e) => {
        if (!disabled) {
          e.currentTarget.style.borderColor = '#e5e7eb';
          e.currentTarget.style.color = '#6b7280';
          e.currentTarget.style.background = '#fff';
        }
      }}
    >
      {loading ? (
        <span style={{ animation: 'spin 1s linear infinite', display: 'inline-flex' }}>
          {icon}
        </span>
      ) : (
        icon
      )}
      {label}
    </button>
  );
}
