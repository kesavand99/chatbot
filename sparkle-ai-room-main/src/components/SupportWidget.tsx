import { useState, useEffect, useRef } from "react";
import { X, Send, Headset, ChevronRight, Cpu, Zap, ChevronLeft, MessageCircle, HelpCircle, ArrowLeft, Clock } from "lucide-react";

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
import { fetchSupportMessages, sendSupportMessage, formatTimestamp, type ApiMessage } from "@/lib/chat-api";
import { toast } from "sonner";
import { useAuth } from "@/contexts/AuthContext";

interface SupportWidgetProps {
  sessionId: string;
  localChats?: any[];
  onClose: () => void;
  onChatCreated?: () => void;
}

interface MenuItem {
  id: string;
  label: string;
  description?: string;
  icon?: React.ReactNode;
  content?: string;
  subItems?: MenuItem[];
  escalate?: boolean;
}

const SUPPORT_FLOW: MenuItem[] = [
  {
    id: "tech",
    label: "Project Technology",
    description: "Learn about our tech stack",
    icon: <Cpu className="w-5 h-5" />,
    subItems: [
      { id: "ai", label: "AI Engine", content: "Built using Ollama with Llama 3.2 running locally for private and free processing." },
      { id: "backend", label: "Backend API", content: "Powered by FastAPI (Python) using asynchronous endpoints for high concurrency." },
      { id: "db", label: "Database", content: "MongoDB Atlas is used for persistent chat storage and session management." },
    ]
  },
  {
    id: "features",
    label: "Key Features",
    description: "Explore what NexusAI can do",
    icon: <Zap className="w-5 h-5" />,
    subItems: [
      { id: "streaming", label: "Real-time Streaming", content: "Uses WebSockets to stream AI tokens directly to the UI as they are generated." },
      { id: "intent", label: "Intent Detection", content: "A custom 'Fast-Path' layer that detects common questions to give instant replies." },
      { id: "history", label: "Chat History", content: "Automatically saves and restores your conversations from the database." },
    ]
  },
  {
    id: "human",
    label: "Customer Support",
    description: "Chat with our support team",
    icon: <Headset className="w-5 h-5" />,
    escalate: true
  }
];

