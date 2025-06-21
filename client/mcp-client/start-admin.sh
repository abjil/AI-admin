#!/bin/bash

# MCP Remote Admin Controller Startup Script
# This script sets up environment variables and starts the admin controller

# Set environment variables for authentication tokens
# These should be set securely in production (e.g., from secrets manager)
export PROD_WEB_01_TOKEN="prod-web-token-replace-with-real-token"
export DEV_SERVER_TOKEN="dev-server-token-replace-with-real-token"
export CI_SERVER_TOKEN="ci-server-token-replace-with-real-token"
export DB_PRIMARY_TOKEN="db-primary-token-replace-with-real-token"

# Optional: Set custom config file path
CONFIG_FILE="${1:-config.json}"

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Config file $CONFIG_FILE not found!"
    echo "Creating example config from config.example.json..."
    
    if [ -f "config.example.json" ]; then
        cp config.example.json "$CONFIG_FILE"
        echo "Example config copied to $CONFIG_FILE"
        echo "Please edit $CONFIG_FILE with your actual server details and tokens"
        exit 1
    else
        echo "config.example.json not found either. Please create a config file."
        exit 1
    fi
fi

echo "Starting MCP Remote Admin Controller..."
echo "Config file: $CONFIG_FILE"
echo "Available environment variables:"
echo "  PROD_WEB_01_TOKEN: ${PROD_WEB_01_TOKEN:0:10}..."
echo "  DEV_SERVER_TOKEN: ${DEV_SERVER_TOKEN:0:10}..."
echo "  CI_SERVER_TOKEN: ${CI_SERVER_TOKEN:0:10}..."
echo "  DB_PRIMARY_TOKEN: ${DB_PRIMARY_TOKEN:0:10}..."

# Start the admin controller with auto-loading enabled
python3 ai-admin.py --config "$CONFIG_FILE" --verbose 