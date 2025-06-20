#!/bin/bash

echo "Starting AI Admin Chatbot..."
echo

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Error: .env file not found!"
    echo "Please copy config.example to .env and configure your API keys."
    exit 1
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Start the Flask application
echo "Starting Flask application on http://localhost:${PORT:-5000}"
echo "Press Ctrl+C to stop"
echo

python3 app.py 