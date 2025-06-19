#!/bin/bash
# Manual SSE Testing Script
# Tests MCP server SSE endpoints using curl

SERVER_URL="http://localhost:8080"
SSE_URL="${SERVER_URL}/sse"
MESSAGES_URL="${SERVER_URL}/messages"

echo "MCP SSE Manual Testing"
echo "====================="
echo "Server URL: $SERVER_URL"
echo "SSE Endpoint: $SSE_URL"
echo "Messages Endpoint: $MESSAGES_URL"
echo

# Function to test if server is running
test_server_health() {
    echo "1. Testing server health..."
    
    # Test basic HTTP response
    if curl -s -I "$SERVER_URL" >/dev/null 2>&1; then
        echo "✓ Server is responding"
    else
        echo "✗ Server is not responding"
        echo "  Make sure to start the server with: python remote_admin_server.py --transport sse"
        return 1
    fi
    
    # Test SSE endpoint
    echo "2. Testing SSE endpoint..."
    if curl -s -I "$SSE_URL" | grep -q "text/event-stream"; then
        echo "✓ SSE endpoint is available"
    else
        echo "✗ SSE endpoint is not available or not returning correct content-type"
        echo "  Expected: text/event-stream"
        echo "  Actual response:"
        curl -s -I "$SSE_URL" | head -5
        return 1
    fi
    
    echo
}

# Function to send MCP initialize message
send_initialize() {
    echo "3. Sending MCP initialize message..."
    
    local response=$(curl -s -X POST "$MESSAGES_URL" \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "manual-test", "version": "1.0.0"}
            }
        }')
    
    if [ $? -eq 0 ]; then
        echo "✓ Initialize message sent"
        echo "Response: $response"
    else
        echo "✗ Failed to send initialize message"
        return 1
    fi
    
    echo
}

# Function to list tools
list_tools() {
    echo "4. Listing available tools..."
    
    local response=$(curl -s -X POST "$MESSAGES_URL" \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }')
    
    if [ $? -eq 0 ]; then
        echo "✓ Tools list request sent"
        echo "Response: $response"
    else
        echo "✗ Failed to list tools"
        return 1
    fi
    
    echo
}

# Function to call a tool
call_health_check() {
    echo "5. Calling health_check tool..."
    
    local response=$(curl -s -X POST "$MESSAGES_URL" \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "health_check",
                "arguments": {}
            }
        }')
    
    if [ $? -eq 0 ]; then
        echo "✓ Health check tool called"
        echo "Response: $response"
    else
        echo "✗ Failed to call health check tool"
        return 1
    fi
    
    echo
}

# Function to listen to SSE stream
listen_sse_stream() {
    echo "6. Listening to SSE stream (press Ctrl+C to stop)..."
    echo "   This will show server messages in real-time"
    echo
    
    curl -N -H "Accept: text/event-stream" "$SSE_URL"
}

# Function to test with authentication
test_with_auth() {
    local auth_token="$1"
    
    echo "Testing with authentication..."
    echo "Auth token: ${auth_token:0:10}..."
    
    local response=$(curl -s -X POST "$MESSAGES_URL" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $auth_token" \
        -d '{
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/list",
            "params": {}
        }')
    
    if [ $? -eq 0 ]; then
        echo "✓ Authenticated request sent"
        echo "Response: $response"
    else
        echo "✗ Authentication failed"
    fi
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --url)
                SERVER_URL="$2"
                SSE_URL="${SERVER_URL}/sse"
                MESSAGES_URL="${SERVER_URL}/messages"
                shift 2
                ;;
            --auth)
                AUTH_TOKEN="$2"
                shift 2
                ;;
            --listen-only)
                LISTEN_ONLY=true
                shift
                ;;
            --help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  --url URL          Server URL (default: http://localhost:8080)"
                echo "  --auth TOKEN       Authentication token"
                echo "  --listen-only      Only listen to SSE stream"
                echo "  --help            Show this help"
                echo
                echo "Examples:"
                echo "  $0                                    # Basic test"
                echo "  $0 --url http://192.168.1.100:8080   # Custom server"
                echo "  $0 --auth mytoken123                 # With authentication"
                echo "  $0 --listen-only                     # Just listen to SSE"
                exit 0
                ;;
            *)
                echo "Unknown option: $1"
                echo "Use --help for usage information"
                exit 1
                ;;
        esac
    done
    
    # If listen-only mode, just listen to SSE
    if [ "$LISTEN_ONLY" = true ]; then
        listen_sse_stream
        exit 0
    fi
    
    # Run tests
    test_server_health || exit 1
    
    if [ -n "$AUTH_TOKEN" ]; then
        test_with_auth "$AUTH_TOKEN"
    else
        send_initialize
        list_tools
        call_health_check
        
        echo "To see live SSE messages, run:"
        echo "  $0 --listen-only"
        echo
        echo "To test with authentication:"
        echo "  $0 --auth your-token-here"
    fi
}

# Run main function
main "$@" 