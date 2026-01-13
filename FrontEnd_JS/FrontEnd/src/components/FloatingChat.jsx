import { MessageCircle, X, Minimize2, Maximize2 } from 'lucide-react';
import { useState, useRef, useEffect } from 'react';
import ChatMessage from '../chat/ChatMessage';
import ChatInput from '../chat/ChatInput';
import { getProductFromTiki } from '../services/productServices';

export default function FloatingChat() {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [position, setPosition] = useState({ x: 20, y: 20 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragOffset, setDragOffset] = useState({ x: 0, y: 0 });
  const chatWindowRef = useRef(null);
  const bottomRef = useRef(null);

  // Auto scroll to bottom when new messages arrive
  useEffect(() => {
    if (messages.length > 0) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages]);

  const handleMouseDown = (e) => {
    if (e.target.closest('button') || e.target.closest('input')) {
      return;
    }
    setIsDragging(true);
    setDragOffset({
      x: e.clientX - position.x,
      y: e.clientY - position.y
    });
  };

  useEffect(() => {
    const handleMouseMove = (e) => {
      if (isDragging) {
        setPosition({
          x: e.clientX - dragOffset.x,
          y: e.clientY - dragOffset.y
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging, dragOffset]);

  const mockProductResponse = async (query) => {
    try {
      const response = await getProductFromTiki(query);
      const products = response;
      return {
        content: `Tôi tìm thấy ${products.length} sản phẩm phù hợp với "${query}". Đây là những lựa chọn tốt nhất:`,
        products,
      };
    } catch (error) {
      console.error(error);
      return {
        content: `Xin lỗi, có lỗi khi tìm kiếm. Vui lòng thử lại.`,
        products: [],
      };
    }
  };

  const handleSendMessage = async (content) => {
    const userMessage = {
      id: Date.now(),
      type: "user",
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    const response = await mockProductResponse(content);
    const botMessage = {
      id: Date.now() + 1,
      type: "bot",
      content: response.content,
      products: response.products,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, botMessage]);
    setIsLoading(false);
  };

  const handleClearChat = () => {
    setMessages([]);
  };

  return (
    <>
      {/* Floating Bubble Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className="fixed w-14 h-14 bg-indigo-600 text-white rounded-full flex items-center justify-center shadow-lg hover:bg-indigo-700 transition-all hover:scale-110 z-50"
          style={{ right: '20px', bottom: '20px' }}
          title="Trợ lý AI"
        >
          <MessageCircle className="w-6 h-6" />
        </button>
      )}

      {/* Floating Chat Window */}
      {isOpen && (
        <div
          ref={chatWindowRef}
          className="fixed bg-white rounded-2xl shadow-2xl border border-gray-200 z-50 flex flex-col"
          style={{
            left: `${position.x}px`,
            top: `${position.y}px`,
            width: isMinimized ? '320px' : '420px',
            height: isMinimized ? '60px' : '600px',
            cursor: isDragging ? 'grabbing' : 'grab'
          }}
        >
          {/* Header - Draggable */}
          <div
            onMouseDown={handleMouseDown}
            className="bg-gradient-to-r from-indigo-600 to-indigo-700 px-6 py-4 text-white flex items-center justify-between cursor-grab active:cursor-grabbing rounded-t-2xl"
          >
            <div>
              <h3 className="font-semibold mb-1">ShopAssist AI</h3>
              {!isMinimized && (
                <p className="text-sm text-indigo-100">Trợ lý tìm sản phẩm</p>
              )}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => setIsMinimized(!isMinimized)}
                className="hover:bg-indigo-500 p-1 rounded transition-colors"
                title={isMinimized ? "Mở rộng" : "Thu nhỏ"}
              >
                {isMinimized ? (
                  <Maximize2 className="w-5 h-5" />
                ) : (
                  <Minimize2 className="w-5 h-5" />
                )}
              </button>
              <button
                onClick={() => {
                  setIsOpen(false);
                  handleClearChat();
                }}
                className="hover:bg-indigo-500 p-1 rounded transition-colors"
                title="Đóng"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Chat Content */}
          {!isMinimized && (
            <>
              {/* Messages Area */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
                {messages.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-center text-gray-600">
                    <MessageCircle className="w-12 h-12 text-indigo-300 mb-3" />
                    <p className="text-sm font-medium mb-2">Xin chào! 👋</p>
                    <p className="text-xs text-gray-500">
                      Hỏi tôi về sản phẩm bạn cần tìm
                    </p>
                  </div>
                ) : (
                  <>
                    {messages.map((message) => (
                      <ChatMessage key={message.id} message={message} />
                    ))}
                    {isLoading && (
                      <div className="flex gap-2">
                        <div className="w-6 h-6 bg-indigo-600 rounded-full flex items-center justify-center text-white text-xs flex-shrink-0">
                          🤖
                        </div>
                        <div className="bg-gray-200 rounded-lg px-3 py-2">
                          <div className="flex gap-1">
                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                            <div
                              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                              style={{ animationDelay: "0.1s" }}
                            ></div>
                            <div
                              className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                              style={{ animationDelay: "0.2s" }}
                            ></div>
                          </div>
                        </div>
                      </div>
                    )}
                    <div ref={bottomRef} />
                  </>
                )}
              </div>

              {/* Input Area */}
              <div className="border-t border-gray-200 bg-white p-3 rounded-b-2xl">
                <form
                  onSubmit={(e) => {
                    e.preventDefault();
                    const input = e.target.elements[0];
                    if (input.value.trim() && !isLoading) {
                      handleSendMessage(input.value.trim());
                      input.value = '';
                    }
                  }}
                  className="flex gap-2"
                >
                  <input
                    type="text"
                    placeholder="Nhập sản phẩm..."
                    disabled={isLoading}
                    className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100 text-sm"
                  />
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                  >
                    <MessageCircle className="w-4 h-4" />
                  </button>
                </form>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
