import { Bot, User, Copy, Check } from "lucide-react";
import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";

interface ChatMessageProps {
  role: "user" | "assistant";
  content: string;
  index: number;
}

const ChatMessage = ({ role, content, index }: ChatMessageProps) => {
  const [copied, setCopied] = useState(false);
  const isUser = role === "user";

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Memoize markdown rendering to avoid re-parsing on every render
  const renderedContent = useMemo(() => {
    if (isUser) {
      return <p className="whitespace-pre-wrap">{content}</p>;
    }

    return (
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // Style code blocks
          pre: ({ children, ...props }) => (
            <pre
              className="bg-background/60 rounded-lg p-3 my-2 overflow-x-auto text-xs border border-border/30"
              {...props}
            >
              {children}
            </pre>
          ),
          code: ({ children, className, ...props }) => {
            const isInline = !className;
            if (isInline) {
              return (
                <code
                  className="bg-primary/10 text-primary px-1.5 py-0.5 rounded text-xs font-mono"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <code className={cn("text-xs font-mono", className)} {...props}>
                {children}
              </code>
            );
          },
          // Style lists
          ul: ({ children, ...props }) => (
            <ul className="list-disc list-inside space-y-1 my-2" {...props}>{children}</ul>
          ),
          ol: ({ children, ...props }) => (
            <ol className="list-decimal list-inside space-y-1 my-2" {...props}>{children}</ol>
          ),
          // Style headings
          h1: ({ children, ...props }) => (
            <h1 className="text-lg font-bold mt-3 mb-1" {...props}>{children}</h1>
          ),
          h2: ({ children, ...props }) => (
            <h2 className="text-base font-semibold mt-3 mb-1" {...props}>{children}</h2>
          ),
          h3: ({ children, ...props }) => (
            <h3 className="text-sm font-semibold mt-2 mb-1" {...props}>{children}</h3>
          ),
          // Style blockquotes
          blockquote: ({ children, ...props }) => (
            <blockquote
              className="border-l-2 border-primary/30 pl-3 my-2 text-muted-foreground italic"
              {...props}
            >
              {children}
            </blockquote>
          ),
          // Style tables
          table: ({ children, ...props }) => (
            <div className="overflow-x-auto my-2">
              <table className="min-w-full text-xs border border-border/30 rounded" {...props}>
                {children}
              </table>
            </div>
          ),
          th: ({ children, ...props }) => (
            <th className="px-3 py-1.5 bg-secondary text-left font-medium border-b border-border/30" {...props}>
              {children}
            </th>
          ),
          td: ({ children, ...props }) => (
            <td className="px-3 py-1.5 border-b border-border/20" {...props}>{children}</td>
          ),
          // Style links
          a: ({ children, ...props }) => (
            <a
              className="text-primary hover:underline"
              target="_blank"
              rel="noopener noreferrer"
              {...props}
            >
              {children}
            </a>
          ),
          // Style paragraphs
          p: ({ children, ...props }) => (
            <p className="my-1 leading-relaxed" {...props}>{children}</p>
          ),
          // Style horizontal rules
          hr: ({ ...props }) => <hr className="border-border/30 my-3" {...props} />,
          // Style strong/bold
          strong: ({ children, ...props }) => (
            <strong className="font-semibold text-foreground" {...props}>{children}</strong>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    );
  }, [content, isUser]);

  return (
    <div
      className="animate-fade-in-up group"
      style={{ animationDelay: `${index * 50}ms` }}
    >
      <div className={cn("flex gap-4 px-4 py-5 max-w-4xl mx-auto", isUser && "flex-row-reverse")}>
        {/* Avatar */}
        <div className={cn(
          "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 mt-0.5",
          isUser
            ? "bg-accent/20 text-accent"
            : "bg-primary/10 text-primary glow-primary"
        )}>
          {isUser ? <User className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
        </div>

        {/* Content */}
        <div className={cn("flex-1 space-y-2", isUser && "text-right")}>
          <p className="text-[11px] font-medium text-muted-foreground">
            {isUser ? "You" : "NexusAI"}
          </p>
          <div className={cn(
            "inline-block text-sm leading-relaxed rounded-2xl px-4 py-3 max-w-[min(100%,52rem)] text-left",
            isUser
              ? "bg-accent/15 text-foreground rounded-tr-sm"
              : "bg-secondary text-foreground rounded-tl-sm prose-sm"
          )}>
            {renderedContent}
          </div>

          {/* Actions */}
          {!isUser && (
            <div className="opacity-0 group-hover:opacity-100 transition-opacity">
              <button onClick={handleCopy} className="text-muted-foreground hover:text-foreground transition-colors p-1">
                {copied ? <Check className="w-3.5 h-3.5 text-primary" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ChatMessage;
