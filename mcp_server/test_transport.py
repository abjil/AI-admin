#!/usr/bin/env python3
"""
Test script to verify MCP server transport modes
"""

import subprocess
import time
import sys
import os
import signal
import socket

def check_port_listening(port):
    """Check if a port is listening"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result == 0
    except:
        return False

def test_stdio_mode():
    """Test STDIO mode (default)"""
    print("Testing STDIO mode...")
    
    # Start server in background
    proc = subprocess.Popen([
        sys.executable, "remote_admin_server.py", 
        "--config", "server_config.json"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(2)  # Wait for startup
    
    # Check if process is running
    if proc.poll() is None:
        print("✓ STDIO server started successfully")
        # STDIO mode should NOT bind to any port
        if not check_port_listening(8080):
            print("✓ STDIO mode correctly does not bind to network port")
        else:
            print("✗ STDIO mode unexpectedly bound to network port")
    else:
        stdout, stderr = proc.communicate()
        print(f"✗ STDIO server failed to start")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
    
    # Clean up
    if proc.poll() is None:
        proc.terminate()
        proc.wait()
    
    print()

def test_sse_mode():
    """Test SSE mode"""
    print("Testing SSE mode...")
    
    # Start server in SSE mode
    proc = subprocess.Popen([
        sys.executable, "remote_admin_server.py",
        "--config", "server_config.json",
        "--transport", "sse"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(3)  # Wait for startup
    
    # Check if process is running
    if proc.poll() is None:
        print("✓ SSE server started successfully")
        # SSE mode should bind to port 8080
        if check_port_listening(8080):
            print("✓ SSE mode correctly bound to network port 8080")
        else:
            print("✗ SSE mode failed to bind to network port 8080")
    else:
        stdout, stderr = proc.communicate()
        print(f"✗ SSE server failed to start")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
    
    # Clean up
    if proc.poll() is None:
        proc.terminate()
        proc.wait()
    
    print()

def test_streamable_http_mode():
    """Test Streamable HTTP mode"""
    print("Testing Streamable HTTP mode...")
    
    # Start server in Streamable HTTP mode
    proc = subprocess.Popen([
        sys.executable, "remote_admin_server.py",
        "--config", "server_config.json", 
        "--transport", "streamable-http"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    
    time.sleep(3)  # Wait for startup
    
    # Check if process is running
    if proc.poll() is None:
        print("✓ Streamable HTTP server started successfully")
        # Streamable HTTP mode should bind to port 8080
        if check_port_listening(8080):
            print("✓ Streamable HTTP mode correctly bound to network port 8080")
        else:
            print("✗ Streamable HTTP mode failed to bind to network port 8080")
    else:
        stdout, stderr = proc.communicate()
        print(f"✗ Streamable HTTP server failed to start")
        print(f"STDOUT: {stdout}")
        print(f"STDERR: {stderr}")
    
    # Clean up
    if proc.poll() is None:
        proc.terminate()
        proc.wait()
    
    print()

def main():
    """Main test function"""
    print("MCP Server Transport Mode Test")
    print("=" * 40)
    
    # Change to script directory
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Check if server script exists
    if not os.path.exists("remote_admin_server.py"):
        print("Error: remote_admin_server.py not found")
        sys.exit(1)
    
    # Check if config exists
    if not os.path.exists("server_config.json"):
        print("Error: server_config.json not found")
        sys.exit(1)
    
    # Test each transport mode
    test_stdio_mode()
    test_sse_mode()
    test_streamable_http_mode()
    
    print("Transport mode testing complete!")

if __name__ == "__main__":
    main() 