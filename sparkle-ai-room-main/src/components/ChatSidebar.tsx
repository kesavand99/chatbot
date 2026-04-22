import { Plus, MessageSquare, Trash2, Bot, Search, X, LogIn, LogOut } from "lucide-react";
import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";

interface Chat {
  id: string;
  title: string;
  date: string;
}

interface ChatSidebarProps {
  chats: Chat[];
  activeChat: string;
  onSelectChat: (id: string) => void;
  onNewChat: () => void;
  onDeleteChat: (id: string) => void;
  isOpen: boolean;
  userName?: string;
  userEmail?: string;
  isLoggedIn?: boolean;
  onLogin?: () => void;
  onLogout?: () => void;
}

const ChatSidebar = ({ chats, activeChat, onSelectChat, onNewChat, onDeleteChat, isOpen, userName, userEmail, isLoggedIn, onLogin, onLogout }: ChatSidebarProps) => {
  const [searchQuery, setSearchQuery] = useState("");

  const filteredChats = useMemo(() => {
    if (!searchQuery.trim()) return chats;
    const q = searchQuery.toLowerCase();
    return chats.filter((chat) => chat.title.toLowerCase().includes(q));
  }, [chats, searchQuery]);

  const userInitial = userName ? userName.charAt(0).toUpperCase() : "?";

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-full w-72 border-r border-border bg-slate-50 transition-transform duration-300 flex flex-col",
        isOpen ? "translate-x-0" : "-translate-x-full",
        "lg:relative lg:translate-x-0"
      )}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-5 py-5 border-b border-border">
        <div className="relative">
          <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center glow-primary">
            <Bot className="w-5 h-5 text-primary" />
          </div>
          <div className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-primary animate-pulse-glow" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-foreground">NexusAI</h1>
          <p className="text-[10px] text-muted-foreground">Intelligent Assistant</p>
        </div>
      </div>

      {/* New Chat Button */}
      <div className="px-3 pt-4 pb-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-3 px-3 py-2.5 rounded-xl bg-card border border-border shadow-sm hover:border-primary/40 hover:shadow-md transition-all duration-200 group"
        >
          <div className="w-8 h-8 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors shrink-0 border border-primary/20">
            <Plus className="w-4 h-4 text-primary" />
          </div>
          <span className="text-sm font-medium text-foreground/90 group-hover:text-primary transition-colors">New Chat</span>
        </button>
      </div>

      {/* Search */}
      <div className="px-3 pb-2">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground/50" />
          <input
            type="text"
            placeholder="Search chats..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full pl-9 pr-8 py-2 rounded-lg bg-secondary/50 border border-border/30 text-xs text-foreground placeholder:text-muted-foreground/50 outline-none focus:border-primary/40 transition-colors"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery("")}
              className="absolute right-2.5 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition-colors"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      </div>

      {/* Chat List */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        <p className="text-[10px] font-medium text-muted-foreground uppercase tracking-wider px-2 py-2">
          {searchQuery ? `Results (${filteredChats.length})` : "Recent"}
        </p>
        {filteredChats.length === 0 && searchQuery && (
          <p className="text-xs text-muted-foreground/60 text-center py-6">
            No chats matching "{searchQuery}"
          </p>
        )}
        {filteredChats.map((chat) => (
          <div
            key={chat.id}
            onClick={() => onSelectChat(chat.id)}
            className={cn(
              "group flex items-start gap-3 px-3 py-3 rounded-xl cursor-pointer transition-all duration-200",
              activeChat === chat.id
                ? "bg-primary/10 text-foreground shadow-[inset_0_0_0_1px_hsl(var(--primary)/0.15)]"
                : "text-muted-foreground hover:bg-secondary hover:text-foreground"
            )}
          >
            <MessageSquare className="w-4 h-4 shrink-0 mt-0.5" />
            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-3">
                <span className="text-sm truncate flex-1">{chat.title}</span>
                <span className="text-[10px] shrink-0 opacity-70">{chat.date}</span>
              </div>
              <p className="text-[10px] mt-1 opacity-70">
                {chat.date === "Draft" ? "Ready for a fresh conversation" : "Open this chat"}
              </p>
            </div>
            <button
              onClick={(e) => { e.stopPropagation(); onDeleteChat(chat.id); }}
              className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition-all mt-0.5"
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>

      {/* Footer */}
      <div className="p-4 border-t border-border space-y-3">
        {/* Auth section */}
        {isLoggedIn ? (
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-primary to-blue-600 flex items-center justify-center text-white text-xs font-bold shrink-0">
              {userInitial}
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs font-medium text-foreground truncate">{userName}</p>
              <p className="text-[10px] text-muted-foreground truncate">{userEmail}</p>
            </div>
            <button
              onClick={onLogout}
              className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-all"
              title="Logout"
            >
              <LogOut className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <button
            onClick={onLogin}
            className="w-full flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-primary/5 border border-primary/20 hover:bg-primary/10 hover:border-primary/30 transition-all group"
          >
            <div className="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center group-hover:bg-primary/20 transition-colors">
              <LogIn className="w-3.5 h-3.5 text-primary" />
            </div>
            <span className="text-xs font-medium text-primary">Sign in with Google</span>
          </button>
        )}

        {/* Status */}
        <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
          <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
          Model Online
        </div>
        <div className="text-[10px] text-muted-foreground/60 space-y-0.5">
          <div className="flex items-center justify-between">
            <span>New chat</span>
            <kbd className="px-1.5 py-0.5 rounded bg-secondary text-[9px] font-mono">Ctrl+N</kbd>
          </div>
          <div className="flex items-center justify-between">
            <span>Toggle sidebar</span>
            <kbd className="px-1.5 py-0.5 rounded bg-secondary text-[9px] font-mono">Ctrl+/</kbd>
          </div>
        </div>
      </div>
    </aside>
  );
};

export default ChatSidebar;

