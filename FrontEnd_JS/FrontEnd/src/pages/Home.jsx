import { useNavigate } from "react-router-dom";
import { useEffect } from "react";

import Sidebar from "../layout/Sidebar";
import Header from "../layout/Header";
import WelcomeScreen from "../home/WelcomeScreen";
import FloatingChat from "../components/FloatingChat";
import { useAuth } from "../context/AuthContext";


export default function Home() {
    const navigate = useNavigate();
    const { user, loading } = useAuth();

    // Redirect admin users to dashboard
    useEffect(() => {
        if (!loading && user?.role === 'admin') {
            navigate('/admin/dashboard');
        }
    }, [user, loading, navigate]);

    if (!loading && user?.role === 'admin') {
        return <div>Redirecting to admin dashboard...</div>;
    }

    const handleNewChat = () => { 
        // Chat is now handled in FloatingChat component
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50">
            <Header onMenuToggle={() => {}} />
            <div className="flex flex-1 pt-32">
                <Sidebar
                    currentChatId={null}
                    onNewChat={handleNewChat}
                    onSelectChat={() => {}}
                    isOpen={false}
                    onClose={() => {}}
                />

                <main className="flex-1 flex flex-col">
                    <WelcomeScreen onPromptClick={() => {}} />
                </main>
            </div>
            <FloatingChat />
        </div>
    );
}
