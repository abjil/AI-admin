#!/usr/bin/env python3
"""
Refactored MCP Remote Admin System - Main Application
Follows SOLID principles:
- Single Responsibility: Each class has one clear purpose
- Open/Closed: Extensible through interfaces without modification
- Liskov Substitution: Interfaces can be substituted with implementations
- Interface Segregation: Small, focused interfaces
- Dependency Inversion: Depends on abstractions, not concretions
"""

import asyncio
import logging
import argparse
from typing import Optional
from mcp.server.fastmcp import FastMCP

# Import our SOLID-compliant architecture
from core.services import RemoteAdminService
from core.mcp_tools import MCPToolsProvider


class RemoteAdminApplication:
    """
    Main application class following Single Responsibility Principle.
    Only responsible for application lifecycle and coordination.
    """
    
    def __init__(self, app_name: str = "Remote Admin Controller"):
        self._app_name = app_name
        self._mcp_app = FastMCP(app_name)
        self._admin_service: Optional[RemoteAdminService] = None
        self._mcp_tools: Optional[MCPToolsProvider] = None
        self._logger = logging.getLogger(__name__)
    
    async def initialize(self, config_file: str) -> bool:
        """
        Initialize the application with dependency injection.
        Follows Dependency Inversion Principle.
        """
        try:
            # Initialize the main service (composition root)
            self._admin_service = RemoteAdminService()
            
            # Initialize service with configuration
            if not await self._admin_service.initialize(config_file):
                self._logger.error("Failed to initialize admin service")
                return False
            
            # Initialize MCP tools provider with service dependency
            self._mcp_tools = MCPToolsProvider(self._admin_service, self._mcp_app)
            
            self._logger.info(f"{self._app_name} initialized successfully")
            return True
            
        except Exception as e:
            self._logger.error(f"Failed to initialize application: {e}")
            return False
    
    async def connect_all_servers(self) -> bool:
        """Connect to all configured servers"""
        if not self._admin_service:
            self._logger.error("Service not initialized")
            return False
        
        try:
            connection_results = await self._admin_service.connect_all_servers()
            successful_connections = sum(1 for connected in connection_results.values() if connected)
            total_servers = len(connection_results)
            
            self._logger.info(f"Connected to {successful_connections}/{total_servers} servers")
            
            if successful_connections < total_servers:
                failed_servers = [name for name, connected in connection_results.items() if not connected]
                self._logger.warning(f"Failed to connect to: {', '.join(failed_servers)}")
            
            return successful_connections > 0
            
        except Exception as e:
            self._logger.error(f"Error connecting to servers: {e}")
            return False
    
    async def run_server(self, port: Optional[int] = None) -> None:
        """Run the MCP server"""
        if not self._admin_service or not self._mcp_tools:
            raise RuntimeError("Application not properly initialized")
        
        try:
            run_kwargs = {}
            if port:
                run_kwargs['port'] = port
            
            self._logger.info(f"Starting {self._app_name} MCP server...")
            await self._mcp_app.run(**run_kwargs)
            
        except Exception as e:
            self._logger.error(f"Error running server: {e}")
            raise
        finally:
            await self.shutdown()
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the application"""
        if self._admin_service:
            try:
                await self._admin_service.shutdown()
                self._logger.info(f"{self._app_name} shut down gracefully")
            except Exception as e:
                self._logger.error(f"Error during shutdown: {e}")


class ConfigurationValidator:
    """
    Validates command line arguments and configuration.
    Follows Single Responsibility Principle.
    """
    
    @staticmethod
    def create_argument_parser() -> argparse.ArgumentParser:
        """Create and configure argument parser"""
        parser = argparse.ArgumentParser(
            description="MCP Remote Admin Controller - SOLID Architecture",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  %(prog)s                                    # Use default config.json
  %(prog)s --config production.json          # Use custom config
  %(prog)s --config dev.json --verbose       # With verbose logging
  %(prog)s --no-auto-load --port 8081        # Manual loading, custom port
            """
        )
        
        parser.add_argument(
            "--config", "-c",
            default="config.json",
            help="Path to configuration file (default: config.json)"
        )
        
        parser.add_argument(
            "--no-auto-load",
            action="store_true",
            help="Don't automatically load config file on startup"
        )
        
        parser.add_argument(
            "--port", "-p",
            type=int,
            help="Port to run MCP server on"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging"
        )
        
        return parser
    
    @staticmethod
    def validate_arguments(args: argparse.Namespace) -> bool:
        """Validate parsed arguments"""
        if args.port and (args.port < 1 or args.port > 65535):
            print("Error: Port must be between 1 and 65535")
            return False
        
        return True


class LoggingConfigurator:
    """
    Configures application logging.
    Follows Single Responsibility Principle.
    """
    
    @staticmethod
    def setup_logging(verbose: bool = False) -> None:
        """Setup application logging"""
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(),
                # Could add file handler here if needed
            ]
        )
        
        # Set specific log levels for noisy libraries
        logging.getLogger('aiohttp').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)


async def main() -> None:
    """
    Main entry point following SOLID principles.
    Acts as the composition root for dependency injection.
    """
    # Parse and validate command line arguments
    parser = ConfigurationValidator.create_argument_parser()
    args = parser.parse_args()
    
    if not ConfigurationValidator.validate_arguments(args):
        parser.print_help()
        return
    
    # Setup logging
    LoggingConfigurator.setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    # Create and initialize application
    app = RemoteAdminApplication()
    
    try:
        # Initialize application (dependency injection happens here)
        if not args.no_auto_load:
            logger.info(f"Auto-loading configuration from {args.config}")
            
            if not await app.initialize(args.config):
                logger.error(f"Failed to initialize with config {args.config}")
                logger.info("You can still use the application, but servers must be registered manually")
                # Initialize with empty service for manual registration
                app._admin_service = RemoteAdminService()
                from core.mcp_tools import MCPToolsProvider
                app._mcp_tools = MCPToolsProvider(app._admin_service, app._mcp_app)
            else:
                # Try to connect to servers
                await app.connect_all_servers()
        else:
            logger.info("Auto-loading disabled - servers can be registered manually")
            # Initialize with empty service
            app._admin_service = RemoteAdminService()
            from core.mcp_tools import MCPToolsProvider
            app._mcp_tools = MCPToolsProvider(app._admin_service, app._mcp_app)
        
        # Run the MCP server
        logger.info("Starting MCP Remote Admin Controller...")
        await app.run_server(args.port)
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise
    finally:
        await app.shutdown()


if __name__ == "__main__":
    """
    Entry point that handles the event loop.
    Follows separation of concerns.
    """
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nShutdown complete.")
    except Exception as e:
        print(f"Fatal error: {e}")
        exit(1) 