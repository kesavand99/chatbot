import React, { useState, useEffect, useRef } from "react";
import ChatSidebar from "@/components/ChatSidebar";
import ChatMessage from "@/components/ChatMessage";
import { createChatSocket, listChats, fetchChatHistory, deleteChatById, type ApiMessage } from "@/lib/chat-api";
import { toast } from "sonner";
import { Send, Menu, MessageSquare, Bot, Trash2, X, Plus, Headset } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import SupportWidget from "@/components/SupportWidget";
import TypingIndicator from "@/components/TypingIndicator";
import LoginPrompt from "@/components/LoginPrompt";
import { useAuth } from "@/contexts/AuthContext";

// Simple UUID fallback for non-secure contexts
const generateId = () => {
  try {
    return crypto.randomUUID();
  } catch (e) {
    return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
      const r = Math.random() * 16 | 0, v = c === 'x' ? r : (r & 0x3 | 0x8);
      return v.toString(16);
    });
  }
};

const ConnectedIndex = () => {
  const [chats, setChats] = useState<any[]>([]);
  const [activeChat, setActiveChat] = useState<string>("");
  const [messages, setMessages] = useState<ApiMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [suggestedReplies, setSuggestedReplies] = useState<string[]>([]);
  const [isSupportOpen, setIsSupportOpen] = useState(false);

  const { user, login, logout, showLoginPrompt } = useAuth();
  
  const getLocalChats = () => {
    try {
      return JSON.parse(localStorage.getItem("nexus_local_chats") || "[]") as string[];
    } catch {
      return [];
    }
  };

  const addLocalChat = (id: string) => {
    const chats = getLocalChats();
    if (!chats.includes(id)) {
      localStorage.setItem("nexus_local_chats", JSON.stringify([id, ...chats]));
    }
  };

  const removeLocalChat = (id: string) => {
    const chats = getLocalChats();
    localStorage.setItem("nexus_local_chats", JSON.stringify(chats.filter(c => c !== id)));
  };

  const [guestSupportId] = useState(() => {
    let id = localStorage.getItem("nexus_guest_support_id");
    if (!id) {
      id = "guest_" + generateId();
      localStorage.setItem("nexus_guest_support_id", id);
    }
    return id;
  });

  const chatSocket = useRef<WebSocket | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Initial load
  useEffect(() => {
    loadChats();
  }, []);

  // Scroll to bottom
  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadChats = async () => {
    try {
      const data = await listChats();
      const localIds = getLocalChats();
      const filteredChats = data.chats.filter(c => localIds.includes(c.session_id));
      
      setChats(filteredChats.map(c => ({
        id: c.session_id,
        title: c.title,
        date: new Date(c.updated_at).toLocaleDateString()
      })));
      
      if (filteredChats.length > 0 && !activeChat) {
        // Don't auto-select if we want a fresh start
      }
    } catch (error) {
      console.error("Failed to load chats", error);
    }
  };

  const handleNewChat = () => {
    setActiveChat("");
    setMessages([]);
    setSuggestedReplies([]);
    setIsSidebarOpen(false);
    setIsLoading(false);
    setIsTyping(false);
  };

  const selectChat = async (id: string) => {
    setActiveChat(id);
    setIsSidebarOpen(false);
    try {
      const data = await fetchChatHistory(id);
      setMessages(data.messages);
      setSuggestedReplies(data.suggested_replies || []);
    } catch (error) {
      toast.error("Failed to load chat history");
    }
  };

  const deleteChat = async (id: string) => {
    try {
      await deleteChatById(id);
      removeLocalChat(id);
      toast.success("Chat deleted");
      if (activeChat === id) {
        handleNewChat();
      }
      loadChats();
    } catch (error) {
      toast.error("Failed to delete chat");
    }
  };

  const sendMessage = (text: string) => {
    if (!text.trim() || isLoading) return;

    const sessionId = activeChat || generateId();
    if (!activeChat) {
      setActiveChat(sessionId);
      addLocalChat(sessionId);
    }

    const userMsg: ApiMessage = { role: "user", content: text };
    setMessages(prev => [...prev, userMsg]);
    setInput("");
    setIsLoading(true);
    setIsTyping(true);
    setSuggestedReplies([]);

    // Connect WebSocket if not connected
    if (!chatSocket.current || chatSocket.current.readyState !== WebSocket.OPEN) {
      chatSocket.current = createChatSocket(sessionId);
      
      chatSocket.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        if (data.type === "chunk") {
          setIsTyping(false);
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last && last.role === "assistant") {
              const updated = [...prev];
              updated[updated.length - 1] = { ...last, content: last.content + data.content };
              return updated;
            } else {
              return [...prev, { role: "assistant", content: data.content }];
            }
          });
        } else if (data.type === "chat_response") {
          setIsLoading(false);
          setIsTyping(false);
          setSuggestedReplies(data.suggested_replies || []);
          loadChats(); // Refresh title
        } else if (data.type === "error") {
          toast.error(data.detail || "Connection error");
          setIsLoading(false);
          setIsTyping(false);
        }
      };

      chatSocket.current.onopen = () => {
        chatSocket.current?.send(JSON.stringify({ message: text, session_id: sessionId }));
      };

      chatSocket.current.onerror = () => {
        toast.error("WebSocket error");
        setIsLoading(false);
        setIsTyping(false);
      };

      chatSocket.current.onclose = () => {
        setIsLoading(false);
        setIsTyping(false);
      };
    } else {
      chatSocket.current.send(JSON.stringify({ message: text, session_id: sessionId }));
    }
  };

  return (
    <div className="flex h-screen bg-background overflow-hidden font-sans">
      {/* Sidebar Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-background/80 backdrop-blur-sm z-30 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <ChatSidebar 
        chats={chats}
        activeChat={activeChat}
        onSelectChat={selectChat}
        onNewChat={handleNewChat}
        onDeleteChat={deleteChat}
        isOpen={isSidebarOpen}
        userName={user?.name}
        userEmail={user?.email}
        isLoggedIn={!!user}
        onLogin={login}
        onLogout={logout}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col relative min-w-0">
        {/* Header */}
        <header className="h-16 border-b border-border flex items-center justify-between px-4 bg-slate-50/90 backdrop-blur-md sticky top-0 z-20">
          <div className="flex items-center gap-3">
            <button 
              onClick={() => setIsSidebarOpen(true)}
              className="p-2 hover:bg-secondary rounded-lg lg:hidden transition-colors"
            >
              <Menu className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center">
                <Bot className="w-5 h-5 text-primary" />
              </div>
              <span className="font-semibold text-sm hidden sm:inline-block">NexusAI Workspace</span>
            </div>
          </div>
          
          {/* <div className="flex items-center gap-2">
             <Button 
               variant="outline" 
               size="sm" 
               className="gap-2 text-[11px] font-bold h-8 rounded-lg"
               onClick={() => window.open('/admin', '_blank')}
             >
               Admin Panel
             </Button>
          </div> */}
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden custom-scrollbar">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center p-8 text-center animate-in fade-in zoom-in duration-500">
              <div className="w-20 h-20 rounded-3xl bg-primary/10 flex items-center justify-center mb-6 glow-primary">
                <Bot className="w-10 h-10 text-primary" />
              </div>
              <h2 className="text-2xl font-bold mb-2 tracking-tight">How can I help you today?</h2>
              <p className="text-muted-foreground max-w-md mb-8 text-sm leading-relaxed">
                Experience the next generation of college assistance with NexusAI. 
                I can help with coding, documentation, and answering your technical questions.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl w-full">
                {[
                  "Explain quantum computing simply",
                  "How to center a div in CSS?",
                  "Write a Python script for web scraping",
                  "What is the current time?"
                ].map((q) => (
                  <button
                    key={q}
                    onClick={() => sendMessage(q)}
                    className="p-4 text-left text-sm rounded-xl border border-border bg-card hover:bg-accent hover:border-primary/30 transition-all duration-200 group"
                  >
                    <p className="font-medium mb-1 group-hover:text-primary transition-colors">{q}</p>
                    <p className="text-xs text-muted-foreground opacity-70">Click to try this prompt</p>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="pb-32">
              {messages.map((msg, i) => (
                <ChatMessage key={i} index={i} role={msg.role as "user" | "assistant"} content={msg.content} userName={user?.name} />
              ))}
              {isTyping && <TypingIndicator />}
              <div ref={scrollRef} />
            </div>
          )}
        </div>

        {/* Input Area */}
        <div className="absolute bottom-0 left-0 right-0 p-4 bg-gradient-to-t from-background via-background to-transparent pt-10">
          <div className="max-w-4xl mx-auto space-y-4">
            {/* Suggestions */}
            {suggestedReplies.length > 0 && !isLoading && (
              <div className="flex flex-wrap gap-2 justify-center animate-in fade-in slide-in-from-bottom-2">
                {suggestedReplies.map((reply, i) => (
                  <button
                    key={i}
                    onClick={() => sendMessage(reply)}
                    className="px-3 py-1.5 rounded-full bg-secondary border border-border text-xs hover:border-primary/30 hover:bg-primary/5 transition-all"
                  >
                    {reply}
                  </button>
                ))}
              </div>
            )}

            {/* Input Field */}
            <div className="relative group">
              <div className="relative flex gap-2 p-1.5 rounded-2xl bg-background border border-border shadow-xl shadow-black/5">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Ask NexusAI anything..."
                  onKeyDown={(e) => e.key === "Enter" && sendMessage(input)}
                  className="flex-1 bg-transparent border-none focus-visible:ring-0 text-sm h-12 px-4 placeholder:text-muted-foreground/50"
                  disabled={isLoading}
                />
                <Button 
                  onClick={() => sendMessage(input)} 
                  disabled={isLoading || !input.trim()}
                  className="h-12 w-12 rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 shadow-lg glow-primary shrink-0 transition-transform active:scale-95"
                >
                  <Send className="w-5 h-5" />
                </Button>
              </div>
            </div>
            
            <p className="text-[10px] text-center text-muted-foreground opacity-50 font-medium">
              NexusAI can make mistakes. Consider checking important info.
            </p>
          </div>
        </div>
      </main>

      {/* Support Floating Button */}
      <button
        onClick={() => setIsSupportOpen(!isSupportOpen)}
        className="fixed bottom-6 right-6 w-14 h-14 rounded-2xl bg-primary text-primary-foreground shadow-2xl flex items-center justify-center z-50 hover:scale-110 active:scale-95 transition-all glow-primary"
      >
        {isSupportOpen ? <X className="w-6 h-6" /> : <Headset className="w-6 h-6" />}
      </button>

      {/* Support Widget */}
      {isSupportOpen && (
        <SupportWidget 
          sessionId={activeChat || guestSupportId} 
          onClose={() => setIsSupportOpen(false)} 
        />
      )}

      {/* Login Prompt Modal */}
      {showLoginPrompt && <LoginPrompt />}
    </div>
  );
};

export default ConnectedIndex;
