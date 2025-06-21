"""
Audit logging implementations.
Focused on compliance and security logging.
"""
import os
import logging
from typing import Optional
from .interfaces import IAuditLogger


class AuditLogger(IAuditLogger):
    """Handles audit logging for compliance and security"""
    
    def __init__(self, log_file: str, log_level: str = "INFO"):
        self._log_file = log_file
        self._logger = logging.getLogger("audit")
        self._logger.setLevel(getattr(logging, log_level.upper()))
        
        # Ensure log directory exists
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        # Add file handler for audit logs
        handler = logging.FileHandler(log_file)
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self._logger.addHandler(handler)
    
    async def log_command_execution(
        self,
        server_name: str,
        command: str,
        user: str,
        success: bool,
        error: Optional[str] = None
    ) -> None:
        """Log command execution for audit"""
        status = "SUCCESS" if success else "FAILED"
        message = f"COMMAND_EXEC - Server: {server_name}, Command: {command}, User: {user}, Status: {status}"
        if error:
            message += f", Error: {error}"
        
        if success:
            self._logger.info(message)
        else:
            self._logger.error(message)
    
    async def log_connection_event(
        self,
        server_name: str,
        event_type: str,
        success: bool,
        details: Optional[str] = None
    ) -> None:
        """Log connection events"""
        status = "SUCCESS" if success else "FAILED"
        message = f"CONNECTION_{event_type.upper()} - Server: {server_name}, Status: {status}"
        if details:
            message += f", Details: {details}"
        
        if success:
            self._logger.info(message)
        else:
            self._logger.warning(message) 