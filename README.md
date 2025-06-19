# MCP Remote Admin System

A comprehensive remote machine administration system built on the Model Context Protocol (MCP). This system allows you to manage multiple remote servers through Claude Desktop or other MCP-compatible hosts.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Claude/Host   │────│  Admin Client    │────│  Remote Server  │
│   (Control UI)  │    │  (Coordinator)   │    │  (Target Box)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │                       │
                                │                ┌─────────────────┐
                                └────────────────│  Remote Server  │
                                                 │  (Target Box)   │
                                                 └─────────────────┘
```

### Components

- **Host (Claude Desktop)**: Your AI assistant interface
- **Admin Client**: Coordination layer that manages connections to multiple remote servers
- **Remote Servers**: MCP servers running on machines to be administered

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Remote Servers

On each machine you want to administer, run:

```bash
# Copy the remote server script
cp mcp_server/remote_admin_server.py /opt/mcp-admin/
cd /opt/mcp-admin/

# Set environment variables
export MCP_SERVER_NAME="server-01"
export MCP_SERVER_PORT="8080"
export MCP_AUTH_TOKEN="your-secure-token-here"

# Run the server
python remote_admin_server.py
```

### 3. Configure the Admin Client

```bash
# Copy the example config
cp config.example.json config.json

# Edit with your server details
vim config.json

# Set environment variables for tokens
export PROD_WEB_01_TOKEN="token1"
export DEV_SERVER_TOKEN="token2"
# ... etc
```

### 4. Run the Admin Client

```bash
python ai-admin.py
```

### 5. Connect Claude Desktop

Add this to your Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "remote-admin": {
      "command": "python",
      "args": ["/path/to/ai-admin.py"]
    }
  }
}
```

## 🔧 Available Commands

### Server Management
- `register_remote_server()` - Add a new server with full configuration
- `list_servers()` - View all registered servers with detailed settings
- `bulk_command()` - Execute commands across multiple servers
- `load_config_file()` - Load server configuration from JSON file
- `get_config_status()` - View current configuration and connection status

### Server Groups & Security
- `get_server_groups()` - List all configured server groups
- `get_servers_by_group()` - Get servers belonging to a specific group
- `validate_command_for_group()` - Check if command is allowed for server group

### System Operations
- `get_system_status()` - CPU, memory, disk, network stats
- `read_remote_file()` - Read files with security restrictions
- `execute_shell_command()` - Run whitelisted commands
- `list_processes()` - View running processes
- `network_connections()` - List listening ports

### Service Management
- `get_service_status()` - Check systemd service status
- `restart_service()` - Restart services
- `get_system_logs()` - Retrieve various log types

## 🔐 Security Features

### Authentication
- Bearer token authentication for all connections
- TLS/SSL encryption for remote connections
- Optional mutual TLS support

### Command Restrictions
- Whitelist-based command filtering
- Path-based file access restrictions
- Service-specific operation limits

### Audit Logging
- All commands logged with timestamps
- Failed authentication attempts tracked
- Configurable log levels and destinations

### Network Security
- Rate limiting and connection throttling
- SSH tunnel support
- VPN-friendly architecture

## 📋 Example Usage

```python
# Register servers
await register_remote_server(
    name="web-server-01",
    host="10.0.1.100",
    port=8080,
    auth_token="secure-token",
    tags=["production", "web"]
)

# Get system status from all production servers
status = await bulk_command(
    command="system_status",
    server_tags=["production"]
)

# Check nginx status on web servers
nginx_status = await bulk_command(
    command="service_status",
    server_tags=["web"],
    params={"service": "nginx"}
)

# Read log files
logs = await get_system_logs(
    server_name="web-server-01",
    log_type="nginx",
    lines=100
)
```

## ⚙️ Configuration Reference

### Server Configuration Parameters

Each server in `remote_servers` array supports:

```json
{
  "name": "server-name",           // Unique identifier
  "host": "10.0.1.100",          // IP address or hostname
  "port": 8080,                   // Port number
  "protocol": "https",            // Protocol (https/http)
  "auth_token": "${TOKEN_VAR}",   // Auth token (supports env vars)
  "tags": ["prod", "web"],        // Server tags for grouping
  "ssl_verify": true,             // SSL certificate verification
  "timeout": 30,                  // Request timeout (seconds)
  "retry_attempts": 3,            // Connection retry attempts
  "custom_headers": {             // Additional HTTP headers
    "X-Custom": "value"
  },
  "allowed_commands": [           // Command whitelist (empty = all)
    "system_status",
    "get_logs"
  ]
}
```

### Security Configuration

Global security settings:

```json
{
  "security": {
    "default_timeout": 30,
    "max_concurrent_connections": 10,
    "rate_limit": {
      "requests_per_minute": 60,
      "burst_size": 10
    },
    "audit_log": {
      "enabled": true,
      "file": "/var/log/mcp-admin/audit.log",
      "level": "INFO"
    }
  }
}
```

### Server Groups

Define server groups with restrictions:

```json
{
  "server_groups": {
    "production": {
      "tags": ["production"],
      "restrictions": {
        "dangerous_commands": false,    // Block risky commands
        "file_write": false,           // Block file modifications
        "service_restart": false       // Block service restarts
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

## 🛡️ Security Best Practices

### Server-Side Security
1. **Run with minimal privileges** - Use dedicated service accounts
2. **Firewall restrictions** - Only allow connections from admin clients
3. **Regular token rotation** - Change authentication tokens periodically
4. **Monitor access logs** - Set up alerting for suspicious activity

### Network Security
1. **Use TLS everywhere** - Never run unencrypted connections
2. **SSH tunneling** - For additional security layer
3. **VPN access** - Isolate admin traffic
4. **Network segmentation** - Separate admin and production networks

### Access Control
1. **Role-based permissions** - Different tokens for different access levels
2. **Command whitelisting** - Strictly control allowed operations
3. **Path restrictions** - Limit file system access
4. **Time-based tokens** - Implement token expiration

## 🚨 Production Deployment

### systemd Service (Remote Server)

```ini
[Unit]
Description=MCP Remote Admin Server
After=network.target

[Service]
Type=simple
User=mcp-admin
Group=mcp-admin
WorkingDirectory=/opt/mcp-admin
Environment=MCP_SERVER_NAME=prod-web-01
Environment=MCP_SERVER_PORT=8080
Environment=MCP_AUTH_TOKEN_FILE=/etc/mcp-admin/token
ExecStart=/usr/bin/python3 remote_admin_server.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Reverse Proxy (nginx)

```nginx
server {
    listen 443 ssl;
    server_name admin.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🔄 Scaling Considerations

### High Availability
- Run multiple admin clients behind a load balancer
- Implement server health checking and failover
- Use service discovery for dynamic server registration

### Performance
- Connection pooling and keep-alive
- Async operations for bulk commands
- Caching for frequently accessed data

### Monitoring
- Prometheus metrics export
- Grafana dashboards for visualization
- AlertManager for critical alerts

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Ensure security best practices
5. Submit a pull request

## 📝 License

MIT License - see LICENSE file for details

## 🆘 Support

- Check the troubleshooting guide in `docs/troubleshooting.md`
- Open issues for bugs or feature requests
- Join our Discord for community support 