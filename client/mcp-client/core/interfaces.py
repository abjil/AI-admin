"""
Abstract interfaces for MCP Remote Admin system.
Follows Dependency Inversion Principle - depend on abstractions, not concretions.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from .models import (
    RemoteServer, SecurityConfig, ServerGroup, ConnectionInfo, 
    CommandResult, BulkCommandResult
)


class IConfigurationManager(ABC):
    """Interface for configuration management"""
    
    @abstractmethod
    async def load_config(self, config_file: str) -> bool:
        """Load configuration from file"""
        pass
    
    @abstractmethod
    def get_servers(self) -> List[RemoteServer]:
        """Get all configured servers"""
        pass
    
    @abstractmethod
    def get_security_config(self) -> Optional[SecurityConfig]:
        """Get security configuration"""
        pass
    
    @abstractmethod
    def get_server_groups(self) -> Dict[str, ServerGroup]:
        """Get server groups"""
        pass


class IServerRegistry(ABC):
    """Interface for server registry management"""
    
    @abstractmethod
    def register_server(self, server: RemoteServer) -> bool:
        """Register a server"""
        pass
    
    @abstractmethod
    def unregister_server(self, server_name: str) -> bool:
        """Unregister a server"""
        pass
    
    @abstractmethod
    def get_server(self, server_name: str) -> Optional[RemoteServer]:
        """Get server by name"""
        pass
    
    @abstractmethod
    def get_all_servers(self) -> Dict[str, RemoteServer]:
        """Get all registered servers"""
        pass
    
    @abstractmethod
    def get_servers_by_tags(self, tags: List[str]) -> List[RemoteServer]:
        """Get servers matching any of the given tags"""
        pass


class IConnectionManager(ABC):
    """Interface for connection management"""
    
    @abstractmethod
    async def connect_to_server(self, server: RemoteServer) -> bool:
        """Connect to a specific server"""
        pass
    
    @abstractmethod
    async def disconnect_from_server(self, server_name: str) -> bool:
        """Disconnect from a server"""
        pass
    
    @abstractmethod
    async def connect_all_servers(self, servers: List[RemoteServer]) -> Dict[str, bool]:
        """Connect to all servers"""
        pass
    
    @abstractmethod
    def get_connection_info(self, server_name: str) -> Optional[ConnectionInfo]:
        """Get connection information for a server"""
        pass
    
    @abstractmethod
    def is_connected(self, server_name: str) -> bool:
        """Check if server is connected"""
        pass


class ICommandExecutor(ABC):
    """Interface for command execution"""
    
    @abstractmethod
    async def execute_command(
        self, 
        server_name: str, 
        command: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> CommandResult:
        """Execute command on a server"""
        pass
    
    @abstractmethod
    async def execute_bulk_command(
        self, 
        server_names: List[str], 
        command: str, 
        params: Optional[Dict[str, Any]] = None
    ) -> BulkCommandResult:
        """Execute command on multiple servers"""
        pass


class ISecurityManager(ABC):
    """Interface for security management"""
    
    @abstractmethod
    def is_command_allowed(self, server_name: str, command: str) -> bool:
        """Check if command is allowed for server"""
        pass
    
    @abstractmethod
    def is_command_allowed_for_group(self, group_name: str, command: str) -> bool:
        """Check if command is allowed for server group"""
        pass
    
    @abstractmethod
    def get_servers_in_group(self, group_name: str) -> List[str]:
        """Get servers belonging to a group"""
        pass
    
    @abstractmethod
    def validate_server_access(self, server_name: str, operation: str) -> bool:
        """Validate if operation is allowed on server"""
        pass


class IEnvironmentVariableSubstitutor(ABC):
    """Interface for environment variable substitution"""
    
    @abstractmethod
    def substitute_variables(self, text: str) -> str:
        """Substitute environment variables in text"""
        pass


class IAuditLogger(ABC):
    """Interface for audit logging"""
    
    @abstractmethod
    async def log_command_execution(
        self, 
        server_name: str, 
        command: str, 
        user: str, 
        success: bool, 
        error: Optional[str] = None
    ) -> None:
        """Log command execution for audit"""
        pass
    
    @abstractmethod
    async def log_connection_event(
        self, 
        server_name: str, 
        event_type: str, 
        success: bool, 
        details: Optional[str] = None
    ) -> None:
        """Log connection events"""
        pass


class IConnectionFactory(ABC):
    """Interface for creating connections"""
    
    @abstractmethod
    async def create_connection(self, server: RemoteServer) -> Any:
        """Create a connection object for the server"""
        pass
    
    @abstractmethod
    def supports_protocol(self, protocol: str) -> bool:
        """Check if factory supports the protocol"""
        pass 