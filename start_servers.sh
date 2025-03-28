#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
echo "Starting WebAutoDash servers from: $SCRIPT_DIR"

# Function to cleanup background processes
cleanup() {
    echo "Shutting down servers..."
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo "Backend server stopped"
    fi
    exit 0
}

# Set up trap to cleanup on script exit
trap cleanup SIGINT SIGTERM

# Activate conda environment
echo "Activating medimind conda environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate medimind

if [ $? -ne 0 ]; then
    echo "Failed to activate medimind environment"
    exit 1
fi

# Start backend server in background
echo "Starting Flask backend server..."
cd "$SCRIPT_DIR/backend"
python app.py &
BACKEND_PID=$!

if [ $? -ne 0 ]; then
    echo "Failed to start backend server"
    exit 1
fi

echo "Backend server started with PID: $BACKEND_PID"

# Wait for backend to start
echo "Waiting for backend to initialize..."
sleep 5

# Start frontend server on port 3008
echo "Starting React frontend server on port 3008..."
cd "$SCRIPT_DIR/frontend"
PORT=3008 npm start

# If we reach here, npm start has exited
cleanup 