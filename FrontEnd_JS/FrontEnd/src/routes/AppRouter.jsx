import { BrowserRouter, Route, Routes, Navigate } from "react-router-dom";
import ShoeFinder from "../components/ShoeFinder";
import Home from "../components/Home";
import ProductDetailPage from "../common/ProductPageDetail";
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
                <Route path="/" element={<Home />} />
                <Route path="/search" element={<ShoeFinder />} />
                <Route path="/product/:title" element={<ProductDetailPage />} />
                {/* <Route path="/search-products" element={<ProductSearchPage />} /> */}
                {/* <Route 
                    path="/admin/dashboard" 
                    element={
                        <AdminRoute>
                            <AdminDashboard />
                        </AdminRoute>
                    } 
                /> */}
            </Routes>
        </BrowserRouter>
    )
}