"""
MCP Tools Provider for Remote Admin system.
Follows Interface Segregation Principle - focused only on MCP tool functionality.
"""
from typing import List, Dict, Any, Optional
from mcp.server.fastmcp import FastMCP
from .services import RemoteAdminService
from .models import RemoteServer


class MCPToolsProvider:
    """
    Provides MCP tools for the Remote Admin system.
    Follows Single Responsibility Principle - only handles MCP tool registration.
    """
    
    def __init__(self, admin_service: RemoteAdminService, mcp_app: FastMCP):
        self._admin_service = admin_service
        self._mcp_app = mcp_app
        self._register_tools()
    
    def _register_tools(self) -> None:
        """Register all MCP tools"""
        self._register_config_tools()
        self._register_server_management_tools()
        self._register_security_tools()
        self._register_system_operation_tools()
    
    def _register_config_tools(self) -> None:
        """Register configuration-related tools"""
        
        @self._mcp_app.tool()
        async def load_config_file(config_file: str = "config.json") -> str:
            """Load server configuration from JSON file"""
            success = await self._admin_service.initialize(config_file)
            if success:
                connection_results = await self._admin_service.connect_all_servers()
                successful_connections = sum(1 for connected in connection_results.values() if connected)
                total_servers = len(connection_results)
                return f"Loaded {total_servers} servers from {config_file}. Successfully connected to {successful_connections}/{total_servers} servers."
            else:
                return f"Failed to load configuration from {config_file}"
        
        @self._mcp_app.tool()
        async def get_config_status() -> Dict[str, Any]:
            """Get current configuration status and server connectivity"""
            servers = self._admin_service.get_all_servers()
            server_info = []
            
            for name, server in servers.items():
                is_connected = self._admin_service.is_connected(name)
                conn_info = self._admin_service.get_connection_info(name)
                
                server_info.append({
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
                    "command_restrictions": len(server.allowed_commands) > 0,
                    "connection_status": conn_info.status.value if conn_info else "unknown",
                    "last_error": conn_info.last_error if conn_info else None
                })
            
            return {
                "servers_registered": len(servers),
                "servers_connected": sum(1 for info in server_info if info["connected"]),
                "servers": server_info,
                "server_groups": self._admin_service.get_server_groups()
            }
    
    def _register_server_management_tools(self) -> None:
        """Register server management tools"""
        
        @self._mcp_app.tool()
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
            
            success = await self._admin_service.register_server(server)
            if success:
                connect_success = await self._admin_service.connect_to_server(name)
                if connect_success:
                    return f"Successfully registered and connected to {name}"
                else:
                    return f"Registered {name} but connection failed. Check server status."
            else:
                return f"Failed to register server {name}"
        
        @self._mcp_app.tool()
        async def list_servers() -> List[Dict[str, Any]]:
            """List all registered remote servers and their status"""
            servers = self._admin_service.get_all_servers()
            servers_info = []
            
            for name, server in servers.items():
                is_connected = self._admin_service.is_connected(name)
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
        
        @self._mcp_app.tool()
        async def connect_to_server(server_name: str) -> str:
            """Connect to a specific server"""
            success = await self._admin_service.connect_to_server(server_name)
            if success:
                return f"Successfully connected to {server_name}"
            else:
                return f"Failed to connect to {server_name}"
    
    def _register_security_tools(self) -> None:
        """Register security-related tools"""
        
        @self._mcp_app.tool()
        async def get_server_groups() -> Dict[str, Any]:
            """Get all configured server groups and their restrictions"""
            server_groups = self._admin_service.get_server_groups()
            if not server_groups:
                return {"error": "No server groups configured"}
            
            return {
                "server_groups": {name: {
                    "tags": group.tags,
                    "restrictions": {
                        "dangerous_commands": group.restrictions.dangerous_commands,
                        "file_write": group.restrictions.file_write,
                        "service_restart": group.restrictions.service_restart
                    }
                } for name, group in server_groups.items()},
                "groups_count": len(server_groups)
            }
        
        @self._mcp_app.tool()
        async def get_servers_by_group(group_name: str) -> Dict[str, Any]:
            """Get all servers that belong to a specific group (by matching tags)"""
            server_groups = self._admin_service.get_server_groups()
            if group_name not in server_groups:
                return {"error": f"Server group '{group_name}' not found"}
            
            servers_in_group = self._admin_service.get_servers_in_group(group_name)
            matching_servers = []
            
            for server_name in servers_in_group:
                server = self._admin_service.get_server(server_name)
                if server:
                    is_connected = self._admin_service.is_connected(server_name)
                    matching_servers.append({
                        "name": server_name,
                        "host": server.host,
                        "port": server.port,
                        "connected": is_connected,
                        "tags": server.tags
                    })
            
            group = server_groups[group_name]
            return {
                "group_name": group_name,
                "group_tags": group.tags,
                "restrictions": {
                    "dangerous_commands": group.restrictions.dangerous_commands,
                    "file_write": group.restrictions.file_write,
                    "service_restart": group.restrictions.service_restart
                },
                "matching_servers": matching_servers,
                "server_count": len(matching_servers)
            }
        
        @self._mcp_app.tool()
        async def validate_command_for_group(group_name: str, command: str) -> Dict[str, Any]:
            """Check if a command is allowed for servers in a specific group"""
            allowed = self._admin_service.is_command_allowed_for_group(group_name, command)
            
            return {
                "group_name": group_name,
                "command": command,
                "allowed": allowed
            }
    
    def _register_system_operation_tools(self) -> None:
        """Register system operation tools"""
        
        @self._mcp_app.tool()
        async def get_system_status(server_name: str) -> Dict[str, Any]:
            """Get system status from a remote server"""
            result = await self._admin_service.execute_command(server_name, "system_status")
            return {
                "server_name": server_name,
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "execution_time": result.execution_time
            }
        
        @self._mcp_app.tool()
        async def read_remote_file(server_name: str, file_path: str) -> Dict[str, Any]:
            """Read a file from a remote server"""
            result = await self._admin_service.execute_command(
                server_name, "read_file", {"path": file_path}
            )
            return {
                "server_name": server_name,
                "file_path": file_path,
                "success": result.success,
                "result": result.result,
                "error": result.error
            }
        
        @self._mcp_app.tool()
        async def execute_shell_command(server_name: str, command: str, timeout: int = 30) -> Dict[str, Any]:
            """Execute a shell command on a remote server"""
            result = await self._admin_service.execute_command(
                server_name, "shell_exec", {"command": command, "timeout": timeout}
            )
            return {
                "server_name": server_name,
                "command": command,
                "success": result.success,
                "result": result.result,
                "error": result.error,
                "execution_time": result.execution_time
            }
        
        @self._mcp_app.tool()
        async def get_service_status(server_name: str, service_name: str) -> Dict[str, Any]:
            """Get status of a specific service on remote server"""
            result = await self._admin_service.execute_command(
                server_name, "service_status", {"service": service_name}
            )
            return {
                "server_name": server_name,
                "service_name": service_name,
                "success": result.success,
                "result": result.result,
                "error": result.error
            }
        
        @self._mcp_app.tool()
        async def restart_service(server_name: str, service_name: str) -> Dict[str, Any]:
            """Restart a service on remote server"""
            result = await self._admin_service.execute_command(
                server_name, "service_restart", {"service": service_name}
            )
            return {
                "server_name": server_name,
                "service_name": service_name,
                "success": result.success,
                "result": result.result,
                "error": result.error
            }
        
        @self._mcp_app.tool()
        async def get_system_logs(server_name: str, log_type: str = "syslog", lines: int = 100) -> Dict[str, Any]:
            """Retrieve system logs from remote server"""
            result = await self._admin_service.execute_command(
                server_name, "get_logs", {"type": log_type, "lines": lines}
            )
            return {
                "server_name": server_name,
                "log_type": log_type,
                "lines_requested": lines,
                "success": result.success,
                "result": result.result,
                "error": result.error
            }
        
        @self._mcp_app.tool()
        async def bulk_command(
            command: str, 
            server_tags: List[str] = None, 
            server_names: List[str] = None
        ) -> Dict[str, Any]:
            """Execute a command across multiple servers filtered by tags or names"""
            target_servers = []
            
            if server_names:
                target_servers = server_names
            elif server_tags:
                servers_by_tags = self._admin_service.get_servers_by_tags(server_tags)
                target_servers = [server.name for server in servers_by_tags]
            else:
                all_servers = self._admin_service.get_all_servers()
                target_servers = list(all_servers.keys())
            
            if not target_servers:
                return {"error": "No servers found matching the criteria"}
            
            bulk_result = await self._admin_service.execute_bulk_command(target_servers, command)
            
            # Convert CommandResult objects to dictionaries
            results_dict = {}
            for server_name, cmd_result in bulk_result.results.items():
                results_dict[server_name] = {
                    "success": cmd_result.success,
                    "result": cmd_result.result,
                    "error": cmd_result.error,
                    "execution_time": cmd_result.execution_time
                }
            
            return {
                "command": command,
                "target_servers": target_servers,
                "success_count": bulk_result.success_count,
                "failed_count": bulk_result.failed_count,
                "results": results_dict
            } 