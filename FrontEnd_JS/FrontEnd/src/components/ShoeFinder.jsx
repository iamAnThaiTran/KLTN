import React, { useState, useEffect, useRef } from 'react';
import { Send, Sparkles, CheckCircle2, AlertCircle, ShoppingBag, Mic, MicOff, Volume2 } from 'lucide-react';
import axios from 'axios';
import SuggestionsPopup from './SuggestionsPopup';

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
  const [lastCategoryName, setLastCategoryName] = useState(''); // Track category for filter search
  const [selectedFilters, setSelectedFilters] = useState({}); // Track selected filters
  const [clarifyingHints, setClarifyingHints] = useState([]); // Suggestions to refine search
  const [hintStyle] = useState('chat-bubble'); // 'chat-bubble', 'banner', or 'tooltip'
  const [showSuggestionsPopup, setShowSuggestionsPopup] = useState(false); // Show/hide SuggestionsPopup
  const [suggestionsPopupFilters, setSuggestionsPopupFilters] = useState([]); // Filter options for popup
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

  // Hàm render clarifying hints (gợi ý hỏi nhẹ)
  const renderClarifyingHints = () => {
    if (!clarifyingHints || clarifyingHints.length === 0) return null;

    if (hintStyle === 'chat-bubble') {
      // 👟 Chat bubble nhỏ - tương tác cao
      return (
        <div className="flex gap-3 mt-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center flex-shrink-0">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <div className="flex-1">
            <div className="bg-amber-50 border-2 border-amber-200 rounded-2xl rounded-tl-none p-4 max-w-2xl">
              {/* <div className="font-semibold text-amber-900 mb-2 text-sm">
                💡 Một vài gợi ý để bạn tìm kiếm chính xác hơn:
              </div> */}
              <div className="flex flex-wrap gap-2">
                {clarifyingHints.map((hint, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuickReply(hint)}
                    className="px-3 py-2 bg-white border-2 border-amber-300 text-amber-700 text-sm rounded-full hover:bg-amber-100 hover:border-amber-400 transition-all font-medium"
                  >
                    {hint}
                  </button>
                ))}
              </div>
              <div className="text-xs text-amber-600 mt-2">
                (Bạn có thể bỏ qua và lựa chọn filter bên dưới)
              </div>
            </div>
          </div>
        </div>
      );
    }

    if (hintStyle === 'banner') {
      // Banner nhỏ ở trên filter
      return (
        <div className="bg-gradient-to-r from-amber-100 to-orange-100 border-l-4 border-amber-500 p-3 rounded-r-lg my-3">
          <div className="flex items-start gap-2">
            <span className="text-lg">💡</span>
            <div>
              {/* <p className="font-semibold text-sm text-amber-900 mb-1">Tinh chỉnh tìm kiếm:</p> */}
              <div className="flex flex-wrap gap-1">
                {clarifyingHints.map((hint, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleQuickReply(hint)}
                    className="px-2 py-1 bg-white text-xs text-amber-700 rounded hover:bg-amber-50 transition-all"
                  >
                    {hint}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      );
    }

    // Default: tooltip dạng text
    return null;
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

  // NEW: Analyze-first flow (T=0.1s hints, then T=0.5s products)
  const analyzeAndSearch = async (userInput) => {
    setIsThinking(true);
    const convId = conversationState.conversationId;
    
    try {
      // Step 1: Call /api/analyze (FAST - T=0.1s)
      console.log('[ANALYZE] Analyzing input:', userInput);
      const analyzeResponse = await axios.post(`${API_BASE_URL}/api/analyze`, {
        user_input: userInput,
        conversation_id: convId
      });
      
      const analyzeData = analyzeResponse.data;
      console.log('[ANALYZE] Response:', analyzeData);
      
      if (!analyzeData.success) {
        addBotMessage(`❌ ${analyzeData.error}`);
        setIsThinking(false);
        return;
      }
      
      // Update conversation state
      setConversationState(prev => ({
        ...prev,
        conversationId: analyzeData.conversation_id
      }));
      
      // Update selected filters state & last category
      setLastCategoryName(analyzeData.category);
      setSelectedFilters({}); // Reset filters for new search
      
      // Step 2: Store filters and show SuggestionsPopup
      console.log('[ANALYZE] Showing SuggestionsPopup with filters');
      console.log('[ANALYZE] clarifying_hints:', analyzeData.clarifying_hints);
      console.log('[ANALYZE] filters:', analyzeData.filters);
      
      // Store category
      setLastCategoryName(analyzeData.category);
      setSelectedFilters({}); // Reset filters for new search
      
      // Step 2: Store hints and filters for popup
      setClarifyingHints(analyzeData.clarifying_hints || []);
      setSuggestionsPopupFilters(analyzeData.filters || []);
      
      // Step 3: Display initial products (with loading skeleton)
      // Show loading skeleton first
      setMessages(prev => [...prev, {
        type: 'loading',
        timestamp: new Date()
      }]);
      
      // Add initial products if found
      if (analyzeData.products && analyzeData.products.length > 0) {
        console.log('[ANALYZE] Found initial products:', analyzeData.products.length);
        // Remove loading skeleton
        setMessages(prev => prev.filter(msg => msg.type !== 'loading'));
        
        // Add results message
        setMessages(prev => [...prev, {
          type: 'results',
          text: `🎯 Tìm thấy ${analyzeData.total || analyzeData.products.length} sản phẩm!`,
          products: analyzeData.products,
          timestamp: new Date()
        }]);
        
        // Add filter options
        if (analyzeData.filters && analyzeData.filters.length > 0) {
          setMessages(prev => [...prev, {
            type: 'filters',
            text: 'Bạn có thể lọc sản phẩm theo các tiêu chí dưới đây:',
            filters: analyzeData.filters,
            timestamp: new Date()
          }]);
        }
      } else {
        // No products found in DB
        console.log('[ANALYZE] No products in DB');
        // Remove loading skeleton
        setMessages(prev => prev.filter(msg => msg.type !== 'loading'));
        
        addBotMessage(
          `ℹ️ Hiện tại chưa có sản phẩm "${analyzeData.category}" trong kho.\n\nVui lòng chọn các tiêu chí tìm kiếm để giúp tôi tìm kiếm chính xác hơn.`
        );
      }
      
      // Step 4: Show popup for filter refinement
      setShowSuggestionsPopup(true);
      
      setIsThinking(false);
      
    } catch (error) {
      console.error('[ANALYZE/SEARCH] Error:', error);
      const errorMsg = error.response?.data?.detail || error.response?.data?.error || error.message || 'Có lỗi xảy ra';
      setMessages(prev => prev.filter(msg => msg.type !== 'loading'));
      addBotMessage(`❌ Lỗi: ${errorMsg}`);
      addBotMessage("Lưu ý: Vui lòng chắc chắn backend Python đang chạy trên http://localhost:8000");
    } finally {
      setIsThinking(false);
    }
  };

  // Connect to backend API (legacy - keep for backward compatibility)
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

  // Gọi endpoint /api/v1/crawl-products để lấy products + filters
  const searchProductsWithFilters = async (categoryName, selectedFilters = {}) => {
    setConversationState(prev => ({ ...prev, isLoading: true }));
    setClarifyingHints([]); // Clear hints khi search mới
    try {
      console.log('Searching products:', { category_name: categoryName, selected_filters: selectedFilters });
      
      // Show loading skeleton ngay lập tức
      setMessages(prev => [...prev, {
        type: 'loading',
        timestamp: new Date()
      }]);

      // Check if filters need conversion (from old "attr:value" format to new {attr: [values]} format)
      let filterObj = selectedFilters;
      
      // If it's in "attr:value" format (old format from filter sidebar), convert it
      if (Object.keys(selectedFilters).some(key => key.includes(':'))) {
        filterObj = {};
        Object.keys(selectedFilters).forEach(key => {
          const [attrName, attrValue] = key.split(':');
          if (!filterObj[attrName]) {
            filterObj[attrName] = [];
          }
          filterObj[attrName].push(attrValue);
        });
      }

      console.log('Final filters for API:', filterObj);
      
      const response = await fetch(`${API_BASE_URL}/api/v1/crawl-products`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          category_name: categoryName,
          selected_filters: filterObj,
          page: 1,
          page_size: 20
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || `HTTP ${response.status}`);
      }

      const data = await response.json();
      console.log('Crawl products response:', data);

      // Remove loading skeleton
      setMessages(prev => prev.filter(msg => msg.type !== 'loading'));

      // Display products + filters
      displayCrawlProductsResponse(data);

    } catch (error) {
      console.error('Crawl products error:', error);
      const errorMsg = error.message || 'Có lỗi xảy ra khi tìm kiếm sản phẩm';
      setMessages(prev => prev.filter(msg => msg.type !== 'loading'));
      addBotMessage(`❌ Lỗi: ${errorMsg}`);
    } finally {
      setConversationState(prev => ({ ...prev, isLoading: false }));
    }
  };

  // Hiển thị sản phẩm + filters từ endpoint crawl-products
  const displayCrawlProductsResponse = (data) => {
    if (!data) {
      console.error('No data received from crawl-products');
      addBotMessage('❌ Không nhận được dữ liệu từ server');
      return;
    }

    if (!data.products || data.products.length === 0) {
      addBotMessage('🔍 Không tìm thấy sản phẩm nào phù hợp');
      return;
    }

    // REPLACE existing results + filters instead of appending
    // This prevents the UI from looking cluttered with multiple product lists
    const resultMessage = `🎯 Tìm thấy ${data.total || data.products.length} sản phẩm!`;
    const resultsMsg = {
      type: 'results',
      text: resultMessage,
      products: data.products,
      timestamp: new Date()
    };

    const filtersMsg = data.filters && data.filters.length > 0 ? {
      type: 'filters',
      text: 'Bạn có thể lọc sản phẩm theo các tiêu chí dưới đây:',
      filters: data.filters,
      timestamp: new Date()
    } : null;

    // Replace old results and filters with new ones
    setMessages(prev => {
      // Remove old results and filters messages
      const filtered = prev.filter(msg => msg.type !== 'results' && msg.type !== 'filters');
      // Add new results and filters
      const updated = [...filtered, resultsMsg];
      if (filtersMsg) {
        updated.push(filtersMsg);
      }
      return updated;
    });
  };

  const displayBackendResponse = (data) => {
    console.log('displayBackendResponse:', data);
    
    // Nếu có clarifying_hints từ backend, set vào state
    if (data.clarifying_hints && Array.isArray(data.clarifying_hints)) {
      console.log('Setting clarifying hints:', data.clarifying_hints);
      setClarifyingHints(data.clarifying_hints);
    }

    // If we have results with category, display filters FIRST, then products from /api/query
    if (data.status === 'results' && data.products && data.products.length > 0) {
      // Display filters FIRST if available from /api/query response
      if (data.filters && data.filters.length > 0) {
        console.log('Displaying filters from /api/query:', data.filters);
        const filterMessage = `Bạn có thể lọc sản phẩm theo các tiêu chí dưới đây:`;
        setMessages(prev => [...prev, {
          type: 'filters',
          text: filterMessage,
          filters: data.filters,
          timestamp: new Date()
        }]);
      }

      // Display products AFTER filters
      const resultMessage = `🎯 **Tìm thấy ${data.total_found || data.products.length} sản phẩm!**`;
      setMessages(prev => [...prev, {
        type: 'results',
        text: resultMessage,
        products: data.products,
        timestamp: new Date()
      }]);
      return;
    }
    
    // Display question if no results yet
    if (data.question) {
      let quickReplies = null;
      if (data.options && Array.isArray(data.options)) {
        quickReplies = data.options.map(opt => opt.label || opt.value || opt);
      }
      console.log('Quick replies:', quickReplies);
      addBotMessage(data.question, null, quickReplies);
    }
  };

  const handleSend = () => {
    if (!currentInput.trim() || isThinking) return;

    addUserMessage(currentInput);
    analyzeAndSearch(currentInput);  // NEW: Use analyze-first flow
    setCurrentInput('');
  };

  /**
   * Handle filter confirmation from SuggestionsPopup
   * Called when user selects filter values and clicks "Tìm kiếm" button
   */
  const handleSuggestionsConfirm = (selectedFilters) => {
    console.log('[POPUP] Selected filters:', selectedFilters);
    // Close the popup
    setShowSuggestionsPopup(false);
    // Call searchProductsWithFilters with the selected filters
    // selectedFilters is already in the format {attribute_name: [values]}
    searchProductsWithFilters(lastCategoryName, selectedFilters);
  };

  const handleQuickReply = (reply) => {
    addUserMessage(reply);
    
    // Check if user clicked "Search with filters" button
    if (reply.includes('🔍 Tìm sản phẩm') && lastCategoryName) {
      searchProductsWithFilters(lastCategoryName);
    } else {
      // Determine question type based on context
      // This is a simplified approach - you might need to track the current step
      sendToBackend(reply);
    }
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

            {msg.type === 'hints' && msg.hints && Array.isArray(msg.hints) && msg.hints.length > 0 && (
              <div className="flex gap-3 mt-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-500 to-orange-500 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <div className="bg-amber-50 border-2 border-amber-200 rounded-2xl rounded-tl-none p-4 max-w-2xl">
                    <div className="font-semibold text-amber-900 mb-2 text-sm">
                      💡 Đây là những tiêu chí tìm kiếm có sẵn:
                    </div>
                    <div className="flex flex-wrap gap-2">
                      {msg.hints.map((hint, idx) => (
                        <span
                          key={idx}
                          className="px-3 py-2 bg-white border-2 border-amber-300 text-amber-700 text-sm rounded-full font-medium"
                        >
                          {hint}
                        </span>
                      ))}
                    </div>
                    <div className="text-xs text-amber-600 mt-2">
                      (Vui lòng chọn các tiêu chí từ popup bên dưới)
                    </div>
                  </div>
                </div>
              </div>
            )}

            {msg.type === 'filters' && msg.filters && (
              <div className="flex gap-3">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-5 h-5 text-white" />
                </div>
                <div className="flex-1">
                  <div className="bg-purple-50 rounded-2xl rounded-tl-none p-4">
                    <div className="font-semibold text-purple-900 mb-3">{msg.text}</div>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {msg.filters.map((filter, filterIdx) => (
                        <div key={filterIdx} className="border border-purple-200 rounded-lg p-2 bg-white">
                          <p className="font-semibold text-sm text-purple-900 mb-1">
                            {filter.display_name || filter.attribute_name}
                          </p>
                          <div className="flex flex-wrap gap-1">
                            {filter.options && filter.options.slice(0, 5).map((option, optIdx) => {
                              const filterKey = `${filter.attribute_name}:${option.attribute_value}`;
                              const isSelected = selectedFilters[filterKey];
                              return (
                                <button
                                  key={optIdx}
                                  onClick={() => {
                                    console.log('Filter toggled:', filter.attribute_name, option.attribute_value);
                                    setSelectedFilters(prev => {
                                      const newFilters = { ...prev };
                                      if (newFilters[filterKey]) {
                                        delete newFilters[filterKey];
                                      } else {
                                        newFilters[filterKey] = true;
                                      }
                                      console.log('Selected filters:', newFilters);
                                      return newFilters;
                                    });
                                  }}
                                  className={`px-2 py-1 text-xs rounded transition-all border ${
                                    isSelected
                                      ? 'bg-purple-500 text-white border-purple-600'
                                      : 'bg-purple-100 hover:bg-purple-200 text-purple-700 border-purple-200'
                                  }`}
                                >
                                  {option.attribute_value} ({option.product_count})
                                </button>
                              );
                            })}
                            {filter.options && filter.options.length > 5 && (
                              <span className="text-xs text-gray-500 px-2 py-1">
                                +{filter.options.length - 5} more
                              </span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                    {Object.keys(selectedFilters).length > 0 && (
                      <button
                        onClick={() => {
                          if (lastCategoryName) {
                            searchProductsWithFilters(lastCategoryName, selectedFilters);
                          }
                        }}
                        className="mt-4 w-full px-4 py-2 bg-purple-500 hover:bg-purple-600 text-white text-sm font-semibold rounded-lg transition-all"
                      >
                        🔍 Lọc sản phẩm ({Object.keys(selectedFilters).length} filters)
                      </button>
                    )}
                    {/* Render clarifying hints nếu có */}
                    {/* {renderClarifyingHints()} */}
                  </div>
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

                {/* Render clarifying hints right after results */}
                {/* {clarifyingHints && clarifyingHints.length > 0 && renderClarifyingHints()} */}

                <div className="ml-13 w-full">
                  <div className="grid grid-cols-3 gap-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                    {msg.products.map((product, i) => (
                      <div 
                        key={product.id || i} 
                        className="bg-white border border-gray-200 rounded-lg overflow-hidden hover:border-blue-400 hover:shadow-md transition-all cursor-pointer group"
                        onClick={() => {
                          if (product.product_url) {
                            window.open(product.product_url, '_blank');
                          }
                        }}
                      >
                        {/* Product Image */}
                        {product.thumbnail && (
                          <div className="relative overflow-hidden bg-gray-100 h-32 flex items-center justify-center">
                            <img
                              src={product.thumbnail}
                              alt={product.title}
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
                          <h3 className="font-semibold text-gray-800 text-xs line-clamp-2 mb-1">{product.title}</h3>
                          
                          {product.min_price && (
                            <div className="text-sm font-bold text-red-600 mb-1">
                              {(product.min_price/1000000).toFixed(1)}tr
                            </div>
                          )}

                          {product.brand && (
                            <div className="text-xs text-gray-600 line-clamp-1">
                              {product.brand}
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Loading skeleton */}
            {msg.type === 'loading' && (
              <div className="space-y-4">
                {/* Skeleton title */}
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center flex-shrink-0">
                    <div className="w-5 h-5 bg-green-600 rounded animate-pulse" />
                  </div>
                  <div className="bg-green-50 rounded-2xl rounded-tl-none p-4 w-64">
                    <div className="h-6 bg-green-200 rounded animate-pulse" />
                  </div>
                </div>

                {/* Skeleton filters */}
                <div className="flex gap-3">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center flex-shrink-0">
                    <div className="w-5 h-5 bg-purple-600 rounded animate-pulse" />
                  </div>
                  <div className="flex-1">
                    <div className="bg-purple-50 rounded-2xl rounded-tl-none p-4">
                      <div className="h-5 bg-purple-200 rounded mb-3 w-40 animate-pulse" />
                      <div className="space-y-2">
                        {[1, 2, 3].map(i => (
                          <div key={i} className="border border-purple-200 rounded-lg p-2 bg-white">
                            <div className="h-4 bg-purple-100 rounded w-24 mb-2 animate-pulse" />
                            <div className="flex gap-1 flex-wrap">
                              {[1, 2, 3, 4].map(j => (
                                <div key={j} className="h-6 w-16 bg-purple-100 rounded-full animate-pulse" />
                              ))}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Skeleton products */}
                <div className="ml-13 w-full">
                  <div className="grid grid-cols-3 gap-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6">
                    {[...Array(18)].map((_, i) => (
                      <div key={i} className="bg-white border border-gray-200 rounded-lg overflow-hidden">
                        <div className="bg-gray-200 h-32 animate-pulse" />
                        <div className="p-2">
                          <div className="h-4 bg-gray-200 rounded mb-2 animate-pulse" />
                          <div className="h-4 bg-gray-200 rounded w-2/3 mb-2 animate-pulse" />
                          <div className="h-4 bg-red-200 rounded w-1/2 animate-pulse" />
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

      {/* SuggestionsPopup - Appears when /api/analyze returns filters */}
      <SuggestionsPopup
        isOpen={showSuggestionsPopup}
        onClose={() => setShowSuggestionsPopup(false)}
        category={lastCategoryName}
        filters={suggestionsPopupFilters}
        hints={clarifyingHints}
        onConfirm={handleSuggestionsConfirm}
        conversationId={conversationState.conversationId}
      />

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
