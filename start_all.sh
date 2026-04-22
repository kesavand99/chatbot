#!/bin/bash

# Function to kill background processes on exit
cleanup() {
    echo "Stopping all services..."
    kill $BACKEND_PID $FRONTEND_PID
    exit
}

trap cleanup SIGINT SIGTERM

echo "Starting Ollama..."
# Check if ollama is already running
if ! pgrep -x "ollama" > /dev/null; then
    ollama serve &
    sleep 2 # wait for it to start
else
    echo "Ollama is already running."
fi

echo "Starting Backend..."
cd backend
# Activate virtual environment and run uvicorn
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
cd ..

echo "Starting Frontend..."
cd sparkle-ai-room-main
npm run dev &
FRONTEND_PID=$!
cd ..

echo "All services are running!"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:8080"
echo "Press Ctrl+C to stop all services."

# Wait for both background processes
wait $BACKEND_PID $FRONTEND_PID
