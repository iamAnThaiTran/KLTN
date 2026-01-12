import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import Home from "../pages/Home";
import ProductDetailPage from "../common/ProductPageDetail";
import LoginPage from "../pages/LoginPage";
import RegisterPage from "../pages/RegisterPage";
import AdminDashboard from "../pages/AdminDashboard";
import { useAuth } from "../context/AuthContext";

// Protected route wrapper for authenticated users
function ProtectedRoute({ children }) {
    const { isAuthenticated, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>;
    }

    return isAuthenticated ? children : <Navigate to="/login" />;
}

// Protected route for admin users only
function AdminRoute({ children }) {
    const { isAuthenticated, user, loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>;
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" />;
    }

    if (user?.role !== 'admin') {
        return <Navigate to="/" />;
    }

    return children;
}

export default function AppRouter() {
    const { loading } = useAuth();

    if (loading) {
        return <div>Loading...</div>;
    }

    return (
        <BrowserRouter>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/" element={<Home />} />
                <Route path="/product/:title" element={<ProductDetailPage />} />
                <Route 
                    path="/admin/dashboard" 
                    element={
                        <AdminRoute>
                            <AdminDashboard />
                        </AdminRoute>
                    } 
                />
            </Routes>
        </BrowserRouter>
    )
}