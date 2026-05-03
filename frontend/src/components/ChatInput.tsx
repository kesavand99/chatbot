import { Send, Paperclip } from "lucide-react";
import { useState, useRef, useEffect } from "react";

interface ChatInputProps {
  onSend: (message: string) => void;
  disabled?: boolean;
}

const ChatInput = ({ onSend, disabled }: ChatInputProps) => {
  const [input, setInput] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 160) + "px";
    }
  }, [input]);

  const handleSubmit = () => {
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border bg-background/80 backdrop-blur-xl">
      <div className="max-w-3xl mx-auto px-4 py-4">
        <div className="relative flex items-end gap-2 glass rounded-2xl px-4 py-3 focus-within:ring-1 focus-within:ring-primary/50 transition-all">
          <button
            type="button"
            className="text-muted-foreground/70 hover:text-foreground transition-colors p-1 mb-0.5"
            aria-label="Attachment placeholder"
          >
            <Paperclip className="w-4 h-4" />
          </button>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={disabled ? "Waiting for connection..." : "Ask anything..."}
            rows={1}
            disabled={disabled}
            className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground resize-none outline-none max-h-40"
          />
          <button
            onClick={handleSubmit}
            disabled={!input.trim() || disabled}
            className="p-2 rounded-lg bg-primary text-primary-foreground disabled:opacity-30 hover:bg-primary/90 transition-all duration-200 mb-0.5 glow-primary disabled:shadow-none"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        <p className="text-[10px] text-center text-muted-foreground mt-2">
          NexusAI can make mistakes. Consider checking important info.
        </p>
      </div>
    </div>
  );
};

export default ChatInput;
