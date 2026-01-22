#!/bin/bash
# Energy AI Management System - Startup Script
# This script starts both backend and frontend servers

set -e

echo "======================================================"
echo "  Energy AI Management System - Starting Services"
echo "======================================================"
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found!"
    echo "   Please run: python3 -m venv .venv"
    echo "   Then: source .venv/bin/activate"
    echo "   Then: pip install -r requirements.txt"
    exit 1
fi

# Check if node_modules exists
if [ ! -d "frontend/node_modules" ]; then
    echo "❌ Frontend dependencies not installed!"
    echo "   Please run: cd frontend && npm install"
    exit 1
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "Shutting down services..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✅ Services stopped"
    exit 0
}

trap cleanup INT TERM

echo "🚀 Starting backend server..."
.venv/bin/uvicorn backend.api:app --port 8002 --reload > /dev/null 2>&1 &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Check if backend is running
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "❌ Backend failed to start!"
    echo "   Try running manually: .venv/bin/uvicorn backend.api:app --port 8002 --reload"
    exit 1
fi

echo "✅ Backend running on http://localhost:8002 (PID: $BACKEND_PID)"
echo ""

echo "🚀 Starting frontend server..."
cd frontend
npm run dev > /dev/null 2>&1 &
FRONTEND_PID=$!
cd ..

# Wait for frontend to start
sleep 3

# Check if frontend is running
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo "❌ Frontend failed to start!"
    echo "   Try running manually: cd frontend && npm run dev"
    kill $BACKEND_PID
    exit 1
fi

echo "✅ Frontend running on http://localhost:5173 (PID: $FRONTEND_PID)"
echo ""
echo "======================================================"
echo "  ✅ All services started successfully!"
echo "======================================================"
echo ""
echo "📊 Dashboard: http://localhost:5173"
echo "🔌 Backend API: http://localhost:8002"
echo ""
echo "Press Ctrl+C to stop all services"
echo ""

# Wait for user interrupt
wait
