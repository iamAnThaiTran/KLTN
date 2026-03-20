import React, { createContext, useContext, useState, useEffect } from 'react';
import { StorageService } from '../services/StorageService.js';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [loading, setLoading] = useState(true);
    const [showLoginModal, setShowLoginModal] = useState(false);

    // Initialize auth state from localStorage
    useEffect(() => {
        const savedToken = StorageService.getToken();
        const savedUser = StorageService.getUser();
        
        if (savedToken && savedUser) {
            setToken(savedToken);
            setUser(savedUser);
        }
        
        setLoading(false);
    }, []);

    const login = async (email, password) => {
        try {

            // Ensure all parameters are strings
            const emailStr = String(email || '').trim();
            const passwordStr = String(password || '').trim();

            const response = await fetch('http://localhost:8000/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: emailStr, password: passwordStr })
            });

            const data = await response.json();

            if (data.access_token) {
                setToken(data.access_token);
                setUser(data.user);
                StorageService.setToken(data.access_token);
                StorageService.setUser(data.user);
                return { success: true, user: data.user };
            } else {
                return { success: false, message: data.detail || 'Login failed' };
            }
        } catch (error) {
            return { success: false, message: error.message };
        }
    };

    const register = async (email, password, name) => {
        try {

            // Ensure all parameters are strings
            const emailStr = String(email || '').trim();
            const passwordStr = String(password || '').trim();
            const nameStr = String(name || '').trim();

            const response = await fetch('http://localhost:8000/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: emailStr, password: passwordStr, full_name: nameStr })
            });

            const data = await response.json();

            if (data.access_token) {
                setToken(data.access_token);
                setUser(data.user);
                StorageService.setToken(data.access_token);
                StorageService.setUser(data.user);
                return { success: true, user: data.user };
            } else {
                return { success: false, message: data.detail || 'Registration failed' };
            }
        } catch (error) {
            return { success: false, message: error.message };
        }
    };

    const googleLogin = async (googleToken) => {
        try {
            console.log('🔍 Starting Google login...');
            const response = await fetch('http://localhost:8000/api/auth/google', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ idToken: googleToken })
            });

            console.log('📡 Response status:', response.status);
            const data = await response.json();
            console.log('📦 Response data:', data);

            if (response.ok && data.access_token) {
                console.log('✅ Login successful, setting state...');
                setToken(data.access_token);
                setUser(data.user);
                StorageService.setToken(data.access_token);
                StorageService.setUser(data.user);
                console.log('✅ State updated, user:', data.user);
                return { success: true, user: data.user };
            } else {
                console.error('❌ Login failed:', data);
                return { success: false, message: data.detail || 'Google login failed' };
            }
        } catch (error) {
            console.error('❌ Error:', error);
            return { success: false, message: 'Connection error: ' + error.message };
        }
    };

    const logout = () => {
        setUser(null);
        setToken(null);
        StorageService.removeToken();
        StorageService.removeUser();
    };

    return (
        <AuthContext.Provider value={{
            user,
            token,
            loading,
            showLoginModal,
            setShowLoginModal,
            isAuthenticated: !!user && !!token,
            login,
            register,
            googleLogin,
            logout
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within AuthProvider');
    }
    return context;
};
