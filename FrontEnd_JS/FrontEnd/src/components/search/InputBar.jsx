import React from 'react';
import { Send, Mic, MicOff, Volume2 } from 'lucide-react';

const InputBar = ({
  value, onChange, onSend, onKeyDown,
  isThinking, isListening, transcript,
  isBrowserSupported, onToggleMic,
  children, // slot for UserQuickActions + login prompt
}) => (
  <div style={{
    borderTop: '1px solid #eff0f8', background: '#fff',
    padding: '14px 40px', flexShrink: 0,
    boxShadow: '0 -4px 20px rgba(99,102,241,0.07)',
    display: 'flex', justifyContent: 'center',
  }}>
    <div style={{ width: '100%' }}>
      {/* Listening transcript */}
      {isListening && transcript && (
        <div style={{
          marginBottom: 10, padding: '10px 14px',
          background: '#eef2ff', border: '1px solid #c7d2fe',
          borderRadius: 10, display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <Volume2 size={14} color="#6366f1" />
          <span style={{ fontSize: 13, color: '#4f46e5' }}>
            Đang nghe: <strong>{transcript}</strong>
          </span>
        </div>
      )}

      {/* Slot (quick actions, login prompt) */}
      {children}

      {/* Input row */}
      <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <input
          type="text"
          value={value}
          onChange={onChange}
          onKeyDown={onKeyDown}
          placeholder="Nhập câu trả lời của bạn hoặc nói vào micro..."
          disabled={isThinking}
          style={{
            flex: 1, padding: '13px 20px',
            border: '2px solid #e8eaf6', borderRadius: 28,
            fontSize: 14.5, color: '#1e1b4b', outline: 'none',
            background: '#f8f9ff', transition: 'all 0.2s', fontFamily: 'inherit',
          }}
          onFocus={e => { e.target.style.borderColor = '#6366f1'; e.target.style.background = '#fff'; }}
          onBlur ={e => { e.target.style.borderColor = '#e8eaf6'; e.target.style.background = '#f8f9ff'; }}
        />

        {isBrowserSupported && (
          <button
            onClick={onToggleMic}
            disabled={isThinking}
            style={{
              width: 46, height: 46, borderRadius: '50%', border: 'none', cursor: 'pointer',
              background: isListening ? 'linear-gradient(135deg,#ef4444,#dc2626)' : '#f1f5f9',
              color: isListening ? '#fff' : '#64748b',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.2s', flexShrink: 0,
              boxShadow: isListening ? '0 4px 16px rgba(239,68,68,0.4)' : 'none',
            }}
          >
            {isListening ? <MicOff size={18} /> : <Mic size={18} />}
          </button>
        )}

        <button
          onClick={onSend}
          disabled={!value.trim() || isThinking}
          style={{
            width: 46, height: 46, borderRadius: '50%', border: 'none', cursor: 'pointer',
            background: 'linear-gradient(135deg,#6366f1,#8b5cf6)', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.2s', flexShrink: 0,
            opacity: (!value.trim() || isThinking) ? 0.45 : 1,
          }}
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  </div>
);

export default InputBar;