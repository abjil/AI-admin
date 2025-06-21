import json
import os
import asyncio
import logging
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import ssl
import aiohttp
from mcp.server.fastmcp import FastMCP
from mcp import types

# Configuration for remote servers
@dataclass
class RemoteServer:
    """Configuration for a remote MCP server"""
    name: str
    host: str
    port: int
    protocol: str = "https"  # https, ssh, ws
    auth_token: Optional[str] = None
    ssh_key_path: Optional[str] = None
    tags: List[str] = None
    ssl_verify: bool = True
    timeout: int = 30
    retry_attempts: int = 3
    custom_headers: Dict[str, str] = None
    allowed_commands: List[str] = None
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []
        if self.custom_headers is None:
            self.custom_headers = {}
        if self.allowed_commands is None:
            self.allowed_commands = []

class MCPRemoteAdminClient:
    """
    MCP Client that manages connections to multiple remote admin servers
    Acts as the coordination layer between Claude/Host and remote servers
    """
    
    def __init__(self, config_file: str = None):
        self.servers: Dict[str, RemoteServer] = {}
        self.active_connections: Dict[str, Any] = {}
        self.logger = logging.getLogger(__name__)
        self.config_file = config_file or "config.json"
        self.config = {}
        self.security_config = {}
        self.server_groups = {}
    
    def _substitute_env_vars(self, text: str) -> str:
        """Substitute environment variables in text using ${VAR_NAME} syntax"""
        def replace_env_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, f"${{{var_name}}}")  # Keep original if not found
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, text)
    
    def load_config(self) -> bool:
        """Load server configuration from JSON file"""
        try:
            if not os.path.exists(self.config_file):
                self.logger.warning(f"Config file {self.config_file} not found")
                return False
            
            with open(self.config_file, 'r') as f:
                config_content = f.read()
                
            # Substitute environment variables
            config_content = self._substitute_env_vars(config_content)
            
            self.config = json.loads(config_content)
            self.logger.info(f"Loaded configuration from {self.config_file}")
            
            # Load remote servers
            if "remote_servers" in self.config:
                for server_config in self.config["remote_servers"]:
                    server = RemoteServer(
                        name=server_config["name"],
                        host=server_config["host"],
                        port=server_config["port"],  
                        protocol=server_config.get("protocol", "https"),
                        auth_token=server_config.get("auth_token"),
                        ssh_key_path=server_config.get("ssh_key_path"),
                        tags=server_config.get("tags", []),
                        ssl_verify=server_config.get("ssl_verify", True),
                        timeout=server_config.get("timeout", 30),
                        retry_attempts=server_config.get("retry_attempts", 3),
                        custom_headers=server_config.get("custom_headers", {}),
                        allowed_commands=server_config.get("allowed_commands", [])
                    )
                    self.register_server(server)
                    self.logger.info(f"Registered server from config: {server.name}")
            
            # Load security configuration
            if "security" in self.config:
                self.security_config = self.config["security"]
                self.logger.info("Loaded security configuration")
            
            # Load server groups
            if "server_groups" in self.config:
                self.server_groups = self.config["server_groups"]
                self.logger.info(f"Loaded {len(self.server_groups)} server groups")
            
            return True
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error loading config: {e}")
            return False
    
    async def connect_all_servers(self) -> Dict[str, bool]:
        """Connect to all registered servers"""
        connection_results = {}
        
        for server_name in self.servers.keys():
            try:
                success = await self.connect_to_server(server_name)
                connection_results[server_name] = success
                if success:
                    self.logger.info(f"Successfully connected to {server_name}")
                else:
                    self.logger.warning(f"Failed to connect to {server_name}")
            except Exception as e:
                self.logger.error(f"Error connecting to {server_name}: {e}")
                connection_results[server_name] = False
        
        return connection_results
        
    def register_server(self, server: RemoteServer):
        """Register a remote server for administration"""
        self.servers[server.name] = server
        self.logger.info(f"Registered server: {server.name} at {server.host}:{server.port}")
    
    async def connect_to_server(self, server_name: str) -> bool:
        """Establish connection to a remote MCP server"""
        if server_name not in self.servers:
            self.logger.error(f"Server {server_name} not registered")
            return False
            
        server = self.servers[server_name]
        
        for attempt in range(server.retry_attempts):
            try:
                if server.protocol == "https":
                    # Create SSL context based on ssl_verify setting
                    if server.ssl_verify:
                        ssl_context = ssl.create_default_context()
                    else:
                        ssl_context = ssl.create_default_context()
                        ssl_context.check_hostname = False
                        ssl_context.verify_mode = ssl.CERT_NONE
                        self.logger.warning(f"SSL verification disabled for {server_name}")
                    
                    # Create connector with timeout and SSL settings
                    timeout = aiohttp.ClientTimeout(total=server.timeout)
                    connector = aiohttp.TCPConnector(ssl=ssl_context)
                    session = aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout
                    )
                    
                    # Test connection
                    url = f"{server.protocol}://{server.host}:{server.port}/health"
                    headers = {}
                    
                    # Add authentication header
                    if server.auth_token:
                        headers["Authorization"] = f"Bearer {server.auth_token}"
                    
                    # Add custom headers
                    headers.update(server.custom_headers)
                        
                    async with session.get(url, headers=headers) as response:
                        if response.status == 200:
                            self.active_connections[server_name] = session
                            self.logger.info(f"Connected to {server_name} on attempt {attempt + 1}")
                            return True
                        else:
                            self.logger.warning(f"Health check failed for {server_name}: HTTP {response.status}")
                            if attempt < server.retry_attempts - 1:
                                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                                
            except asyncio.TimeoutError:
                self.logger.warning(f"Connection timeout to {server_name} (attempt {attempt + 1}/{server.retry_attempts})")
                if attempt < server.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                self.logger.error(f"Failed to connect to {server_name} (attempt {attempt + 1}/{server.retry_attempts}): {e}")
                if attempt < server.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
        
        return False
    
    async def execute_remote_command(self, server_name: str, command: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Execute a command on a remote server"""
        if server_name not in self.active_connections:
            await self.connect_to_server(server_name)
        
        if server_name not in self.active_connections:
            return {"error": f"Unable to connect to {server_name}"}
        
        server = self.servers[server_name]
        session = self.active_connections[server_name]
        
        # Check if command is allowed for this server
        if server.allowed_commands and command not in server.allowed_commands:
            return {"error": f"Command '{command}' not allowed for server {server_name}. Allowed commands: {server.allowed_commands}"}
        
        try:
            url = f"{server.protocol}://{server.host}:{server.port}/mcp"
            headers = {"Content-Type": "application/json"}
            
            # Add authentication header
            if server.auth_token:
                headers["Authorization"] = f"Bearer {server.auth_token}"
            
            # Add custom headers
            headers.update(server.custom_headers)
            
            payload = {
                "jsonrpc": "2.0",
                "id": f"{server_name}_{datetime.now().isoformat()}",
                "method": command,
                "params": params or {}
            }
            
            # Use server-specific timeout
            timeout = aiohttp.ClientTimeout(total=server.timeout)
            
            async with session.post(url, json=payload, headers=headers, timeout=timeout) as response:
                return await response.json()
                
        except asyncio.TimeoutError:
            self.logger.error(f"Command execution timed out on {server_name} after {server.timeout}s")
            return {"error": f"Command timed out after {server.timeout}s"}
        except Exception as e:
            self.logger.error(f"Command execution failed on {server_name}: {e}")
            return {"error": str(e)}

# FastMCP Server - This runs on the HOST (Claude Desktop side)
mcp_app = FastMCP("Remote Admin Controller")

# Global client instance
admin_client = MCPRemoteAdminClient()

@mcp_app.tool()
async def load_config_file(config_file: str = "config.json") -> str:
    """Load server configuration from JSON file"""
    global admin_client
    
    # Create new client with specified config file
    admin_client = MCPRemoteAdminClient(config_file)
    
    success = admin_client.load_config()
    if success:
        # Try to connect to all servers
        connection_results = await admin_client.connect_all_servers()
        
        successful_connections = sum(1 for connected in connection_results.values() if connected)
        total_servers = len(connection_results)
        
        return f"Loaded {total_servers} servers from {config_file}. Successfully connected to {successful_connections}/{total_servers} servers."
    else:
        return f"Failed to load configuration from {config_file}"

@mcp_app.tool()
async def get_config_status() -> Dict[str, Any]:
    """Get current configuration status and server connectivity"""
    config_info = {
        "config_file": admin_client.config_file,
        "config_loaded": bool(admin_client.config),
        "servers_registered": len(admin_client.servers),
        "servers_connected": len(admin_client.active_connections),
        "servers": []
    }
    
    for name, server in admin_client.servers.items():
        is_connected = name in admin_client.active_connections
        config_info["servers"].append({
            "name": name,
            "host": server.host,
            "port": server.port,
            "protocol": server.protocol,
            "connected": is_connected,
            "tags": server.tags,
            "has_auth_token": bool(server.auth_token),
            "ssl_verify": server.ssl_verify,
            "timeout": server.timeout,
            "retry_attempts": server.retry_attempts,
            "custom_headers": server.custom_headers,
            "allowed_commands": server.allowed_commands,
            "command_restrictions": len(server.allowed_commands) > 0
        })
    
    # Add security and server group info
    if admin_client.security_config:
        config_info["security"] = admin_client.security_config
    
    if admin_client.server_groups:
        config_info["server_groups"] = admin_client.server_groups
    
    return config_info

@mcp_app.tool()
async def get_server_groups() -> Dict[str, Any]:
    """Get all configured server groups and their restrictions"""
    if not admin_client.server_groups:
        return {"error": "No server groups configured"}
    
    return {
        "server_groups": admin_client.server_groups,
        "groups_count": len(admin_client.server_groups)
    }

@mcp_app.tool()
async def get_servers_by_group(group_name: str) -> Dict[str, Any]:
    """Get all servers that belong to a specific group (by matching tags)"""
    if group_name not in admin_client.server_groups:
        return {"error": f"Server group '{group_name}' not found"}
    
    group_config = admin_client.server_groups[group_name]
    group_tags = group_config.get("tags", [])
    
    matching_servers = []
    for name, server in admin_client.servers.items():
        # Check if server has any of the group's tags
        if any(tag in server.tags for tag in group_tags):
            is_connected = name in admin_client.active_connections
            matching_servers.append({
                "name": name,
                "host": server.host,
                "port": server.port,
                "connected": is_connected,
                "tags": server.tags,
                "restrictions": group_config.get("restrictions", {})
            })
    
    return {
        "group_name": group_name,
        "group_config": group_config,
        "matching_servers": matching_servers,
        "server_count": len(matching_servers)
    }

@mcp_app.tool()
async def validate_command_for_group(group_name: str, command: str) -> Dict[str, Any]:
    """Check if a command is allowed for servers in a specific group"""
    if group_name not in admin_client.server_groups:
        return {"error": f"Server group '{group_name}' not found"}
    
    group_config = admin_client.server_groups[group_name]
    restrictions = group_config.get("restrictions", {})
    
    # Check various restriction types
    validation_result = {
        "group_name": group_name,
        "command": command,
        "allowed": True,
        "restrictions_checked": []
    }
    
    # Check dangerous commands restriction
    if not restrictions.get("dangerous_commands", True):
        dangerous_commands = ["shell_exec", "service_restart", "reboot", "shutdown"]
        if command in dangerous_commands:
            validation_result["allowed"] = False
            validation_result["restrictions_checked"].append("dangerous_commands_disabled")
    
    # Check file write restriction
    if not restrictions.get("file_write", True):
        file_write_commands = ["write_file", "edit_file", "create_file"]
        if command in file_write_commands:
            validation_result["allowed"] = False
            validation_result["restrictions_checked"].append("file_write_disabled")
    
    # Check service restart restriction
    if not restrictions.get("service_restart", True):
        if command == "service_restart":
            validation_result["allowed"] = False
            validation_result["restrictions_checked"].append("service_restart_disabled")
    
    return validation_result

@mcp_app.tool()
async def register_remote_server(
    name: str,
    host: str, 
    port: int,
    protocol: str = "https",
    auth_token: str = None,
    tags: List[str] = None,
    ssl_verify: bool = True,
    timeout: int = 30,
    retry_attempts: int = 3,
    custom_headers: Dict[str, str] = None,
    allowed_commands: List[str] = None
) -> str:
    """Register a new remote server for administration"""
    server = RemoteServer(
        name=name,
        host=host,
        port=port,
        protocol=protocol,
        auth_token=auth_token,
        tags=tags or [],
        ssl_verify=ssl_verify,
        timeout=timeout,
        retry_attempts=retry_attempts,
        custom_headers=custom_headers or {},
        allowed_commands=allowed_commands or []
    )
    
    admin_client.register_server(server)
    success = await admin_client.connect_to_server(name)
    
    if success:
        return f"Successfully registered and connected to {name}"
    else:
        return f"Registered {name} but connection failed. Check server status."

@mcp_app.tool()
async def list_servers() -> List[Dict[str, Any]]:
    """List all registered remote servers and their status"""
    servers_info = []
    
    for name, server in admin_client.servers.items():
        is_connected = name in admin_client.active_connections
        servers_info.append({
            "name": name,
            "host": server.host,
            "port": server.port,
            "protocol": server.protocol,
            "connected": is_connected,
            "tags": server.tags,
            "ssl_verify": server.ssl_verify,
            "timeout": server.timeout,
            "retry_attempts": server.retry_attempts,
            "has_custom_headers": len(server.custom_headers) > 0,
            "custom_headers": server.custom_headers,
            "has_command_restrictions": len(server.allowed_commands) > 0,
            "allowed_commands": server.allowed_commands
        })
    
    return servers_info

@mcp_app.tool()
async def get_system_status(server_name: str) -> Dict[str, Any]:
    """Get system status from a remote server"""
    return await admin_client.execute_remote_command(
        server_name, 
        "system_status"
    )

@mcp_app.tool()
async def read_remote_file(server_name: str, file_path: str) -> Dict[str, Any]:
    """Read a file from a remote server"""
    return await admin_client.execute_remote_command(
        server_name,
        "read_file",
        {"path": file_path}
    )

@mcp_app.tool()
async def execute_shell_command(server_name: str, command: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute a shell command on a remote server"""
    return await admin_client.execute_remote_command(
        server_name,
        "shell_exec",
        {"command": command, "timeout": timeout}
    )

@mcp_app.tool()
async def get_service_status(server_name: str, service_name: str) -> Dict[str, Any]:
    """Get status of a specific service on remote server"""
    return await admin_client.execute_remote_command(
        server_name,
        "service_status",
        {"service": service_name}
    )

@mcp_app.tool()
async def restart_service(server_name: str, service_name: str) -> Dict[str, Any]:
    """Restart a service on remote server"""
    return await admin_client.execute_remote_command(
        server_name,
        "service_restart",
        {"service": service_name}
    )

@mcp_app.tool()
async def get_system_logs(server_name: str, log_type: str = "syslog", lines: int = 100) -> Dict[str, Any]:
    """Retrieve system logs from remote server"""
    return await admin_client.execute_remote_command(
        server_name,
        "get_logs",
        {"type": log_type, "lines": lines}
    )

@mcp_app.tool()
async def bulk_command(command: str, server_tags: List[str] = None, server_names: List[str] = None) -> Dict[str, Any]:
    """Execute a command across multiple servers filtered by tags or names"""
    target_servers = []
    
    if server_names:
        target_servers = server_names
    elif server_tags:
        # Filter servers by tags
        for name, server in admin_client.servers.items():
            if any(tag in server.tags for tag in server_tags):
                target_servers.append(name)
    else:
        # All servers
        target_servers = list(admin_client.servers.keys())
    
    results = {}
    tasks = []
    
    for server_name in target_servers:
        task = admin_client.execute_remote_command(server_name, command)
        tasks.append((server_name, task))
    
    # Execute in parallel
    for server_name, task in tasks:
        try:
            result = await task
            results[server_name] = result
        except Exception as e:
            results[server_name] = {"error": str(e)}
    
    return results

if __name__ == "__main__":
    import argparse
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Remote Admin Controller")
    parser.add_argument("--config", "-c", default="config.json", 
                       help="Path to configuration file (default: config.json)")
    parser.add_argument("--no-auto-load", action="store_true", 
                       help="Don't automatically load config file on startup")
    parser.add_argument("--port", "-p", type=int, default=None,
                       help="Port to run MCP server on")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    async def initialize_client():
        """Initialize the admin client with async operations"""
        global admin_client
        
        # Initialize client with config file
        admin_client = MCPRemoteAdminClient(args.config)
        
        # Auto-load config if not disabled
        if not args.no_auto_load:
            logging.info(f"Auto-loading configuration from {args.config}")
            success = admin_client.load_config()
            
            if success:
                # Try to connect to all servers
                connection_results = await admin_client.connect_all_servers()
                successful_connections = sum(1 for connected in connection_results.values() if connected)
                total_servers = len(connection_results)
                
                logging.info(f"Loaded {total_servers} servers from config")
                logging.info(f"Successfully connected to {successful_connections}/{total_servers} servers")
                
                if successful_connections < total_servers:
                    failed_servers = [name for name, connected in connection_results.items() if not connected]
                    logging.warning(f"Failed to connect to: {', '.join(failed_servers)}")
            else:
                logging.warning(f"Could not load config file {args.config} - servers can be registered manually")
    
    def main():
        # Configure logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        try:
            # Initialize client asynchronously
            asyncio.run(initialize_client())
            
            # Note: FastMCP doesn't support port parameter in run()
            if args.port:
                logging.warning(f"FastMCP doesn't support custom port in run(), ignoring port setting: {args.port}")
                logging.warning("FastMCP will use its default port configuration")
            
            # Run the MCP server synchronously (FastMCP manages its own event loop)
            logging.info("Starting MCP Remote Admin Controller...")
            mcp_app.run()
            
        except KeyboardInterrupt:
            logging.info("Received interrupt signal, shutting down...")
        except Exception as e:
            logging.error(f"Unexpected error: {e}")
            raise
    
    main()