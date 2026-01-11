import React from 'react';
import { LogIn, LogOut, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useNavigate } from 'react-router-dom';

export default function LoginButton() {
    const { user, isAuthenticated, logout } = useAuth();
    const navigate = useNavigate();

    if (isAuthenticated && user) {
        // Logged in - show user info and logout
        return (
            <div className="flex space-x-3">
                {/* User Info Card */}
                <div className="p-0.5 rounded-lg border border-blue-200">
                    <div className="flex items-center gap-3 mb-3">
                        <div className="w-10 h-10 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white font-bold text-sm">
                            {user.name ? user.name[0].toUpperCase() : 'U'}
                        </div>
                        <div className="flex-1 min-w-0">
                            <p className="font-semibold text-gray-900 text-sm truncate">{user.name || user.email}</p>
                            <p className="text-xs text-gray-600 truncate">{user.email}</p>
                            {user.role === 'admin' && (
                                <span className="inline-block mt-1 px-2 py-0.5 bg-red-100 text-red-700 text-xs font-semibold rounded-full">
                                    Admin
                                </span>
                            )}
                        </div>
                    </div>
                </div>

                {/* Logout Button */}
                <button
                    onClick={logout}
                    className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium text-sm"
                >
                    <LogOut className="w-4 h-4" />
                    Đăng Xuất
                </button>
            </div>
        );
    }

    // Not logged in - show login and register buttons
    return (
        <div className="flex gap-2">
            <button
                onClick={() => navigate('/login')}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium text-sm"
            >
                <LogIn className="w-4 h-4" />
                Đăng Nhập
            </button>
            <button
                onClick={() => navigate('/register')}
                className="flex items-center justify-center gap-2 px-4 py-2 bg-gray-200 text-gray-900 rounded-lg hover:bg-gray-300 transition-colors font-medium text-sm"
            >
                <User className="w-4 h-4" />
                Đăng Ký
            </button>
        </div>
    );
}
