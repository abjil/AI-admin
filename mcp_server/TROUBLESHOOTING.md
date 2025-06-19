# MCP Remote Admin Server Troubleshooting

## Common Issues and Solutions

### 1. FastMCP.run() TypeError: unexpected keyword arguments

**Errors:**
```
TypeError: FastMCP.run() got an unexpected keyword argument 'host'
TypeError: FastMCP.run() got an unexpected keyword argument 'port'
```

**Cause:** FastMCP doesn't support `host` or `port` parameters in its `run()` method.

**Solution:** 
- The server has been updated to call `run()` without parameters
- The `host` and `port` configurations are kept for future compatibility but may be ignored
- Server will use FastMCP's default host/port configuration
- Check FastMCP documentation for supported configuration methods

**Fixed in:** Server version with parameterless `run()` call

**Alternative Solutions:**
- Use environment variables if FastMCP supports them (check FastMCP docs)
- Use a reverse proxy (nginx, Apache) to bind to specific host/port
- Modify the FastMCP source if you need specific network configuration

### 1b. RuntimeError: Already running asyncio in this thread

**Error:**
```
RuntimeError: Already running asyncio in this thread
```

**Cause:** FastMCP uses anyio.run() internally, which conflicts with existing asyncio event loops.

**Solution:**
- Server updated to call `server.run()` directly without `asyncio.run()` wrapper
- FastMCP should manage its own event loop internally
- Ensure the script is run directly, not from within another async context

**Fixed in:** Server version with direct `run()` call

### 2. Authentication Token Issues

**Issue:** Server shows "Authentication token configured" even when MCP_AUTH_TOKEN is not set.

**Cause:** Environment variable substitution leaves `${MCP_AUTH_TOKEN}` as literal string when variable is unset.

**Solution:**
- Server now checks if auth_token starts with `${` to detect unsubstituted variables
- Properly warns when no real token is configured

**To set authentication:**
```bash
export MCP_AUTH_TOKEN="your-secure-token-here"
./start-server.sh
```

### 3. Permission Denied Errors

**Issue:** Commands fail with permission denied errors.

**Solutions:**
1. **Check allowed_paths:** Ensure the path is in the `allowed_paths` configuration
2. **Check allowed_commands:** Ensure the command is in the `allowed_commands` list
3. **File permissions:** Verify the server process has read permissions
4. **Dangerous commands:** Check if command is in `dangerous_commands` and enable if needed

**Example fix:**
```json
{
  "security": {
    "allowed_commands": ["systemctl", "journalctl", "ps"],
    "allowed_paths": ["/var/log", "/etc", "/home/user"],
    "enable_dangerous_commands": false
  }
}
```

### 4. Server Won't Start

**Issue:** Server fails to start or crashes immediately.

**Common causes:**
1. **Port already in use:** Another service is using the configured port
2. **Missing dependencies:** Required Python packages not installed
3. **Invalid configuration:** JSON syntax errors in config file
4. **Permission issues:** Server can't create log files or bind to port

**Solutions:**
```bash
# Check port usage
netstat -tulpn | grep :8080

# Install dependencies
pip install fastmcp psutil aiohttp

# Validate JSON config
python -m json.tool server_config.json

# Check permissions for log directory
mkdir -p /var/log/mcp-admin
chmod 755 /var/log/mcp-admin
```

### 5. Configuration Not Loading

**Issue:** Server uses defaults instead of config file values.

**Solutions:**
1. **Check file path:** Ensure config file exists and path is correct
2. **JSON validation:** Validate JSON syntax
3. **Environment variables:** Check if variables are properly substituted

**Debug steps:**
```bash
# Check if file exists
ls -la server_config.json

# Validate JSON
python -c "import json; print(json.load(open('server_config.json')))"

# Test environment variable substitution
echo $MCP_AUTH_TOKEN
```

### 6. Logging Issues

**Issue:** Logs not appearing in expected location.

