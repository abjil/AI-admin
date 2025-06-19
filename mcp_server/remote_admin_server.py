#!/usr/bin/env python3
"""
MCP Remote Admin Server
This runs on the REMOTE MACHINE to be administered
Exposes system administration capabilities via MCP protocol
"""

import asyncio
import json
import os
import re
import subprocess
import psutil
import logging
import argparse
from datetime import datetime
from typing import Dict, Any, List, Set
from pathlib import Path
from logging.handlers import RotatingFileHandler
from mcp.server.fastmcp import FastMCP
from mcp import types

# Global configuration
config = {}
logger = None
mcp_server = None


class ServerConfiguration:
    """Manages server configuration loading and validation"""
    
    def __init__(self):
        self.config = {}
        self.config_file = None
    
    def substitute_env_vars(self, text: str) -> str:
        """Substitute environment variables in text using ${VAR_NAME} syntax"""
        def replace_env_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, f"${{{var_name}}}")
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, text)
    
    def load_config(self, config_file: str) -> bool:
        """Load configuration from JSON file"""
        try:
            self.config_file = config_file
            
            if not os.path.exists(config_file):
                print(f"Warning: Config file {config_file} not found, using defaults")
                self._load_defaults()
                return True
            
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            # Substitute environment variables
            config_content = self.substitute_env_vars(config_content)
            self.config = json.loads(config_content)
            
            # Validate and set defaults
            self._validate_and_set_defaults()
            
            print(f"Successfully loaded configuration from {config_file}")
            return True
            
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            print(f"Error loading config: {e}")
            return False
    
    def _load_defaults(self):
        """Load default configuration"""
        self.config = {
            "server": {
                "name": "remote-admin-server",
                "port": 8080,
                "host": "0.0.0.0",
                "auth_token": "",
                "log_level": "INFO",
                "max_connections": 10
            },
            "security": {
                "allowed_commands": [
                    "systemctl", "service", "ps", "top", "df", "free", "uptime",
                    "netstat", "ss", "iptables", "ufw", "tail", "head", "grep",
                    "ls", "find", "cat", "less", "journalctl"
                ],
                "allowed_paths": [
                    "/var/log", "/etc", "/proc", "/sys", "/tmp", "/home"
                ],
                "command_timeout": 30,
                "max_file_size": 10485760,
                "max_file_lines": 1000,
                "enable_dangerous_commands": False,
                "dangerous_commands": [
                    "rm", "rmdir", "mv", "cp", "chmod", "chown", "mount", "umount",
                    "fdisk", "mkfs", "dd", "reboot", "shutdown", "halt", "poweroff"
                ]
            },
            "logging": {
                "file": None,
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "max_size": 10485760,
                "backup_count": 5,
                "audit_enabled": True,
                "audit_file": "/var/log/mcp-admin-audit.log"
            },
            "features": {
                "system_status": True,
                "file_operations": True,
                "shell_execution": True,
                "service_management": True,
                "log_retrieval": True,
                "process_management": True,
                "network_info": True
            },
            "limits": {
                "max_processes_list": 100,
                "max_log_lines": 1000,
                "max_concurrent_commands": 5,
                "rate_limit_per_minute": 60
            }
        }
    
    def _validate_and_set_defaults(self):
        """Validate configuration and set defaults for missing values"""
        defaults = ServerConfiguration()
        defaults._load_defaults()
        
        # Merge with defaults
        for section, default_values in defaults.config.items():
            if section not in self.config:
                self.config[section] = default_values
            else:
                for key, default_value in default_values.items():
                    if key not in self.config[section]:
                        self.config[section][key] = default_value
    
    def get(self, section: str, key: str = None):
        """Get configuration value"""
        if key is None:
            return self.config.get(section, {})
        return self.config.get(section, {}).get(key)


