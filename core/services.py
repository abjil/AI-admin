"""
Service layer for MCP Remote Admin system.
Follows Dependency Inversion Principle by using interfaces.
"""
import logging
from typing import List, Dict, Any, Optional
from .interfaces import (
    IConfigurationManager, IServerRegistry, IConnectionManager, ICommandExecutor,
    ISecurityManager, IAuditLogger
)
from .config import ConfigurationManager, EnvironmentVariableSubstitutor
from .registry import ServerRegistry
from .connections import ConnectionManager, HTTPSConnectionFactory, MCPConnectionFactory
from .commands import CommandExecutor
from .security import SecurityManager
from .audit import AuditLogger
from .models import RemoteServer, ServerGroup, CommandResult, BulkCommandResult


class RemoteAdminService:
    """
    Main service class that orchestrates all components.
    Follows Single Responsibility Principle - only coordinates between components.
    """
    
    def __init__(self):
        # Initialize dependencies following Dependency Inversion Principle
        self._env_substitutor = EnvironmentVariableSubstitutor()
        self._config_manager = ConfigurationManager(self._env_substitutor)
        self._server_registry = ServerRegistry()
        
        # Connection factories (extensible for new protocols)
        connection_factories = [
            MCPConnectionFactory(),  # MCP protocol support (SSE, Streamable HTTP)
            HTTPSConnectionFactory()  # Legacy HTTP support
        ]
        self._connection_manager = ConnectionManager(connection_factories)
        
        # Security manager (initialized later after config load)
        self._security_manager: Optional[ISecurityManager] = None
        
        # Command executor (initialized later after other components)
        self._command_executor: Optional[ICommandExecutor] = None
        
        # Audit logger (initialized later after security config load)
        self._audit_logger: Optional[IAuditLogger] = None
        
        self._logger = logging.getLogger(__name__)
    
    async def initialize(self, config_file: str) -> bool:
        """Initialize the service with configuration"""
        try:
            # Load configuration
            if not await self._config_manager.load_config(config_file):
                return False
            
            # Register all servers from config
            servers = self._config_manager.get_servers()
            for server in servers:
                self._server_registry.register_server(server)
            
            # Initialize security manager with server groups
            server_groups = self._config_manager.get_server_groups()
            self._security_manager = SecurityManager(self._server_registry, server_groups)
            
            # Initialize command executor
            self._command_executor = CommandExecutor(
                self._connection_manager,
                self._server_registry,
                self._security_manager
            )
            
            # Initialize audit logger if enabled
            security_config = self._config_manager.get_security_config()
            if security_config and security_config.audit_log_enabled:
                self._audit_logger = AuditLogger(
                    security_config.audit_log_file,
                    security_config.audit_log_level
                )
            
            self._logger.info("Remote Admin Service initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize service: {e}")
            return False
    
    async def connect_all_servers(self) -> Dict[str, bool]:
        """Connect to all registered servers"""
        servers = list(self._server_registry.get_all_servers().values())
        return await self._connection_manager.connect_all_servers(servers)
    
    async def register_server(self, server: RemoteServer) -> bool:
        """Register a new server"""
        success = self._server_registry.register_server(server)
        if success and self._audit_logger:
            await self._audit_logger.log_connection_event(
                server.name, "REGISTER", True, f"Server registered: {server.host}:{server.port}"
            )
        return success
    
    async def connect_to_server(self, server_name: str) -> bool:
        """Connect to a specific server"""
        server = self._server_registry.get_server(server_name)
        if not server:
            return False
        
        success = await self._connection_manager.connect_to_server(server)
        if self._audit_logger:
            await self._audit_logger.log_connection_event(
                server_name, "CONNECT", success
            )
        return success
    
    async def execute_command(
        self,
        server_name: str,
        command: str,
        params: Optional[Dict[str, Any]] = None,
        user: str = "system"
    ) -> CommandResult:
        """Execute command on server with audit logging"""
        if not self._command_executor:
            raise RuntimeError("Service not properly initialized")
        
        result = await self._command_executor.execute_command(server_name, command, params)
        
        if self._audit_logger:
            await self._audit_logger.log_command_execution(
                server_name, command, user, result.success, result.error
            )
        
        return result
    
    async def execute_bulk_command(
        self,
        server_names: List[str],
        command: str,
        params: Optional[Dict[str, Any]] = None,
        user: str = "system"
    ) -> BulkCommandResult:
        """Execute command on multiple servers with audit logging"""
        if not self._command_executor:
            raise RuntimeError("Service not properly initialized")
        
        result = await self._command_executor.execute_bulk_command(server_names, command, params)
        
        if self._audit_logger:
            for server_name, cmd_result in result.results.items():
                await self._audit_logger.log_command_execution(
                    server_name, command, user, cmd_result.success, cmd_result.error
                )
        
        return result
    
    def get_all_servers(self) -> Dict[str, RemoteServer]:
        """Get all registered servers"""
        return self._server_registry.get_all_servers()
    
    def get_server(self, server_name: str) -> Optional[RemoteServer]:
        """Get server by name"""
        return self._server_registry.get_server(server_name)
    
    def get_servers_by_tags(self, tags: List[str]) -> List[RemoteServer]:
        """Get servers by tags"""
        return self._server_registry.get_servers_by_tags(tags)
    
    def is_connected(self, server_name: str) -> bool:
        """Check if server is connected"""
        return self._connection_manager.is_connected(server_name)
    
    def get_connection_info(self, server_name: str):
        """Get connection info for server"""
        return self._connection_manager.get_connection_info(server_name)
    
    def get_server_groups(self) -> Dict[str, ServerGroup]:
        """Get server groups"""
        return self._config_manager.get_server_groups()
    
    def is_command_allowed(self, server_name: str, command: str) -> bool:
        """Check if command is allowed for server"""
        if not self._security_manager:
            return True
        return self._security_manager.is_command_allowed(server_name, command)
    
    def is_command_allowed_for_group(self, group_name: str, command: str) -> bool:
        """Check if command is allowed for server group"""
        if not self._security_manager:
            return True
        return self._security_manager.is_command_allowed_for_group(group_name, command)
    
    def get_servers_in_group(self, group_name: str) -> List[str]:
        """Get servers in group"""
        if not self._security_manager:
            return []
        return self._security_manager.get_servers_in_group(group_name)
    
    async def shutdown(self) -> None:
        """Shutdown the service gracefully"""
        servers = self._server_registry.get_all_servers()
        for server_name in servers.keys():
            await self._connection_manager.disconnect_from_server(server_name)
        
        self._logger.info("Remote Admin Service shut down") 