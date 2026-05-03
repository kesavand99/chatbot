import { Bot, Sparkles, Code, Lightbulb, MessageCircle } from "lucide-react";

interface WelcomeScreenProps {
  onSuggestionClick: (text: string) => void;
  disabled?: boolean;
}

const suggestions = [
  { icon: Code, text: "Help me write a Python script", color: "text-[#2dd4bf]" },
  { icon: Lightbulb, text: "Explain quantum computing simply", color: "text-[#fbbf24]" },
  { icon: MessageCircle, text: "Draft a professional email", color: "text-[#2dd4bf]" },
  { icon: Sparkles, text: "Generate creative story ideas", color: "text-[#fbbf24]" },
];

const WelcomeScreen = ({ onSuggestionClick, disabled }: WelcomeScreenProps) => {
  return (
    <div className="flex-1 flex items-center justify-center px-4 py-10">
      <div className="text-center space-y-8 max-w-2xl">
        {/* Animated Logo */}
        <div className="relative inline-block animate-float">
          <div className="w-20 h-20 rounded-2xl bg-primary/10 flex items-center justify-center glow-primary border border-primary/20">
            <Bot className="w-10 h-10 text-[#2dd4bf]" />
          </div>
          <div className="absolute -inset-4 rounded-3xl bg-primary/5 animate-pulse-glow -z-10" />
        </div>

        <div className="space-y-3">
          <h2 className="text-2xl font-semibold text-foreground">
            Start a smarter conversation
          </h2>
          <p className="text-sm text-muted-foreground leading-relaxed">
            I'm NexusAI, your intelligent assistant. Ask me anything — from coding to creative writing.
          </p>
        </div>

        {/* Suggestion Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-left">
          {suggestions.map((s, i) => (
            <button
              key={i}
              onClick={() => onSuggestionClick(s.text)}
              disabled={disabled}
              className="flex items-center gap-3 px-4 py-4 rounded-2xl bg-[#0a0f14]/80 hover:bg-[#0a0f14] border border-sidebar-border/30 hover:border-primary/40 transition-all duration-200 text-left group disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <s.icon className={`w-4 h-4 ${s.color} shrink-0 group-hover:scale-110 transition-transform`} />
              <div className="flex-1 min-w-0">
                <span className="text-sm text-muted-foreground group-hover:text-foreground transition-colors block truncate">{s.text}</span>
                {disabled && <span className="text-[10px] text-primary/60">Connecting...</span>}
              </div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};

export default WelcomeScreen;
