import React, { useState, useEffect } from 'react';
import { 
  ArrowLeft, 
  Loader, 
  Trash2, 
  Star, 
  Calendar,
  Edit2,
  Eye,
  AlertCircle,
} from 'lucide-react';
import {
  getComparisonHistory,
  deleteComparison,
  toggleComparisonStar,
  updateComparisonNotes,
  getComparisonDetail,
} from '../utils/comparisonHistoryApi';

/**
 * ComparisonHistory Modal
 * Shows list of saved product comparisons with options to view, edit, delete
 */
export default function ComparisonHistoryModal({ user, onBack, onSelectComparison }) {
  const [comparisons, setComparisons] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedComparison, setSelectedComparison] = useState(null);
  const [showDetail, setShowDetail] = useState(false);
  const [showStarredOnly, setShowStarredOnly] = useState(false);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [editingNotes, setEditingNotes] = useState(null);
  const [notesText, setNotesText] = useState('');
  const [deleting, setDeleting] = useState(null);

  const limit = 10;

  // Fetch comparisons on mount and when filters change
  useEffect(() => {
    fetchComparisons();
  }, [showStarredOnly, page]);

  const fetchComparisons = async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await getComparisonHistory({
        limit,
        offset: page * limit,
        starred_only: showStarredOnly,
      });
      setComparisons(response.comparisons);
      setTotal(response.total);
    } catch (err) {
      console.error('Error fetching comparisons:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleViewDetail = async (comparison) => {
    try {
      setLoading(true);
      const detail = await getComparisonDetail(comparison.id);
      setSelectedComparison(detail);
      setShowDetail(true);
    } catch (err) {
      setError(`Error loading comparison: ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (comparisonId) => {
    if (!window.confirm('Bạn có chắc muốn xóa so sánh này?')) return;

    try {
      setDeleting(comparisonId);
      await deleteComparison(comparisonId);
      setComparisons(comps => comps.filter(c => c.id !== comparisonId));
      setTotal(t => t - 1);
    } catch (err) {
      setError(`Error deleting comparison: ${err.message}`);
    } finally {
      setDeleting(null);
    }
  };

  const handleToggleStar = async (comparison) => {
    try {
      const newStarred = !comparison.is_starred;
      await toggleComparisonStar(comparison.id, newStarred);
      setComparisons(comps =>
        comps.map(c =>
          c.id === comparison.id ? { ...c, is_starred: newStarred } : c
        )
      );
    } catch (err) {
      setError(`Error updating star: ${err.message}`);
    }
  };

  const handleEditNotes = async (comparisonId) => {
    try {
      await updateComparisonNotes(comparisonId, notesText);
      setComparisons(comps =>
        comps.map(c =>
          c.id === comparisonId ? { ...c, notes: notesText } : c
        )
      );
      setEditingNotes(null);
      setNotesText('');
    } catch (err) {
      setError(`Error updating notes: ${err.message}`);
    }
  };

  // Format date
  const formatDate = (dateStr) => {
    const date = new Date(dateStr);
    return date.toLocaleDateString('vi-VN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  // If showing detail, render detail view
  if (showDetail && selectedComparison) {
    return (
      <ComparisonHistoryDetail
        comparison={selectedComparison}
        onBack={() => {
          setShowDetail(false);
          setSelectedComparison(null);
        }}
        onSelect={onSelectComparison}
      />
    );
  }

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#fff',
      borderRadius: 12,
      overflow: 'hidden',
      animation: 'slideIn 0.3s ease',
    }}>
      <style>{`
        @keyframes slideIn {
          from { opacity: 0; transform: translateX(20px); }
          to { opacity: 1; transform: translateX(0); }
        }
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .comparison-item {
          animation: fadeIn 0.3s ease;
        }
        @keyframes fadeIn {
          from { opacity: 0; }
          to { opacity: 1; }
        }
      `}</style>

      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '16px 20px',
        borderBottom: '1px solid #f0f0f8',
        background: 'linear-gradient(135deg, #667eea, #764ba2)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <button
            onClick={onBack}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              color: '#fff',
              borderRadius: '50%',
              width: 36,
              height: 36,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.3)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'rgba(255,255,255,0.2)')}
          >
            <ArrowLeft size={18} />
          </button>
          <div style={{ color: '#fff' }}>
            <div style={{ fontSize: 16, fontWeight: 700 }}>📋 Lịch sử so sánh</div>
            <div style={{ fontSize: 12, opacity: 0.8 }}>
              {total > 0 ? `${total} so sánh` : 'Chưa có so sánh'}
            </div>
          </div>
        </div>

        {/* Filter buttons */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            onClick={() => {
              setShowStarredOnly(!showStarredOnly);
              setPage(0);
            }}
            style={{
              background: showStarredOnly ? 'rgba(255,215,0,0.9)' : 'rgba(255,255,255,0.2)',
              border: 'none',
              color: showStarredOnly ? '#000' : '#fff',
              padding: '6px 12px',
              borderRadius: 6,
              cursor: 'pointer',
              fontSize: 11,
              fontWeight: 600,
              transition: 'all 0.2s',
            }}
          >
            ⭐ Yêu thích
          </button>
        </div>
      </div>

      {/* Content */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: 16,
      }}>
        {loading && comparisons.length === 0 ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#94a3b8',
            flexDirection: 'column',
            gap: 12,
          }}>
            <Loader size={32} style={{ animation: 'spin 1s linear infinite' }} />
            <div>Đang tải lịch sử...</div>
          </div>
        ) : error ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#e11d48',
            flexDirection: 'column',
            gap: 12,
            textAlign: 'center',
          }}>
            <AlertCircle size={32} />
            <div>{error}</div>
            <button
              onClick={fetchComparisons}
              style={{
                padding: '8px 16px',
                background: '#e11d48',
                color: '#fff',
                border: 'none',
                borderRadius: 6,
                cursor: 'pointer',
                fontWeight: 600,
                marginTop: 8,
              }}
            >
              Thử lại
            </button>
          </div>
        ) : comparisons.length === 0 ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            color: '#94a3b8',
            flexDirection: 'column',
            gap: 12,
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 48 }}>📭</div>
            <div>
              <div style={{ fontSize: 16, fontWeight: 600, color: '#475569' }}>
                Chưa có so sánh {showStarredOnly ? 'yêu thích' : ''}
              </div>
              <div style={{ fontSize: 13, marginTop: 4 }}>
                So sánh sản phẩm để lưu lịch sử
              </div>
            </div>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {comparisons.map((comparison) => (
              <ComparisonHistoryItem
                key={comparison.id}
                comparison={comparison}
                onView={handleViewDetail}
                onDelete={handleDelete}
                onToggleStar={handleToggleStar}
                deleting={deleting}
                formatDate={formatDate}
              />
            ))}
          </div>
        )}
      </div>

      {/* Footer with pagination */}
      {total > limit && (
        <div style={{
          padding: '12px 16px',
          borderTop: '1px solid #f0f0f8',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: '#f8f9fb',
        }}>
          <div style={{ fontSize: 12, color: '#6b7280' }}>
            {page * limit + 1}-{Math.min((page + 1) * limit, total)} trên {total}
          </div>
          <div style={{ display: 'flex', gap: 8 }}>
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              style={{
                padding: '6px 12px',
                background: page === 0 ? '#e5e7eb' : '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: 4,
                cursor: page === 0 ? 'not-allowed' : 'pointer',
                fontSize: 12,
                fontWeight: 600,
                color: page === 0 ? '#9ca3af' : '#6b7280',
              }}
            >
              Trước
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={(page + 1) * limit >= total}
              style={{
                padding: '6px 12px',
                background: (page + 1) * limit >= total ? '#e5e7eb' : '#fff',
                border: '1px solid #e5e7eb',
                borderRadius: 4,
                cursor: (page + 1) * limit >= total ? 'not-allowed' : 'pointer',
                fontSize: 12,
                fontWeight: 600,
                color: (page + 1) * limit >= total ? '#9ca3af' : '#6b7280',
              }}
            >
              Sau
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Comparison History Item Component
 */
function ComparisonHistoryItem({
  comparison,
  onView,
  onDelete,
  onToggleStar,
  deleting,
  formatDate,
}) {
  const [showNotes, setShowNotes] = useState(false);

  return (
    <div
      className="comparison-item"
      style={{
        background: '#f8f9fb',
        borderRadius: 10,
        padding: 12,
        border: '1px solid #e2e8f0',
        cursor: 'pointer',
        transition: 'all 0.2s',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.background = '#f0f4ff';
        e.currentTarget.style.boxShadow = '0 4px 12px rgba(102,126,234,0.15)';
        e.currentTarget.style.transform = 'translateY(-2px)';
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.background = '#f8f9fb';
        e.currentTarget.style.boxShadow = 'none';
        e.currentTarget.style.transform = 'translateY(0)';
      }}
    >
      {/* Main info row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div
          style={{ flex: 1, cursor: 'pointer' }}
          onClick={() => onView(comparison)}
        >
          <div style={{ fontSize: 13, fontWeight: 600, color: '#1e1b4b', marginBottom: 4 }}>
            {comparison.product_name_1} vs {comparison.product_name_2}
          </div>
          <div style={{ display: 'flex', gap: 12, fontSize: 11, color: '#6b7280' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <Calendar size={12} />
              {formatDate(comparison.created_at)}
            </span>
            {comparison.comparison_type && (
              <span style={{ background: '#e0e7ff', padding: '2px 6px', borderRadius: 3 }}>
                {comparison.comparison_type}
              </span>
            )}
          </div>
        </div>

        {/* Action buttons */}
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <button
            onClick={() => onToggleStar(comparison)}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontSize: 16,
              opacity: comparison.is_starred ? 1 : 0.4,
              transition: 'all 0.2s',
            }}
            title={comparison.is_starred ? 'Bỏ yêu thích' : 'Yêu thích'}
          >
            ⭐
          </button>

          <button
            onClick={() => onView(comparison)}
            style={{
              background: '#667eea',
              border: 'none',
              color: '#fff',
              borderRadius: 6,
              width: 28,
              height: 28,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = '#764ba2')}
            onMouseLeave={(e) => (e.currentTarget.style.background = '#667eea')}
          >
            <Eye size={14} />
          </button>

          <button
            onClick={() => onDelete(comparison.id)}
            disabled={deleting === comparison.id}
            style={{
              background: '#fee2e2',
              border: 'none',
              color: '#dc2626',
              borderRadius: 6,
              width: 28,
              height: 28,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: deleting === comparison.id ? 'not-allowed' : 'pointer',
              transition: 'all 0.2s',
              opacity: deleting === comparison.id ? 0.5 : 1,
            }}
            onMouseEnter={(e) =>
              deleting !== comparison.id && (e.currentTarget.style.background = '#fecaca')
            }
            onMouseLeave={(e) => (e.currentTarget.style.background = '#fee2e2')}
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Notes section */}
      {comparison.notes && (
        <div style={{
          background: '#fff',
          padding: 8,
          borderRadius: 6,
          fontSize: 12,
          color: '#4b5563',
          borderLeft: '3px solid #f59e0b',
        }}>
          {comparison.notes}
        </div>
      )}
    </div>
  );
}

/**
 * Comparison History Detail View
 */
function ComparisonHistoryDetail({ comparison, onBack, onSelect }) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100%',
      background: '#fff',
      borderRadius: 12,
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 12,
        padding: '16px 20px',
        borderBottom: '1px solid #f0f0f8',
        background: 'linear-gradient(135deg, #667eea, #764ba2)',
      }}>
        <button
          onClick={onBack}
          style={{
            background: 'rgba(255,255,255,0.2)',
            border: 'none',
            color: '#fff',
            borderRadius: '50%',
            width: 36,
            height: 36,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
          }}
        >
          <ArrowLeft size={18} />
        </button>
        <div style={{ color: '#fff', flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700 }}>
            {comparison.product_name_1} vs {comparison.product_name_2}
          </div>
          <div style={{ fontSize: 11, opacity: 0.8 }}>
            Lưu lúc {new Date(comparison.created_at).toLocaleString('vi-VN')}
          </div>
        </div>
        <button
          onClick={() => onSelect(comparison)}
          style={{
            background: 'rgba(255,255,255,0.95)',
            border: 'none',
            color: '#667eea',
            padding: '8px 16px',
            borderRadius: 6,
            cursor: 'pointer',
            fontSize: 12,
            fontWeight: 600,
          }}
        >
          Xem chi tiết
        </button>
      </div>

      {/* Content - just show basic info */}
      <div style={{
        flex: 1,
        overflow: 'auto',
        padding: 16,
      }}>
        {comparison.snapshot_a && comparison.snapshot_b && (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <ProductSnapshot product={comparison.snapshot_a} label="Sản phẩm 1" />
            <ProductSnapshot product={comparison.snapshot_b} label="Sản phẩm 2" />
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Product Snapshot Component
 */
function ProductSnapshot({ product, label }) {
  return (
    <div style={{
      background: '#f8f9fb',
      borderRadius: 10,
      padding: 12,
      border: '1px solid #e2e8f0',
    }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: '#6b7280', marginBottom: 8 }}>
        {label}
      </div>
      {product.thumbnail && (
        <img
          src={product.thumbnail}
          alt={product.name}
          style={{
            width: '100%',
            height: 100,
            objectFit: 'contain',
            background: '#fff',
            borderRadius: 6,
            marginBottom: 8,
          }}
        />
      )}
      <div style={{ fontSize: 12, fontWeight: 600, color: '#1e1b4b', marginBottom: 4 }}>
        {product.name}
      </div>
      <div style={{ fontSize: 14, fontWeight: 700, color: '#f59e0b' }}>
        {typeof product.price === 'number'
          ? (product.price / 1000000).toFixed(1) + 'tr'
          : product.price}
      </div>
    </div>
  );
}
