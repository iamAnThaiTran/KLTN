import React, { useState } from 'react';
import { Calendar, Activity } from 'lucide-react';
import { SideAdminbar } from '../components/SideAdminBar';
import DashboardTab from './admin-tabs/DashboardTab';
import ProductsTab from './admin-tabs/ProductsTab';
import StatisticsTab from './admin-tabs/StatisticsTab';

export default function AdminDashboard() {
  const [activeTab, setActiveTab] = useState('dashboard');

  return (
    <div className="flex h-screen bg-gray-50">
      <SideAdminbar activeTab={activeTab} setActiveTab={setActiveTab} />
     
      <main className="flex-1 overflow-y-auto">
        <header className="bg-white border-b border-gray-200 px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Calendar className="w-5 h-5 text-gray-400" />
              <span className="text-sm text-gray-600">
                {new Date().toLocaleDateString('vi-VN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
              </span>
            </div>
            <div className="flex items-center gap-4">
              <button className="relative p-2 hover:bg-gray-100 rounded-lg">
                <Activity className="w-5 h-5 text-gray-600" />
                <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full"></span>
              </button>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-blue-600 rounded-full flex items-center justify-center text-white font-bold">
                  A
                </div>
                <div>
                  <p className="text-sm font-semibold text-gray-900">Admin User</p>
                  <p className="text-xs text-gray-500">admin@example.com</p>
                </div>
              </div>
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-7xl w-full px-4 md:px-6 lg:px-8 py-8">
          {activeTab === 'dashboard' && <DashboardTab />}
          {activeTab === 'products' && <ProductsTab />}
          {activeTab === 'statistics' && <StatisticsTab />}
          {activeTab === 'categories' && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <h2 className="text-2xl font-bold mb-4">Quản lý Danh mục</h2>
              <p className="text-gray-600">Tính năng đang phát triển...</p>
            </div>
          )}
          {activeTab === 'users' && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <h2 className="text-2xl font-bold mb-4">Quản lý Người dùng</h2>
              <p className="text-gray-600">Tính năng đang phát triển...</p>
            </div>
          )}
          {activeTab === 'chats' && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <h2 className="text-2xl font-bold mb-4">Cuộc trò chuyện</h2>
              <p className="text-gray-600">Tính năng đang phát triển...</p>
            </div>
          )}
          {activeTab === 'settings' && (
            <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
              <h2 className="text-2xl font-bold mb-4">Cài đặt Hệ thống</h2>
              <p className="text-gray-600">Tính năng đang phát triển...</p>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}