def setup_logging(config: ServerConfiguration):
    """Setup logging based on configuration"""
    global logger
    
    log_config = config.get("logging")
    log_level = getattr(logging, log_config["level"].upper())
    
    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(log_level)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = logging.Formatter(log_config["format"])
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if configured
    if log_config["file"]:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(log_config["file"])
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = RotatingFileHandler(
                log_config["file"],
                maxBytes=log_config["max_size"],
                backupCount=log_config["backup_count"]
            )
            file_handler.setLevel(log_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            
        except Exception as e:
            logger.warning(f"Could not setup file logging: {e}")
    
    # Audit logger if enabled
    if log_config["audit_enabled"] and log_config["audit_file"]:
        try:
            audit_dir = os.path.dirname(log_config["audit_file"])
            if audit_dir:
                os.makedirs(audit_dir, exist_ok=True)
            
            audit_handler = RotatingFileHandler(
                log_config["audit_file"],
                maxBytes=log_config["max_size"],
                backupCount=log_config["backup_count"]
            )
            audit_handler.setLevel(logging.INFO)
            audit_formatter = logging.Formatter(
                '%(asctime)s - AUDIT - %(message)s'
            )
            audit_handler.setFormatter(audit_formatter)
            
            # Create separate audit logger
            audit_logger = logging.getLogger("audit")
            audit_logger.setLevel(logging.INFO)
            audit_logger.addHandler(audit_handler)
            
        except Exception as e:
            logger.warning(f"Could not setup audit logging: {e}")


def initialize_server(config: ServerConfiguration):
    """Initialize the MCP server with configuration"""
    global mcp_server
    
    server_config = config.get("server")
    
    # Try to initialize FastMCP with port if supported
    try:
        # Some versions might support port in constructor
        mcp_server = FastMCP(server_config["name"], port=server_config["port"])
    except TypeError:
        # Fallback to basic initialization
        logger.warning("FastMCP doesn't support port in constructor, using default configuration")
        mcp_server = FastMCP(server_config["name"])
    
    return mcp_server

def is_path_allowed(path: str, server_config: ServerConfiguration) -> bool:
    """Check if a file path is within allowed directories"""
    try:
        resolved_path = Path(path).resolve()
        allowed_paths = server_config.get("security", "allowed_paths")
        return any(str(resolved_path).startswith(allowed) for allowed in allowed_paths)
    except:
        return False

def is_command_allowed(command: str, server_config: ServerConfiguration) -> bool:
    """Check if a command is in the whitelist"""
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return False
    
    base_command = cmd_parts[0].split('/')[-1]  # Handle full paths
    security_config = server_config.get("security")
    
    # Check if it's a dangerous command and if they're enabled
    if base_command in security_config["dangerous_commands"]:
        if not security_config["enable_dangerous_commands"]:
            return False
    
    # Check if command is in allowed list
    return base_command in security_config["allowed_commands"]

def log_audit_event(message: str):
    """Log audit event"""
    audit_logger = logging.getLogger("audit")
    audit_logger.info(message)

def register_tools(server: FastMCP, server_config: ServerConfiguration):
    """Register MCP tools based on configuration"""
    
    features = server_config.get("features")
    security = server_config.get("security")
    limits = server_config.get("limits")
    
    if features["system_status"]:
        @server.tool()
        async def system_status() -> Dict[str, Any]:
            """Get comprehensive system status"""
            try:
                log_audit_event("system_status command executed")
                
                # CPU information
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                
                # Memory information
                memory = psutil.virtual_memory()
                swap = psutil.swap_memory()
                
                # Disk information
                disk_usage = {}
                for partition in psutil.disk_partitions():
                    try:
                        usage = psutil.disk_usage(partition.mountpoint)
                        disk_usage[partition.mountpoint] = {
                            "total": usage.total,
                            "used": usage.used,
                            "free": usage.free,
                            "percent": usage.percent
                        }
                    except PermissionError:
                        continue
                
                # Network information
                network_stats = psutil.net_io_counters()
                
                # Boot time
                boot_time = datetime.fromtimestamp(psutil.boot_time())
                
                # Load average (Unix-like systems)
                load_avg = None
                try:
                    load_avg = os.getloadavg()
                except (OSError, AttributeError):
                    pass
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "hostname": os.uname().nodename,
                    "cpu": {
                        "percent": cpu_percent,
                        "count": cpu_count,
                        "load_average": load_avg
                    },
                    "memory": {
                        "total": memory.total,
                        "available": memory.available,
                        "percent": memory.percent,
                        "used": memory.used,
                        "free": memory.free
                    },
                    "swap": {
                        "total": swap.total,
                        "used": swap.used,
                        "free": swap.free,
                        "percent": swap.percent
                    },
                    "disk": disk_usage,
                    "network": {
                        "bytes_sent": network_stats.bytes_sent,
                        "bytes_recv": network_stats.bytes_recv,
                        "packets_sent": network_stats.packets_sent,
                        "packets_recv": network_stats.packets_recv
                    },
                    "boot_time": boot_time.isoformat(),
                    "uptime_seconds": (datetime.now() - boot_time).total_seconds()
                }
            except Exception as e:
                logger.error(f"Error getting system status: {e}")
                return {"error": str(e)}

    if features["file_operations"]:
        @server.tool()
        async def read_file(path: str, max_lines: int = None) -> Dict[str, Any]:
            """Read a file from the filesystem with security restrictions"""
            try:
                if max_lines is None:
                    max_lines = security["max_file_lines"]
                
                max_lines = min(max_lines, security["max_file_lines"])  # Enforce limit
                
                if not is_path_allowed(path, server_config):
                    log_audit_event(f"read_file access denied: {path}")
                    return {"error": f"Access denied: {path} is not in allowed paths"}
                
                file_path = Path(path)
                if not file_path.exists():
                    return {"error": f"File not found: {path}"}
                
                if not file_path.is_file():
                    return {"error": f"Path is not a file: {path}"}
                
                # Check file size
                file_size = file_path.stat().st_size
                if file_size > security["max_file_size"]:
                    return {"error": f"File too large: {file_size} bytes (max: {security['max_file_size']})"}
                
                log_audit_event(f"read_file executed: {path}")
                
                # Read file with line limit
                lines = []
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            break
                        lines.append(line.rstrip('\n'))
                
                return {
                    "path": str(file_path),
                    "lines": lines,
                    "line_count": len(lines),
                    "truncated": len(lines) >= max_lines,
                    "size": file_size,
                    "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
                }
            except Exception as e:
                logger.error(f"Error reading file {path}: {e}")
                return {"error": str(e)}

    if features["shell_execution"]:
        @server.tool()
        async def shell_exec(command: str, timeout: int = None) -> Dict[str, Any]:
            """Execute a shell command with security restrictions"""
            try:
                if timeout is None:
                    timeout = security["command_timeout"]
                
                timeout = min(timeout, security["command_timeout"])  # Enforce limit
                
                if not is_command_allowed(command, server_config):
                    log_audit_event(f"shell_exec command denied: {command}")
                    return {"error": f"Command not allowed: {command}"}
                
                # Log the command execution for auditing
                log_audit_event(f"shell_exec executed: {command}")
                logger.info(f"Executing command: {command}")
                
                # Execute command with timeout
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    shell=True
                )
                
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(), 
                        timeout=timeout
                    )
                    
                    return {
                        "command": command,
                        "return_code": process.returncode,
                        "stdout": stdout.decode('utf-8', errors='ignore'),
                        "stderr": stderr.decode('utf-8', errors='ignore'),
                        "timeout": False
                    }
                except asyncio.TimeoutError:
                    process.kill()
                    log_audit_event(f"shell_exec timeout: {command}")
                    return {
                        "command": command,
                        "error": "Command timed out",
                        "timeout": True
                    }
                    
            except Exception as e:
                logger.error(f"Error executing command {command}: {e}")
                return {"error": str(e)}

    if features["service_management"]:
        @server.tool()
        async def service_status(service: str) -> Dict[str, Any]:
            """Get status of a system service"""
            try:
                log_audit_event(f"service_status executed: {service}")
                
                # Use systemctl to check service status
                result = await shell_exec(f"systemctl status {service}")
                
                if result.get("error"):
                    return result
                
                # Parse systemctl output for key information
                is_active = "active (running)" in result["stdout"]
                is_enabled = "enabled" in result["stdout"]
                
                return {
                    "service": service,
                    "active": is_active,
                    "enabled": is_enabled,
                    "status_output": result["stdout"],
                    "return_code": result["return_code"]
                }
            except Exception as e:
                logger.error(f"Error checking service {service}: {e}")
                return {"error": str(e)}

        @server.tool()
        async def service_restart(service: str) -> Dict[str, Any]:
            """Restart a system service"""
            try:
                log_audit_event(f"service_restart executed: {service}")
                logger.warning(f"Restarting service: {service}")
                
                # Restart the service
                result = await shell_exec(f"systemctl restart {service}")
                
                if result["return_code"] == 0:
                    # Check if service is now running
                    status = await service_status(service)
                    return {
                        "service": service,
                        "restarted": True,
                        "active": status.get("active", False),
                        "output": result["stdout"]
                    }
                else:
                    return {
                        "service": service,
                        "restarted": False,
                        "error": result["stderr"],
                        "return_code": result["return_code"]
                    }
                    
            except Exception as e:
                logger.error(f"Error restarting service {service}: {e}")
                return {"error": str(e)}

    if features["log_retrieval"]:
        @server.tool()
        async def get_logs(log_type: str = "syslog", lines: int = None) -> Dict[str, Any]:
            """Retrieve system logs"""
            try:
                if lines is None:
                    lines = limits["max_log_lines"]
                
                lines = min(lines, limits["max_log_lines"])  # Enforce limit
                
                log_audit_event(f"get_logs executed: {log_type}, lines: {lines}")
                
                log_commands = {
                    "syslog": f"journalctl -n {lines}",
                    "kernel": f"journalctl -k -n {lines}",
                    "auth": f"journalctl _COMM=sshd -n {lines}",
                    "nginx": f"journalctl -u nginx -n {lines}",
                    "apache": f"journalctl -u apache2 -n {lines}",
                    "docker": f"journalctl -u docker -n {lines}"
                }
                
                if log_type not in log_commands:
                    return {"error": f"Unknown log type: {log_type}"}
                
                result = await shell_exec(log_commands[log_type])
                
                if result.get("error"):
                    return result
                
                return {
                    "log_type": log_type,
                    "lines_requested": lines,
                    "logs": result["stdout"],
                    "return_code": result["return_code"]
                }
                
            except Exception as e:
                logger.error(f"Error getting logs {log_type}: {e}")
                return {"error": str(e)}

    if features["process_management"]:
        @server.tool()
        async def list_processes() -> Dict[str, Any]:
            """List running processes"""
            try:
                log_audit_event("list_processes executed")
                
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
                    try:
                        processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                # Sort by CPU usage and limit results
                processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
                max_processes = limits["max_processes_list"]
                
                return {
                    "process_count": len(processes),
                    "processes": processes[:max_processes]
                }
            except Exception as e:
                logger.error(f"Error listing processes: {e}")
                return {"error": str(e)}

    if features["network_info"]:
        @server.tool()
        async def network_connections() -> Dict[str, Any]:
            """List network connections"""
            try:
                log_audit_event("network_connections executed")
                
                connections = []
                for conn in psutil.net_connections(kind='inet'):
                    if conn.status == psutil.CONN_LISTEN:
                        connections.append({
                            "protocol": "TCP" if conn.type == 1 else "UDP",
                            "local_address": f"{conn.laddr.ip}:{conn.laddr.port}",
                            "status": conn.status,
                            "pid": conn.pid
                        })
                
                return {
                    "listening_ports": connections
                }
            except Exception as e:
                logger.error(f"Error getting network connections: {e}")
                return {"error": str(e)}

    # Always register health check
    @server.tool()
    async def health_check() -> Dict[str, Any]:
        """Health check for the MCP server"""
        return {
            "status": "healthy",
            "server": server_config.get("server", "name"),
            "timestamp": datetime.now().isoformat(),
            "version": "1.0.0",
            "config_file": server_config.config_file
        }


