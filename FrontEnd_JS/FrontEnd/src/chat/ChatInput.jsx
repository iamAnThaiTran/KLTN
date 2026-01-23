import { useState, useRef, useEffect } from "react";
import { Send, Mic, MicOff, Volume2 } from 'lucide-react';

function ChatInput({ onSend, disabled }) {
  const [input, setInput] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [transcript, setTranscript] = useState('');
  const recognitionRef = useRef(null);
  const [isBrowserSupported, setIsBrowserSupported] = useState(true);

  // Khởi tạo Web Speech API
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    
    if (!SpeechRecognition) {
      setIsBrowserSupported(false);
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
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
        setInput(prev => (prev + ' ' + finalTranscript).trim());
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

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
      setTranscript('');
    }
  };
  
  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {isListening && transcript && (
        <div className="max-w-4xl mx-auto mb-3 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <div className="flex items-center gap-2 text-sm text-blue-700">
            <Volume2 className="w-4 h-4 animate-pulse" />
            <span>Đang nghe: <strong>{transcript}</strong></span>
          </div>
        </div>
      )}
      <form onSubmit={handleSubmit} className="max-w-4xl mx-auto flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Nhập gợi ý sản phẩm hoặc nói vào micro"
          disabled={disabled}
          className="flex-1 px-4 py-3 border border-gray-300 rounded-xl focus:outline-none focus:ring-2 focus:ring-indigo-500 disabled:bg-gray-100"
        />
        
        <button
          type="button"
          onClick={handleMicClick}
          disabled={disabled || !isBrowserSupported}
          className={`px-4 py-3 rounded-xl transition-colors flex items-center gap-2 font-medium ${
            isListening
              ? 'bg-red-500 text-white hover:bg-red-600'
              : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
          } disabled:opacity-50 disabled:cursor-not-allowed`}
          title={isListening ? 'Dừng ghi âm' : isBrowserSupported ? 'Bắt đầu ghi âm' : 'Trình duyệt không hỗ trợ'}
        >
          {isListening ? (
            <MicOff className="w-5 h-5" />
          ) : (
            <Mic className="w-5 h-5" />
          )}
        </button>
        
        <button
          type="submit"
          disabled={disabled || !input.trim()}
          className="px-6 py-3 bg-indigo-600 text-white rounded-xl hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
        >
          <Send className="w-5 h-5" />
        </button>
      </form>
    </div>
  );
}

export default ChatInput;