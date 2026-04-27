# NexusAI Project Setup & Installation Guide

This guide provides step-by-step instructions for installing and running the NexusAI project, which consists of three main components: **Ollama (AI Engine)**, **Backend (Python FastAPI)**, and **Frontend (React)**.

---

## Part 1: Install & Set Up Ollama

Ollama is the local AI engine that powers NexusAI.

### 1. Download and Install Ollama
1. Go to the official Ollama website: [https://ollama.com/download](https://ollama.com/download)
2. Choose your operating system (Windows, macOS, or Linux).
3. Download the installer and run it.

### 2. Verify Installation
1. Open a terminal (Command Prompt, PowerShell, or Terminal).
2. Run the following command to check if Ollama is installed:
   ```bash
   ollama --version
   ```

### 3. Download the AI Model
NexusAI requires an AI model to generate responses. By default, it expects **llama3.2**.
1. In your terminal, run the following command to download the model:
   ```bash
   ollama pull llama3.2
   ```
   *(Note: This might take a few minutes as the model is several gigabytes in size).*
  
  ollama start : ollama run llama3.2 
---

## Part 2: Install & Set Up the Backend

The backend handles API requests, database interactions, and communicates with Ollama.

### 1. Install Python
1. Download **Python 3.10+** from [python.org](https://www.python.org/downloads/).
2. **Crucial**: During installation, make sure to check the box that says **"Add Python to PATH"**.

### 2. Set Up the Project
1. Open a terminal and navigate to the `backend` folder inside the project:
   ```bash
   cd path/to/chatbot/backend
   ```
2. Create a virtual environment to isolate the dependencies:
   ```bash
   python -m venv venv
   ```
3. Activate the virtual environment:
   - **Windows**: `venv\Scripts\activate`
   - **Mac/Linux**: `source venv/bin/activate`
4. Install all the required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Start the Backend Server
Make sure your virtual environment is still activated!
```bash
backend start : 
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```
*The backend should now be running at `http://localhost:8000`.*

---

## Part 3: Install & Set Up the Frontend

The frontend is the React-based user interface you see in your browser.

### 1. Install Node.js
1. Download and install **Node.js (LTS version)** from [nodejs.org](https://nodejs.org/).
2. Verify the installation by running:
   ```bash
   node -v
   npm -v
   ```

### 2. Install Project Dependencies
1. Open a *new* terminal window (leave the backend running).
2. Navigate to the frontend folder:
   ```bash
   cd path/to/chatbot/sparkle-ai-room-main
   ```
3. Install all the necessary packages:
   ```bash
   npm install
   ```

### 3. Start the Frontend Server
```bash
frontend start: 
    
    npm run dev
    
```
*The application should now be available at `http://localhost:8080` or `http://localhost:5173` depending on your Vite configuration.*

---

## Part 4: Easy One-Command Startup (Recommended)

To avoid manually opening multiple terminals every time you want to work on the project, you can use the automated startup script!

### Starting Everything Automatically
1. Open a terminal in the root `chatbot` folder.
2. Run the `start_all.sh` script:
   ```bash
   ./start_all.sh
   ```

**What this script does:**
1. Starts the **Ollama** application automatically.
2. Starts the **Python Backend** in the background on port `8000`.
3. Starts the **React Frontend** in the background on port `8080`.

To stop all services simultaneously, simply press `Ctrl+C` in the terminal where you ran the script.

---

## Network Configuration (Using on other laptops)

If you want to access the chatbot from a mobile phone or another laptop on the same Wi-Fi network:

1. **Find your host IP Address:** (e.g., `192.168.0.40`).
2. **Update Backend `.env`**: Make sure your IP is in `CLIENT_ORIGINS`.
   ```env
   CLIENT_ORIGINS=http://localhost:5173,http://localhost:8080,http://192.168.0.40:8080
   ```
3. **Update Frontend `.env`**: Make sure `VITE_API_BASE_URL` points to your IP.
   ```env
   VITE_API_BASE_URL=http://192.168.0.40:8000
   ```
4. Restart the backend and frontend servers for the changes to take effect.
5. On the other laptop, open a browser and type: `http://192.168.0.40:8080`
