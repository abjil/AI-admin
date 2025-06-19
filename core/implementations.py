"""
Concrete implementations of interfaces for MCP Remote Admin system.
Each class follows Single Responsibility Principle.
"""
import json
import os
import re
import ssl
import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from .interfaces import (
    IConfigurationManager, IServerRegistry, IConnectionManager, ICommandExecutor,
    ISecurityManager, IEnvironmentVariableSubstitutor, IAuditLogger, IConnectionFactory
)
from .models import (
    RemoteServer, SecurityConfig, ServerGroup, ConnectionInfo, ConnectionStatus,
    CommandResult, BulkCommandResult, ServerGroupRestrictions, Protocol
)


class EnvironmentVariableSubstitutor(IEnvironmentVariableSubstitutor):
    """Handles environment variable substitution"""
    
    def substitute_variables(self, text: str) -> str:
        """Substitute environment variables in text using ${VAR_NAME} syntax"""
        def replace_env_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, f"${{{var_name}}}")  # Keep original if not found
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, text)


class ConfigurationManager(IConfigurationManager):
    """Manages configuration loading and parsing"""
    
    def __init__(self, env_substitutor: IEnvironmentVariableSubstitutor):
        self._env_substitutor = env_substitutor
        self._servers: List[RemoteServer] = []
        self._security_config: Optional[SecurityConfig] = None
        self._server_groups: Dict[str, ServerGroup] = {}
        self._logger = logging.getLogger(__name__)
    
    async def load_config(self, config_file: str) -> bool:
        """Load configuration from JSON file"""
        try:
            if not os.path.exists(config_file):
                self._logger.warning(f"Config file {config_file} not found")
                return False
            
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            # Substitute environment variables
            config_content = self._env_substitutor.substitute_variables(config_content)
            config = json.loads(config_content)
            
            self._load_servers(config)
            self._load_security_config(config)
            self._load_server_groups(config)
            
            self._logger.info(f"Successfully loaded configuration from {config_file}")
            return True
            
        except json.JSONDecodeError as e:
            self._logger.error(f"Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            self._logger.error(f"Error loading config: {e}")
            return False
    
    def _load_servers(self, config: Dict[str, Any]) -> None:
        """Load server configurations"""
        if "remote_servers" not in config:
            return
        
        self._servers = []
        for server_config in config["remote_servers"]:
            server = RemoteServer(
                name=server_config["name"],
                host=server_config["host"],
                port=server_config["port"],
                protocol=server_config.get("protocol", Protocol.HTTPS.value),
                auth_token=server_config.get("auth_token"),
                ssh_key_path=server_config.get("ssh_key_path"),
                tags=server_config.get("tags", []),
                ssl_verify=server_config.get("ssl_verify", True),
                timeout=server_config.get("timeout", 30),
                retry_attempts=server_config.get("retry_attempts", 3),
                custom_headers=server_config.get("custom_headers", {}),
                allowed_commands=server_config.get("allowed_commands", [])
            )
            self._servers.append(server)
    
    def _load_security_config(self, config: Dict[str, Any]) -> None:
        """Load security configuration"""
        if "security" not in config:
            return
        
        sec_config = config["security"]
        rate_limit = sec_config.get("rate_limit", {})
        audit_log = sec_config.get("audit_log", {})
        
        self._security_config = SecurityConfig(
            default_timeout=sec_config.get("default_timeout", 30),
            max_concurrent_connections=sec_config.get("max_concurrent_connections", 10),
            rate_limit_requests_per_minute=rate_limit.get("requests_per_minute", 60),
            rate_limit_burst_size=rate_limit.get("burst_size", 10),
            audit_log_enabled=audit_log.get("enabled", True),
            audit_log_file=audit_log.get("file", "/var/log/mcp-admin/audit.log"),
            audit_log_level=audit_log.get("level", "INFO")
        )
    
    def _load_server_groups(self, config: Dict[str, Any]) -> None:
        """Load server groups configuration"""
        if "server_groups" not in config:
            return
        
        self._server_groups = {}
        for group_name, group_config in config["server_groups"].items():
            restrictions_config = group_config.get("restrictions", {})
            restrictions = ServerGroupRestrictions(
                dangerous_commands=restrictions_config.get("dangerous_commands", True),
                file_write=restrictions_config.get("file_write", True),
                service_restart=restrictions_config.get("service_restart", True)
            )
            
            self._server_groups[group_name] = ServerGroup(
                name=group_name,
                tags=group_config.get("tags", []),
                restrictions=restrictions
            )
    
    def get_servers(self) -> List[RemoteServer]:
        """Get all configured servers"""
        return self._servers.copy()
    
    def get_security_config(self) -> Optional[SecurityConfig]:
        """Get security configuration"""
        return self._security_config
    
    def get_server_groups(self) -> Dict[str, ServerGroup]:
        """Get server groups"""
        return self._server_groups.copy()


class ServerRegistry(IServerRegistry):
    """Manages server registration and lookup"""
    
    def __init__(self):
        self._servers: Dict[str, RemoteServer] = {}
        self._logger = logging.getLogger(__name__)
    
    def register_server(self, server: RemoteServer) -> bool:
        """Register a server"""
        try:
            self._servers[server.name] = server
            self._logger.info(f"Registered server: {server.name} at {server.host}:{server.port}")
            return True
        except Exception as e:
            self._logger.error(f"Failed to register server {server.name}: {e}")
            return False
    
    def unregister_server(self, server_name: str) -> bool:
        """Unregister a server"""
        if server_name in self._servers:
            del self._servers[server_name]
            self._logger.info(f"Unregistered server: {server_name}")
            return True
        return False
    
    def get_server(self, server_name: str) -> Optional[RemoteServer]:
        """Get server by name"""
        return self._servers.get(server_name)
    
    def get_all_servers(self) -> Dict[str, RemoteServer]:
        """Get all registered servers"""
        return self._servers.copy()
    
    def get_servers_by_tags(self, tags: List[str]) -> List[RemoteServer]:
        """Get servers matching any of the given tags"""
        matching_servers = []
        for server in self._servers.values():
            if any(tag in server.tags for tag in tags):
                matching_servers.append(server)
        return matching_servers


class HTTPSConnectionFactory(IConnectionFactory):
    """Factory for creating HTTPS connections"""
    
    def supports_protocol(self, protocol: str) -> bool:
        """Check if factory supports the protocol"""
        return protocol.lower() in [Protocol.HTTPS.value, Protocol.HTTP.value]
    
    async def create_connection(self, server: RemoteServer) -> aiohttp.ClientSession:
        """Create an HTTPS connection for the server"""
        # Create SSL context based on ssl_verify setting
        if server.ssl_verify:
            ssl_context = ssl.create_default_context()
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
        
        # Create connector with timeout and SSL settings
        timeout = aiohttp.ClientTimeout(total=server.timeout)
        connector = aiohttp.TCPConnector(ssl=ssl_context)
        
        return aiohttp.ClientSession(
            connector=connector,
            timeout=timeout
        )


class ConnectionManager(IConnectionManager):
    """Manages connections to remote servers"""
    
    def __init__(self, connection_factories: List[IConnectionFactory]):
        self._connection_factories = connection_factories
        self._connections: Dict[str, Any] = {}
        self._connection_info: Dict[str, ConnectionInfo] = {}
        self._logger = logging.getLogger(__name__)
    
    async def connect_to_server(self, server: RemoteServer) -> bool:
        """Connect to a specific server"""
        factory = self._find_factory_for_protocol(server.protocol)
        if not factory:
            self._logger.error(f"No factory available for protocol: {server.protocol}")
            return False
        
        self._connection_info[server.name] = ConnectionInfo(
            server_name=server.name,
            status=ConnectionStatus.CONNECTING
        )
        
        for attempt in range(server.retry_attempts):
            try:
                session = await factory.create_connection(server)
                
                # Test connection with health check
                success = await self._health_check(server, session)
                if success:
                    self._connections[server.name] = session
                    self._connection_info[server.name] = ConnectionInfo(
                        server_name=server.name,
                        status=ConnectionStatus.CONNECTED,
                        connected_at=datetime.now().isoformat()
                    )
                    self._logger.info(f"Connected to {server.name} on attempt {attempt + 1}")
                    return True
                else:
                    if attempt < server.retry_attempts - 1:
                        await asyncio.sleep(2 ** attempt)  # Exponential backoff
                        
            except asyncio.TimeoutError:
                self._logger.warning(f"Connection timeout to {server.name} (attempt {attempt + 1}/{server.retry_attempts})")
                if attempt < server.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                error_msg = f"Failed to connect to {server.name} (attempt {attempt + 1}/{server.retry_attempts}): {e}"
                self._logger.error(error_msg)
                if attempt < server.retry_attempts - 1:
                    await asyncio.sleep(2 ** attempt)
        
        self._connection_info[server.name] = ConnectionInfo(
            server_name=server.name,
            status=ConnectionStatus.FAILED,
            last_error="Connection failed after all retry attempts"
        )
        return False
    
    async def _health_check(self, server: RemoteServer, session: aiohttp.ClientSession) -> bool:
        """Perform health check on server connection"""
        try:
            url = f"{server.protocol}://{server.host}:{server.port}/health"
            headers = {}
            
            if server.auth_token:
                headers["Authorization"] = f"Bearer {server.auth_token}"
            headers.update(server.custom_headers)
            
            async with session.get(url, headers=headers) as response:
                return response.status == 200
        except Exception:
            return False
    
    def _find_factory_for_protocol(self, protocol: str) -> Optional[IConnectionFactory]:
        """Find appropriate factory for protocol"""
        for factory in self._connection_factories:
            if factory.supports_protocol(protocol):
                return factory
        return None
    
    async def disconnect_from_server(self, server_name: str) -> bool:
        """Disconnect from a server"""
        if server_name in self._connections:
            try:
                session = self._connections[server_name]
                await session.close()
                del self._connections[server_name]
                
                if server_name in self._connection_info:
                    self._connection_info[server_name].status = ConnectionStatus.DISCONNECTED
                
                self._logger.info(f"Disconnected from {server_name}")
                return True
            except Exception as e:
                self._logger.error(f"Error disconnecting from {server_name}: {e}")
                return False
        return False
    
    async def connect_all_servers(self, servers: List[RemoteServer]) -> Dict[str, bool]:
        """Connect to all servers"""
        connection_results = {}
        tasks = []
        
        for server in servers:
            task = asyncio.create_task(self.connect_to_server(server))
            tasks.append((server.name, task))
        
        for server_name, task in tasks:
            try:
                success = await task
                connection_results[server_name] = success
            except Exception as e:
                self._logger.error(f"Error connecting to {server_name}: {e}")
                connection_results[server_name] = False
        
        return connection_results
    
    def get_connection_info(self, server_name: str) -> Optional[ConnectionInfo]:
        """Get connection information for a server"""
        return self._connection_info.get(server_name)
    
    def is_connected(self, server_name: str) -> bool:
        """Check if server is connected"""
        return server_name in self._connections


class SecurityManager(ISecurityManager):
    """Manages security policies and access control"""
    
    def __init__(self, server_registry: IServerRegistry, server_groups: Dict[str, ServerGroup]):
        self._server_registry = server_registry
        self._server_groups = server_groups
        self._dangerous_commands = {
            "shell_exec", "service_restart", "reboot", "shutdown"
        }
        self._file_write_commands = {
            "write_file", "edit_file", "create_file"
        }
    
    def is_command_allowed(self, server_name: str, command: str) -> bool:
        """Check if command is allowed for server"""
        server = self._server_registry.get_server(server_name)
        if not server:
            return False
        
        # If server has specific allowed commands, check against that list
        if server.allowed_commands:
            return command in server.allowed_commands
        
        # Check group restrictions
        for group in self._server_groups.values():
            if any(tag in server.tags for tag in group.tags):
                if not self._is_command_allowed_by_restrictions(command, group.restrictions):
                    return False
        
        return True
    
    def is_command_allowed_for_group(self, group_name: str, command: str) -> bool:
        """Check if command is allowed for server group"""
        if group_name not in self._server_groups:
            return False
        
        group = self._server_groups[group_name]
        return self._is_command_allowed_by_restrictions(command, group.restrictions)
    
    def _is_command_allowed_by_restrictions(self, command: str, restrictions: ServerGroupRestrictions) -> bool:
        """Check command against group restrictions"""
        if not restrictions.dangerous_commands and command in self._dangerous_commands:
            return False
        
        if not restrictions.file_write and command in self._file_write_commands:
            return False
        
        if not restrictions.service_restart and command == "service_restart":
            return False
        
        return True
    
    def get_servers_in_group(self, group_name: str) -> List[str]:
        """Get servers belonging to a group"""
        if group_name not in self._server_groups:
            return []
        
        group = self._server_groups[group_name]
        servers = self._server_registry.get_servers_by_tags(group.tags)
        return [server.name for server in servers]
    
    def validate_server_access(self, server_name: str, operation: str) -> bool:
        """Validate if operation is allowed on server"""
        # Basic validation - can be extended with more complex rules
        server = self._server_registry.get_server(server_name)
        return server is not None


class CommandExecutor(ICommandExecutor):
    """Executes commands on remote servers"""
    
    def __init__(
        self, 
        connection_manager: IConnectionManager,
        server_registry: IServerRegistry,
        security_manager: ISecurityManager
    ):
        self._connection_manager = connection_manager
        self._server_registry = server_registry
        self._security_manager = security_manager
        self._logger = logging.getLogger(__name__)
    
    async def execute_command(
        self,
        server_name: str,
        command: str,
        params: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """Execute command on a server"""
        start_time = datetime.now()
        
        # Validate command is allowed
        if not self._security_manager.is_command_allowed(server_name, command):
            return CommandResult(
                server_name=server_name,
                command=command,
                success=False,
                result={},
                execution_time=0.0,
                error=f"Command '{command}' not allowed for server {server_name}"
            )
        
        # Check connection  
        if not self._connection_manager.is_connected(server_name):
            return CommandResult(
                server_name=server_name,
                command=command,
                success=False,
                result={},
                execution_time=0.0,
                error=f"Not connected to server {server_name}"
            )
        
        try:
            server = self._server_registry.get_server(server_name)
            if not server:
                raise ValueError(f"Server {server_name} not found in registry")
            
            result = await self._execute_remote_command(server, command, params)
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return CommandResult(
                server_name=server_name,
                command=command,
                success=True,
                result=result,
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self._logger.error(f"Command execution failed on {server_name}: {e}")
            
            return CommandResult(
                server_name=server_name,
                command=command,
                success=False,
                result={},
                execution_time=execution_time,
                error=str(e)
            )
    
    async def _execute_remote_command(
        self,
        server: RemoteServer,
        command: str,
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute command on remote server via HTTP"""
        # This would be implemented based on the specific protocol
        # For now, returning a placeholder implementation
        return {
            "status": "success",
            "message": f"Command {command} executed on {server.name}",
            "params": params or {}
        }
    
    async def execute_bulk_command(
        self,
        server_names: List[str],
        command: str,
        params: Optional[Dict[str, Any]] = None
    ) -> BulkCommandResult:
        """Execute command on multiple servers"""
        tasks = []
        for server_name in server_names:
            task = asyncio.create_task(self.execute_command(server_name, command, params))
            tasks.append((server_name, task))
        
        results = {}
        success_count = 0
        failed_count = 0
        
        for server_name, task in tasks:
            try:
                result = await task
                results[server_name] = result
                if result.success:
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as e:
                failed_count += 1
                results[server_name] = CommandResult(
                    server_name=server_name,
                    command=command,
                    success=False,
                    result={},
                    execution_time=0.0,
                    error=str(e)
                )
        
        return BulkCommandResult(
            command=command,
            target_servers=server_names,
            results=results,
            success_count=success_count,
            failed_count=failed_count
        )


class AuditLogger(IAuditLogger):
    """Handles audit logging for compliance and security"""
    
    def __init__(self, log_file: str, log_level: str = "INFO"):
        self._log_file = log_file
        self._logger = logging.getLogger("audit")
        self._logger.setLevel(getattr(logging, log_level.upper()))
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Add file handler for audit logs
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
    
    async def log_command_execution(
        self,
        server_name: str,
        command: str,
        user: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log command execution for audit"""
        status = "SUCCESS" if success else "FAILED"
        message = f"COMMAND_EXEC - Server: {server_name}, Command: {command}, User: {user}, Status: {status}"
        if error:
            message += f", Error: {error}"
        
        if success:
            self._logger.info(message)
        else:
            self._logger.error(message)
    
    async def log_connection_event(
        self,
        server_name: str,
        event_type: str,
        success: bool,
        details: Optional[str] = None
    ) -> None:
        """Log connection events"""
        status = "SUCCESS" if success else "FAILED"
        message = f"CONNECTION_{event_type.upper()} - Server: {server_name}, Status: {status}"
        if details:
            message += f", Details: {details}"
        
        if success:
            self._logger.info(message)
        else:
            self._logger.warning(message) 