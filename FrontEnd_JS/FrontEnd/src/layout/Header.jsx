import React, { useState } from 'react';
import { MessageCircle, Search } from 'lucide-react';
import LoginButton from '../components/button/LoginButton';

export default function Header() {
    return (
        <header className="fixed top-0 left-64 right-0 bg-white shadow-md z-40">
            {/* Top Navigation */}
            <nav className="bg-gray-50 border-b border-gray-200">
                <div className="max-w-full px-6 py-2 flex justify-between items-center text-sm">
                    <div className="flex gap-6 text-gray-700">
                        <a href="/" className="hover:text-blue-600 transition">Trang chủ</a>
                        <a href="/categories" className="hover:text-blue-600 transition">Danh mục</a>
                        <a href="/about" className="hover:text-blue-600 transition">Giới thiệu</a>
                        <a href="/contact" className="hover:text-blue-600 transition">Liên hệ</a>
                    </div>
                    <div>
                        <LoginButton />
                    </div>
                </div>
            </nav>

            {/* Main Header with Logo and Search */}
           

            {/* Category Navigation Bar */}
            <nav className="bg-yellow-400 border-t border-yellow-500">
                <div className="px-6 py-3 flex justify-center gap-8 text-sm font-semibold text-gray-900 overflow-x-auto">
                    <a href="/" className="hover:text-blue-600 transition whitespace-nowrap">TRANG CHỦ</a>
                    <a href="/electronics" className="hover:text-blue-600 transition whitespace-nowrap">ĐIỆN TỬ - ĐIỆN LẠNH</a>
                    <a href="/home" className="hover:text-blue-600 transition whitespace-nowrap">ĐIỆN GIA DỤNG</a>
                    <a href="/fashion" className="hover:text-blue-600 transition whitespace-nowrap">NHÀ CỬA ĐỒI SỐNG</a>
                    <a href="/phone" className="hover:text-blue-600 transition whitespace-nowrap">ĐIỆN THOẠI - MÁY TÍNH BẢNG</a>
                    <a href="/accessories" className="hover:text-blue-600 transition whitespace-nowrap">THIẾT BỊ SỐ</a>
                    <a href="/laptop" className="hover:text-blue-600 transition whitespace-nowrap">MÁY VI TÍNH - LAPTOP</a>
                </div>
            </nav>
        </header>
    );
}