const SupportWidget = ({ sessionId, localChats, onClose, onChatCreated }: SupportWidgetProps) => {
  const [view, setView] = useState<"menu" | "chat" | "history">("menu");
  const [menuStack, setMenuStack] = useState<MenuItem[][]>([SUPPORT_FLOW]);
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
  const [typingItem, setTypingItem] = useState<string>("");
  const [messages, setMessages] = useState<ApiMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();
  
  const [overrideSessionId, setOverrideSessionId] = useState<string | null>(null);
  const activeSessionId = overrideSessionId || sessionId;

  useEffect(() => {
    setOverrideSessionId(null);
  }, [sessionId]);

  const currentMenu = menuStack[menuStack.length - 1];

  useEffect(() => {
    if (view === "chat") {
      loadMessages();
      const interval = setInterval(loadMessages, 3000);
      return () => clearInterval(interval);
    }
  }, [activeSessionId, view]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, view, typingItem]);

  const loadMessages = async () => {
    try {
      const data = await fetchSupportMessages(activeSessionId);
      setMessages(data);
      if (data.length > 0) setView("chat");
    } catch (error) {
      console.error("Failed to load support messages");
    }
  };

  const handleMenuClick = (item: MenuItem) => {
    if (item.escalate) {
      setView("chat");
      return;
    }

    if (item.subItems) {
      setMenuStack([...menuStack, item.subItems]);
      return;
    }

    // Deliberate "real-time" typing feel for menu answers
    setSelectedItem(item);
    setTypingItem("");
    let i = 0;
    const fullText = item.content || "";
    const interval = setInterval(() => {
      setTypingItem(fullText.slice(0, i + 1));
      i++;
      if (i >= fullText.length) clearInterval(interval);
    }, 15);
  };

  const goBack = () => {
    if (selectedItem) {
      setSelectedItem(null);
    } else if (menuStack.length > 1) {
      setMenuStack(menuStack.slice(0, -1));
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const text = input.trim();
    setInput("");
    setIsLoading(true);
    try {
      await sendSupportMessage(activeSessionId, text, user?.name);
      setMessages([...messages, { role: "user", content: text, timestamp: new Date().toISOString() }]);
      if (messages.length === 0 && onChatCreated) {
        // Now that the session is truly created in DB, force a reload of the sidebar
        onChatCreated();
      }
    } catch (error) {
      toast.error("Failed to send message");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="fixed bottom-24 right-6 w-[370px] h-[540px] flex flex-col z-[100] animate-in slide-in-from-bottom-5 duration-300"
      style={{
        borderRadius: "20px",
        background: "#ffffff",
        boxShadow: "0 20px 60px rgba(0,0,0,0.15), 0 8px 20px rgba(0,0,0,0.08)",
        overflow: "hidden",
        fontFamily: "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif",
      }}
    >
      {/* ── Header ── */}
      <div
        style={{
          background: "linear-gradient(135deg, #0ea5e9 0%, #2563eb 100%)",
          padding: "18px 20px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "42px",
              height: "42px",
              borderRadius: "12px",
              background: "rgba(255,255,255,0.2)",
              backdropFilter: "blur(8px)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <Headset className="w-5 h-5" style={{ color: "#fff" }} />
          </div>
          <div>
            <div style={{ fontSize: "15px", fontWeight: 700, color: "#fff", letterSpacing: "-0.01em" }}>
              Nexus Support
            </div>
            <div style={{ fontSize: "11px", color: "rgba(255,255,255,0.75)", fontStyle: "italic" }}>
              College Project v1.0
            </div>
          </div>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <button
            onClick={() => setView(view === "history" ? "menu" : "history")}
            title="Past Tickets"
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              border: "none",
              background: "rgba(255,255,255,0.15)",
              color: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.3)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.15)")}
          >
            <Clock className="w-4 h-4" />
          </button>
          <button
            onClick={onClose}
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "8px",
              border: "none",
              background: "rgba(255,255,255,0.15)",
              color: "#fff",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              transition: "background 0.2s",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.3)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "rgba(255,255,255,0.15)")}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* ── Body ── */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        {view === "history" ? (
            <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
                <div style={{ fontSize: "14px", fontWeight: 600, color: "#1e293b", marginBottom: "12px" }}>
                    Past Support Tickets
                </div>
                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                    {localChats?.filter(c => c.title.toLowerCase().includes("support") || c.id.startsWith("support_")).map(c => (
                        <div 
                          key={c.id}
                          onClick={() => {
                              setOverrideSessionId(c.id);
                              setView("chat");
                          }}
                          style={{
                              padding: "12px",
                              background: "#f8fafc",
                              borderRadius: "12px",
                              cursor: "pointer",
                              border: "1px solid #e2e8f0",
                              transition: "all 0.2s"
                          }}
                          onMouseEnter={(e) => { e.currentTarget.style.borderColor = "#93c5fd"; e.currentTarget.style.background = "#eff6ff"; }}
                          onMouseLeave={(e) => { e.currentTarget.style.borderColor = "#e2e8f0"; e.currentTarget.style.background = "#f8fafc"; }}
                        >
                            <div style={{ fontSize: "13px", fontWeight: 600, color: "#334155" }}>{c.title}</div>
                            <div style={{ fontSize: "11px", color: "#64748b", marginTop: "4px" }}>
                                {c.date} • {c.id.substring(0,8)}...
                            </div>
                        </div>
                    ))}
                    {(!localChats || localChats.filter(c => c.title.toLowerCase().includes("support") || c.id.startsWith("support_")).length === 0) && (
                        <div style={{ fontSize: "13px", color: "#64748b", textAlign: "center", padding: "32px 0" }}>
                            <Clock className="w-8 h-8 opacity-20 mx-auto mb-3" />
                            No past tickets found.
                        </div>
                    )}
                </div>
            </div>
        ) : view === "menu" ? (
          <div style={{ flex: 1, overflowY: "auto", padding: "16px 16px 20px" }}>
            {/* Back button */}
            {(menuStack.length > 1 || selectedItem) && (
              <button
                onClick={goBack}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                  fontSize: "12px",
                  color: "#64748b",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  padding: "4px 8px",
                  borderRadius: "6px",
                  marginBottom: "12px",
                  marginLeft: "-4px",
                  transition: "color 0.2s, background 0.2s",
                }}
                onMouseEnter={(e) => { e.currentTarget.style.color = "#2563eb"; e.currentTarget.style.background = "#eff6ff"; }}
                onMouseLeave={(e) => { e.currentTarget.style.color = "#64748b"; e.currentTarget.style.background = "none"; }}
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Back
              </button>
            )}

            {selectedItem ? (
              /* ── Detail card ── */
              <div className="animate-in fade-in slide-in-from-right-2" style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
                <div
                  style={{
                    background: "#f8fafc",
                    borderRadius: "14px",
                    border: "1px solid #e2e8f0",
                    padding: "18px",
                  }}
                >
                  <h4 style={{ fontSize: "14px", fontWeight: 700, color: "#2563eb", marginBottom: "10px" }}>
                    {selectedItem.label}
                  </h4>
                  <p style={{ fontSize: "13px", color: "#334155", lineHeight: 1.7, margin: 0, whiteSpace: "pre-wrap" }}>
                    {typingItem}
                    <span
                      style={{
                        width: "6px",
                        height: "14px",
                        background: "#93c5fd",
                        display: "inline-block",
                        marginLeft: "3px",
                        borderRadius: "1px",
                        animation: "pulse 1s infinite",
                      }}
                    />
                  </p>
                </div>
                <button
                  onClick={() => setView("chat")}
                  style={{
                    width: "100%",
                    padding: "10px",
                    borderRadius: "12px",
                    border: "1px solid #e2e8f0",
                    background: "#fff",
                    fontSize: "12px",
                    fontWeight: 600,
                    color: "#2563eb",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                  onMouseEnter={(e) => { e.currentTarget.style.background = "#eff6ff"; e.currentTarget.style.borderColor = "#93c5fd"; }}
                  onMouseLeave={(e) => { e.currentTarget.style.background = "#fff"; e.currentTarget.style.borderColor = "#e2e8f0"; }}
                >
                  💬 Still need help? Talk to Admin
                </button>
              </div>
            ) : (
              /* ── Menu list ── */
              <div className="animate-in fade-in slide-in-from-left-2" style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                <div style={{ marginBottom: "6px", paddingLeft: "2px" }}>
                  <h3 style={{ fontSize: "11px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "#94a3b8", margin: 0 }}>
                    {menuStack.length === 1 ? "How can we help?" : "Select a Topic"}
                  </h3>
                </div>

                {currentMenu.map((item) => (
                  <button
                    key={item.id}
                    onClick={() => handleMenuClick(item)}
                    style={{
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      padding: "14px 16px",
                      borderRadius: "14px",
                      border: "1px solid #e2e8f0",
                      background: "#fff",
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                      textAlign: "left",
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = "#eff6ff";
                      e.currentTarget.style.borderColor = "#93c5fd";
                      e.currentTarget.style.transform = "translateY(-1px)";
                      e.currentTarget.style.boxShadow = "0 4px 12px rgba(37,99,235,0.08)";
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = "#fff";
                      e.currentTarget.style.borderColor = "#e2e8f0";
                      e.currentTarget.style.transform = "translateY(0)";
                      e.currentTarget.style.boxShadow = "none";
                    }}
                  >
                    <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                      <div
                        style={{
                          width: "38px",
                          height: "38px",
                          borderRadius: "10px",
                          background: "#eff6ff",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          color: "#2563eb",
                          flexShrink: 0,
                        }}
                      >
                        {item.icon || <ChevronRight className="w-5 h-5" />}
                      </div>
                      <div>
                        <div style={{ fontSize: "13.5px", fontWeight: 600, color: "#1e293b" }}>{item.label}</div>
                        {item.description && (
                          <div style={{ fontSize: "11px", color: "#94a3b8", marginTop: "2px" }}>{item.description}</div>
                        )}
                      </div>
                    </div>
                    {item.subItems && <ChevronRight className="w-4 h-4" style={{ color: "#cbd5e1" }} />}
                  </button>
                ))}
              </div>
            )}
            <div ref={scrollRef} />
          </div>
        ) : (
          /* ── Chat view ── */
          <>
            <div style={{ flex: 1, overflowY: "auto", padding: "16px" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {/* Welcome message */}
                <div style={{ display: "flex", alignItems: "flex-start", gap: "8px" }}>
                  <div
                    style={{
                      width: "28px",
                      height: "28px",
                      borderRadius: "50%",
                      background: "linear-gradient(135deg, #0ea5e9, #2563eb)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      marginTop: "2px",
                    }}
                  >
                    <Headset className="w-3.5 h-3.5" style={{ color: "#fff" }} />
                  </div>
                  <div
                    style={{
                      background: "#f1f5f9",
                      padding: "10px 14px",
                      borderRadius: "4px 16px 16px 16px",
                      fontSize: "13px",
                      color: "#334155",
                      lineHeight: 1.6,
                      maxWidth: "80%",
                    }}
                  >
                    Hello! 👋 Describe your issue or ask a question for the admin.
                  </div>
                </div>

                {/* Messages */}
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className="flex flex-col gap-1 w-full"
                    style={{ alignItems: msg.role === "user" ? "flex-end" : "flex-start" }}
                  >
                    <div
                      style={{
                        display: "flex",
                        justifyContent: msg.role === "user" ? "flex-end" : "flex-start",
                        alignItems: "flex-start",
                        gap: "8px",
                      }}
                    >
                      {msg.role !== "user" && (
                        <div
                          style={{
                            width: "28px",
                            height: "28px",
                            borderRadius: "50%",
                            background: "linear-gradient(135deg, #0ea5e9, #2563eb)",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            flexShrink: 0,
                            marginTop: "2px",
                          }}
                        >
                          <Headset className="w-3.5 h-3.5" style={{ color: "#fff" }} />
                        </div>
                      )}
                      <div
                        style={{
                          maxWidth: "80%",
                          padding: "10px 14px",
                          fontSize: "13px",
                          lineHeight: 1.6,
                          ...(msg.role === "user"
                            ? {
                                background: "linear-gradient(135deg, #0ea5e9, #2563eb)",
                                color: "#fff",
                                borderRadius: "16px 4px 16px 16px",
                              }
                            : {
                                background: "#f1f5f9",
                                color: "#334155",
                                borderRadius: "4px 16px 16px 16px",
                              }),
                        }}
                      >
                        {msg.content}
                      </div>
                    </div>
                    {msg.timestamp && (
                      <div
                        style={{
                          fontSize: "10px",
                          color: "#94a3b8",
                          marginRight: msg.role === "user" ? "4px" : "0",
                          marginLeft: msg.role !== "user" ? "36px" : "0",
                        }}
                      >
                        {formatTimestamp(msg.timestamp)}
                      </div>
                    )}
                  </div>
                ))}
                <div ref={scrollRef} />
              </div>
            </div>

            {/* ── Chat input / Closed State ── */}
            {messages.some((m) => m.role === "admin" && m.content === "This support ticket has been closed. Thank you!") ? (
              <div style={{ padding: "16px", textAlign: "center", borderTop: "1px solid #f1f5f9" }}>
                <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "12px" }}>
                  This support ticket has been closed.
                </div>
                <button
                  onClick={() => {
                    const newId = "support_" + generateId();
                    try {
                      const localChats = JSON.parse(localStorage.getItem("nexus_local_chats") || "[]");
                      localStorage.setItem("nexus_local_chats", JSON.stringify([newId, ...localChats]));
                    } catch(e) {}
                    
                    setOverrideSessionId(newId);
                    setMessages([]);
                    setView("menu");
                    setMenuStack([SUPPORT_FLOW]);
                    setSelectedItem(null);
                    if (onChatCreated) onChatCreated();
                  }}
                  style={{
                    background: "linear-gradient(135deg, #0ea5e9, #2563eb)",
                    color: "#fff",
                    border: "none",
                    padding: "10px 20px",
                    borderRadius: "12px",
                    fontSize: "14px",
                    fontWeight: 600,
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(14, 165, 233, 0.25)",
                    transition: "all 0.2s ease"
                  }}
                  onMouseOver={(e) => (e.currentTarget.style.transform = "translateY(-1px)")}
                  onMouseOut={(e) => (e.currentTarget.style.transform = "translateY(0)")}
                >
                  Start New Chat
                </button>
              </div>
            ) : (
              <div style={{ padding: "12px 16px 16px", borderTop: "1px solid #f1f5f9" }}>
                <div
                  style={{
                    display: "flex",
                    gap: "8px",
                    alignItems: "center",
                  }}
                >
                  <input
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Type your message..."
                    onKeyDown={(e) => e.key === "Enter" && handleSend()}
                    disabled={isLoading}
                    style={{
                      flex: 1,
                      height: "40px",
                      padding: "0 14px",
                      fontSize: "13px",
                      borderRadius: "12px",
                      border: "1px solid #e2e8f0",
                      background: "#f8fafc",
                      color: "#1e293b",
                      outline: "none",
                      transition: "border-color 0.2s, box-shadow 0.2s",
                    }}
                    onFocus={(e) => {
                      e.currentTarget.style.borderColor = "#93c5fd";
                      e.currentTarget.style.boxShadow = "0 0 0 3px rgba(37,99,235,0.1)";
                    }}
                    onBlur={(e) => {
                      e.currentTarget.style.borderColor = "#e2e8f0";
                      e.currentTarget.style.boxShadow = "none";
                    }}
                  />
                  <button
                    onClick={handleSend}
                    disabled={isLoading || !input.trim()}
                    style={{
                      width: "40px",
                      height: "40px",
                      borderRadius: "12px",
                      border: "none",
                      background: !input.trim() || isLoading
                        ? "#e2e8f0"
                        : "linear-gradient(135deg, #0ea5e9, #2563eb)",
                      color: !input.trim() || isLoading ? "#94a3b8" : "#fff",
                      cursor: !input.trim() || isLoading ? "not-allowed" : "pointer",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                      transition: "all 0.2s",
                    }}
                  >
                    <Send className="w-4 h-4" />
                  </button>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default SupportWidget;
