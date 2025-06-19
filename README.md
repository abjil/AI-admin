# MCP Remote Admin

A comprehensive Model Context Protocol (MCP) based remote administration system that allows you to manage multiple remote servers through Claude Desktop.

## Architecture

This system implements a 3-tier architecture:

1. **Host (Claude Desktop)** - The AI interface
2. **Client (`ai-admin-refactored.py`)** - Coordination layer and MCP proxy
3. **Servers (`remote_admin_server.py`)** - Remote machines to be administered

## Features

- **Multi-Protocol Support**: Connects to remote MCP servers using SSE, Streamable HTTP, or legacy HTTP protocols
- **Configuration-Driven**: JSON configuration with environment variable substitution
- **Security**: Command whitelisting, server groups, audit logging, rate limiting
- **Scalability**: Bulk operations across multiple servers
- **Extensible**: SOLID principles architecture for easy extension

## Protocol Support

The client supports multiple connection protocols:

### MCP Protocols (Recommended)
- **`mcp-sse`**: Server-Sent Events transport for MCP servers
- **`mcp-http`**: Streamable HTTP transport for MCP servers  
- **`mcp`**: Default MCP transport (uses SSE)

### Legacy Protocols
- **`https`**: Direct HTTPS connections (legacy mode)
- **`http`**: Direct HTTP connections (legacy mode)

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Remote Servers

Edit `config.json`:

```json
{
  "remote_servers": [
    {
      "name": "production-server",
      "host": "prod.example.com",
      "port": 8080,
      "protocol": "mcp-sse",
      "auth_token": "your-secure-token",
      "tags": ["production", "critical"],
      "ssl_verify": true
    },
    {
      "name": "dev-server",
      "host": "dev.example.com", 
      "port": 8080,
      "protocol": "mcp-http",
      "auth_token": "dev-token",
      "tags": ["development"],
      "ssl_verify": false
    }
  ]
}
```

### 3. Start Remote MCP Servers

On each remote machine:

```bash
# Configure the server
cp mcp_server/server_config.example.json mcp_server/server_config.json
# Edit server_config.json as needed

# Start with SSE transport (for mcp-sse clients)
cd mcp_server
python remote_admin_server.py --transport sse

# Or start with Streamable HTTP transport (for mcp-http clients)  
python remote_admin_server.py --transport streamable-http
```

### 4. Start the Admin Client

```bash
# Start the MCP client (connects to Claude Desktop via STDIO)
python ai-admin-refactored.py

# Or with custom config
python ai-admin-refactored.py --config my-config.json --verbose
```

### 5. Connect Claude Desktop

Add to your Claude Desktop MCP configuration:

```json
{
  "mcpServers": {
    "remote-admin": {
      "command": "python",
      "args": ["/path/to/ai-admin-refactored.py"],
      "env": {}
    }
  }
}
```

## Configuration

### Server Configuration

Each remote server in `config.json` supports:

```json
{
  "name": "server-name",
  "host": "hostname-or-ip",
  "port": 8080,
  "protocol": "mcp-sse|mcp-http|mcp|https|http",
  "auth_token": "authentication-token", 
  "tags": ["tag1", "tag2"],
  "ssl_verify": true,
  "timeout": 30,
  "retry_attempts": 3,
  "custom_headers": {
    "X-Custom-Header": "value"
  },
  "allowed_commands": ["command1", "command2"]
}
```

### Protocol Details

| Protocol | Transport | Use Case | Server Endpoint |
|----------|-----------|----------|-----------------|
| `mcp-sse` | Server-Sent Events | Real-time updates, web-based | `/sse` |
| `mcp-http` | Streamable HTTP | Modern web apps | `/mcp` |  
| `mcp` | SSE (default) | General purpose | `/sse` |
| `https` | Direct HTTP | Legacy systems | `/health` |
| `http` | Direct HTTP | Development | `/health` |

### Security Groups

Define server groups with restrictions:

```json
{
  "server_groups": {
    "production": {
      "tags": ["production"],
      "restrictions": {
        "dangerous_commands": false,
        "file_write": false,
        "service_restart": false
      }
    },
    "development": {
      "tags": ["development"],
      "restrictions": {
        "dangerous_commands": true,
        "file_write": true,
        "service_restart": true
      }
    }
  }
}
```

## Available Commands

When connected to Claude Desktop, you can use these MCP tools:

- `load_config_file` - Load server configuration
- `connect_to_server` - Connect to specific server
- `execute_command` - Run command on server
- `execute_bulk_command` - Run command on multiple servers
- `get_server_status` - Check server connection status
- `get_config_status` - View current configuration
- `register_server` - Add new server dynamically

## MCP Server Setup

### Server Configuration

On remote machines, configure `mcp_server/server_config.json`:

```json
{
  "server": {
    "name": "Remote Admin Server",
    "version": "1.0.0",
    "port": 8080,
    "transport": "sse"
  },
  "security": {
    "auth_required": true,
    "auth_token": "your-secure-token",
    "allowed_origins": ["*"],
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 60
    }
  }
}
```

### Transport Modes

Start the server with different transports:

```bash
# SSE transport (for mcp-sse clients)
python remote_admin_server.py --transport sse

# Streamable HTTP transport (for mcp-http clients)
python remote_admin_server.py --transport streamable-http

# STDIO transport (for local MCP clients)
python remote_admin_server.py --transport stdio
```

## Architecture Details

### SOLID Principles Implementation

The system follows SOLID principles:

- **Single Responsibility**: Each class has one reason to change
- **Open/Closed**: Extensible without modification
- **Liskov Substitution**: All implementations are substitutable
- **Interface Segregation**: Small, focused interfaces
- **Dependency Inversion**: Depends on abstractions, not concretions

### Core Components

```
core/
├── models.py           # Data structures
├── interfaces.py       # Abstract interfaces
├── config.py          # Configuration management
├── registry.py        # Server registry
├── connections.py     # Connection management (HTTP + MCP)
├── commands.py        # Command execution
├── security.py        # Security policies
├── audit.py          # Audit logging
├── services.py       # Service coordination
└── mcp_tools.py      # MCP tool providers
```

## Connection Flow

### MCP Connection Process

1. **Configuration Load**: Parse JSON config with environment variables
2. **Factory Selection**: Choose appropriate connection factory based on protocol
3. **Transport Creation**: Create SSE or Streamable HTTP transport
4. **MCP Client**: Initialize FastMCP client with transport
5. **Health Check**: Ping MCP server to verify connection
6. **Command Execution**: Use `client.call_tool()` for MCP commands

### Example MCP Connection

```python
# Client connects to remote MCP server
transport = SSETransport(url="https://server:8080/sse", headers={"Authorization": "Bearer token"})
client = Client(transport)

# Execute MCP tool
async with client:
    result = await client.call_tool("system_status", {})
```

## Troubleshooting

### Common Issues

1. **Connection Failures**: Check server transport mode matches client protocol
2. **Authentication Errors**: Verify auth tokens match between client and server
3. **Port Conflicts**: Ensure servers are running on configured ports
4. **SSL Issues**: Check `ssl_verify` settings for development environments

### Debugging

Enable verbose logging:

```bash
python ai-admin-refactored.py --verbose
```

Check server logs:

```bash
# Server logs show transport mode and connections
python remote_admin_server.py --transport sse --verbose
```

## License

MIT License - see LICENSE file for details. 