# MCP Remote Admin Server

This is the server component that runs on remote machines to be administered via the MCP (Model Context Protocol). It exposes system administration capabilities through a secure, configurable interface.

## 🚀 Quick Start

1. **Install Dependencies**
   ```bash
   pip install fastmcp psutil aiohttp
   ```

2. **Create Configuration**
   ```bash
   cp server_config.example.json server_config.json
   # Edit server_config.json with your settings
   ```

3. **Set Authentication Token**
   ```bash
   export MCP_AUTH_TOKEN="your-secure-token-here"
   ```

4. **Start Server**
   ```bash
   # Linux/macOS
   ./start-server.sh
   
   # Windows
   start-server.bat
   
   # Direct Python
   python3 remote_admin_server.py
   ```

## ⚙️ Configuration

The server uses a JSON configuration file with the following sections:

### Transport Modes

The server supports three transport modes for different deployment scenarios:

1. **STDIO (Default)** - For local integrations
   ```json
   { "transport": "stdio" }
   ```
   - Communication via standard input/output
   - No network binding required
   - Designed for MCP clients like Claude Desktop
   - Process started by client for each session

2. **SSE (Server-Sent Events)** - For web deployments (legacy)
   ```json
   { "transport": "sse" }
   ```
   - HTTP-based transport using Server-Sent Events
   - Binds to network port
   - Client URL: `http://host:port/sse`
   - Legacy option, prefer Streamable HTTP for new projects

3. **Streamable HTTP** - For modern web deployments
   ```json
   { "transport": "streamable-http" }
   ```
   - Modern HTTP-based transport
   - More efficient than SSE
   - Binds to network port
   - Client URL: `http://host:port/mcp`

### Server Configuration
```json
{
  "server": {
    "name": "remote-admin-server",
    "port": 8080,
    "host": "0.0.0.0",
    "auth_token": "${MCP_AUTH_TOKEN}",
    "log_level": "INFO",
    "max_connections": 10
  }
}
```

**Note**: The `host` and `port` parameters are included for configuration completeness but FastMCP currently has limited configuration options. The server may use default host/port settings regardless of configuration. Check the FastMCP documentation for supported parameters.

### Security Configuration
```json
{
  "security": {
    "allowed_commands": ["ps", "top", "df", "systemctl"],
    "allowed_paths": ["/var/log", "/etc", "/proc"],
    "command_timeout": 30,
    "max_file_size": 10485760,
    "max_file_lines": 1000,
    "enable_dangerous_commands": false,
    "dangerous_commands": ["rm", "shutdown", "reboot"]
  }
}
```

### Feature Configuration
```json
{
  "features": {
    "system_status": true,
    "file_operations": true,
    "shell_execution": true,
    "service_management": true,
    "log_retrieval": true,
    "process_management": true,
    "network_info": true
  }
}
```

### Logging Configuration
```json
{
  "logging": {
    "file": "/var/log/mcp-admin-server.log",
    "level": "INFO",
    "audit_enabled": true,
    "audit_file": "/var/log/mcp-admin-audit.log"
  }
}
```

## 🔧 Command Line Options

```bash
python3 remote_admin_server.py [OPTIONS]

Options:
  -c, --config FILE      Configuration file (default: server_config.json)
  -p, --port PORT        Override port from config
  --host HOST            Override host from config
  -t, --transport MODE   Transport mode: stdio, sse, streamable-http
  --help                Show help message
```

### Transport Mode Examples

```bash
# STDIO mode (default) - for Claude Desktop integration
python3 remote_admin_server.py

# SSE mode - for web clients (legacy)
python3 remote_admin_server.py --transport sse

# Streamable HTTP mode - for modern web clients
python3 remote_admin_server.py --transport streamable-http

# Override config settings
python3 remote_admin_server.py --transport sse --host 0.0.0.0 --port 8080
```

## 🔒 Security Features

