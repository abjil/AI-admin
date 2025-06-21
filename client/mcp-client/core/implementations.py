"""
Backward compatibility layer for implementations.
Re-exports all implementations from the modular files.
"""

# Configuration implementations
from .config import ConfigurationManager, EnvironmentVariableSubstitutor

# Server registry implementations
from .registry import ServerRegistry

# Connection implementations
from .connections import ConnectionManager, HTTPSConnectionFactory

# Command execution implementations
from .commands import CommandExecutor

# Security implementations
from .security import SecurityManager

# Audit logging implementations
from .audit import AuditLogger

# Make all implementations available for import
__all__ = [
    'ConfigurationManager',
    'EnvironmentVariableSubstitutor',
    'ServerRegistry',
    'ConnectionManager',
    'HTTPSConnectionFactory',
    'CommandExecutor',
    'SecurityManager',
    'AuditLogger'
] 