**Solutions:**
1. **Directory permissions:** Ensure log directory exists and is writable
2. **Path configuration:** Check log file paths in configuration
3. **Log level:** Verify log level is appropriate

**Example:**
```bash
# Create log directory
sudo mkdir -p /var/log/mcp-admin
sudo chown $USER:$USER /var/log/mcp-admin

# Test logging
tail -f /var/log/mcp-admin-server.log
```

### 7. Command Execution Timeouts

**Issue:** Commands timeout before completion.

**Solutions:**
1. **Increase timeout:** Adjust `command_timeout` in security configuration
2. **Check command:** Ensure command doesn't hang or require interaction
3. **Resource limits:** Check if system is under heavy load

**Configuration:**
```json
{
  "security": {
    "command_timeout": 60
  }
}
```

### 8. File Size Limits

**Issue:** Cannot read large files.

**Solution:** Adjust file size and line limits in configuration:
```json
{
  "security": {
    "max_file_size": 10485760,
    "max_file_lines": 2000
  }
}
```

### 9. FastMCP Event Loop Conflicts

**Error**: `RuntimeError: Already running asyncio in this thread`

**Cause**: FastMCP manages its own event loop internally using `anyio.run()`. Wrapping it with `asyncio.run()` creates a conflict.

**Solution**: 
- Make your main function synchronous
- Call `server.run()` directly (not `await server.run()`)
- Let FastMCP handle its own event loop

**Example**:
```python
# ❌ WRONG - causes event loop conflict
async def main():
    await server.run()

asyncio.run(main())

# ✅ CORRECT - let FastMCP handle its own event loop
def main():
    server.run()

main()
```

### 10. FastMCP Parameter Limitations

**Issue**: FastMCP constructor and run() method don't support all expected parameters.

**Limitations**:
- `FastMCP()` constructor may not accept `port` parameter
- `server.run()` method doesn't accept `host` or `port` parameters
- FastMCP uses its own default configuration

**Solution**: 
- Remove unsupported parameters
- Add warnings about ignored configuration
- Let FastMCP use its default settings

### 11. Understanding FastMCP Transport Modes

**Important**: FastMCP is NOT a traditional HTTP server. It doesn't bind to network ports like a web server.

#### FastMCP Transport Types:

1. **STDIO Transport (Default)**:
   - Communication via standard input/output
   - Used for local integrations (like Claude Desktop)
   - No network binding required
   - Process started by client for each session

2. **SSE Transport (Server-Sent Events)**:
   - HTTP-based but uses MCP protocol over SSE
   - For web-based deployments
   - Still not a traditional HTTP API server
   - Requires `mcp.run(transport="sse")`

3. **Streamable HTTP Transport (Recommended for web)**:
   - Modern HTTP-based transport
   - More efficient than SSE
   - Requires `mcp.run(transport="streamable-http")`

#### Why No Port Binding in `netstat`?

When you see logs like:
```
INFO Starting remote-admin-server on 0.0.0.0:8080
```

But `netstat` shows no process on port 8080, this is because:

1. **FastMCP uses STDIO by default** - no network binding
2. **The host/port configuration is ignored** in STDIO mode
3. **FastMCP logs are misleading** - they show config values but don't reflect actual behavior

#### Correct Usage for Web Deployment:

```python
# For web-based access (SSE transport)
server.run(transport="sse", host="0.0.0.0", port=8080)

# For modern web-based access (Streamable HTTP)
server.run(transport="streamable-http", host="0.0.0.0", port=8080)

# For local integration (STDIO - default)
server.run()  # No network binding
```

### 12. Server Not Accessible from Network

**Issue**: Can't connect to server from remote clients

**Cause**: Server running in STDIO mode (default) instead of web transport

**Solution**: Explicitly specify web transport:

