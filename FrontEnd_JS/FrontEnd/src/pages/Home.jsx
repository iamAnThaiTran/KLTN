import { useState, useRef, useEffect } from "react";

import {
    MessageCircle,
    Plus,
    Search,
    Trash2,
    Send,
    Sparkles,
} from "lucide-react";
import StorageService from "../services/StorageService";
import Sidebar from "../layout/Sidebar";
import Header from "../layout/Header";
import WelcomeScreen from "../home/WelcomeScreen";
import ChatInput from "../chat/ChatInput";
import ChatMessage from "../chat/ChatMessage";
import { getProductFromTiki } from "../services/productServices";


export default function Home() {
    const [currentChatId, setCurrentChatId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const bottomRef = useRef(null);

    useEffect(() => {
        if (messages.length > 0) {
            const lastMessage = messages[messages.length - 1];
            if (lastMessage.type === "user") {
                bottomRef.current?.scrollIntoView({ behavior: "smooth" });
            }
        }
    }, [messages]);


    const handleNewChat = () => { 
        setCurrentChatId(null);
        setMessages([]);
    };

    const handleSelectChat = (chat) => {
        setCurrentChatId(chat.id);
        setMessages(chat.messages || []);
    };

    //handle mock data
    const mockProductResponse = async (query) => {
        try {
            const response = await getProductFromTiki(query);
            const products = response;
            return {
                content: `Tôi tìm thấy ${products.length} sản phẩm phù hợp với "${query}". Đây là những lựa chọn tốt nhất:`,
                products,
            };
        } catch (error) {
            console.error(error);
        }
    };

    const handleSendMessage = async (content) => {
        const userMessage = {
            id: Date.now(),
            type: "user",
            content,
            timestamp: new Date(),
        };

        setMessages((prev) => [...prev, userMessage]);
        setIsLoading(true);   
        const response = await mockProductResponse(content);
        const botMessage = {
            id: Date.now() + 1,
            type: "bot",
            content: response.content,
            products: response.products,
            timestamp: new Date(),
        };

        const newMessages = [...messages, userMessage, botMessage];
        setMessages(newMessages);
        setIsLoading(false);

        // Save to history
        if (!currentChatId) {
            const newChatId = `chat_${Date.now()}`;
            const newChat = {
                id: newChatId,
                title: content.substring(0, 50),
                messages: newMessages,
                timestamp: new Date(),
            };
            StorageService.saveChat(newChat);
            setCurrentChatId(newChatId);
        }
    };

    const handlePromptClick = (prompt) => {
        handleSendMessage(prompt);
    };

    return (
        <div className="flex flex-col h-screen bg-gray-50 ">
            <Header />
            <div className="flex flex-1">
                <Sidebar
                    currentChatId={currentChatId}
                    onNewChat={handleNewChat}
                    onSelectChat={handleSelectChat}
                />

                <main className="flex-1 flex flex-col">
                {messages.length === 0 ? (
                    <WelcomeScreen onPromptClick={handlePromptClick} />
                ) : (
                    <div className="flex-1 overflow-y-auto p-6">
                        <div className="max-w-7xl mx-auto">
                            {messages.map((message) => (
                                <ChatMessage key={message.id} message={message} />
                            ))}
                            {isLoading && (
                                <div className="flex gap-3 mb-4">
                                    <div className="w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                                        🤖
                                    </div>
                                    <div className="bg-gray-100 rounded-2xl px-4 py-3">
                                        <div className="flex gap-1">
                                            <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                            <div
                                                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                                style={{ animationDelay: "0.1s" }}
                                            ></div>
                                            <div
                                                className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                                                style={{ animationDelay: "0.2s" }}
                                            ></div>
                                        </div>
                                    </div>
                                </div>
                            )}
                            {/* scrolling */}
                            <div ref={bottomRef} />
                        </div>
                    </div>
                )}
    </main>
            </div>
                <ChatInput onSend={handleSendMessage} disabled={isLoading} />
           
        </div>
    );
}
