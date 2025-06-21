"""
Data models for MCP Remote Admin system.
Follows Single Responsibility Principle - only contains data structures.
"""
from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from enum import Enum


class ConnectionStatus(Enum):
    """Status of server connections"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAILED = "failed"


class Protocol(Enum):
    """Supported connection protocols"""
    HTTPS = "https"
    HTTP = "http"
    SSH = "ssh"
    WEBSOCKET = "ws"
    MCP_SSE = "mcp-sse"
    MCP_HTTP = "mcp-http"
    MCP = "mcp"


@dataclass
class RemoteServer:
    """Configuration for a remote MCP server"""
    name: str
    host: str
    port: int
    protocol: str = Protocol.HTTPS.value
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


@dataclass
class SecurityConfig:
    """Security configuration settings"""
    default_timeout: int = 30
    max_concurrent_connections: int = 10
    rate_limit_requests_per_minute: int = 60
    rate_limit_burst_size: int = 10
    audit_log_enabled: bool = True
    audit_log_file: str = "/var/log/mcp-admin/audit.log"
    audit_log_level: str = "INFO"


@dataclass
class ServerGroupRestrictions:
    """Restrictions for a server group"""
    dangerous_commands: bool = True
    file_write: bool = True
    service_restart: bool = True


@dataclass
class ServerGroup:
    """Configuration for a server group"""
    name: str
    tags: List[str]
    restrictions: ServerGroupRestrictions = None
    
    def __post_init__(self):
        if self.restrictions is None:
            self.restrictions = ServerGroupRestrictions()


@dataclass
class ConnectionInfo:
    """Information about a server connection"""
    server_name: str
    status: ConnectionStatus
    connected_at: Optional[str] = None
    last_error: Optional[str] = None
    retry_count: int = 0


@dataclass
class CommandResult:
    """Result of a command execution"""
    server_name: str
    command: str
    success: bool
    result: Dict[str, Any]
    execution_time: float
    error: Optional[str] = None


@dataclass
class BulkCommandResult:
    """Result of bulk command execution"""
    command: str
    target_servers: List[str]
    results: Dict[str, CommandResult]
    success_count: int
    failed_count: int 