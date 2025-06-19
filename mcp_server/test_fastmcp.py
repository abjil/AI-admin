#!/usr/bin/env python3
"""
Test script to verify FastMCP functionality and supported parameters.
This helps determine what configuration options are actually supported.
"""

import asyncio
import inspect
from mcp.server.fastmcp import FastMCP

def test_fastmcp_constructor():
    """Test FastMCP constructor parameters"""
    print("Testing FastMCP constructor...")
    
    # Get constructor signature
    sig = inspect.signature(FastMCP.__init__)
    print(f"FastMCP.__init__ signature: {sig}")
    
    # Test basic initialization
    try:
        server = FastMCP("test-server")
        print("✓ Basic initialization works")
    except Exception as e:
        print(f"✗ Basic initialization failed: {e}")
        return False
    
    # Test with port parameter
    try:
        server = FastMCP("test-server", port=8081)
        print("✓ Port parameter supported in constructor")
    except TypeError as e:
        print(f"✗ Port parameter not supported in constructor: {e}")
    
    # Test with host parameter
    try:
        server = FastMCP("test-server", host="127.0.0.1")
        print("✓ Host parameter supported in constructor")
    except TypeError as e:
        print(f"✗ Host parameter not supported in constructor: {e}")
    
    return True

def test_fastmcp_run():
    """Test FastMCP run method parameters"""
    print("\nTesting FastMCP.run() method...")
    
    server = FastMCP("test-server")
    
    # Get run method signature
    sig = inspect.signature(server.run)
    print(f"FastMCP.run signature: {sig}")
    
    print("\nSupported parameters:")
    for param_name, param in sig.parameters.items():
        if param_name != 'self':
            print(f"  - {param_name}: {param}")

async def test_server_creation():
    """Test actual server creation and basic functionality"""
    print("\nTesting server creation and basic setup...")
    
    try:
        server = FastMCP("test-server")
        
        # Test adding a simple tool
        @server.tool()
        async def test_tool() -> dict:
            """Test tool"""
            return {"status": "ok", "message": "Test tool works"}
        
        print("✓ Server creation and tool registration works")
        
        # Note: We don't actually run the server to avoid blocking
        print("✓ Server setup completed successfully")
        
    except Exception as e:
        print(f"✗ Server creation failed: {e}")
        return False
    
    return True

def test_event_loop():
    """Test event loop compatibility"""
    print("\nTesting event loop compatibility...")
    
    try:
        # Check if we're in an event loop
        loop = asyncio.get_running_loop()
        print("✗ Already in an asyncio event loop - this may cause issues with FastMCP")
        print("  FastMCP should be run from a clean Python process")
        return False
    except RuntimeError:
        print("✓ No active event loop detected - good for FastMCP")
        return True

def main():
    """Main test function"""
    print("FastMCP Configuration Test")
    print("=" * 40)
    
    # Test event loop first
    if not test_event_loop():
        print("\nWarning: Event loop issues detected!")
    
    # Test constructor
    if not test_fastmcp_constructor():
        return
    
    # Test run method
    test_fastmcp_run()
    
    # Test server creation
    asyncio.run(test_server_creation())
    
    print("\n" + "=" * 40)
    print("Test completed. Check output above for supported parameters.")
    print("\nIf you see event loop warnings, run this script in a fresh Python process.")

if __name__ == "__main__":
    main() 