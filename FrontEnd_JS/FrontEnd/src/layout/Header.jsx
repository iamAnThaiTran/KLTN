import React, { useState } from 'react';
import { Search, Menu, Loader2 } from 'lucide-react';
import LoginButton from '../components/button/LoginButton';

export default function Header({ onMenuToggle, onSearch, isSearching }) {
    const [searchQuery, setSearchQuery] = useState('');

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && searchQuery.trim()) {
            onSearch(searchQuery.trim());
        }
    };

    const handleSearchClick = () => {
        if (searchQuery.trim()) {
            onSearch(searchQuery.trim());
        }
    };

    return (
        <header className="fixed top-0 left-0 right-0 bg-white shadow-md z-40">
            {/* Main Header - Clean and focused */}
            <div className="px-6 py-4 flex items-center justify-between gap-6 border-b border-gray-100">
                {/* Menu Button + Logo */}
                <div className="flex items-center gap-4 flex-shrink-0">
                    <button
                        onClick={onMenuToggle}
                        className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                        title="Mở chat history"
                    >
                        <Menu className="w-5 h-5 text-gray-700" />
                    </button>
                    <a href="/" className="flex items-center gap-2">
                        <div className="w-8 h-8 bg-gradient-to-br from-indigo-600 to-indigo-700 rounded-lg flex items-center justify-center text-white font-bold">
                            🛍️
                        </div>
                        <span className="font-bold text-lg text-gray-900">ShopAssist</span>
                    </a>
                </div>

                {/* Centered Search Bar - Main Focus */}
                <div className="flex-1 max-w-2xl">
                    <div className="flex gap-2">
                        <div className="relative flex-1">
                            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                            <input
                                type="text"
                                placeholder="Tìm kiếm sản phẩm, thương hiệu..."
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                onKeyDown={handleKeyDown}
                                disabled={isSearching}
                                className="w-full pl-12 pr-4 py-2.5 border border-gray-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent bg-gray-50 hover:bg-white transition-colors disabled:opacity-50"
                            />
                        </div>
                        <button
                            onClick={handleSearchClick}
                            disabled={isSearching || !searchQuery.trim()}
                            className="px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                        >
                            {isSearching ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <Search className="w-5 h-5" />
                            )}
                        </button>
                    </div>
                </div>

                {/* User Profile */}
                <div className="flex-shrink-0">
                    <LoginButton />
                </div>
            </div>

            {/* Quick Categories - Horizontal, Compact */}
            <div className="px-6 py-3 border-t border-gray-100 bg-gray-50 overflow-x-auto">
                <div className="flex gap-4 whitespace-nowrap text-sm">
                    <button onClick={() => onSearch('Laptop')} className="px-3 py-1 hover:text-indigo-600 transition text-gray-700 font-medium">💻 Laptop</button>
                    <button onClick={() => onSearch('Điện thoại')} className="px-3 py-1 hover:text-indigo-600 transition text-gray-700 font-medium">📱 Điện thoại</button>
                    <button onClick={() => onSearch('Gaming')} className="px-3 py-1 hover:text-indigo-600 transition text-gray-700 font-medium">🎮 Gaming</button>
                    <button onClick={() => onSearch('Mỹ phẩm')} className="px-3 py-1 hover:text-indigo-600 transition text-gray-700 font-medium">🧴 Mỹ phẩm</button>
                    <button onClick={() => onSearch('Nhà cửa')} className="px-3 py-1 hover:text-indigo-600 transition text-gray-700 font-medium">🏠 Nhà cửa</button>
                </div>
            </div>
        </header>
    );
}
