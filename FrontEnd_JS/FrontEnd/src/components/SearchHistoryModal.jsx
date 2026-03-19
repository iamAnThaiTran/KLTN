import React, { useState, useEffect } from 'react';
import { X, Clock, Trash2, Loader, AlertCircle } from 'lucide-react';
import { SearchHistoryService } from '../services/searchHistoryService';
import { normalizeQuery, getCategoryIcon, isQueryContinuation } from '../utils/queryNormalizer';

/**
 * SearchHistoryModal - New Version
 * Display actual search history (search queries), not categories/brands
 * 
 * Features:
 * - Humanized/normalized queries
 * - Click to fill input (not auto search)
 * - Category icon + tag
 * - Recent vs older searches
 */
export const SearchHistoryModal = ({ isOpen, onClose, token, onQuerySelect }) => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [searchHistory, setSearchHistory] = useState([]);

  useEffect(() => {
    if (isOpen && token) {
      fetchSearchHistory();
    }
  }, [isOpen, token]);

  const fetchSearchHistory = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await SearchHistoryService.getSearchHistory(token, 20, 30);
      if (data.searches && Array.isArray(data.searches)) {
        // Sort by date descending (newest first)
        const sorted = [...data.searches].sort((a, b) => {
          return new Date(b.searched_at) - new Date(a.searched_at);
        });
        setSearchHistory(sorted);
      } else {
        setError('Không thể tải lịch sử tìm kiếm');
      }
    } catch (err) {
      console.error('[SearchHistoryModal] Error:', err);
      setError(err.message || 'Lỗi tải dữ liệu');
    } finally {
      setLoading(false);
    }
  };

  const handleQueryClick = (query) => {
    if (onQuerySelect) {
      onQuerySelect(query);
    }
    onClose();
  };

  const handleDeleteHistory = async (id) => {
    // TODO: Implement delete functionality
    console.log('Delete history item:', id);
  };

  // Helper: Organize search history into groups
  // Group consecutive queries by their category, mark continuations
  const organizeSearchHistory = (searches) => {
    // Reverse so we go oldest → newest
    const reversed = [...searches].reverse();
    const groups = [];
    let currentGroup = null;

    for (let i = 0; i < reversed.length; i++) {
      const item = reversed[i];
      const prevItem = i > 0 ? reversed[i - 1] : null;
      
      // Check if this is a continuation of the previous query
      const isContinuation = prevItem && isQueryContinuation(item.query, prevItem.query) && item.category === prevItem.category;

      if (!currentGroup || (currentGroup.category !== item.category && !isContinuation)) {
        // Start a new group
        if (currentGroup) {
          groups.push(currentGroup);
        }
        currentGroup = {
          category: item.category,
          mainItem: item,
          continuations: []
        };
      } else if (isContinuation) {
        // Add as continuation to current group
        currentGroup.continuations.push(item);
      } else {
        // Different category, start new group
        groups.push(currentGroup);
        currentGroup = {
          category: item.category,
          mainItem: item,
          continuations: []
        };
      }
    }

    if (currentGroup) {
      groups.push(currentGroup);
    }

    // Reverse groups to show newest first
    return groups.reverse();
  };

  const searchGroups = organizeSearchHistory(searchHistory);

  if (!isOpen) return null;

  if (!token) {
    return (
      <div
        style={{
          position: 'fixed',
          inset: 0,
          zIndex: 1000,
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'flex-end',
          background: 'rgba(15,23,42,0.3)',
          paddingTop: 60
        }}
        onClick={e => e.target === e.currentTarget && onClose()}
      >
        <div
          style={{
            background: '#fff',
            width: '100%',
            maxWidth: 420,
            maxHeight: 'calc(100vh - 60px)',
            boxShadow: '-8px 0 40px rgba(0,0,0,0.15)',
            display: 'flex',
            flexDirection: 'column',
            padding: '20px 24px',
            animation: 'slideIn 0.3s ease'
          }}
        >
          <AlertCircle size={40} color="#dc2626" style={{ margin: '20px auto' }} />
          <p style={{ textAlign: 'center', color: '#dc2626', fontWeight: 600 }}>
            ❌ Chưa đăng nhập
          </p>
          <p style={{ textAlign: 'center', fontSize: 13, color: '#64748b', marginTop: 10 }}>
            Vui lòng đăng nhập để xem lịch sử tìm kiếm
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'flex-end',
        background: 'rgba(15,23,42,0.3)',
        backdropFilter: 'blur(4px)',
        paddingTop: 60
      }}
      onClick={e => e.target === e.currentTarget && onClose()}
    >
      <style>{`
        @keyframes slideIn {
          from { transform: translateX(100%); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
      `}</style>

      <div
        style={{
          background: '#fff',
          width: '100%',
          maxWidth: 420,
          maxHeight: 'calc(100vh - 60px)',
          overflowY: 'auto',
          boxShadow: '-8px 0 40px rgba(0,0,0,0.15)',
          animation: 'slideIn 0.3s ease',
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #f0f0f8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            color: '#fff',
            flexShrink: 0
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <Clock size={20} />
            <h2 style={{ fontSize: 16, fontWeight: 700, margin: 0 }}>Lịch sử tìm kiếm</h2>
          </div>
          <button
            onClick={onClose}
            style={{
              background: 'rgba(255,255,255,0.2)',
              border: 'none',
              borderRadius: 8,
              padding: 6,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.3)'}
            onMouseLeave={e => e.currentTarget.style.background = 'rgba(255,255,255,0.2)'}
          >
            <X size={18} color="#fff" />
          </button>
        </div>

        {/* Content */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 0' }}>
          {loading ? (
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 10,
                minHeight: 200,
                color: '#6366f1'
              }}
            >
              <Loader size={32} style={{ animation: 'spin 1s linear infinite' }} />
              <span style={{ fontSize: 13, fontWeight: 500 }}>Đang tải...</span>
            </div>
          ) : error ? (
            <div
              style={{
                padding: '16px 24px',
                background: '#fef2f2',
                border: '1px solid #fecaca',
                borderRadius: 0,
                display: 'flex',
                gap: 10,
                color: '#dc2626',
                margin: '12px 0'
              }}
            >
              <AlertCircle size={18} style={{ flexShrink: 0, marginTop: 2 }} />
              <div style={{ fontSize: 13 }}>{error}</div>
            </div>
          ) : searchHistory.length === 0 ? (
            <div
              style={{
                padding: '40px 24px',
                textAlign: 'center',
                color: '#94a3b8'
              }}
            >
              <div style={{ fontSize: 40, marginBottom: 12 }}>🔍</div>
              <p style={{ fontSize: 13, fontWeight: 500 }}>Chưa có lịch sử tìm kiếm</p>
              <p style={{ fontSize: 12, color: '#cbd5e1', marginTop: 8 }}>
                Các tìm kiếm của bạn sẽ xuất hiện ở đây
              </p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              {searchGroups.map((group, groupIdx) => {
                const mainNormalized = normalizeQuery(group.mainItem.query);
                const mainIcon = getCategoryIcon(group.mainItem.category);
                const mainDate = new Date(group.mainItem.searched_at);
                const mainIsRecent = (new Date() - mainDate) < 7 * 24 * 60 * 60 * 1000;

                return (
                  <div key={`group-${groupIdx}`}>
                    {/* Main item */}
                    <div
                      style={{
                        padding: '12px 24px',
                        borderBottom: group.continuations.length > 0 ? '1px solid #f0f0f8' : '1px solid #f0f0f8',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        background: '#fff'
                      }}
                      onMouseEnter={e => e.currentTarget.style.background = '#f9fafb'}
                      onMouseLeave={e => e.currentTarget.style.background = '#fff'}
                      onClick={() => handleQueryClick(group.mainItem.query)}
                    >
                      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                        {/* Icon */}
                        <div style={{ fontSize: 18, marginTop: 2, flexShrink: 0 }}>
                          {mainIcon}
                        </div>

                        {/* Content */}
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <span style={{ fontSize: 13, fontWeight: 600, color: '#1e1b4b', flex: 1 }}>
                              {mainNormalized}
                            </span>
                            {mainIsRecent && (
                              <span
                                style={{
                                  fontSize: 10,
                                  fontWeight: 600,
                                  color: '#fff',
                                  background: '#6366f1',
                                  padding: '2px 6px',
                                  borderRadius: 4,
                                  flexShrink: 0,
                                  whiteSpace: 'nowrap'
                                }}
                              >
                                Gần đây
                              </span>
                            )}
                          </div>

                          {/* Metadata */}
                          <div style={{ fontSize: 11, color: '#94a3b8', marginTop: 6 }}>
                            {group.mainItem.category && (
                              <span style={{ marginRight: 16 }}>
                                📁 {group.mainItem.category}
                              </span>
                            )}
                            {group.mainItem.result_count > 0 && (
                              <span>{group.mainItem.result_count} kết quả</span>
                            )}
                          </div>
                        </div>

                        {/* Delete button */}
                        <button
                          onClick={e => {
                            e.stopPropagation();
                            handleDeleteHistory(group.mainItem.id);
                          }}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            cursor: 'pointer',
                            padding: 4,
                            color: '#cbd5e1',
                            flexShrink: 0,
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'center',
                            transition: 'color 0.2s'
                          }}
                          onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
                          onMouseLeave={e => e.currentTarget.style.color = '#cbd5e1'}
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>

                    {/* Continuation items (indented) */}
                    {group.continuations.length > 0 && (
                      <div style={{ background: '#f9fafb', borderBottom: '1px solid #f0f0f8' }}>
                        {group.continuations.map((contItem, contIdx) => {
                          const contNormalized = normalizeQuery(contItem.query, true);
                          const contDate = new Date(contItem.searched_at);
                          const contIsRecent = (new Date() - contDate) < 7 * 24 * 60 * 60 * 1000;

                          return (
                            <div
                              key={`cont-${groupIdx}-${contIdx}`}
                              style={{
                                padding: '10px 24px 10px 56px', // Indent with left padding
                                borderBottom: '1px solid #f0f0f8',
                                cursor: 'pointer',
                                transition: 'all 0.2s',
                                background: '#f9fafb'
                              }}
                              onMouseEnter={e => e.currentTarget.style.background = '#f0f0f6'}
                              onMouseLeave={e => e.currentTarget.style.background = '#f9fafb'}
                              onClick={() => handleQueryClick(contItem.query)}
                            >
                              <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                                {/* Arrow indicator */}
                                <div style={{ fontSize: 12, color: '#cbd5e1', marginTop: 1, flexShrink: 0 }}>
                                  ↳
                                </div>

                                {/* Content */}
                                <div style={{ flex: 1, minWidth: 0 }}>
                                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                                    <span style={{ fontSize: 12, fontWeight: 500, color: '#475569', flex: 1 }}>
                                      {contNormalized}
                                    </span>
                                    {contIsRecent && (
                                      <span
                                        style={{
                                          fontSize: 10,
                                          fontWeight: 600,
                                          color: '#fff',
                                          background: '#6366f1',
                                          padding: '2px 6px',
                                          borderRadius: 4,
                                          flexShrink: 0,
                                          whiteSpace: 'nowrap'
                                        }}
                                      >
                                        Gần đây
                                      </span>
                                    )}
                                  </div>

                                  {/* Metadata */}
                                  {contItem.result_count > 0 && (
                                    <div style={{ fontSize: 10, color: '#94a3b8', marginTop: 4 }}>
                                      {contItem.result_count} kết quả
                                    </div>
                                  )}
                                </div>

                                {/* Delete button */}
                                <button
                                  onClick={e => {
                                    e.stopPropagation();
                                    handleDeleteHistory(contItem.id);
                                  }}
                                  style={{
                                    background: 'transparent',
                                    border: 'none',
                                    cursor: 'pointer',
                                    padding: 4,
                                    color: '#cbd5e1',
                                    flexShrink: 0,
                                    display: 'flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    transition: 'color 0.2s'
                                  }}
                                  onMouseEnter={e => e.currentTarget.style.color = '#ef4444'}
                                  onMouseLeave={e => e.currentTarget.style.color = '#cbd5e1'}
                                >
                                  <Trash2 size={14} />
                                </button>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SearchHistoryModal;
