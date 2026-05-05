import React from 'react';
import { Heart, Clock, Tag, Gift } from 'lucide-react';

const ACTIONS = (onFavoritesClick, onAction) => [
  { icon: <Heart size={14} />, label: 'Sản phẩm yêu thích', color: '#e11d48', bg: '#fff1f2', border: '#fecdd3', onClick: onFavoritesClick },
  { icon: <Clock size={14} />, label: 'Tìm kiếm gần đây',   color: '#6366f1', bg: '#eef2ff', border: '#c7d2fe', onClick: () => onAction('Tìm kiếm gần đây') },
  { icon: <Tag  size={14} />, label: 'Ưu đãi hôm nay',      color: '#d97706', bg: '#fffbeb', border: '#fde68a', onClick: () => onAction('Ưu đãi hôm nay') },
  { icon: <Gift size={14} />, label: 'Gợi ý cho bạn',       color: '#059669', bg: '#ecfdf5', border: '#a7f3d0', onClick: () => onAction('Gợi ý cho bạn') },
];

const UserQuickActions = ({ onAction, onFavoritesClick }) => (
  <div style={{ display: 'flex', gap: 8, paddingBottom: 10, flexWrap: 'wrap' }}>
    {ACTIONS(onFavoritesClick, onAction).map((a, i) => (
      <button
        key={i}
        onClick={a.onClick}
        style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '6px 14px', borderRadius: 20,
          border: `1.5px solid ${a.border}`,
          background: a.bg, color: a.color,
          fontSize: 13, fontWeight: 600, cursor: 'pointer',
          transition: 'all 0.15s', fontFamily: 'inherit',
        }}
        onMouseEnter={e => {
          e.currentTarget.style.transform  = 'translateY(-1px)';
          e.currentTarget.style.boxShadow  = `0 3px 10px ${a.border}`;
        }}
        onMouseLeave={e => {
          e.currentTarget.style.transform  = 'none';
          e.currentTarget.style.boxShadow  = 'none';
        }}
      >
        {a.icon}{a.label}
      </button>
    ))}
  </div>
);

export default UserQuickActions;