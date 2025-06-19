#!/usr/bin/env python3
"""
MCP Remote Admin Server
This runs on the REMOTE MACHINE to be administered
Exposes system administration capabilities via MCP protocol
"""

import asyncio
import json
import os
import subprocess
import psutil
import logging
from datetime import datetime
from typing import Dict, Any, List
from pathlib import Path
from mcp.server.fastmcp import FastMCP
from mcp import types

# Server configuration
SERVER_NAME = os.getenv("MCP_SERVER_NAME", "remote-admin-server")
SERVER_PORT = int(os.getenv("MCP_SERVER_PORT", "8080"))
AUTH_TOKEN = os.getenv("MCP_AUTH_TOKEN", "")

# Create the MCP server instance
mcp_server = FastMCP(SERVER_NAME)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Security: Whitelist of allowed commands and paths
ALLOWED_COMMANDS = {
    "systemctl", "service", "ps", "top", "df", "free", "uptime", 
    "netstat", "ss", "iptables", "ufw", "tail", "head", "grep",
    "ls", "find", "cat", "less", "journalctl"
}

ALLOWED_PATHS = {
    "/var/log", "/etc", "/proc", "/sys", "/tmp", "/home"
}

def is_path_allowed(path: str) -> bool:
    """Check if a file path is within allowed directories"""
    try:
        resolved_path = Path(path).resolve()
        return any(str(resolved_path).startswith(allowed) for allowed in ALLOWED_PATHS)
    except:
        return False

def is_command_allowed(command: str) -> bool:
    """Check if a command is in the whitelist"""
    cmd_parts = command.strip().split()
    if not cmd_parts:
        return False
    base_command = cmd_parts[0].split('/')[-1]  # Handle full paths
    return base_command in ALLOWED_COMMANDS

@mcp_server.tool()
async def system_status() -> Dict[str, Any]:
    """Get comprehensive system status"""
    try:
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

@mcp_server.tool()
async def read_file(path: str, max_lines: int = 1000) -> Dict[str, Any]:
    """Read a file from the filesystem with security restrictions"""
    try:
        if not is_path_allowed(path):
            return {"error": f"Access denied: {path} is not in allowed paths"}
        
        file_path = Path(path)
        if not file_path.exists():
            return {"error": f"File not found: {path}"}
        
        if not file_path.is_file():
            return {"error": f"Path is not a file: {path}"}
        
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
            "size": file_path.stat().st_size,
            "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat()
        }
    except Exception as e:
        logger.error(f"Error reading file {path}: {e}")
        return {"error": str(e)}

@mcp_server.tool()
async def shell_exec(command: str, timeout: int = 30) -> Dict[str, Any]:
    """Execute a shell command with security restrictions"""
    try:
        if not is_command_allowed(command):
            return {"error": f"Command not allowed: {command}"}
        
        # Log the command execution for auditing
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
            return {
                "command": command,
                "error": "Command timed out",
                "timeout": True
            }
            
    except Exception as e:
        logger.error(f"Error executing command {command}: {e}")
        return {"error": str(e)}

@mcp_server.tool()
async def service_status(service: str) -> Dict[str, Any]:
    """Get status of a system service"""
    try:
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

@mcp_server.tool()
async def service_restart(service: str) -> Dict[str, Any]:
    """Restart a system service"""
    try:
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

@mcp_server.tool()
async def get_logs(log_type: str = "syslog", lines: int = 100) -> Dict[str, Any]:
    """Retrieve system logs"""
    try:
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

@mcp_server.tool()
async def list_processes() -> Dict[str, Any]:
    """List running processes"""
    try:
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent', 'status']):
            try:
                processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        
        # Sort by CPU usage
        processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
        
        return {
            "process_count": len(processes),
            "processes": processes[:50]  # Limit to top 50 processes
        }
    except Exception as e:
        logger.error(f"Error listing processes: {e}")
        return {"error": str(e)}

@mcp_server.tool()
async def network_connections() -> Dict[str, Any]:
    """List network connections"""
    try:
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

# Health check endpoint
@mcp_server.tool()
async def health_check() -> Dict[str, Any]:
    """Health check for the MCP server"""
    return {
        "status": "healthy",
        "server": SERVER_NAME,
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

async def main():
    """Main function to run the MCP server"""
    logger.info(f"Starting {SERVER_NAME} on port {SERVER_PORT}")
    
    if AUTH_TOKEN:
        logger.info("Authentication token configured")
    else:
        logger.warning("No authentication token set - server is unsecured!")
    
    # Run the server
    await mcp_server.run(port=SERVER_PORT)

if __name__ == "__main__":
    asyncio.run(main()) 