import os
import json
import logging
import subprocess
import threading
import time
from .utils import log_message


class MCPClientManager:
    """Manages communication with the MCP client process"""
    
    def __init__(self, logger: logging.Logger):
        self.process = None
        self.status = {"connected": False, "servers": [], "tools": []}
        self.is_running = False
        self.mcp_client_path = None
        self.config_path = None
        self.logger = logger
    
    def start_mcp_client(self):
        """Start MCP client as subprocess"""
        try:
            # Get paths from environment or use defaults
            # Go up one level from modules directory to client directory
            client_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.mcp_client_path = os.path.join(client_dir, "mcp-client", "ai-admin-refactored.py")
            self.config_path = os.path.join(client_dir, "mcp-client", "config.json")
            
            self.logger.info(log_message(f"MCP client path: {self.mcp_client_path}"))
            self.logger.info(log_message(f"Config path: {self.config_path}"))
            
            # Check if files exist
            if not os.path.exists(self.mcp_client_path):
                self.logger.error(log_message(f"MCP client not found at: {self.mcp_client_path}"))
                return False
                
            if not os.path.exists(self.config_path):
                self.logger.error(log_message(f"Config file not found at: {self.config_path}"))
                return False
            
            # Start the MCP client process
            self.logger.info(log_message("Starting MCP client subprocess..."))
            self.process = subprocess.Popen(
                ["python", self.mcp_client_path, "--config", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=os.path.dirname(self.mcp_client_path),
                text=True
            )
            
            # Start monitoring thread
            self.is_running = True
            monitor_thread = threading.Thread(target=self._monitor_process, daemon=True)
            monitor_thread.start()
            
            self.logger.info(log_message(f"MCP client started with PID: {self.process.pid}"))
            return True
            
        except Exception as e:
            self.logger.error(log_message(f"Failed to start MCP client: {e}"))
            return False
    
    def _monitor_process(self):
        """Monitor the MCP client process"""
        while self.is_running and self.process:
            try:
                # Check if process is still running
                if self.process.poll() is not None:
                    self.logger.warning(log_message("MCP client process has terminated"))
                    self.status["connected"] = False
                    break
                
                # Update status - in a real implementation, this would
                # communicate with the MCP client to get actual status
                self.status["connected"] = True
                
                # Sleep for a bit before checking again
                time.sleep(5)
                
            except Exception as e:
                self.logger.error(log_message(f"Error monitoring MCP client: {e}"))
                break
    
    def get_status(self):
        """Get current MCP client status"""
        # Check if subprocess is running
        process_running = self.process and self.process.poll() is None
        self.logger.debug(log_message(f"Process running: {process_running}, Config path: {self.config_path}"))
        
        # Load server configuration from config.json if available
        servers = []
        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    config = json.load(f)
                    # Parse the remote_servers array from the config
                    for server_config in config.get("remote_servers", []):
                        servers.append({
                            "name": server_config.get("name", "unknown"),
                            "host": server_config.get("host", "unknown"),
                            "port": server_config.get("port", 0),
                            "protocol": server_config.get("protocol", "unknown"),
                            "connected": process_running,  # Assume connected if process is running
                            "auth_token": server_config.get("auth_token", ""),
                            "tags": server_config.get("tags", []),
                            "tools": [
                                "system_status", "read_file", "shell_exec",
                                "service_status", "service_restart", "get_logs",
                                "list_processes", "network_connections", "health_check"
                            ]
                        })
                self.logger.info(log_message(f"Loaded {len(servers)} servers from config file"))
            except Exception as e:
                self.logger.error(log_message(f"Error reading config file: {e}"))
                # Fallback to default servers
                servers = [
                    {
                        "name": "test1",
                        "host": "192.168.10.18",
                        "port": 8080,
                        "protocol": "mcp-sse",
                        "connected": process_running,
                        "tools": [
                            "system_status", "read_file", "shell_exec",
                            "service_status", "service_restart", "get_logs",
                            "list_processes", "network_connections", "health_check"
                        ]
                    },
                    {
                        "name": "test2", 
                        "host": "192.168.10.17",
                        "port": 8080,
                        "protocol": "mcp-http",
                        "connected": process_running,
                        "tools": [
                            "system_status", "read_file", "shell_exec",
                            "service_status", "service_restart", "get_logs",
                            "list_processes", "network_connections", "health_check"
                        ]
                    }
                ]
        
        self.status.update({
            "connected": process_running,
            "servers": servers,
            "process_pid": self.process.pid if self.process else None
        })
        
        return self.status
    
    def stop(self):
        """Stop the MCP client manager and subprocess"""
        self.is_running = False
        
        if self.process:
            try:
                self.logger.info(log_message("Terminating MCP client subprocess..."))
                self.process.terminate()
                
                # Wait for process to terminate gracefully
                try:
                    self.process.wait(timeout=10)
                    self.logger.info(log_message("MCP client subprocess terminated gracefully"))
                except subprocess.TimeoutExpired:
                    self.logger.warning(log_message("MCP client subprocess did not terminate gracefully, forcing kill"))
                    self.process.kill()
                    self.process.wait()
                    
            except Exception as e:
                self.logger.error(log_message(f"Error stopping MCP client subprocess: {e}"))
            finally:
                self.process = None
                
        self.logger.info(log_message("MCP client manager stopped"))