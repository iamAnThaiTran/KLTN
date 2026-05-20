import React, { useState, useEffect } from 'react';
import { SlidersHorizontal, ChevronDown, CheckCircle2, RotateCcw, X, Loader2 } from 'lucide-react';
import { API_BASE_URL } from '../../config';

const SIDEBAR_STYLES = `
  @keyframes sidebarIn { from{opacity:0;transform:translateX(-10px)} to{opacity:1;transform:translateX(0)} }
  .filter-sidebar { animation: sidebarIn 0.3s ease; }
  .fchip {
    padding: 5px 12px; border-radius: 16px; font-size: 12.5px; font-weight: 500;
    border: 1.5px solid #e2e8f0; background: #fff; color: #475569;
    cursor: pointer; transition: all 0.14s; white-space: nowrap; font-family: inherit;
    line-height: 1.4;
  }
  .fchip:hover { border-color: #6366f1; color: #6366f1; background: #eef2ff; }
  .fchip.on {
    border-color: #6366f1; background: #6366f1; color: #fff;
    box-shadow: 0 2px 6px rgba(99,102,241,0.28);
  }
  .group-toggle {
    width: 100%; display: flex; align-items: center; justify-content: space-between;
    padding: 11px 16px; background: none; border: none; cursor: pointer;
    font-family: inherit; border-bottom: 1px solid #f0f0f8;
  }
  .group-toggle:hover { background: #f5f3ff; }
  .apply-btn {
    width: 100%; padding: 11px; border-radius: 10px; border: none;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    color: #fff; font-weight: 700; font-size: 14px; cursor: pointer;
    font-family: inherit; transition: box-shadow 0.2s;
    box-shadow: 0 4px 14px rgba(99,102,241,0.3);
    display: flex; align-items: center; justify-content: center; gap: 6px;
  }
  .apply-btn:hover { box-shadow: 0 6px 20px rgba(99,102,241,0.45); }
  .apply-btn:disabled { opacity: 0.6; cursor: not-allowed; }
  .reset-btn {
    display: flex; align-items: center; gap: 4px;
    color: #94a3b8; font-size: 12px; background: none; border: none;
    cursor: pointer; font-family: inherit; padding: 0;
  }
  .reset-btn:hover { color: #6366f1; }
`;

