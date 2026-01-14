import { useEffect, useRef, useState } from 'react';
import { X, Send, MessageSquare } from 'lucide-react';
import './AssistOverlay.css';

/**
 * AssistOverlay Component - Enhanced UI Version
 * 
 * A fixed overlay that appears above the home page for intent clarification.
 * Fully controlled by server response data - no business logic inside.
 */
export default function AssistOverlay({
  isOpen = false,
  data = null,
  onOptionSelect = () => {},
  onSkip = () => {},
  onClose = () => {},
}) {
  const overlayRef = useRef(null);
  const contentRef = useRef(null);
  const [userInput, setUserInput] = useState('');
  const inputRef = useRef(null);

  // Debug logging
  console.log('AssistOverlay - isOpen:', isOpen, 'data:', data);

  // Handle ESC key to close overlay
  useEffect(() => {
    if (!isOpen) return;

    const handleEscape = (e) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };

    document.addEventListener('keydown', handleEscape);
    document.body.style.overflow = 'hidden';

    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [isOpen, onClose]);

  // Handle click outside to close
  const handleBackdropClick = (e) => {
    if (e.target === overlayRef.current) {
      onClose();
    }
  };

  // Handle user input submission
  const handleSubmitInput = () => {
    if (userInput.trim()) {
      onOptionSelect(userInput.trim());
      setUserInput('');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmitInput();
    }
  };

  if (!isOpen || !data) {
    return null;
  }

  const {
    summary = '',
    question = '',
    options = [],
    allow_skip = false,
  } = data;

  return (
    <div 
      ref={overlayRef}
      className="assist-overlay"
      onClick={handleBackdropClick}
    >
      {/* Backdrop blur effect */}
      <div className="assist-overlay__backdrop" />

      {/* Content container */}
      <div ref={contentRef} className="assist-overlay__content">
        {/* Header with title and query tag */}
        <div className="assist-overlay__header">
          <div className="assist-overlay__header-title">
            <MessageSquare size={20} className="assist-overlay__icon" />
            <h2>Trợ lý tìm kiếm</h2>
          </div>
          <div className="assist-overlay__header-actions">
            {summary && (
              <span className="assist-overlay__query-tag">
                {summary.replace('✔ Đã hiểu: ', '')}
              </span>
            )}
            <button
              onClick={onClose}
              className="assist-overlay__close"
              aria-label="Close assist overlay"
            >
              <X size={20} />
            </button>
          </div>
        </div>

        {/* Helper text */}
        <div className="assist-overlay__helper-text">
          <p>Tôi cần thêm một vài thông tin để giới ý chính xác hơn cho bạn:</p>
        </div>

        {/* Questions and options container */}
        <div className="assist-overlay__questions-container">
          {/* Question section */}
          {question && (
            <div className="assist-overlay__question-section">
              <h3 className="assist-overlay__question-text">
                {question}
              </h3>

              {/* Options as chips/tags */}
              {options && options.length > 0 && (
                <div className="assist-overlay__options-grid">
                  {options.map((option) => (
                    <button
                      key={option.key}
                      onClick={() => onOptionSelect(option.key)}
                      className="assist-overlay__option-chip"
                    >
                      {option.label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Input section - custom response */}
        <div className="assist-overlay__input-section">
          <div className="assist-overlay__input-wrapper">
            <input
              ref={inputRef}
              type="text"
              value={userInput}
              onChange={(e) => setUserInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Hoặc nhập câu hỏi của bạn..."
              className="assist-overlay__input"
            />
            <button
              onClick={handleSubmitInput}
              className="assist-overlay__submit-btn"
              disabled={!userInput.trim()}
            >
              <Send size={18} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
