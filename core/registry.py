"""
Server registry implementations.
Focused on server registration and lookup functionality.
"""
import logging
from typing import List, Dict, Optional
from .interfaces import IServerRegistry
from .models import RemoteServer


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