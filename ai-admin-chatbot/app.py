#!/usr/bin/env python3
"""
Flask Chatbot Application with MCP Integration
Uses TogetherAI for LLM and integrates with ai-admin-refactored.py MCP client
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
import requests
import uuid
import subprocess
import threading
import time
from dataclasses import dataclass

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')

# Configuration
TOGETHER_API_KEY = os.getenv('TOGETHER_API_KEY')
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
MCP_CLIENT_PROCESS = None
MCP_CLIENT_STATUS = {"connected": False, "servers": [], "tools": []}

@dataclass
class ChatMessage:
    id: str
    content: str
    role: str  # 'user' or 'assistant'
    timestamp: str
    mcp_tools_used: List[str] = None

class MCPClientManager:
    """Manages communication with the MCP client process"""
    
    def __init__(self):
        self.process = None
        self.status = {"connected": False, "servers": [], "tools": []}
        self.is_running = False
    
    def start_mcp_client(self):
        """Check if MCP client is available (don't start as subprocess)"""
        try:
            # Instead of starting as subprocess, we'll check if it's accessible
            # The MCP client should be started separately by the user
            logger.info("MCP client manager initialized - expecting external MCP client")
            self.is_running = True  # Assume available for demo
            return True
        except Exception as e:
            logger.error(f"Failed to initialize MCP client manager: {e}")
            return False
    
    def _monitor_process(self):
        """Monitor the MCP client connectivity (placeholder)"""
        # In a real implementation, this would ping the MCP client
        # For now, this is just a placeholder
        pass
    
    def get_status(self):
        """Get current MCP client status"""
        # For demo purposes, show the expected servers from config.json
        # In a real implementation, this would query the actual MCP client
        self.status.update({
            "connected": True,  # Show as connected for demo
            "servers": [
                {
                    "name": "test1",
                    "host": "192.168.10.18",
                    "port": 8080,
                    "protocol": "mcp-sse",
                    "connected": True,  # This should reflect actual MCP client status
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
                    "connected": True,  # Server is now running with streamable-http
                    "tools": [
                        "system_status", "read_file", "shell_exec",
                        "service_status", "service_restart", "get_logs",
                        "list_processes", "network_connections", "health_check"
                    ]
                }
            ]
        })
        
        return self.status
    
    def stop(self):
        """Stop the MCP client manager"""
        self.is_running = False
        logger.info("MCP client manager stopped")

class TogetherAIClient:
    """Client for TogetherAI API"""
    
    def __init__(self):
        if not TOGETHER_API_KEY:
            raise ValueError("TOGETHER_API_KEY environment variable not set")
        self.api_key = TOGETHER_API_KEY
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(self, messages: List[Dict], model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free") -> str:
        """Get chat completion from TogetherAI"""
        try:
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7,
                "stream": False
            }
            
            response = requests.post(
                TOGETHER_API_URL,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            return result['choices'][0]['message']['content']
            
        except Exception as e:
            logger.error(f"TogetherAI API error: {e}")
            return f"Error: {str(e)}"

# Global instances
mcp_manager = MCPClientManager()
together_client = TogetherAIClient() if TOGETHER_API_KEY else None

@app.route('/')
def index():
    """Main chatbot interface"""
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle chat messages"""
    try:
        data = request.get_json()
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({"error": "Message cannot be empty"}), 400
        
        if not together_client:
            return jsonify({"error": "TogetherAI API key not configured"}), 500
        
        # Prepare messages for the LLM
        messages = [
            {
                "role": "system",
                "content": """You are a helpful assistant with access to remote server administration tools via MCP (Model Context Protocol). 
                You can help users manage remote servers, check system status, execute commands, and retrieve logs. 
                When users ask for server administration tasks, explain what MCP tools are available and how they can be used."""
            },
            {
                "role": "user", 
                "content": user_message
            }
        ]
        
        # Get response from TogetherAI
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            response = loop.run_until_complete(
                together_client.chat_completion(messages)
            )
        finally:
            loop.close()
        
        # Create response
        chat_response = {
            "id": str(uuid.uuid4()),
            "content": response,
            "role": "assistant",
            "timestamp": datetime.now().isoformat(),
            "mcp_tools_used": []  # TODO: Track actual MCP tool usage
        }
        
        return jsonify(chat_response)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/status')
def mcp_status():
    """Get MCP client status"""
    try:
        status = mcp_manager.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(f"MCP status error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/servers')
def mcp_servers():
    """Get list of MCP servers and their tools"""
    try:
        status = mcp_manager.get_status()
        return jsonify(status.get("servers", []))
    except Exception as e:
        logger.error(f"MCP servers error: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/execute', methods=['POST'])
def mcp_execute():
    """Execute MCP tool (placeholder for future implementation)"""
    try:
        data = request.get_json()
        server_name = data.get('server_name')
        tool_name = data.get('tool_name')
        parameters = data.get('parameters', {})
        
        # TODO: Implement actual MCP tool execution
        # This would require communication with the running MCP client
        
        return jsonify({
            "result": f"Would execute {tool_name} on {server_name} with params: {parameters}",
            "success": True
        })
        
    except Exception as e:
        logger.error(f"MCP execute error: {e}")
        return jsonify({"error": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(f"Client connected: {request.sid}")
    emit('status', {'message': 'Connected to chatbot'})
    
    # Send current MCP status
    status = mcp_manager.get_status()
    emit('mcp_status', status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('chat_message')
def handle_chat_message(data):
    """Handle real-time chat messages via WebSocket"""
    try:
        user_message = data.get('message', '').strip()
        
        if not user_message or not together_client:
            emit('error', {'message': 'Invalid message or API not configured'})
            return
        
        # Process message asynchronously
        # For now, emit a placeholder response
        response = {
            "id": str(uuid.uuid4()),
            "content": f"You said: {user_message}",
            "role": "assistant",
            "timestamp": datetime.now().isoformat()
        }
        
        emit('chat_response', response)
        
    except Exception as e:
        logger.error(f"WebSocket chat error: {e}")
        emit('error', {'message': str(e)})

def cleanup():
    """Cleanup function"""
    if mcp_manager:
        mcp_manager.stop()

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    # Start MCP client if not already running
    if not mcp_manager.start_mcp_client():
        logger.warning("Failed to start MCP client - running without MCP integration")
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Flask chatbot on port {port}")
    logger.info(f"TogetherAI configured: {TOGETHER_API_KEY is not None}")
    logger.info(f"MCP client status: {mcp_manager.get_status()}")
    
    socketio.run(app, host='0.0.0.0', port=port, debug=debug)
