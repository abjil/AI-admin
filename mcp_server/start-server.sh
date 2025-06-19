#!/bin/bash
# MCP Remote Admin Server Startup Script

# Set default values
CONFIG_FILE="server_config.json"
PORT=""
HOST=""
TRANSPORT=""
VERBOSE=""

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -c, --config FILE      Configuration file (default: server_config.json)"
    echo "  -p, --port PORT        Override port from config"
    echo "  -h, --host HOST        Override host from config"
    echo "  -t, --transport MODE   Transport mode: stdio, sse, streamable-http"
    echo "  -v, --verbose          Enable verbose logging"
    echo "  --help                Show this help message"
    echo ""
    echo "Environment Variables:"
    echo "  MCP_AUTH_TOKEN       Authentication token for the server"
    echo ""
    echo "Transport Modes:"
    echo "  stdio (default)        For local MCP clients like Claude Desktop"
    echo "  sse                   For web clients using Server-Sent Events"
    echo "  streamable-http       For modern web clients (recommended)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # STDIO mode (default)"
    echo "  $0 -t sse                            # SSE web mode"
    echo "  $0 -t streamable-http                # Modern web mode"
    echo "  $0 -c production.json -t sse         # Custom config + SSE"
    echo "  $0 -t sse -p 9090 -v                # SSE mode, custom port, verbose"
    echo "  MCP_AUTH_TOKEN=secret123 $0 -t sse   # With authentication"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -t|--transport)
            TRANSPORT="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE="--verbose"
            shift
            ;;
        --help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed or not in PATH"
    exit 1
fi

# Check if config file exists
if [ ! -f "$CONFIG_FILE" ]; then
    echo "Warning: Config file '$CONFIG_FILE' not found"
    echo "The server will use default configuration"
fi

# Build command arguments
ARGS="--config $CONFIG_FILE"

if [ -n "$PORT" ]; then
    ARGS="$ARGS --port $PORT"
fi

if [ -n "$HOST" ]; then
    ARGS="$ARGS --host $HOST"
fi

if [ -n "$TRANSPORT" ]; then
    ARGS="$ARGS --transport $TRANSPORT"
fi

# Set environment variables if not already set
if [ -z "$MCP_AUTH_TOKEN" ]; then
    echo "Warning: MCP_AUTH_TOKEN not set - server will run without authentication"
fi

# Start the server
echo "Starting MCP Remote Admin Server..."
echo "Config file: $CONFIG_FILE"
echo "Arguments: $ARGS"
echo ""

python3 remote_admin_server.py $ARGS 