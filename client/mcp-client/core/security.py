"""
Security management implementations.
Focused on security policies and access control.
"""
from typing import List, Dict
from .interfaces import ISecurityManager, IServerRegistry
from .models import ServerGroup, ServerGroupRestrictions


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