# MCP Remote Admin Server Troubleshooting

## Common Issues and Solutions

### 1. FastMCP.run() TypeError: unexpected keyword argument 'host'

**Error:**
```
TypeError: FastMCP.run() got an unexpected keyword argument 'host'
```

**Cause:** FastMCP doesn't support the `host` parameter in its `run()` method.

**Solution:** 
- The server has been updated to only use the `port` parameter
- The `host` configuration is kept for future compatibility but ignored
- Server will bind to all interfaces (equivalent to 0.0.0.0)

**Fixed in:** Server version with updated `main()` function

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

1. **Check logs:** Always check both server logs and audit logs
2. **Validate config:** Ensure JSON configuration is valid
3. **Test permissions:** Verify file and command permissions
4. **Check dependencies:** Ensure all required packages are installed
5. **Review security settings:** Check if operations are allowed by configuration

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