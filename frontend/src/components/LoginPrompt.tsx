import { useEffect, useRef } from "react";
import { useAuth } from "@/contexts/AuthContext";
import { X } from "lucide-react";

const LoginPrompt = () => {
  const { dismissPrompt, gisReady, renderGoogleButton } = useAuth();
  const googleBtnRef = useRef<HTMLDivElement>(null);

  // Render the official Google Sign-In button when GIS is ready
  useEffect(() => {
    if (gisReady && googleBtnRef.current) {
      renderGoogleButton(googleBtnRef.current);
    }
  }, [gisReady, renderGoogleButton]);

  return (
    <div className="fixed inset-0 z-[100] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={dismissPrompt}
      />

      {/* Card */}
      <div className="relative z-10 w-full max-w-sm mx-4 animate-in fade-in zoom-in-95 duration-300">
        <div className="bg-white rounded-2xl shadow-2xl border border-border/50 overflow-hidden">
          {/* Header accent */}
          <div className="h-1.5 bg-gradient-to-r from-primary via-blue-500 to-primary" />

          <div className="p-6 text-center">
            {/* Close button */}
            <button
              onClick={dismissPrompt}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            >
              <X className="w-4 h-4" />
            </button>

            {/* Icon */}
            <div className="w-14 h-14 rounded-2xl bg-primary/10 flex items-center justify-center mx-auto mb-4">
              <svg className="w-7 h-7 text-primary" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M15 3h4a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-4" />
                <polyline points="10 17 15 12 10 7" />
                <line x1="15" y1="12" x2="3" y2="12" />
              </svg>
            </div>

            <h3 className="text-lg font-semibold mb-1.5">Sign in for a better experience</h3>
            <p className="text-sm text-muted-foreground mb-6 leading-relaxed">
              Sign in with Google to save your chat history and personalize your experience.
            </p>

            <div className="flex flex-col items-center gap-4">
              {/* Official Google Sign-In button renders here */}
              {gisReady ? (
                <div ref={googleBtnRef} className="flex justify-center" />
              ) : (
                <div className="text-xs text-muted-foreground py-3 flex items-center gap-2">
                  <div className="w-4 h-4 border-2 border-primary/30 border-t-primary rounded-full animate-spin" />
                  Loading Google Sign-In...
                </div>
              )}

              <button
                onClick={dismissPrompt}
                className="w-full py-2.5 px-4 rounded-xl bg-secondary text-foreground/80 font-medium text-sm hover:bg-secondary/80 transition-all"
              >
                No, thanks
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default LoginPrompt;