def main():
    """Main function to run the MCP server"""
    global config
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Remote Admin Server")
    parser.add_argument(
        "--config", "-c",
        default="server_config.json",
        help="Path to configuration file (default: server_config.json)"
    )
    parser.add_argument(
        "--port", "-p",
        type=int,
        help="Override port from config file"
    )
    parser.add_argument(
        "--host",
        help="Override host from config file"
    )
    
    args = parser.parse_args()
    
    # Load configuration
    config = ServerConfiguration()
    if not config.load_config(args.config):
        print("Failed to load configuration, exiting...")
        return
    
    # Override with command line arguments
    if args.port:
        config.config["server"]["port"] = args.port
    if args.host:
        config.config["server"]["host"] = args.host
    
    # Setup logging
    setup_logging(config)
    
    # Initialize server
    server = initialize_server(config)
    
    # Register tools based on configuration
    register_tools(server, config)
    
    server_config = config.get("server")
    logger.info(f"Starting {server_config['name']} on {server_config['host']}:{server_config['port']}")
    
    auth_token = server_config["auth_token"]
    if auth_token and not auth_token.startswith("${"):
        logger.info("Authentication token configured")
    else:
        logger.warning("No authentication token set - server is unsecured!")
    
    # Log enabled features
    features = config.get("features")
    enabled_features = [name for name, enabled in features.items() if enabled]
    logger.info(f"Enabled features: {', '.join(enabled_features)}")
    
    # Run the server
    # Note: FastMCP doesn't support host or port parameters in run()
    if server_config["host"] != "0.0.0.0":
        logger.warning(f"FastMCP doesn't support custom host binding, ignoring host setting: {server_config['host']}")
    
    if server_config["port"] != 8080:
        logger.warning(f"FastMCP doesn't support custom port in run(), ignoring port setting: {server_config['port']}")
        logger.warning("FastMCP will use its default port configuration")
    
    # FastMCP manages its own event loop internally
    # Call run() directly - it's designed to be called from a synchronous context
    try:
        # This should be a synchronous call that handles async internally
        server.run()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise


if __name__ == "__main__":
    main() 