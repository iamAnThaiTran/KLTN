import React, { createContext, useContext, useState, useEffect } from 'react';
import { StorageService } from '../services/StorageService.js';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [loading, setLoading] = useState(true);

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

            const response = await fetch('http://localhost:3000/api/v1/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: emailStr, password: passwordStr })
            });

            const data = await response.json();

            if (data.success) {
                setToken(data.token);
                setUser(data.user);
                StorageService.setToken(data.token);
                StorageService.setUser(data.user);
                return { success: true, user: data.user };
            } else {
                return { success: false, message: data.message };
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

            const response = await fetch('http://localhost:3000/api/v1/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: emailStr, password: passwordStr, name: nameStr })
            });

            const data = await response.json();

            if (data.success) {
                setToken(data.token);
                setUser(data.user);
                StorageService.setToken(data.token);
                StorageService.setUser(data.user);
                return { success: true, user: data.user };
            } else {
                return { success: false, message: data.message };
            }
        } catch (error) {
            return { success: false, message: error.message };
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
            isAuthenticated: !!user && !!token,
            login,
            register,
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
