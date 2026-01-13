import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

import Sidebar from "../layout/Sidebar";
import Header from "../layout/Header";
import AIUnderstandingPanel from "../components/AIUnderstandingPanel";
import ProductGrid from "../components/ProductGrid";
import { useAuth } from "../context/AuthContext";
import { getProductFromTiki } from "../services/productServices";
import { hotProducts } from "../data/mockProducts";

export default function Home() {
    const navigate = useNavigate();
    const { user, loading } = useAuth();

    const [searchMode, setSearchMode] = useState('recommended'); // "recommended", "clarify", "query"
    const [products, setProducts] = useState(hotProducts); // Load mock data by default
    const [isSearching, setIsSearching] = useState(false);
    const [currentQuery, setCurrentQuery] = useState("");
    const [clarifyData, setClarifyData] = useState(null); // { question, options, understanding }

    // Redirect admin users to dashboard
    useEffect(() => {
        if (!loading && user?.role === 'admin') {
            navigate('/admin/dashboard');
        }
    }, [user, loading, navigate]);

    if (!loading && user?.role === 'admin') {
        return <div>Redirecting to admin dashboard...</div>;
    }

    const handleSearch = async (query) => {
        setIsSearching(true);
        setCurrentQuery(query);

        try {
            // Call backend search API
            const response = await fetch('http://localhost:3000/api/v1/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query })
            });

            const data = await response.json();

            if (data.type === 'query') {
                // Clear query - show products
                setSearchMode('query');
                setClarifyData(null);
                
                // Fetch products (using existing service)
                try {
                    const productResponse = await getProductFromTiki(query);
                    setProducts(productResponse || []);
                } catch (error) {
                    console.error('Error fetching products:', error);
                    setProducts([]);
                }
            } else if (data.type === 'clarify') {
                // Ambiguous query - show clarification panel
                setSearchMode('clarify');
                setClarifyData({
                    question: data.question,
                    options: data.options,
                    understanding: data.understanding
                });
                setProducts([]);
            }
        } catch (error) {
            console.error('Search error:', error);
            // Fallback: treat as regular product search
            setSearchMode('query');
            try {
                const productResponse = await getProductFromTiki(query);
                setProducts(productResponse || []);
            } catch {
                setProducts([]);
            }
        } finally {
            setIsSearching(false);
        }
    };

    const handleSelectOption = async (option) => {
        if (!currentQuery) return;

        setIsSearching(true);

        try {
            // Send option selection back to backend with context
            const response = await fetch('http://localhost:3000/api/v1/search', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    query: currentQuery,
                    selectedOption: option
                })
            });

            const data = await response.json();

            if (data.type === 'query') {
                setSearchMode('query');
                setClarifyData(null);
                
                try {
                    const productResponse = await getProductFromTiki(currentQuery + ' ' + option);
                    setProducts(productResponse || []);
                } catch (error) {
                    console.error('Error fetching products:', error);
                    setProducts([]);
                }
            } else if (data.type === 'clarify') {
                setClarifyData({
                    question: data.question,
                    options: data.options,
                    understanding: data.understanding
                });
                setProducts([]);
            }
        } catch (error) {
            console.error('Option selection error:', error);
        } finally {
            setIsSearching(false);
        }
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50">
            <Header 
                onMenuToggle={() => {}} 
                onSearch={handleSearch}
                isSearching={isSearching}
            />
            
            <div className="flex flex-1 pt-32">
                <Sidebar
                    currentChatId={null}
                    onNewChat={() => {}}
                    onSelectChat={() => {}}
                    isOpen={false}
                    onClose={() => {}}
                />

                <main className="flex-1 flex flex-col">
                    {/* Show recommended products label when on home */}
                    {searchMode === 'recommended' && (
                        <div className="px-6 pt-4 pb-2">
                            <h2 className="text-lg font-semibold text-gray-900">🔥 Sản phẩm nổi bật</h2>
                        </div>
                    )}

                    {/* AI Understanding Panel - shown when clarifying */}
                    {searchMode === 'clarify' && clarifyData && (
                        <AIUnderstandingPanel
                            understanding={clarifyData.understanding}
                            question={clarifyData.question}
                            options={clarifyData.options}
                            onSelectOption={handleSelectOption}
                            isLoading={isSearching}
                        />
                    )}

                    {/* Product Grid - shown when query is clear, clarifying, or recommended */}
                    <ProductGrid
                        products={products}
                        isLoading={isSearching && searchMode === 'query'}
                        isHidden={false}
                    />
                </main>
            </div>
        </div>
    );
}
