# MCP SSE Transport Guide

## Overview

SSE (Server-Sent Events) transport allows MCP servers to be accessed over HTTP, enabling web-based clients and remote access. This guide explains how SSE works for both server and client sides.

## How SSE Transport Works

### Server Side

When you start the MCP server with SSE transport:

```bash
python remote_admin_server.py --transport sse --host 0.0.0.0 --port 8080
```

**What the server does:**

1. **HTTP Server Creation**: FastMCP creates an HTTP server using Starlette/Uvicorn
2. **SSE Endpoint**: Exposes an SSE endpoint at `/sse` 
3. **Message Endpoint**: Creates a POST endpoint for receiving client messages
4. **MCP Protocol Wrapping**: Wraps MCP protocol messages in SSE format

**Server Endpoints:**
- `GET http://host:port/sse` - SSE stream for server-to-client messages
- `POST http://host:port/messages` - Endpoint for client-to-server messages

### Client Side

MCP clients connect to SSE servers using two connections:

1. **SSE Connection**: Long-lived connection to receive server messages
2. **HTTP POST**: For sending messages to the server

## Practical Examples

### 1. Server Setup

```python
# In remote_admin_server.py
from mcp.server.fastmcp import FastMCP

server = FastMCP("remote-admin-server")

# Register tools...
@server.tool()
async def system_status():
    return {"status": "healthy"}

# Run with SSE transport
if __name__ == "__main__":
    server.run(transport="sse", host="0.0.0.0", port=8080)
```

**Server URLs:**
- SSE Stream: `http://localhost:8080/sse`
- Message Endpoint: `http://localhost:8080/messages`

### 2. Client Connection (Python)

```python
from fastmcp import Client

# Connect to SSE server
client = Client("http://localhost:8080/sse")

async def main():
    async with client:
        # List available tools
        tools = await client.list_tools()
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        # Call a tool
        result = await client.call_tool("system_status")
        print(f"System status: {result}")

import asyncio
asyncio.run(main())
```

### 3. Client Connection (JavaScript/Web)

```javascript
// Connect to SSE endpoint
const eventSource = new EventSource('http://localhost:8080/sse');

// Listen for messages from server
eventSource.onmessage = function(event) {
    const message = JSON.parse(event.data);
    console.log('Received from server:', message);
    handleMCPMessage(message);
};

// Send message to server
async function sendToServer(mcpMessage) {
    const response = await fetch('http://localhost:8080/messages', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(mcpMessage)
    });
    return response.json();
}

// Example: List tools
async function listTools() {
    const message = {
        jsonrpc: "2.0",
        id: 1,
        method: "tools/list",
        params: {}
    };
    
    return await sendToServer(message);
}
```

### 4. Manual Testing with curl

```bash
# Test SSE connection (will stream server messages)
curl -N -H "Accept: text/event-stream" http://localhost:8080/sse

# Send MCP message to server
curl -X POST http://localhost:8080/messages \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/list",
    "params": {}
  }'
```

## Message Flow

### 1. Client Initialization
```
Client -> Server: POST /messages
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "initialize",
  "params": {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "test-client", "version": "1.0.0"}
  }
}

Server -> Client: SSE Event
data: {
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "protocolVersion": "2024-11-05",
    "capabilities": {...},
    "serverInfo": {"name": "remote-admin-server", "version": "1.0.0"}
  }
}
```

### 2. Tool Discovery
```
Client -> Server: POST /messages
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/list",
  "params": {}
}

Server -> Client: SSE Event
data: {
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "tools": [
      {
        "name": "system_status",
        "description": "Get system status",
        "inputSchema": {...}
      }
    ]
  }
}
```

### 3. Tool Execution
```
Client -> Server: POST /messages
{
  "jsonrpc": "2.0",
  "id": 3,
  "method": "tools/call",
  "params": {
    "name": "system_status",
    "arguments": {}
  }
}

Server -> Client: SSE Event
data: {
  "jsonrpc": "2.0",
  "id": 3,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "{\"status\": \"healthy\", \"cpu\": \"45%\", \"memory\": \"60%\"}"
      }
    ]
  }
}
```

## Network Verification

When SSE server is running, you should see:

```bash
# Check if server is listening
netstat -tulnp | grep 8080
# Should show: tcp 0 0 0.0.0.0:8080 0.0.0.0:* LISTEN <pid>/python

# Test SSE endpoint
curl -I http://localhost:8080/sse
# Should return: HTTP/1.1 200 OK with text/event-stream content-type
```

## SSE vs STDIO Comparison

| Aspect | STDIO Transport | SSE Transport |
|--------|----------------|---------------|
| **Network Binding** | No | Yes (HTTP server) |
| **Client Location** | Local only | Remote possible |
| **Protocol** | MCP over stdin/stdout | MCP over HTTP/SSE |
| **Use Case** | Claude Desktop, local tools | Web clients, remote access |
| **Process Management** | Client starts/stops server | Server runs independently |
| **Port Visibility** | No netstat entry | Visible in netstat |

## Authentication with SSE

```python
# Server with authentication
server = FastMCP("remote-admin-server")

# FastMCP handles auth via headers or query params
# Client must provide authentication

# Client with auth
from fastmcp.client.transports import SSETransport

transport = SSETransport(
    url="http://localhost:8080/sse",
    headers={"Authorization": "Bearer your-token-here"}
)
client = Client(transport)
```

## Troubleshooting SSE

### Common Issues

1. **Server not binding to port**
   ```bash
   # Check if using correct transport
   python remote_admin_server.py --transport sse
   ```

2. **CORS issues with web clients**
   ```python
   # Server may need CORS configuration
   # FastMCP handles this automatically for SSE
   ```

3. **Connection drops**
   ```javascript
   // Handle SSE connection drops
   eventSource.onerror = function(event) {
       console.log('SSE connection error:', event);
       // Implement reconnection logic
   };
   ```

4. **Authentication failures**
   ```bash
   # Verify auth token
   export MCP_AUTH_TOKEN="your-token"
   python remote_admin_server.py --transport sse
   ```

## Best Practices

1. **Use HTTPS in production**
   ```bash
   # Use reverse proxy (nginx/caddy) for SSL termination
   ```

2. **Implement proper error handling**
   ```python
   async with client:
       try:
           result = await client.call_tool("system_status")
       except Exception as e:
           print(f"Tool call failed: {e}")
   ```

3. **Handle connection lifecycle**
   ```python
   # Proper client cleanup
   async with client:
       # Do work here
       pass  # Client automatically closes
   ```

4. **Monitor server health**
   ```python
   # Regular health checks
   async def health_check():
       try:
           await client.ping()
           return True
       except:
           return False
   ```

## When to Use SSE Transport

**Use SSE when:**
- Need remote access to MCP server
- Building web-based MCP clients
- Want server to run independently
- Multiple clients need to connect
- Deploying in containerized environments

**Use STDIO when:**
- Integrating with Claude Desktop
- Building local command-line tools
- Want client to manage server lifecycle
- Security requires no network exposure
- Simpler deployment model preferred 