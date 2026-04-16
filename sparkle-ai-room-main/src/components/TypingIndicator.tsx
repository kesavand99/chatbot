import { Bot } from "lucide-react";

const TypingIndicator = () => (
  <div className="flex gap-4 px-4 py-5 max-w-3xl mx-auto animate-fade-in-up">
    <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center shrink-0 glow-primary">
      <Bot className="w-4 h-4" />
    </div>
    <div className="space-y-2">
      <p className="text-[11px] font-medium text-muted-foreground">NexusAI</p>
      <div className="bg-secondary rounded-2xl rounded-tl-sm px-4 py-3 inline-flex gap-1.5">
        <span className="typing-dot w-2 h-2 rounded-full bg-primary" />
        <span className="typing-dot w-2 h-2 rounded-full bg-primary" />
        <span className="typing-dot w-2 h-2 rounded-full bg-primary" />
      </div>
    </div>
  </div>
);

export default TypingIndicator;
