import { useState, useEffect, useRef } from "react";
import { toast } from "sonner";
import { 
  listPendingAdmin, 
  listResolvedAdmin,
  fetchSupportMessages, 
  answerAsAdmin, 
  closeTicket,
  type ChatSummary, 
  type ApiMessage 
} from "@/lib/chat-api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import ChatMessage from "@/components/ChatMessage";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Card } from "@/components/ui/card";
import { Headset, User } from "lucide-react";

const AdminChat = () => {
  const [pendingChats, setPendingChats] = useState<ChatSummary[]>([]);
  const [selectedSession, setSelectedSession] = useState<string | null>(null);
  const [messages, setMessages] = useState<ApiMessage[]>([]);
  const [reply, setReply] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const [viewMode, setViewMode] = useState<"active" | "history">("active");
  const [historyChats, setHistoryChats] = useState<ChatSummary[]>([]);

  const pendingCountRef = useRef(0);
  const messageCountRef = useRef(0);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 2000); // Polling for snappier feel
    return () => clearInterval(interval);
  }, [viewMode]);

  useEffect(() => {
    if (!selectedSession) return;

    const pollMessages = async () => {
      try {
        const data = await fetchSupportMessages(selectedSession);
        
        // Alert if new message arrived
        if (data.length > messageCountRef.current && messageCountRef.current > 0) {
          const newMsg = data[data.length - 1];
          if (newMsg.role === "user") {
            toast.info("💬 New message from user");
          }
        }
        messageCountRef.current = data.length;

        setMessages(data);
      } catch (error) {
        console.error("Failed to poll support messages");
      }
    };

    pollMessages(); // Initial load
    const interval = setInterval(pollMessages, 3000); // Poll active chat every 3 seconds
    return () => clearInterval(interval);
  }, [selectedSession]);

  const loadData = async () => {
    if (viewMode === "active") {
      try {
        const data = await listPendingAdmin();
        if (data.chats.length > pendingCountRef.current && pendingCountRef.current > 0) {
          toast("🔔 New Support Ticket!", { description: "A user is waiting for assistance." });
        }
        pendingCountRef.current = data.chats.length;
        setPendingChats(data.chats);
      } catch (error) {
        console.error("Failed to load pending chats");
      }
    } else {
      try {
        const data = await listResolvedAdmin();
        setHistoryChats(data.chats);
      } catch (error) {
        console.error("Failed to load resolved chats");
      }
    }
  };

  const selectChat = async (sessionId: string) => {
    setSelectedSession(sessionId);
    try {
      const data = await fetchSupportMessages(sessionId);
      messageCountRef.current = data.length;
      setMessages(data);
    } catch (error) {
      toast.error("Failed to load support history");
    }
  };

  const handleSend = async () => {
    if (!selectedSession || !reply.trim()) return;
    setIsLoading(true);
    try {
      await answerAsAdmin(selectedSession, reply);
      toast.success("Answer sent!");
      setReply("");
      // Update local messages
      messageCountRef.current += 1;
      setMessages([...messages, { role: "admin", content: reply }]);
      loadData();
    } catch (error) {
      toast.error("Failed to send answer");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCloseTicket = async () => {
    if (!selectedSession) return;
    try {
      await closeTicket(selectedSession);
      toast.success("Ticket closed successfully");
      setSelectedSession(null);
      setMessages([]);
      messageCountRef.current = 0;
      loadData();
    } catch (error) {
      toast.error("Failed to close ticket");
    }
  };

  return (
    <div className="flex h-screen bg-background text-foreground">
      {/* Sidebar */}
      <div className="w-80 border-r flex flex-col bg-slate-50">
        <div className="p-6 border-b bg-transparent">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center">
              <Headset className="w-6 h-6 text-primary-foreground" />
            </div>
            <div>
              <h1 className="font-bold text-lg leading-tight">Admin</h1>
              <p className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">Support Center</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" className="flex-1 h-8 text-[10px]" onClick={loadData}>
              Refresh
            </Button>
          </div>
        </div>
        
        <div className="flex bg-muted/20 border-b">
           <button 
             onClick={() => setViewMode("active")}
             className={`flex-1 py-3 text-[10px] font-bold uppercase tracking-wider transition-colors ${viewMode === "active" ? "bg-background border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
           >
             Active ({pendingChats.length})
           </button>
           <button 
             onClick={() => setViewMode("history")}
             className={`flex-1 py-3 text-[10px] font-bold uppercase tracking-wider transition-colors ${viewMode === "history" ? "bg-background border-b-2 border-primary text-primary" : "text-muted-foreground hover:text-foreground"}`}
           >
             History
           </button>
        </div>

        <ScrollArea className="flex-1">
          {viewMode === "active" ? (
            pendingChats.length === 0 ? (
              <div className="p-8 text-muted-foreground text-center animate-in fade-in">
                <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mx-auto mb-3 opacity-50">
                  <User className="w-6 h-6" />
                </div>
                <p className="text-xs font-medium">All clear!</p>
                <p className="text-[10px] opacity-70">No pending support requests.</p>
              </div>
            ) : (
              <div className="divide-y divide-border/40 animate-in fade-in">
                {pendingChats.map((chat) => (
                  <div
                    key={chat.session_id}
                    onClick={() => selectChat(chat.session_id)}
                    className={`p-4 cursor-pointer hover:bg-accent/50 transition-all border-l-4 ${
                      selectedSession === chat.session_id 
                        ? "bg-accent border-l-primary shadow-sm" 
                        : "border-l-transparent"
                    }`}
                  >
                    <div className="flex justify-between items-start mb-1">
                      <div className="font-bold text-sm truncate pr-2">{chat.title || "Support Request"}</div>
                      <div className="text-[9px] text-primary font-bold bg-primary/10 px-1.5 py-0.5 rounded uppercase">NEW</div>
                    </div>
                    <div className="text-[10px] text-muted-foreground flex items-center gap-1">
                      <User className="w-3 h-3" />
                      ID: {chat.session_id.slice(0, 8)}...
                    </div>
                    <div className="text-[9px] text-muted-foreground mt-2 opacity-60">
                      {new Date(chat.updated_at).toLocaleTimeString()}
                    </div>
                  </div>
                ))}
              </div>
            )
          ) : (
            historyChats.length === 0 ? (
              <div className="p-8 text-muted-foreground text-center animate-in fade-in">
                <p className="text-xs font-medium">No History</p>
                <p className="text-[10px] opacity-70">Closed tickets will appear here.</p>
              </div>
            ) : (
              <div className="divide-y divide-border/40 animate-in fade-in">
                {historyChats.map((chat) => (
                  <div
                    key={chat.session_id}
                    onClick={() => selectChat(chat.session_id)}
                    className={`p-4 cursor-pointer hover:bg-accent/50 transition-all border-l-4 ${
                      selectedSession === chat.session_id 
                        ? "bg-accent border-l-primary shadow-sm" 
                        : "border-l-transparent text-muted-foreground hover:text-foreground"
                    }`}
                  >
                    <div className="font-bold text-sm truncate mb-1">{chat.title || "Resolved Ticket"}</div>
                    <div className="text-[10px] flex items-center gap-1 opacity-80">
                      <User className="w-3 h-3" />
                      ID: {chat.session_id.slice(0, 8)}...
                    </div>
                    <div className="text-[9px] mt-2 opacity-60">
                      Closed: {new Date(chat.updated_at).toLocaleDateString()}
                    </div>
                  </div>
                ))}
              </div>
            )
          )}
        </ScrollArea>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-muted/5">
        {selectedSession ? (
          <>
            <div className="p-4 border-b bg-slate-50/80 backdrop-blur-md flex justify-between items-center px-8 shadow-sm">
              <div className="flex items-center gap-4">
                <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center border-2 border-primary/20">
                    <User className="w-5 h-5 text-muted-foreground" />
                </div>
                <div>
                    <div className="font-bold text-sm">Session: {selectedSession.slice(0, 12)}...</div>
                    <div className="flex items-center gap-2">
                        <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                        <span className="text-[10px] text-muted-foreground font-medium">User is Waiting</span>
                    </div>
                </div>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" size="sm" className="h-9 rounded-xl text-xs" onClick={() => setSelectedSession(null)}>
                  Hide
                </Button>
                {viewMode === "active" && (
                  <Button variant="destructive" size="sm" className="h-9 rounded-xl text-xs font-bold" onClick={handleCloseTicket}>
                    Resolve & Close
                  </Button>
                )}
              </div>
            </div>
            
            <ScrollArea className="flex-1 p-8">
              <div className="space-y-6 max-w-3xl mx-auto">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`flex items-start gap-4 ${msg.role === "admin" ? "flex-row-reverse" : ""}`}>
                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center shrink-0 shadow-sm ${
                        msg.role === "admin" ? "bg-gradient-to-br from-primary to-blue-600 text-white" : "bg-muted text-muted-foreground"
                    }`}>
                        {msg.role === "admin" ? <Headset className="w-5 h-5" /> : <User className="w-5 h-5 text-muted-foreground" />}
                    </div>
                    <div className={`flex flex-col ${msg.role === "admin" ? "items-end" : "items-start"}`}>
                        <div className={`p-4 rounded-2xl text-sm leading-relaxed shadow-sm max-w-[500px] min-w-[80px] text-center ${
                            msg.role === "admin" 
                                ? "bg-gradient-to-br from-primary to-blue-600 text-white rounded-tr-none text-left" 
                                : "bg-white text-foreground rounded-tl-none border border-border/50 text-left"
                        }`}>
                            {msg.content}
                        </div>
                        <span className="text-[9px] text-muted-foreground mt-1.5 px-1 font-medium opacity-60 uppercase tracking-tighter">
                            {msg.role === "admin" ? "Agent Response" : "User Message"}
                        </span>
                    </div>
                  </div>
                ))}
              </div>
            </ScrollArea>

            <div className={`p-6 border-t shadow-[0_-4px_20px_-10px_rgba(0,0,0,0.1)] ${viewMode === "active" ? "bg-background" : "bg-muted/30"}`}>
              <div className="max-w-3xl mx-auto">
                {viewMode === "active" ? (
                  <>
                    <div className="relative group">
                        <Input
                          value={reply}
                          onChange={(e) => setReply(e.target.value)}
                          placeholder="Type a professional response to the user..."
                          onKeyDown={(e) => e.key === "Enter" && handleSend()}
                          disabled={isLoading}
                          className="h-14 pl-5 pr-32 text-sm rounded-2xl bg-muted/20 border-muted-foreground/20 focus-visible:ring-primary focus-visible:border-primary transition-all shadow-inner"
                        />
                        <div className="absolute right-2 top-2 bottom-2">
                            <Button 
                                onClick={handleSend} 
                                disabled={isLoading || !reply.trim()}
                                className="h-full px-6 rounded-xl font-bold text-xs shadow-lg shadow-primary/20"
                            >
                              {isLoading ? "Sending..." : "Send Response"}
                            </Button>
                        </div>
                    </div>
                    <p className="text-[10px] text-center text-muted-foreground mt-3 opacity-60">
                        Your response will be instantly visible to the user in their support widget.
                    </p>
                  </>
                ) : (
                  <div className="h-14 flex items-center justify-center rounded-2xl border border-dashed border-muted-foreground/30 text-muted-foreground text-xs font-medium">
                    This ticket is closed. It will reopen if the user replies.
                  </div>
                )}
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center text-muted-foreground">
            Select a chat from the sidebar to respond
          </div>
        )}
      </div>
    </div>
  );
};

export default AdminChat;
