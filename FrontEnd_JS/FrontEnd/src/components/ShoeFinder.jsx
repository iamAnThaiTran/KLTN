import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, CheckCircle2, AlertCircle, ShoppingBag, Mic, MicOff, Volume2 } from 'lucide-react';
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
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isBrowserSupported, setIsBrowserSupported] = useState(true);
  const messagesEndRef = useRef(null);
  const recognitionRef = useRef(null);

  useEffect(() => {
    // Initial greeting
    addBotMessage(
      "Xin chào! 👋 Tôi sẽ giúp bạn tìm đôi giày phù hợp nhất.\n\nBạn đang tìm loại giày gì? (Ví dụ: giày chạy bộ, sneaker, giày da, sandal...)"
    );

    // Khởi tạo Web Speech API
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      setIsBrowserSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'vi-VN';

    recognition.onstart = () => {
      setIsListening(true);
      setTranscript('');
    };

    recognition.onresult = (event) => {
      let interimTranscript = '';
      let finalTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      setTranscript(interimTranscript);
      
      // Nếu có kết quả cuối cùng, thêm vào input
      if (finalTranscript) {
        setCurrentInput(prev => (prev + ' ' + finalTranscript).trim());
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
      setTranscript('');
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }
    };
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

  const handleMicClick = () => {
    if (!recognitionRef.current) return;

    if (isListening) {
      recognitionRef.current.stop();
      setIsListening(false);
    } else {
      try {
        recognitionRef.current.start();
      } catch (error) {
        console.error('Error starting speech recognition:', error);
      }
    }
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
    console.log('displayBackendResponse:', data);
    // Display the question or results from backend
    if (data.question) {
      let quickReplies = null;
      if (data.options && Array.isArray(data.options)) {
        quickReplies = data.options.map(opt => opt.label || opt.value || opt);
      }
      console.log('Quick replies:', quickReplies);
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
    <div className="h-screen w-screen bg-gradient-to-br from-slate-50 to-blue-50 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4 shadow-lg">
        <div className="flex items-center gap-3">
          <ShoppingBag className="w-8 h-8" />
          <div>
            <h1 className="text-2xl font-bold">RCM</h1>
            <p className="text-blue-100 text-sm">RCM</p>
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
                  <div className="bg-gray-100 rounded-2xl rounded-tl-none p-4 max-w-2xl">
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
                <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-2xl rounded-tr-none p-4 max-w-2xl">
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
                  <div className="bg-green-50 rounded-2xl rounded-tl-none p-4 max-w-2xl">
                    <div className="font-semibold text-green-900">{msg.text}</div>
                  </div>
                </div>

                <div className="ml-13 w-full">
                  <div className="grid grid-cols-3 gap-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                    {msg.products.map((product, i) => (
                      <div 
                        key={product.id || i} 
                        className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:border-blue-400 hover:shadow-md transition-all cursor-pointer group"
                        onClick={() => {
                          if (product.link) {
                            window.open(product.link, '_blank');
                          }
                        }}
                      >
                        {/* Product Image */}
                        {product.image && (
                          <div className="relative overflow-hidden bg-gray-100 h-32 flex items-center justify-center">
                            <img
                              src={product.image}
                              alt={product.name}
                              className="max-w-full max-h-full object-contain group-hover:scale-110 transition-transform"
                            />
                            {i === 0 && (
                              <div className="absolute top-1 right-1 bg-yellow-100 text-yellow-800 text-xs px-1.5 py-0.5 rounded font-semibold">
                                TOP
                              </div>
                            )}
                          </div>
                        )}

                        {/* Product Info */}
                        <div className="p-2">
                          <h3 className="font-semibold text-gray-800 text-xs line-clamp-2 mb-1">{product.name}</h3>
                          
                          {product.price && (
                            <div className="text-sm font-bold text-red-600 mb-1">
                              {(product.price/1000000).toFixed(1)}tr
                            </div>
                          )}

                          {product.description && (
                            <div className="text-xs text-gray-600 line-clamp-1">
                              {product.description}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
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
      <div className="border-t bg-gray-50 px-6 py-4 shadow-lg">
        {isListening && transcript && (
          <div className="mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <div className="flex items-center gap-2 text-sm text-blue-700">
              <Volume2 className="w-4 h-4 animate-pulse" />
              <span>Đang nghe: <strong>{transcript}</strong></span>
            </div>
          </div>
        )}
        <div className="flex gap-3">
          <input
            type="text"
            value={currentInput}
            onChange={(e) => setCurrentInput(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSend()}
            placeholder="Nhập câu trả lời của bạn hoặc nói vào micro..."
            className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-full focus:border-blue-500 focus:outline-none"
            disabled={isThinking}
          />
          
          {isBrowserSupported && (
            <button
              type="button"
              onClick={handleMicClick}
              disabled={isThinking}
              className={`w-12 h-12 rounded-full flex items-center justify-center transition-all flex-shrink-0 ${
                isListening
                  ? 'bg-red-500 text-white hover:bg-red-600'
                  : 'bg-gray-300 text-gray-700 hover:bg-gray-400'
              } disabled:opacity-50 disabled:cursor-not-allowed`}
              title={isListening ? 'Dừng ghi âm' : isBrowserSupported ? 'Bắt đầu ghi âm' : 'Trình duyệt không hỗ trợ'}
            >
              {isListening ? (
                <MicOff className="w-5 h-5" />
              ) : (
                <Mic className="w-5 h-5" />
              )}
            </button>
          )}
          
          <button
            onClick={handleSend}
            disabled={!currentInput.trim() || isThinking}
            className="w-12 h-12 bg-gradient-to-r from-blue-600 to-indigo-600 text-white rounded-full flex items-center justify-center hover:from-blue-700 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex-shrink-0"
          >
            <Send className="w-5 h-5" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ShoeFinder;
