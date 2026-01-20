import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, CheckCircle2, AlertCircle, ShoppingBag } from 'lucide-react';
import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

const ShoeFinder = () => {
  const [messages, setMessages] = useState([]);
  const [currentInput, setCurrentInput] = useState('');
  const [conversationState, setConversationState] = useState({
    conversationId: null,
    isLoading: false,
    error: null
  });
  const [isThinking, setIsThinking] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Initial greeting
    addBotMessage(
      "Xin chào! 👋 Tôi sẽ giúp bạn tìm đôi giày phù hợp nhất.\n\nBạn đang tìm loại giày gì? (Ví dụ: giày chạy bộ, sneaker, giày da, sandal...)"
    );
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const addBotMessage = (text, options = null, quickReplies = null) => {
    setMessages(prev => [...prev, {
      type: 'bot',
      text,
      options,
      quickReplies,
      timestamp: new Date()
    }]);
  };

  const addUserMessage = (text) => {
    setMessages(prev => [...prev, {
      type: 'user',
      text,
      timestamp: new Date()
    }]);
  };

  // Connect to backend API
  const sendToBackend = async (userInput) => {
    setIsThinking(true);
    try {
      console.log('Sending to backend:', { user_input: userInput, conversation_id: conversationState.conversationId });
      
      const response = await axios.post(`${API_BASE_URL}/api/query`, {
        user_input: userInput,
        conversation_id: conversationState.conversationId
      });

      console.log('Backend response:', response.data);
      const data = response.data;
      
      // Update conversation ID
      if (data.conversation_id) {
        setConversationState(prev => ({
          ...prev,
          conversationId: data.conversation_id
        }));
      }

      // Display response from backend
      displayBackendResponse(data);

    } catch (error) {
      console.error('Backend API Error:', error);
      const errorMsg = error.response?.data?.detail || error.message || 'Có lỗi xảy ra. Vui lòng thử lại.';
      addBotMessage(`❌ Lỗi: ${errorMsg}`);
      addBotMessage("Lưu ý: Vui lòng chắc chắn backend Python đang chạy trên http://localhost:8000");
    } finally {
      setIsThinking(false);
    }
  };

  const sendResponseToBackend = async (questionType, value, attributeName = null) => {
    setIsThinking(true);
    try {
      const response = await axios.post(`${API_BASE_URL}/api/respond`, {
        conversation_id: conversationState.conversationId,
        question_type: questionType,
        value: value,
        attribute_name: attributeName
      });

      const data = response.data;
      displayBackendResponse(data);

    } catch (error) {
      console.error('Backend API Error:', error);
      const errorMsg = error.response?.data?.detail || 'Có lỗi xảy ra. Vui lòng thử lại.';
      addBotMessage(`❌ Lỗi: ${errorMsg}`);
    } finally {
      setIsThinking(false);
    }
  };

  const displayBackendResponse = (data) => {
    // Display the question or results from backend
    if (data.question) {
      let quickReplies = null;
      if (data.options && Array.isArray(data.options)) {
        quickReplies = data.options.map(opt => opt.label || opt.value || opt);
      }
      addBotMessage(data.question, null, quickReplies);
    }

    // If there are products (results)
    if (data.products && Array.isArray(data.products) && data.products.length > 0) {
      const resultMessage = `🎯 **Tìm thấy ${data.products.length} sản phẩm phù hợp!**\n\nDựa trên nhu cầu của bạn, đây là top gợi ý:`;
      setMessages(prev => [...prev, {
        type: 'results',
        text: resultMessage,
        products: data.products,
        timestamp: new Date()
      }]);
    }
  };

  const handleSend = () => {
    if (!currentInput.trim() || isThinking) return;

    addUserMessage(currentInput);
    sendToBackend(currentInput);
    setCurrentInput('');
  };

  const handleQuickReply = (reply) => {
    addUserMessage(reply);
    
    // Determine question type based on context
    // This is a simplified approach - you might need to track the current step
    sendToBackend(reply);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-blue-50 flex items-center justify-center p-4">
      <div className="w-full max-w-4xl h-[90vh] bg-white rounded-3xl shadow-2xl flex flex-col overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6">
          <div className="flex items-center gap-3">
            <ShoppingBag className="w-8 h-8" />
            <div>
              <h1 className="text-2xl font-bold">Shoe Finder AI</h1>
              <p className="text-blue-100 text-sm">Trợ lý tìm giày thông minh</p>
            </div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, idx) => (
            <div key={idx}>
              {msg.type === 'bot' && (
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-5 h-5 text-white" />
                  </div>
                  <div className="flex-1">
                    <div className="bg-gray-100 rounded-2xl rounded-tl-none p-4 max-w-xl">
                      <div className="whitespace-pre-wrap text-gray-800">{msg.text}</div>
                    </div>

                    {msg.quickReplies && (
                      <div className="flex flex-wrap gap-2 mt-3">
                        {msg.quickReplies.map((reply, i) => (
                          <button
                            key={i}
                            onClick={() => handleQuickReply(reply)}
                            className="px-4 py-2 bg-white border-2 border-blue-300 text-blue-700 rounded-full hover:bg-blue-50 hover:border-blue-400 transition-all text-sm font-medium"
                          >
                            {reply}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}

              {msg.type === 'user' && (
                <div className="flex justify-end">
                  <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl rounded-tr-none p-4 max-w-xl">
                    {msg.text}
                  </div>
                </div>
              )}

              {msg.type === 'results' && (
                <div className="space-y-4">
                  <div className="flex gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center flex-shrink-0">
                      <CheckCircle2 className="w-5 h-5 text-white" />
                    </div>
                    <div className="bg-green-50 rounded-2xl rounded-tl-none p-4 max-w-xl">
                      <div className="font-semibold text-green-900">{msg.text}</div>
                    </div>
                  </div>

                  <div className="space-y-3 ml-13">
                    {msg.products.map((product, i) => (
                      <div key={product.id || i} className="bg-white border-2 border-gray-200 rounded-xl p-4 hover:border-blue-300 transition-all">
                        <div className="flex gap-4">
                          {product.image && (
                            <img
                              src={product.image}
                              alt={product.name}
                              className="w-32 h-24 object-cover rounded-lg"
                            />
                          )}
                          <div className="flex-1">
                            <div className="flex items-start justify-between mb-2">
                              <div>
                                <div className="flex items-center gap-2">
                                  <h3 className="font-bold text-gray-800">{product.name}</h3>
                                  {i === 0 && (
                                    <span className="bg-yellow-100 text-yellow-800 text-xs px-2 py-1 rounded-full font-semibold">
                                      Phù hợp nhất
                                    </span>
                                  )}
                                </div>
                                {product.price && (
                                  <div className="text-sm text-gray-500 mt-1">
                                    Giá: {(product.price/1000000).toFixed(1)}tr
                                  </div>
                                )}
                              </div>
                              {product.match_score && (
                                <div className="text-xl font-bold text-blue-600">
                                  {product.match_score}%
                                </div>
                              )}
                            </div>

                            {product.description && (
                              <div className="text-sm text-gray-700 mb-2">
                                {product.description}
                              </div>
                            )}

                            {product.explanation && (
                              <div className="text-sm text-gray-700">
                                {product.explanation}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}

          {isThinking && (
            <div className="flex gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-500 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white animate-pulse" />
              </div>
              <div className="bg-gray-100 rounded-2xl rounded-tl-none p-4">
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t bg-gray-50 p-4">
          <div className="flex gap-3">
            <input
              type="text"
              value={currentInput}
              onChange={(e) => setCurrentInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Nhập câu trả lời của bạn..."
              className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-full focus:border-blue-500 focus:outline-none"
              disabled={isThinking}
            />
            <button
              onClick={handleSend}
              disabled={!currentInput.trim() || isThinking}
              className="w-12 h-12 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-full flex items-center justify-center hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ShoeFinder;
