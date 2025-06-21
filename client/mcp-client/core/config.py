"""
Configuration management implementations.
Focused on loading and parsing configuration files.
"""
import json
import os
import re
import logging
from typing import List, Dict, Any, Optional
from .interfaces import IConfigurationManager, IEnvironmentVariableSubstitutor
from .models import RemoteServer, SecurityConfig, ServerGroup, ServerGroupRestrictions, Protocol


class EnvironmentVariableSubstitutor(IEnvironmentVariableSubstitutor):
    """Handles environment variable substitution"""
    
    def substitute_variables(self, text: str) -> str:
        """Substitute environment variables in text using ${VAR_NAME} syntax"""
        def replace_env_var(match):
            var_name = match.group(1)
            return os.getenv(var_name, f"${{{var_name}}}")  # Keep original if not found
        
        return re.sub(r'\$\{([^}]+)\}', replace_env_var, text)


class ConfigurationManager(IConfigurationManager):
    """Manages configuration loading and parsing"""
    
    def __init__(self, env_substitutor: IEnvironmentVariableSubstitutor):
        self._env_substitutor = env_substitutor
        self._servers: List[RemoteServer] = []
        self._security_config: Optional[SecurityConfig] = None
        self._server_groups: Dict[str, ServerGroup] = {}
        self._logger = logging.getLogger(__name__)
    
    async def load_config(self, config_file: str) -> bool:
        """Load configuration from JSON file"""
        try:
            if not os.path.exists(config_file):
                self._logger.warning(f"Config file {config_file} not found")
                return False
            
            with open(config_file, 'r') as f:
                config_content = f.read()
            
            # Substitute environment variables
            config_content = self._env_substitutor.substitute_variables(config_content)
            config = json.loads(config_content)
            
            self._load_servers(config)
            self._load_security_config(config)
            self._load_server_groups(config)
            
            self._logger.info(f"Successfully loaded configuration from {config_file}")
            return True
            
        except json.JSONDecodeError as e:
            self._logger.error(f"Invalid JSON in config file: {e}")
            return False
        except Exception as e:
            self._logger.error(f"Error loading config: {e}")
            return False
    
    def _load_servers(self, config: Dict[str, Any]) -> None:
        """Load server configurations"""
        if "remote_servers" not in config:
            return
        
        self._servers = []
        for server_config in config["remote_servers"]:
            server = RemoteServer(
                name=server_config["name"],
                host=server_config["host"],
                port=server_config["port"],
                protocol=server_config.get("protocol", Protocol.HTTPS.value),
                auth_token=server_config.get("auth_token"),
                ssh_key_path=server_config.get("ssh_key_path"),
                tags=server_config.get("tags", []),
                ssl_verify=server_config.get("ssl_verify", True),
                timeout=server_config.get("timeout", 30),
                retry_attempts=server_config.get("retry_attempts", 3),
                custom_headers=server_config.get("custom_headers", {}),
                allowed_commands=server_config.get("allowed_commands", [])
            )
            self._servers.append(server)
    
    def _load_security_config(self, config: Dict[str, Any]) -> None:
        """Load security configuration"""
        if "security" not in config:
            return
        
        sec_config = config["security"]
        rate_limit = sec_config.get("rate_limit", {})
        audit_log = sec_config.get("audit_log", {})
        
        self._security_config = SecurityConfig(
            default_timeout=sec_config.get("default_timeout", 30),
            max_concurrent_connections=sec_config.get("max_concurrent_connections", 10),
            rate_limit_requests_per_minute=rate_limit.get("requests_per_minute", 60),
            rate_limit_burst_size=rate_limit.get("burst_size", 10),
            audit_log_enabled=audit_log.get("enabled", True),
            audit_log_file=audit_log.get("file", "/var/log/mcp-admin/audit.log"),
            audit_log_level=audit_log.get("level", "INFO")
        )
    
    def _load_server_groups(self, config: Dict[str, Any]) -> None:
        """Load server groups configuration"""
        if "server_groups" not in config:
            return
        
        self._server_groups = {}
        for group_name, group_config in config["server_groups"].items():
            restrictions_config = group_config.get("restrictions", {})
            restrictions = ServerGroupRestrictions(
                dangerous_commands=restrictions_config.get("dangerous_commands", True),
                file_write=restrictions_config.get("file_write", True),
                service_restart=restrictions_config.get("service_restart", True)
            )
            
            self._server_groups[group_name] = ServerGroup(
                name=group_name,
                tags=group_config.get("tags", []),
                restrictions=restrictions
            )
    
    def get_servers(self) -> List[RemoteServer]:
        """Get all configured servers"""
        return self._servers.copy()
    
    def get_security_config(self) -> Optional[SecurityConfig]:
        """Get security configuration"""
        return self._security_config
    
    def get_server_groups(self) -> Dict[str, ServerGroup]:
        """Get server groups"""
        return self._server_groups.copy() 