import React from 'react';
import {
  LayoutDashboard, Package,
  Users, MessageSquare,
  BarChart3, Settings, LogOut,
  FolderTree
} from 'lucide-react';

// Sidebar Component
export function SideAdminbar({ activeTab, setActiveTab }) {
  const menuItems = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'products', label: 'Quản lý Sản phẩm', icon: Package },
    { id: 'categories', label: 'Danh mục', icon: FolderTree },
    { id: 'statistics', label: 'Thống kê', icon: BarChart3 },
    { id: 'users', label: 'Người dùng', icon: Users },
    { id: 'chats', label: 'Cuộc trò chuyện', icon: MessageSquare },
    { id: 'settings', label: 'Cài đặt', icon: Settings }
  ];

  return (
    <aside className="w-64 bg-gray-900 text-white flex flex-col h-full">
      <div className="p-6 border-b border-gray-800">
        <h1 className="text-2xl font-bold">Admin Panel</h1>
        <p className="text-sm text-gray-400 mt-1">Affiliate Management</p>
      </div>
     
      <nav className="flex-1 p-4 space-y-1">
        {menuItems.map(item => (
          <button
            key={item.id}
            onClick={() => setActiveTab(item.id)}
            className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
              activeTab === item.id
                ? 'bg-blue-600 text-white'
                : 'text-gray-300 hover:bg-gray-800'
            }`}
          >
            <item.icon className="w-5 h-5" />
            <span>{item.label}</span>
          </button>
        ))}
      </nav>
     
      <div className="p-4 border-t border-gray-800">
        <button className="w-full flex items-center gap-3 px-4 py-3 text-gray-300 hover:bg-gray-800 rounded-lg">
          <LogOut className="w-5 h-5" />
          <span>Đăng xuất</span>
        </button>
      </div>
    </aside>
  );
}