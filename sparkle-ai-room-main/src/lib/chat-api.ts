const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8000";

const AUTH_BASE_URL =
  (import.meta.env.VITE_AUTH_BASE_URL as string | undefined)?.replace(/\/$/, "") ||
  "http://localhost:8001";

const WS_BASE_URL = API_BASE_URL.replace(/^http/i, "ws");

export interface ApiMessage {
  role: "user" | "assistant" | "admin";
  content: string;
  timestamp?: string;
}

export interface ChatSummary {
  session_id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ChatHistoryResponse {
  session_id: string;
  messages: ApiMessage[];
  suggested_replies: string[];
  is_admin_needed: boolean;
}

export interface ChatSocketResponse {
  type: "chat_response" | "error";
  detail?: string;
  session_id?: string;
  user_message?: ApiMessage;
  assistant_message?: ApiMessage;
  suggested_replies?: string[];
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const errorBody = await response.json().catch(() => ({}));
    throw new Error(errorBody.detail || "Request failed.");
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function listChats() {
  return request<{ chats: ChatSummary[] }>("/chats");
}

export function fetchChatHistory(sessionId: string) {
  return request<ChatHistoryResponse>(`/chat/${sessionId}`);
}

export function deleteChatById(sessionId: string) {
  return request<void>(`/chat/${sessionId}`, { method: "DELETE" });
}

export function createChatSocket(sessionId: string) {
  return new WebSocket(`${WS_BASE_URL}/ws/chat/${sessionId}`);
}

export function listPendingAdmin() {
  return request<{ chats: ChatSummary[] }>("/admin/pending");
}

export function listResolvedAdmin() {
  return request<{ chats: ChatSummary[] }>("/admin/resolved");
}

export function answerAsAdmin(sessionId: string, message: string) {
  return request<{ status: string }>(`/admin/answer/${sessionId}`, {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  });
}

export function closeTicket(sessionId: string) {
  return request<{ status: string }>(`/admin/close/${sessionId}`, {
    method: "POST",
  });
}

export function sendSupportMessage(sessionId: string, message: string, userName?: string) {
  return request<{ status: string }>(`/chat/${sessionId}/support`, {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message, user_name: userName }),
  });
}

export function fetchSupportMessages(sessionId: string) {
  return request<ApiMessage[]>(`/chat/${sessionId}/support`);
}

/** Formats ISO string to 'DD/MM/YYYY hh:mm a/pm' */
export function formatTimestamp(isoString?: string): string {
  if (!isoString) return "";
  const d = new Date(isoString);
  if (isNaN(d.getTime())) return "";
  
  const day = d.getDate().toString().padStart(2, "0");
  const month = (d.getMonth() + 1).toString().padStart(2, "0");
  const year = d.getFullYear();
  
  let hours = d.getHours();
  const minutes = d.getMinutes().toString().padStart(2, "0");
  const ampm = hours >= 12 ? "pm" : "am";
  
  hours = hours % 12;
  hours = hours ? hours : 12; // the hour '0' should be '12'
  
  return `${day}/${month}/${year} ${hours}.${minutes} ${ampm}`;
}

// ─── Auth Service helpers ─────────────────────────────────────
export interface AuthUser {
  name: string;
  email: string;
  token: string;
  userId: string;
}

export async function fetchGoogleConfig(): Promise<{ client_id: string }> {
  const res = await fetch(`${AUTH_BASE_URL}/auth/google/config`);
  if (!res.ok) throw new Error("Failed to fetch Google config");
  return res.json();
}

export async function googleAuthenticate(idToken: string): Promise<AuthUser> {
  const res = await fetch(`${AUTH_BASE_URL}/auth/googleauthentication`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id_token: idToken }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Google authentication failed");
  }
  const json = await res.json();
  const d = json.data;
  return {
    name: [d.first_name, d.last_name].filter(Boolean).join(" ") || d.email,
    email: d.email,
    token: d.access_token,
    userId: d.userId,
  };
}
