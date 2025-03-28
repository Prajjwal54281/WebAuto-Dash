#!/bin/bash

# WebAutoDash Startup Script
# This script starts both backend (Flask) and frontend (React) servers

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

echo "🚀 Starting WebAutoDash Medical Portal..."
echo "📁 Project Directory: $SCRIPT_DIR"

# Check if directories exist
if [ ! -d "$BACKEND_DIR" ]; then
    echo "❌ Backend directory not found: $BACKEND_DIR"
    exit 1
fi

if [ ! -d "$FRONTEND_DIR" ]; then
    echo "❌ Frontend directory not found: $FRONTEND_DIR"
    exit 1
fi

# Function to check if port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Check if backend is already running
if check_port 5005; then
    echo "⚠️  Backend already running on port 5005"
    read -p "Do you want to kill the existing process and restart? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Stopping existing backend process..."
        lsof -ti:5005 | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        echo "ℹ️  Using existing backend process"
    fi
fi

# Check if frontend is already running
if check_port 3008; then
    echo "⚠️  Frontend already running on port 3008"
    read -p "Do you want to kill the existing process and restart? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🔄 Stopping existing frontend process..."
        lsof -ti:3008 | xargs kill -9 2>/dev/null || true
        sleep 2
    else
        echo "ℹ️  Using existing frontend process"
        echo "🌐 Frontend should be available at: http://localhost:3008"
        exit 0
    fi
fi

# Change to frontend directory and start both servers
cd "$FRONTEND_DIR"

echo "🔧 Starting backend (Flask) and frontend (React) servers..."
echo "📍 Backend will run on: http://localhost:5005"
echo "📍 Frontend will run on: http://localhost:3008"
echo ""
echo "💡 Press Ctrl+C to stop both servers"
echo "----------------------------------------"

# Start both servers using npm run dev
npm run dev 