```python
if __name__ == "__main__":
    # For web access
    server.run(transport="streamable-http", host="0.0.0.0", port=8080)
    
    # OR for legacy SSE
    server.run(transport="sse", host="0.0.0.0", port=8080)
```

### 13. Configuration Loading Issues

**Error**: Configuration file not found or invalid JSON

**Solutions**:
- Verify file path: `server_config.json` exists in current directory
- Check JSON syntax with a validator
- Ensure environment variables are properly set
- Use absolute paths if needed

### 14. Environment Variable Substitution

**Issue**: Environment variables not being substituted in config

**Format**: Use `${VARIABLE_NAME}` syntax in JSON config files

**Example**:
```json
{
  "auth_token": "${MCP_AUTH_TOKEN}",
  "database_path": "${HOME}/data/db.sqlite"
}
```

**Troubleshooting**:
- Ensure environment variables are set before starting server
- Check variable names match exactly (case-sensitive)
- Use `echo $VARIABLE_NAME` to verify values

### 15. Client Connection Issues

**Issue**: MCP clients can't connect to server

**For STDIO clients (like Claude Desktop)**:
- Server should run in STDIO mode (default)
- Client launches server process directly
- No network configuration needed

**For web clients**:
- Use SSE or Streamable HTTP transport
- Ensure correct URL format
- Check firewall settings
- Verify authentication tokens

### 16. Tool Registration Problems

**Issue**: Tools not appearing in client

**Causes**:
- Function not decorated with `@server.tool()`
- Import errors in server code
- Server not fully initialized

**Solutions**:
- Check server logs for errors
- Verify all imports work
- Test function independently
- Ensure proper async/await usage

### 17. Performance Issues

**Issue**: Slow response times or timeouts

**Solutions**:
- Use async functions for I/O operations
- Implement proper error handling
- Add timeout configurations
- Monitor resource usage
- Use connection pooling for databases

## Debugging Tips

### Enable Debug Logging
```json
{
  "logging": {
    "level": "DEBUG"
  }
}
```

### Check Server Health
```bash
curl http://localhost:8080/health
```

### Monitor Audit Logs
```bash
tail -f /tmp/mcp-admin-audit.log
```

### Test Configuration
```bash
python3 remote_admin_server.py --config test_config.json --port 8081
```

## Getting Help

1. **Check the logs** - Enable verbose logging for detailed output
2. **Verify FastMCP version** - Ensure you're using a compatible version
3. **Test with minimal config** - Start with basic configuration
4. **Check MCP protocol documentation** - Understand MCP vs HTTP differences
5. **Review FastMCP documentation** - https://gofastmcp.com/

## Configuration Validation Script

Create a simple validation script:
```python
#!/usr/bin/env python3
import json
import sys

def validate_config(config_file):
    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        
        required_sections = ['server', 'security', 'features']
        for section in required_sections:
            if section not in config:
                print(f"Missing required section: {section}")
                return False
        
        print("Configuration is valid!")
        return True
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}")
        return False
    except FileNotFoundError:
        print(f"Config file not found: {config_file}")
        return False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python3 validate_config.py <config_file>")
        sys.exit(1)
    
    if not validate_config(sys.argv[1]):
        sys.exit(1)
```

## FastMCP vs Traditional HTTP Servers

**Key Difference**: FastMCP implements the Model Context Protocol (MCP), not HTTP REST APIs.

| Aspect | Traditional HTTP Server | FastMCP Server |
|--------|------------------------|----------------|
| Protocol | HTTP REST/GraphQL | MCP over STDIO/SSE |
| Client | Web browsers, curl, etc | MCP clients (Claude Desktop, etc) |
| Binding | Binds to network ports | STDIO or MCP-specific transports |
| Usage | General web services | AI agent integrations |
| Discovery | Manual API documentation | Automatic tool/resource discovery |

**When to use each**:
- **FastMCP**: For AI agent integrations, tool discovery, MCP protocol compatibility
- **Traditional HTTP**: For web APIs, REST services, general client access 