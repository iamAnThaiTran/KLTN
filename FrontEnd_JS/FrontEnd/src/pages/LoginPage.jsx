import React, { useState } from 'react';
import { AlertCircle, Loader } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import { GoogleLogin } from '@react-oauth/google';

export default function LoginPage() {
    const [error, setError] = useState('');
    const [loading, setLoading] = useState(false);
    
    const { googleLogin } = useAuth();
    const navigate = useNavigate();

    const handleGoogleSuccess = async (credentialResponse) => {
        setError('');
        setLoading(true);

        try {
            const result = await googleLogin(credentialResponse.credential);
            
            if (result.success) {
                // Check if user is admin
                if (result.user?.role === 'admin') {
                    navigate('/admin/dashboard');
                } else {
                    navigate('/');
                }
            } else {
                setError(result.message || 'Đăng nhập thất bại');
            }
        } catch (err) {
            setError('Lỗi: ' + err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleGoogleError = () => {
        setError('Google login failed. Please try again.');
    };

    return (
        <div className="min-h-screen  flex items-center justify-center p-4">
            <div className="bg-white rounded-lg shadow-xl p-8 w-full max-w-md">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="inline-block mb-4">
                        <div className="w-16 h-16  rounded-full flex items-center justify-center text-3xl">
                            🤖
                        </div>
                    </div>
                    <h1 className="text-3xl font-bold text-gray-900">Đăng Nhập</h1>
                    <p className="text-gray-600 mt-2">Chào mừng quay lại</p>
                </div>

                {/* Error Message */}
                {error && (
                    <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg flex items-center gap-3">
                        <AlertCircle className="w-5 h-5 text-red-600" />
                        <p className="text-red-800 text-sm">{error}</p>
                    </div>
                )}

                {/* Google Login */}
                <div className="flex justify-center mt-8">
                    <GoogleLogin
                        onSuccess={handleGoogleSuccess}
                        onError={handleGoogleError}
                        text="signin_with"
                    />
                </div>

                {loading && (
                    <div className="mt-6 flex items-center justify-center">
                        <Loader className="w-5 h-5 animate-spin text-blue-500" />
                        <span className="ml-2 text-gray-600">Đang xác thực...</span>
                    </div>
                )}
            </div>
        </div>
    );
}