- **Command Whitelisting**: Only pre-approved commands can be executed
- **Path Restrictions**: File access limited to specified directories
- **Dangerous Command Control**: Optional blocking of destructive commands
- **File Size Limits**: Prevents reading of extremely large files
- **Timeout Controls**: Commands automatically terminated after timeout
- **Audit Logging**: All operations logged for security compliance
- **Authentication**: Token-based authentication support

## 📊 Available Tools

### System Information
- `system_status()` - Get CPU, memory, disk, network status
- `list_processes()` - List running processes
- `network_connections()` - Show listening ports

### File Operations
- `read_file(path, max_lines)` - Read file contents with security checks
- Path access restricted to configured allowed paths

### Command Execution
- `shell_exec(command, timeout)` - Execute shell commands safely
- Commands must be in the allowed list

### Service Management
- `service_status(service)` - Check service status
- `service_restart(service)` - Restart system services

### Log Retrieval
- `get_logs(log_type, lines)` - Retrieve system logs
- Supports syslog, kernel, auth, nginx, apache, docker logs

### Health Check
- `health_check()` - Server health and status information

## 🌍 Environment Variables

- `MCP_AUTH_TOKEN` - Authentication token for the server
- Variables can be used in config files with `${VARIABLE_NAME}` syntax

## 📝 Example Usage

### Basic Configuration
```json
{
  "server": {
    "name": "web-server-01",
    "port": 8080,
    "auth_token": "${MCP_AUTH_TOKEN}"
  },
  "security": {
    "allowed_commands": ["ps", "top", "df", "systemctl", "journalctl"],
    "allowed_paths": ["/var/log", "/etc/nginx"],
    "enable_dangerous_commands": false
  },
  "features": {
    "system_status": true,
    "file_operations": true,
    "shell_execution": true,
    "service_management": true
  }
}
```

### Production Configuration
```json
{
  "server": {
    "name": "prod-server-01",
    "port": 8443,
    "host": "127.0.0.1",
    "auth_token": "${PROD_MCP_TOKEN}"
  },
  "security": {
    "allowed_commands": ["systemctl", "journalctl", "ps", "top"],
    "allowed_paths": ["/var/log"],
    "command_timeout": 15,
    "enable_dangerous_commands": false
  },
  "logging": {
    "file": "/var/log/mcp-admin.log",
    "audit_enabled": true,
    "audit_file": "/var/log/mcp-audit.log"
  },
  "limits": {
    "max_processes_list": 25,
    "max_log_lines": 50
  }
}
```

## 🔍 Troubleshooting

### Common Issues

1. **Permission Denied**
   - Check that allowed_paths includes the directories you need
   - Verify the server process has appropriate permissions

2. **Command Not Allowed**
   - Add the command to the allowed_commands list
   - Check if it's in dangerous_commands and enable if needed

3. **Connection Issues**
   - Verify the port is not blocked by firewall
   - Check if the host binding is correct (0.0.0.0 vs 127.0.0.1)

4. **Authentication Failures**
   - Ensure MCP_AUTH_TOKEN is set correctly
   - Verify the token matches between client and server

### Logging

- Server logs show operational information
- Audit logs track all command executions
- Log levels: DEBUG, INFO, WARNING, ERROR
- Logs can be written to files or console

## 🛡️ Security Best Practices

1. **Use Authentication**: Always set MCP_AUTH_TOKEN
2. **Limit Commands**: Only allow necessary commands
3. **Restrict Paths**: Limit file access to required directories
4. **Enable Auditing**: Track all operations for compliance
5. **Network Security**: Use firewall rules to restrict access
6. **Regular Updates**: Keep dependencies updated
7. **Monitor Logs**: Review audit logs regularly

## 📋 Requirements

- Python 3.7+
- fastmcp
- psutil
- aiohttp
- Linux/Unix system (for some features)

## 🔄 Updates

To update the server:
1. Stop the running server
2. Update the Python script
3. Review configuration for new options
4. Restart the server

The server supports graceful shutdowns and will log all operations for audit purposes. 