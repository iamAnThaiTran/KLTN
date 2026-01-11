import { useState } from "react";
import StorageService from "../services/StorageService";
import { MessageCircle, Plus, Search, Trash2, Send, Sparkles, X } from 'lucide-react';
import ChatHistoryItem from "../chat/ChatHistoryItem";

function Sidebar({ currentChatId, onNewChat, onSelectChat, isOpen, onClose }) {
  const [histories, setHistories] = useState(StorageService.getAllChats());
  const [searchTerm, setSearchTerm] = useState('');
  
  const handleDeleteChat = (id) => {
    StorageService.deleteChat(id);
    setHistories(StorageService.getAllChats());
    if (currentChatId === id) {
      onNewChat();
    }
  };
  
  const filteredHistories = histories.filter(chat =>
    chat.title.toLowerCase().includes(searchTerm.toLowerCase())
  );
  
  return (
    <>
      {/* Overlay */}
      {isOpen && (
        <div
          className="fixed inset-0 bg-black bg-opacity-30 z-30"
          onClick={onClose}
        />
      )}
      
      {/* Sidebar */}
      <aside
        className={`fixed left-0 top-0 h-screen w-64 bg-white border-r border-gray-200 flex flex-col transition-transform duration-300 z-40 ${
          isOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        {/* Header with Close Button */}
        <div className="p-4 border-b border-gray-200 flex-shrink-0 flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Lịch sử chat</h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 rounded transition-colors"
          >
            <X className="w-5 h-5 text-gray-600" />
          </button>
        </div>
        
        {/* New Chat Button */}
        <div className="p-3 border-b border-gray-200 flex-shrink-0">
          <button
            onClick={onNewChat}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium"
          >
            <Plus className="w-5 h-5" />
            Trò chuyện mới
          </button>
        </div>
        
        {/* Search */}
        <div className="p-3 border-b border-gray-200 flex-shrink-0">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder="Tìm kiếm..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
        </div>
        
        {/* History List - Scrollable */}
        <nav className="flex-1 overflow-y-auto p-3 space-y-1 min-h-0">
          {filteredHistories.length === 0 ? (
            <div className="text-center py-8 text-gray-400 text-sm">
              {searchTerm ? 'Không tìm thấy' : 'Chưa có lịch sử'}
            </div>
          ) : (
            filteredHistories.map((chat) => (
              <ChatHistoryItem
                key={chat.id}
                chat={chat}
                isActive={chat.id === currentChatId}
                onClick={() => onSelectChat(chat)}
                onDelete={handleDeleteChat}
              />
            ))
          )}
        </nav>
        
        {/* Footer */}
        <div className="p-3 border-t border-gray-200 space-y-3 flex-shrink-0">
          <button
            onClick={() => {
              if (window.confirm('Xóa tất cả lịch sử?')) {
                StorageService.clearAll();
                setHistories([]);
                onNewChat();
              }
            }}
            className="w-full text-sm text-gray-600 hover:text-red-600 py-2"
          >
            Xóa tất cả lịch sử
          </button>
        </div>
      </aside>
    </>
  );
}

export default Sidebar;