import { MessageCircle, X } from 'lucide-react';
import { useState } from 'react';

export default function AssistantBubble() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <>
      {/* Floating Bubble Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 bg-indigo-600 text-white rounded-full flex items-center justify-center shadow-lg hover:bg-indigo-700 transition-all hover:scale-110 z-50"
        title="Trợ lý AI"
      >
        {isOpen ? (
          <X className="w-6 h-6" />
        ) : (
          <MessageCircle className="w-6 h-6" />
        )}
      </button>

      {/* Quick Chat Popup - Optional */}
      {isOpen && (
        <div className="fixed bottom-24 right-6 w-96 bg-white rounded-2xl shadow-2xl border border-gray-200 z-50 overflow-hidden">
          {/* Header */}
          <div className="bg-gradient-to-r from-indigo-600 to-indigo-700 px-6 py-4 text-white">
            <h3 className="font-semibold mb-1">ShopAssist AI</h3>
            <p className="text-sm text-indigo-100">Hỏi gì về sản phẩm bạn cần</p>
          </div>

          {/* Content */}
          <div className="p-6 space-y-4">
            <p className="text-sm text-gray-600">
              💡 Bạn có thể hỏi về:
            </p>
            <ul className="text-sm space-y-2 text-gray-600">
              <li>• Laptop dưới 20 triệu</li>
              <li>• Điện thoại pin lâu</li>
              <li>• Sản phẩm mua nhiều nhất</li>
            </ul>
            <button className="w-full bg-indigo-600 text-white py-2 rounded-lg hover:bg-indigo-700 transition-colors text-sm font-medium">
              Bắt đầu tìm kiếm
            </button>
          </div>
        </div>
      )}
    </>
  );
}
