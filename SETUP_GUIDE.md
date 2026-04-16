# Project Setup & Network Configuration Guide

This guide documents the changes made to enable network access (using the app on other laptops) and how to run the project correctly.

## 0. Prerequisites & Installation

Follow these steps to set up the project for the first time:

### Step 1: Install Python
1.  Download and install **Python 3.10+** from [python.org](https://www.python.org/downloads/).
2.  **Crucial**: During installation, check the box that says **"Add Python to PATH"**.
3.  Check if Python and Pip are installed:
    ```bash
    python --version
    pip --version
    ```

### Step 2: Set Up the Backend
1.  Open a terminal and navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Create a virtual environment:
    ```bash
    python -m venv venv
    ```
3.  Activate the virtual environment:
    - **Windows**: `venv\Scripts\activate`
    - **Mac/Linux**: `source venv/bin/activate`
4.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### Step 3: Install Node.js
1.  Download and install **Node.js (LTS version)** from [nodejs.org](https://nodejs.org/).
2.  Check if Node and NPM are installed:
    ```bash
    node -v
    npm -v
    ```

### Step 4: Set Up the Frontend
1.  Navigate to the frontend directory:
    ```bash
    cd sparkle-ai-room-main
    ```
2.  Install dependencies:
    ```bash
    npm install
    ```

---

## 1. IP Address Configuration
The current host IP address is identified as: `192.168.0.40`. All configurations have been updated to use this IP.

### Backend Configuration (`backend/.env`)
The `CLIENT_ORIGINS` were updated to allow the frontend to communicate with the backend from different addresses:
```env
CLIENT_ORIGINS=http://localhost:5173,http://localhost:8080,http://127.0.0.1:8080,http://192.168.0.40:8080
```

### Frontend Configuration (`sparkle-ai-room-main/.env`)
The API base URL was updated to point to the host machine's IP so other devices can reach the backend:
```env
VITE_API_BASE_URL=http://192.168.0.40:8000
```

---

## 2. Running the Project for Network Access

To use the app on other laptops in the same Wi-Fi network, follow these steps:

### Step A: Run the Backend
You **must** use the `--host 0.0.0.0` flag to allow incoming connections from the network.
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Step B: Run the Frontend
Vite is already configured to broadcast on the network.
```bash
cd sparkle-ai-room-main
npm run dev
```

---

## 3. How to Access from Another Laptop

1.  Connect the other laptop to the **same Wi-Fi network**.
2.  Open a web browser.
3.  Enter the following URL:
    `http://192.168.0.40:8080`

---

## 4. Troubleshooting WebSocket Errors
If you see a "WebSocket error" on the other laptop:
1.  **Firewall**: Ensure Windows Firewall isn't blocking port `8000` or `8080`.
2.  **IP Change**: If your router restarts, your IP might change from `192.168.0.40` to something else. Run `ipconfig` to check and update the `.env` files if necessary.
3.  **Restart**: Always restart both `uvicorn` and `npm run dev` after making changes to `.env` files.

---

## 5. Recent Features Added
- **Typing Indicator**: Re-implemented the "NexusAI is typing..." animation that shows while waiting for the AI response.
- **Auto-Hide**: The typing dots now disappear automatically once the AI starts streaming its answer for a smoother experience.
