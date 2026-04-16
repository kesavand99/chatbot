# College Project Report: NexusAI - Intelligent Chatbot System

---

## Chapter 1: Introduction
### 1.1 Project Overview
NexusAI is a production-grade, full-stack intelligent chatbot application designed to facilitate seamless interaction between users and an LLM-powered assistant. The system provides a real-time, responsive interface with features including chat history management, administrative support integration, and cross-device network accessibility.

### 1.2 Objectives
*   **Real-time Communication**: Utilizing WebSockets for low-latency, streaming AI responses.
*   **Persistent Storage**: Implementing a robust database layer to preserve user conversations.
*   **Scalable Architecture**: Designing a decoupled frontend and backend for independent scaling.
*   **Network Accessibility**: Enabling multi-device access within a local area network (LAN).
*   **User Experience**: Providing a modern, accessible UI with features like typing indicators and markdown rendering.

### 1.3 Key Features
*   **AI Workspace**: A clean, focused interface for interacting with the AI.
*   **Streaming Responses**: Real-time content delivery for a natural conversational feel.
*   **Admin Panel**: Specialized interface for administrators to monitor and manage support tickets.
*   **Responsive Design**: Mobile-first approach using Tailwind CSS and Radix UI.
*   **Support System**: Integrated widget for users to request human assistance.

---

## Chapter 2: System Architecture & Technologies
### 2.1 Backend Architecture
The backend is built with **FastAPI**, a modern, high-performance web framework for Python.
*   **Asynchronous Processing**: Leveraging Python's `asyncio` for efficient concurrent handling of WebSocket connections.
*   **Database**: **MongoDB** is used for its flexible schema-less structure, ideal for storing varied conversational data.
*   **API Design**: RESTful endpoints for CRUD operations (chats, rename, delete) and WebSocket protocols for the chat engine.

### 2.2 Frontend Architecture
The frontend is a modern **React** application built with **Vite** and **TypeScript**.
*   **State Management**: React Hooks (`useState`, `useEffect`, `useRef`) for local state and UI logic.
*   **UI Components**: **Shadcn/UI** (based on Radix UI) provides accessible, high-quality components.
*   **Styling**: **Tailwind CSS** for a utility-first, highly customizable design.
*   **API Interaction**: Custom fetch wrappers and WebSocket handlers in `chat-api.ts`.

### 2.3 Technology Stack Summary
*   **Language**: Python 3.10+, TypeScript 5.0+
*   **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons, React Markdown.
*   **Backend**: FastAPI, Uvicorn, Motor (Async MongoDB Driver), Pydantic.
*   **Database**: MongoDB (Atlas or Local).

---

## Chapter 3: Implementation Details
### 3.1 Real-time Chat Engine
The core of the application is the WebSocket handler in `app/api/routes.py`. When a user sends a message:
1.  The client establishes a WebSocket connection using a unique `session_id`.
2.  The backend receives the JSON payload.
3.  The `ChatService` streams chunks of the AI response back to the client.
4.  The frontend dynamically updates the `messages` state, appending new text chunks to the last assistant message.

### 3.2 Typing Indicator & UX
To improve perceived performance, a `TypingIndicator` component was implemented.
*   **Logic**: It triggers immediately upon sending a message and is hidden as soon as the first "chunk" of data arrives from the server.
*   **Animations**: CSS `@keyframes` handle the "bouncing dots" effect, providing visual feedback that the AI is processing the request.

### 3.3 Database Schema (Pydantic Models)
Conversations are stored as documents in MongoDB with the following structure:
*   `session_id`: Unique identifier (UUID).
*   `messages`: Array of message objects (role, content, timestamp).
*   `metadata`: Title, creation date, and last update time for sidebar listing.

---

## Chapter 4: Network & Security Configuration
### 4.1 Cross-Origin Resource Sharing (CORS)
Since the frontend and backend run on different ports (and potentially different IPs), CORS is strictly configured in `app/main.py` using `CORSMiddleware`. This prevents unauthorized domains from accessing the API while allowing trusted network IPs.

### 4.2 Local Network Deployment
To support "Other Laptop" access:
*   **Binding**: The backend server is bound to `0.0.0.0` instead of `127.0.0.1`.
*   **Service Discovery**: Environment variables (`.env`) are used to point the frontend to the host machine's specific LAN IP (e.g., `192.168.0.40`).
*   **Vite Host**: The Vite dev server is configured with `host: "::"` to broadcast the UI across the network.

---

## Chapter 5: Conclusion & Future Scope
### 5.1 Project Status
The project successfully meets all primary objectives, providing a functional, multi-user AI chat environment that is accessible across a local network.

### 5.2 Challenges Overcome
*   **WebSocket Stability**: Managing connection closures and error states gracefully.
*   **IP Synchronization**: Handling dynamic IP changes in local development environments.
*   **Performance**: Optimizing React renders during high-frequency streaming updates.

### 5.3 Future Enhancements
*   **Authentication**: Adding a user login system (JWT) for private chat histories.
*   **Multi-Model Support**: Allowing users to switch between different LLMs (e.g., GPT-4, Llama 3, Claude).
*   **File Uploads**: Enabling RAG (Retrieval-Augmented Generation) so users can chat with their documents (PDFs, TXT).
*   **Voice Interface**: Integrating speech-to-text and text-to-speech for hands-free interaction.
