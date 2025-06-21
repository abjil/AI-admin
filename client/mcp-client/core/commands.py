"""
Command execution implementations.
Focused on executing commands on remote servers.
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from .interfaces import ICommandExecutor, IConnectionManager, IServerRegistry, ISecurityManager
from .models import CommandResult, BulkCommandResult


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
        server,
        command: str,
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute command on remote server via MCP or HTTP"""
        # Try MCP client first
        if hasattr(self._connection_manager, 'get_mcp_client'):
            mcp_client = self._connection_manager.get_mcp_client(server.name)
            if mcp_client:
                return await self._execute_mcp_command(mcp_client, command, params)
        
        # Fallback to HTTP implementation
        return await self._execute_http_command(server, command, params)
    
    async def _execute_mcp_command(
        self,
        client,
        command: str,
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute command via MCP client"""
        try:
            async with client:
                # Call the MCP tool
                result = await client.call_tool(command, params or {})
                
                # Convert MCP result to our expected format
                if result and len(result) > 0:
                    # MCP returns a list of content objects
                    content = result[0]
                    if hasattr(content, 'text'):
                        # Try to parse as JSON if possible
                        try:
                            import json
                            return json.loads(content.text)
                        except:
                            return {"output": content.text}
                    else:
                        return {"result": str(content)}
                else:
                    return {"status": "success", "message": "Command executed successfully"}
                    
        except Exception as e:
            raise Exception(f"MCP command execution failed: {e}")
    
    async def _execute_http_command(
        self,
        server,
        command: str,
        params: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Execute command via HTTP (legacy)"""
        # This would be implemented based on the specific HTTP API
        # For now, returning a placeholder implementation
        return {
            "status": "success",
            "message": f"Command {command} executed on {server.name} via HTTP",
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