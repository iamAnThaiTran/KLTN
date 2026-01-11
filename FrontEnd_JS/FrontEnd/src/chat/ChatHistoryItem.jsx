import { useState } from "react";
import { MessageCircle, Trash2 } from 'lucide-react';

function ChatHistoryItem({ chat, isActive, onClick, onDelete }) {
  const [isHovered, setIsHovered] = useState(false);
  
  return (
    <div
      className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-all ${
        isActive 
          ? 'bg-indigo-50 border border-indigo-200' 
          : 'hover:bg-gray-100'
      }`}
      onClick={onClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <MessageCircle className="w-4 h-4 text-gray-500 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">
          {chat.title}
        </p>
        <p className="text-xs text-gray-500">
          {new Date(chat.timestamp).toLocaleDateString('vi-VN')}
        </p>
      </div>
      {isHovered && (
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete(chat.id);
          }}
          className="p-1 hover:bg-red-100 rounded"
        >
          <Trash2 className="w-4 h-4 text-red-500" />
        </button>
      )}
    </div>
  );
}

export default ChatHistoryItem;