const FilterSidebar = ({ filters, selectedFilters, onToggle, onApply, onReset, resultCount, isLoading, categoryId, categoryName }) => {
  const [openGroups, setOpenGroups] = useState({});
  const [isApplying, setIsApplying] = useState(false);

  useEffect(() => {
    if (filters?.length) {
      const init = {};
      filters.forEach((_, i) => { init[i] = true; });
      setOpenGroups(init);
    }
  }, [filters]);

  // Debug: Log when categoryName changes
  useEffect(() => {
    console.log('🎯 FilterSidebar received:', { categoryId, categoryName, filtersCount: filters?.length });
  }, [categoryId, categoryName, filters?.length]);

  const activeCount  = Object.keys(selectedFilters).length;
  const toggleGroup  = (i) => setOpenGroups(p => ({ ...p, [i]: !p[i] }));

  /**
   * Convert selectedFilters from format {`attribute:value`...} to {attribute_name: [values...]}
   * Then call API to filter + rank products
   */
  const handleApplyFilters = async () => {
    if (!categoryId && !categoryName) {
      alert('❌ Không có category ID hoặc category name');
      return;
    }

    setIsApplying(true);
    try {
      // Convert format: {`brand:Nike`, `size:42`} → {brand: [`Nike`], size: [`42`]}
      const attributesMap = {};
      for (const key of Object.keys(selectedFilters)) {
        const [attrName, attrValue] = key.split(':');
        if (!attributesMap[attrName]) {
          attributesMap[attrName] = [];
        }
        attributesMap[attrName].push(attrValue);
      }

      console.log('📤 Sending filter request:', { categoryId, categoryName, attributes: attributesMap });

      // Call backend API
      const response = await fetch(`${API_BASE_URL}/api/products/filter-with-ranking`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_id: categoryId,
          category_name: categoryName,
          attributes: attributesMap,
          limit: 100
        })
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.statusText}`);
      }

      const data = await response.json();
      console.log('📥 Filter response:', data);

      if (data.success && onApply) {
        // Convert selectedFilters for logging
        const attributesMap = {};
        for (const key of Object.keys(selectedFilters)) {
          const [attrName, attrValue] = key.split(':');
          if (!attributesMap[attrName]) {
            attributesMap[attrName] = [];
          }
          attributesMap[attrName].push(attrValue);
        }
        
        // Pass filtered + ranked products to parent component
        onApply({
          products: data.products,
          total: data.total,
          categoryId: data.category_id,
          categoryName: categoryName,
          selectedFilters: selectedFilters,
          attributesMap: attributesMap
        });
      }
    } catch (err) {
      console.error('❌ Filter error:', err);
      alert('❌ Lỗi: ' + err.message);
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div style={{
      width: 256, flexShrink: 0,
      borderRight: '1px solid #ebe9f8',
      background: '#fafafa',
      display: 'flex', flexDirection: 'column',
      height: '100%',
    }}>
      <style>{SIDEBAR_STYLES}</style>

      <div className="filter-sidebar" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        {/* Header */}
        <div style={{
          padding: '14px 16px 12px',
          borderBottom: '1px solid #ebe9f8',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          flexShrink: 0,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <SlidersHorizontal size={15} color="#6366f1" />
            <span style={{ fontWeight: 700, fontSize: 14, color: '#1e1b4b' }}>Bộ lọc</span>
            {activeCount > 0 && (
              <span style={{
                background: '#6366f1', color: '#fff',
                borderRadius: 10, padding: '1px 7px',
                fontSize: 11, fontWeight: 700, lineHeight: 1.6,
              }}>{activeCount}</span>
            )}
          </div>
          {activeCount > 0 && (
            <button className="reset-btn" onClick={onReset} disabled={isApplying}>
              <RotateCcw size={11} /> Xóa tất cả
            </button>
          )}
        </div>

        {/* Result count */}
        {resultCount != null && (
          <div style={{ padding: '10px 16px', flexShrink: 0 }}>
            <div style={{
              background: 'linear-gradient(135deg,#eef2ff,#f0f7ff)',
              border: '1px solid #e0e7ff', borderRadius: 8,
              padding: '8px 12px', display: 'flex', alignItems: 'center', gap: 6,
            }}>
              <CheckCircle2 size={13} color="#6366f1" />
              <span style={{ fontSize: 13, color: '#4f46e5', fontWeight: 600 }}>
                {isLoading || isApplying ? '⏳ Đang tìm...' : `${resultCount} sản phẩm`}
              </span>
            </div>
          </div>
        )}

        {/* Filter groups */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0 8px' }}>
          {filters.map((filter, fi) => {
            const isOpen = openGroups[fi] !== false;
            return (
              <div key={fi} style={{ borderBottom: '1px solid #f0f0f8' }}>
                <button className="group-toggle" onClick={() => toggleGroup(fi)}>
                  <span style={{ fontWeight: 600, fontSize: 13, color: '#374151' }}>
                    {filter.display_name || filter.attribute_name}
                  </span>
                  <ChevronDown
                    size={14} color="#9ca3af"
                    style={{ transform: isOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.2s', flexShrink: 0 }}
                  />
                </button>

                {isOpen && (
                  <div style={{ padding: '8px 14px 12px', display: 'flex', flexWrap: 'wrap', gap: 7 }}>
                    {filter.options?.map((opt, oi) => {
                      const key    = `${filter.attribute_name}:${opt.attribute_value}`;
                      const active = !!selectedFilters[key];
                      return (
                        <button
                          key={oi}
                          className={`fchip${active ? ' on' : ''}`}
                          onClick={() => onToggle(key)}
                          disabled={isApplying}
                        >
                          {opt.attribute_value}
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Selected chips summary + Apply */}
        <div style={{ borderTop: '1px solid #ebe9f8', flexShrink: 0 }}>

          {/* Các tiêu chí đã chọn */}
          {activeCount > 0 && (
            <div style={{ padding: '10px 14px 4px' }}>
              <div style={{ fontSize: 11, fontWeight: 600, color: '#94a3b8', marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                Đã chọn
              </div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                {Object.keys(selectedFilters).map((key) => {
                  const [, value] = key.split(':');
                  return (
                    <span
                      key={key}
                      style={{
                        display: 'inline-flex', alignItems: 'center', gap: 4,
                        padding: '4px 10px', borderRadius: 14,
                        background: '#6366f1', color: '#fff',
                        fontSize: 12, fontWeight: 600,
                      }}
                    >
                      {value}
                      <button
                        onClick={() => onToggle(key)}
                        disabled={isApplying}
                        style={{
                          background: 'none', border: 'none', color: '#fff',
                          cursor: isApplying ? 'not-allowed' : 'pointer', padding: 0, lineHeight: 1,
                          display: 'flex', alignItems: 'center',
                          opacity: 0.8,
                        }}
                        onMouseEnter={e => e.currentTarget.style.opacity = '1'}
                        onMouseLeave={e => e.currentTarget.style.opacity = '0.8'}
                      >
                        <X size={11} />
                      </button>
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          <div style={{ padding: '10px 16px 14px' }}>
            {activeCount > 0 ? (
              <button 
                className="apply-btn" 
                onClick={handleApplyFilters}
                disabled={isApplying || isLoading}
              >
                {isApplying ? (
                  <>
                    <Loader2 size={14} style={{ animation: 'spin 1s linear infinite' }} />
                    Đang xử lý...
                  </>
                ) : (
                  `Áp dụng (${activeCount} tiêu chí)`
                )}
              </button>
            ) : (
              <p style={{ margin: 0, fontSize: 12, color: '#b0b7c3', textAlign: 'center', fontStyle: 'italic' }}>
                Chọn tiêu chí để lọc sản phẩm
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default FilterSidebar;