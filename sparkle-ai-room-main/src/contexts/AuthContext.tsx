import React, { createContext, useContext, useState, useEffect, useCallback, useRef } from "react";
import { toast } from "sonner";

// ── User type (no backend dependency) ──
export interface AuthUser {
  name: string;
  email: string;
  picture?: string;
}

interface AuthContextType {
  user: AuthUser | null;
  admin: AuthUser | null;
  login: () => void;
  logout: () => void;
  showLoginPrompt: boolean;
  dismissPrompt: () => void;
  gisReady: boolean;
  renderGoogleButton: (container: HTMLElement) => void;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  admin: null,
  login: () => {},
  logout: () => {},
  showLoginPrompt: false,
  dismissPrompt: () => {},
  gisReady: false,
  renderGoogleButton: () => {},
});

export const useAuth = () => useContext(AuthContext);

const USER_STORAGE_KEY = "nexus_auth_user";
const ADMIN_STORAGE_KEY = "nexus_auth_admin";
const PROMPT_INTERVAL_MS = 2 * 60 * 1000; // 2 minutes

// Google Client ID from env (public value, safe to embed in frontend)
const GOOGLE_CLIENT_ID =
  (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined) || "";

/**
 * Decode a JWT payload without verification.
 * Google ID tokens are standard JWTs — the payload has name, email, picture.
 * Verification happens on the backend when the user actually sends messages.
 */
function decodeJwtPayload(token: string): Record<string, any> {
  const parts = token.split(".");
  if (parts.length !== 3) throw new Error("Invalid JWT");
  const payload = parts[1].replace(/-/g, "+").replace(/_/g, "/");
  return JSON.parse(atob(payload));
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<AuthUser | null>(() => {
    try {
      const stored = localStorage.getItem(USER_STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [admin, setAdmin] = useState<AuthUser | null>(() => {
    try {
      const stored = localStorage.getItem(ADMIN_STORAGE_KEY);
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [showLoginPrompt, setShowLoginPrompt] = useState(false);
  const [gisReady, setGisReady] = useState(false);
  const promptTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const handleGoogleResponseRef = useRef<(resp: any) => void>(() => {});

  // Keep the callback ref up to date so it always closes over latest state
  handleGoogleResponseRef.current = (response: { credential?: string }) => {
    const idToken = response?.credential;
    if (!idToken) {
      toast.error("No Google token received");
      return;
    }
    try {
      // Decode user info directly from Google's ID token (JWT)
      const payload = decodeJwtPayload(idToken);
      const authUser: AuthUser = {
        name: payload.name || payload.email || "User",
        email: payload.email || "",
        picture: payload.picture || undefined,
      };
      
      if (window.location.pathname.startsWith('/admin')) {
        setAdmin(authUser);
        localStorage.setItem(ADMIN_STORAGE_KEY, JSON.stringify(authUser));
        toast.success(`Welcome Admin, ${authUser.name}!`);
      } else {
        setUser(authUser);
        localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(authUser));
        setShowLoginPrompt(false);
        toast.success(`Welcome, ${authUser.name}!`);
      }
    } catch (err: any) {
      console.error("Failed to decode Google token:", err);
      toast.error("Google login failed");
    }
  };

  // ── Initialize Google Identity Services ──
  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) {
      console.error("VITE_GOOGLE_CLIENT_ID is not set in .env");
      return;
    }

    let cancelled = false;

    const init = async () => {
      // Wait for GIS library to load (from the <script> in index.html)
      const waitForGis = () =>
        new Promise<boolean>((resolve) => {
          if (window.google?.accounts?.id) return resolve(true);
          const interval = setInterval(() => {
            if (window.google?.accounts?.id) {
              clearInterval(interval);
              resolve(true);
            }
          }, 300);
          setTimeout(() => { clearInterval(interval); resolve(false); }, 10000);
        });

      const gisLoaded = await waitForGis();
      if (cancelled || !gisLoaded) {
        console.warn("Google Identity Services library did not load");
        return;
      }

      // Initialize GIS with the client ID from env
      window.google!.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: (resp: any) => handleGoogleResponseRef.current(resp),
        auto_select: false,
      });

      setGisReady(true);
    };

    init();
    return () => { cancelled = true; };
  }, []);

  // ── Periodic login prompt (only when not logged in) ──
  useEffect(() => {
    if (user) {
      if (promptTimerRef.current) clearInterval(promptTimerRef.current);
      setShowLoginPrompt(false);
      return;
    }

    promptTimerRef.current = setInterval(() => {
      // Don't show login prompt on admin page
      if (window.location.pathname.startsWith('/admin')) return;
      setShowLoginPrompt(true);
    }, PROMPT_INTERVAL_MS);

    return () => {
      if (promptTimerRef.current) clearInterval(promptTimerRef.current);
    };
  }, [user]);

  // ── Render Google button into a container element ──
  const renderGoogleButton = useCallback((container: HTMLElement) => {
    if (!gisReady || !window.google?.accounts?.id) return;
    container.innerHTML = "";
    window.google.accounts.id.renderButton(container, {
      type: "standard",
      size: "large",
      theme: "outline",
      text: "sign_in_with",
      shape: "rectangular",
      width: 320,
    });
  }, [gisReady]);

  // ── Login: show the prompt modal (which contains the Google button) ──
  const login = useCallback(() => {
    setShowLoginPrompt(true);
  }, []);

  // ── Logout ──
  const logout = useCallback(() => {
    if (window.location.pathname.startsWith('/admin')) {
      setAdmin(null);
      localStorage.removeItem(ADMIN_STORAGE_KEY);
    } else {
      setUser(null);
      localStorage.removeItem(USER_STORAGE_KEY);
    }
    toast.success("Logged out successfully");
  }, []);

  // ── Dismiss prompt ──
  const dismissPrompt = useCallback(() => {
    setShowLoginPrompt(false);
  }, []);

  return (
    <AuthContext.Provider value={{ user, admin, login, logout, showLoginPrompt, dismissPrompt, gisReady, renderGoogleButton }}>
      {children}
    </AuthContext.Provider>
  );
};

// Extend window for Google GIS types
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: any) => void;
          prompt: (callback?: (notification: any) => void) => void;
          renderButton: (parent: HTMLElement, config: any) => void;
          revoke: (hint: string, callback: () => void) => void;
        };
      };
    };
  }
}
