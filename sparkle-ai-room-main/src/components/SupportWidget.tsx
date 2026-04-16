import { useState, useEffect, useRef } from "react";
import { X, Send, Headset, ChevronRight, Cpu, Zap, ChevronLeft } from "lucide-react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import { Card } from "./ui/card";
import { fetchSupportMessages, sendSupportMessage, type ApiMessage } from "@/lib/chat-api";
import { toast } from "sonner";

interface SupportWidgetProps {
  sessionId: string;
  onClose: () => void;
}

interface MenuItem {
  id: string;
  label: string;
  icon?: React.ReactNode;
  content?: string;
  subItems?: MenuItem[];
  escalate?: boolean;
}

const SUPPORT_FLOW: MenuItem[] = [
  {
    id: "tech",
    label: "Project Technology",
    icon: <Cpu className="w-4 h-4" />,
    subItems: [
      { id: "ai", label: "AI Engine", content: "Built using Ollama with Llama 3.2 running locally for private and free processing." },
      { id: "backend", label: "Backend API", content: "Powered by FastAPI (Python) using asynchronous endpoints for high concurrency." },
      { id: "db", label: "Database", content: "MongoDB Atlas is used for persistent chat storage and session management." },
    ]
  },
  {
    id: "features",
    label: "Key Features",
    icon: <Zap className="w-4 h-4" />,
    subItems: [
      { id: "streaming", label: "Real-time Streaming", content: "Uses WebSockets to stream AI tokens directly to the UI as they are generated." },
      { id: "intent", label: "Intent Detection", content: "A custom 'Fast-Path' layer that detects common questions to give instant replies." },
      { id: "history", label: "Chat History", content: "Automatically saves and restores your conversations from the database." },
    ]
  },
  {
    id: "human",
    label: "Contact Developer",
    icon: <Headset className="w-4 h-4" />,
    escalate: true
  }
];

const SupportWidget = ({ sessionId, onClose }: SupportWidgetProps) => {
  const [view, setView] = useState<"menu" | "chat">("menu");
  const [menuStack, setMenuStack] = useState<MenuItem[][]>([SUPPORT_FLOW]);
  const [selectedItem, setSelectedItem] = useState<MenuItem | null>(null);
  const [typingItem, setTypingItem] = useState<string>("");
  const [messages, setMessages] = useState<ApiMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const currentMenu = menuStack[menuStack.length - 1];

  useEffect(() => {
    if (view === "chat") {
      loadMessages();
      const interval = setInterval(loadMessages, 3000);
      return () => clearInterval(interval);
    }
  }, [sessionId, view]);

  useEffect(() => {
    scrollRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, view, typingItem]);

  const loadMessages = async () => {
    try {
      const data = await fetchSupportMessages(sessionId);
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
      await sendSupportMessage(sessionId, text);
      setMessages([...messages, { role: "user", content: text }]);
    } catch (error) {
      toast.error("Failed to send message");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Card className="fixed bottom-24 right-6 w-[360px] h-[520px] shadow-2xl flex flex-col border-primary/20 animate-in slide-in-from-bottom-5 z-[100] overflow-hidden rounded-2xl bg-background/95 backdrop-blur-xl">
      <div className="p-4 border-b bg-primary text-primary-foreground flex justify-between items-center">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-white/20 flex items-center justify-center backdrop-blur-md">
            <Headset className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="text-sm font-bold tracking-tight">Nexus Support</div>
            <div className="text-[10px] opacity-80 italic">College Project v1.0</div>
          </div>
        </div>
        <Button variant="ghost" size="icon" className="h-8 w-8 text-white hover:bg-white/10" onClick={onClose}>
          <X className="w-4 h-4" />
        </Button>
      </div>

      <div className="flex-1 overflow-hidden flex flex-col bg-accent/5">
        {view === "menu" ? (
          <ScrollArea className="flex-1 p-4">
            <div className="space-y-4">
              {(menuStack.length > 1 || selectedItem) && (
                <Button variant="ghost" size="sm" onClick={goBack} className="h-7 text-[10px] px-2 -ml-1 text-muted-foreground hover:text-primary">
                  ← Back
                </Button>
              )}

              {selectedItem ? (
                <div className="space-y-4 animate-in fade-in slide-in-from-right-2">
                  <div className="p-4 rounded-xl border bg-card shadow-sm">
                    <h4 className="font-bold text-sm mb-2 text-primary">{selectedItem.label}</h4>
                    <p className="text-xs text-muted-foreground leading-relaxed whitespace-pre-wrap min-h-[60px]">
                      {typingItem}
                      <span className="w-1.5 h-3 bg-primary/40 inline-block ml-1 animate-pulse" />
                    </p>
                  </div>
                  <Button variant="outline" className="w-full text-xs h-9 rounded-xl" onClick={() => setView("chat")}>
                    Still need help? Talk to Admin
                  </Button>
                </div>
              ) : (
                <div className="space-y-2 animate-in fade-in slide-in-from-left-2">
                  <div className="mb-4">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-muted-foreground ml-1">
                      {menuStack.length === 1 ? "Main Menu" : "Select Topic"}
                    </h3>
                  </div>
                  {currentMenu.map((item) => (
                    <button
                      key={item.id}
                      onClick={() => handleMenuClick(item)}
                      className="w-full flex items-center justify-between p-3 rounded-xl border bg-background hover:bg-accent hover:border-primary/30 transition-all group"
                    >
                      <div className="flex items-center gap-3">
                        <div className="text-primary group-hover:scale-110 transition-transform">
                          {item.icon || <ChevronRight className="w-4 h-4" />}
                        </div>
                        <span className="text-sm font-medium">{item.label}</span>
                      </div>
                      {item.subItems && <ChevronRight className="w-4 h-4 text-muted-foreground" />}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </ScrollArea>
        ) : (
          <>
            <ScrollArea className="flex-1 p-4">
              <div className="space-y-4">
                <div className="flex justify-start">
                    <div className="bg-muted p-3 rounded-2xl rounded-tl-none text-xs text-foreground max-w-[85%] border shadow-sm">
                        Hello! Describe your issue or ask a question for the admin.
                    </div>
                </div>
                {messages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                    <div className={`max-w-[85%] p-3 rounded-2xl text-xs ${
                      msg.role === "user" 
                        ? "bg-primary text-primary-foreground rounded-tr-none shadow-md" 
                        : "bg-background text-foreground rounded-tl-none border shadow-sm"
                    }`}>
                      {msg.content}
                    </div>
                  </div>
                ))}
                <div ref={scrollRef} />
              </div>
            </ScrollArea>
            <div className="p-3 border-t bg-background">
              <div className="flex gap-2">
                <Input 
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  placeholder="Message for admin..."
                  onKeyDown={(e) => e.key === "Enter" && handleSend()}
                  className="flex-1 h-9 text-xs rounded-xl"
                  disabled={isLoading}
                />
                <Button size="icon" className="h-9 w-9 rounded-xl" onClick={handleSend} disabled={isLoading || !input.trim()}>
                  <Send className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </>
        )}
      </div>
    </Card>
  );
};

export default SupportWidget;
