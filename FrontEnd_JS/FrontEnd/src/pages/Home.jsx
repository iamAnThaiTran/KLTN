import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import Sidebar from '../layout/Sidebar';
import Header from '../layout/Header';
import AIUnderstandingPanel from '../components/AIUnderstandingPanel';
import AssistOverlay from '../components/AssistOverlay';
import ProductGrid from '../components/ProductGrid';
import HomeCategorySection from '../components/HomeCategorySection';
import { useAuth } from '../context/AuthContext';
import { getProductFromTiki } from '../services/productServices';
import Footer from '../layout/Footer';
import NewsSection from '../components/NewsSection';

export default function Home() {
    const navigate = useNavigate();
    const { user, loading } = useAuth();

    const [searchMode, setSearchMode] = useState('recommended');
    const [products, setProducts] = useState([]);
    const [isSearching, setIsSearching] = useState(false);
    const [currentQuery, setCurrentQuery] = useState('');
    const [clarifyData, setClarifyData] = useState(null);
    const [showAssistOverlay, setShowAssistOverlay] = useState(false);
    const [assistOverlayData, setAssistOverlayData] = useState(null);

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
            const response = await getProductFromTiki(query);
            console.log('handleSearch - response:', response);

            // Handle overlay assist response
            if (response.ui_mode === 'OVERLAY_ASSIST') {
                console.log('Setting overlay data and showing overlay');
                setAssistOverlayData(response);
                setShowAssistOverlay(true);
                return;
            }

            // Handle clarification response type
            if (response.type === 'clarify') {
                setClarifyData({
                    question: response.question,
                    options: response.options || [],
                    understanding: response.understanding,
                });
                setSearchMode('clarify');
                setProducts([]);
            } else {
                // Handle query response type
                setProducts(response.products || []);
                setSearchMode('query');
                setClarifyData(null);
            }
        } catch (error) {
            console.error('Search error:', error);
            setProducts([]);
            setSearchMode('query');
            setClarifyData(null);
        } finally {
            setIsSearching(false);
        }
    };

    const handleSelectOption = async (option) => {
        if (!currentQuery) return;

        setIsSearching(true);

        try {
            const combinedQuery = currentQuery + ' ' + option;
            const response = await getProductFromTiki(combinedQuery);

            // Handle overlay assist response
            if (response.ui_mode === 'OVERLAY_ASSIST') {
                setAssistOverlayData(response);
                setShowAssistOverlay(true);
                setIsSearching(false);
                return;
            }

            // Handle clarification response type
            if (response.type === 'clarify') {
                setClarifyData({
                    question: response.question,
                    options: response.options || [],
                    understanding: response.understanding,
                });
                setSearchMode('clarify');
                setProducts([]);
            } else {
                // Handle query response type
                setProducts(response.products || []);
                setSearchMode('query');
                setClarifyData(null);
            }
        } catch (error) {
            console.error('Option selection error:', error);
            setProducts([]);
            setSearchMode('query');
            setClarifyData(null);
        } finally {
            setIsSearching(false);
        }
    };

    const handleAssistOptionSelect = async (optionKey) => {
        const combinedQuery = currentQuery + ' ' + optionKey;
        setShowAssistOverlay(false);
        setAssistOverlayData(null);
        await handleSearch(combinedQuery);
    };

    const handleAssistSkip = () => {
        setShowAssistOverlay(false);
        setAssistOverlayData(null);
        setSearchMode('query');
    };

    const handleAssistClose = () => {
        setShowAssistOverlay(false);
        setAssistOverlayData(null);
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50">
            <AssistOverlay
                isOpen={showAssistOverlay}
                data={assistOverlayData}
                onOptionSelect={handleAssistOptionSelect}
                onSkip={handleAssistSkip}
                onClose={handleAssistClose}
            />

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
                    <div className="mx-auto max-w-7xl w-full px-4 md:px-6 lg:px-8">
                        {/* Show recommended products label when on home */}
                        {searchMode === 'recommended' && <NewsSection />}
                        {searchMode === 'recommended' && (
                            <div className="pt-4 pb-2">
                                <h2 className="text-lg font-semibold text-gray-900">
                                    🔥 Sản phẩm nổi bật
                                </h2>
                            </div>
                        )}

                        

                        {/* Category Product List - shown when on recommended view */}
                        {searchMode === 'recommended' && <HomeCategorySection />}

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

                        {/* Intent Analysis Summary - shown when query is clear */}
                        {searchMode === 'query' && currentQuery && (
                            <div className="pt-4 pb-2">
                                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                                    <p className="text-sm text-gray-700">
                                        <span className="font-semibold">
                                            ✓ Đã hiểu:
                                        </span>{' '}
                                        {currentQuery}
                                    </p>
                                    {/* Show search criteria if available */}
                                    {products && products.length === 0 && (
                                        <p className="text-xs text-gray-500 mt-2">
                                            💡 Chúng tôi hiểu bạn tìm kiếm:{' '}
                                            <span className="font-medium">
                                                {currentQuery}
                                            </span>
                                        </p>
                                    )}
                                </div>
                            </div>
                        )}

                        {/* Product Grid - shown when query is clear, clarifying, or recommended */}
                        <ProductGrid
                            products={products}
                            isLoading={isSearching && searchMode === 'query'}
                            isHidden={false}
                        />
                    </div>
                </main>
            </div>

            <Footer />
        </div>
    );
}
