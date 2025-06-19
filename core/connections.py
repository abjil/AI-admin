"""
Connection management implementations.
Focused on server connections and connection factories.
"""
import ssl
import asyncio
import logging
import aiohttp
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastmcp import Client
from fastmcp.client.transports import SSETransport, StreamableHttpTransport
from .interfaces import IConnectionManager, IConnectionFactory
from .models import RemoteServer, ConnectionInfo, ConnectionStatus, Protocol


class HTTPSConnectionFactory(IConnectionFactory):
    """Factory for creating HTTPS connections (legacy)"""
    
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


class MCPConnectionFactory(IConnectionFactory):
    """Factory for creating MCP connections using FastMCP client"""
    
    def supports_protocol(self, protocol: str) -> bool:
        """Check if factory supports the protocol"""
        return protocol.lower() in ["mcp-sse", "mcp-http", "mcp"]
    
    async def create_connection(self, server: RemoteServer) -> Client:
        """Create an MCP connection for the server"""
        # Determine transport type based on protocol
        if server.protocol.lower() == "mcp-sse":
            transport_type = "sse"
        elif server.protocol.lower() in ["mcp-http", "mcp"]:
            transport_type = "streamable-http"
        else:
            transport_type = "sse"  # Default to SSE
        
        # Build URL based on transport type
        scheme = "https" if server.ssl_verify else "http"
        if transport_type == "sse":
            url = f"{scheme}://{server.host}:{server.port}/sse"
        else:  # streamable-http
            url = f"{scheme}://{server.host}:{server.port}/mcp"
        
        # Prepare headers
        headers = {}
        if server.auth_token:
            headers["Authorization"] = f"Bearer {server.auth_token}"
        headers.update(server.custom_headers)
        
        # Create appropriate transport
        if transport_type == "sse":
            transport = SSETransport(url=url, headers=headers)
        else:
            transport = StreamableHttpTransport(url=url, headers=headers)
        
        # Create MCP client
        client = Client(transport)
        return client


class ConnectionManager(IConnectionManager):
    """Manages connections to remote servers"""
    
    def __init__(self, connection_factories: List[IConnectionFactory]):
        self._connection_factories = connection_factories
        self._connections: Dict[str, Any] = {}
        self._connection_info: Dict[str, ConnectionInfo] = {}
        self._logger = logging.getLogger(__name__)
        self._mcp_clients: Dict[str, Client] = {}  # Track MCP clients separately
    
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
                connection = await factory.create_connection(server)
                
                # Test connection based on type
                if isinstance(connection, Client):
                    success = await self._health_check_mcp(server, connection)
                    if success:
                        # Store the client for later use (don't keep connection open)
                        self._mcp_clients[server.name] = connection
                else:
                    success = await self._health_check_http(server, connection)
                
                if success:
                    self._connections[server.name] = connection
                    self._connection_info[server.name] = ConnectionInfo(
                        server_name=server.name,
                        status=ConnectionStatus.CONNECTED,
                        connected_at=datetime.now().isoformat()
                    )
                    self._logger.info(f"Connected to {server.name} on attempt {attempt + 1}")
                    return True
                else:
                    # For MCP clients, we don't need to close anything here
                    # since async with handles the connection lifecycle
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
    
    async def _health_check_mcp(self, server: RemoteServer, client: Client) -> bool:
        """Perform health check on MCP server connection"""
        try:
            # Test connection using the async with pattern from working example
            async with client:
                tools = await client.list_tools()
                return True  # If we can list tools, server is healthy
        except Exception as e:
            self._logger.debug(f"MCP health check failed for {server.name}: {e}")
            return False
    
    async def _health_check_http(self, server: RemoteServer, session: aiohttp.ClientSession) -> bool:
        """Perform health check on HTTP server connection"""
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
                connection = self._connections[server_name]
                
                # Handle MCP client disconnection
                if server_name in self._mcp_clients:
                    client = self._mcp_clients[server_name]
                    await client.close()
                    del self._mcp_clients[server_name]
                elif hasattr(connection, 'close'):
                    await connection.close()
                
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
    
    def get_mcp_client(self, server_name: str) -> Optional[Client]:
        """Get MCP client for server"""
        return self._mcp_clients.get(server_name) 