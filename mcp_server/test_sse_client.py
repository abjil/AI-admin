#!/usr/bin/env python3
"""
Test client for SSE MCP server
Demonstrates how to connect to and interact with an SSE-based MCP server
"""

import asyncio
import sys
from fastmcp import Client
from fastmcp.client.transports import SSETransport

async def test_sse_connection(server_url="http://localhost:8080/sse"):
    """Test connection to SSE MCP server"""
    
    print(f"Testing SSE connection to: {server_url}")
    print("-" * 50)
    
    try:
        # Create SSE transport
        transport = SSETransport(url=server_url)
        client = Client(transport)
        
        async with client:
            print("✓ Connected to SSE server")
            
            # Test ping
            try:
                await client.ping()
                print("✓ Ping successful")
            except Exception as e:
                print(f"✗ Ping failed: {e}")
            
            # List available tools
            try:
                tools = await client.list_tools()
                print(f"✓ Found {len(tools)} tools:")
                for tool in tools:
                    print(f"  - {tool.name}: {tool.description}")
            except Exception as e:
                print(f"✗ Failed to list tools: {e}")
                return
            
            # Test a simple tool call
            if tools:
                tool_name = tools[0].name
                print(f"\n🔧 Testing tool: {tool_name}")
                try:
                    result = await client.call_tool(tool_name)
                    print(f"✓ Tool result: {result}")
                except Exception as e:
                    print(f"✗ Tool call failed: {e}")
            
            # List resources if available
            try:
                resources = await client.list_resources()
                if resources:
                    print(f"✓ Found {len(resources)} resources:")
                    for resource in resources:
                        print(f"  - {resource.uri}: {resource.name}")
                else:
                    print("ℹ No resources available")
            except Exception as e:
                print(f"ℹ Resources not available: {e}")
                
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        print("\nTroubleshooting tips:")
        print("1. Ensure the MCP server is running with SSE transport:")
        print("   python remote_admin_server.py --transport sse")
        print("2. Check if the server is listening on the port:")
        print("   netstat -tulnp | grep 8080")
        print("3. Test the SSE endpoint directly:")
        print(f"   curl -I {server_url}")

async def test_with_auth(server_url="http://localhost:8080/sse", auth_token=None):
    """Test SSE connection with authentication"""
    
    print(f"Testing SSE connection with auth to: {server_url}")
    print("-" * 50)
    
    headers = {}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
        print(f"Using auth token: {auth_token[:10]}...")
    
    try:
        transport = SSETransport(url=server_url, headers=headers)
        client = Client(transport)
        
        async with client:
            print("✓ Connected with authentication")
            tools = await client.list_tools()
            print(f"✓ Authenticated access to {len(tools)} tools")
            
    except Exception as e:
        print(f"✗ Authentication failed: {e}")

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Test SSE MCP Client")
    parser.add_argument(
        "--url", "-u",
        default="http://localhost:8080/sse",
        help="SSE server URL (default: http://localhost:8080/sse)"
    )
    parser.add_argument(
        "--auth-token", "-t",
        help="Authentication token"
    )
    parser.add_argument(
        "--test-auth",
        action="store_true",
        help="Test authentication"
    )
    
    args = parser.parse_args()
    
    print("MCP SSE Client Test")
    print("=" * 50)
    
    if args.test_auth:
        asyncio.run(test_with_auth(args.url, args.auth_token))
    else:
        asyncio.run(test_sse_connection(args.url))

if __name__ == "__main__":
    main() 