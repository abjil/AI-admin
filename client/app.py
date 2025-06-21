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
from together import Together
from dotenv import load_dotenv
from modules.mcpClientManager import MCPClientManager
from modules.togetherAIclient import TogetherAIClient
from modules.utils import log_message
from modules.loadapikey import LoadAPIKey

# Configure logging first
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(script_dir, '.env')

load_api_key = LoadAPIKey(env_path, logger)
load_api_key.simple_load_api_key()

# Debug: Show what directory we're looking in
logger.info(log_message(f"Script directory: {script_dir}"))

# Configuration
TOGETHER_API_KEY = load_api_key.api_key

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('FLASK_SECRET_KEY', 'your-secret-key-here')
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='gevent')
TOGETHER_API_URL = "https://api.together.xyz/v1/chat/completions"
MCP_CLIENT_PROCESS = None
MCP_CLIENT_STATUS = {"connected": False, "servers": [], "tools": []}

# @dataclass
# class ChatMessage:
#     id: str
#     content: str
#     role: str  # 'user' or 'assistant'
#     timestamp: str
#     mcp_tools_used: List[str] = None

# Global instances
mcp_client_manager = MCPClientManager(logger)

# Initialize TogetherAI client with error handling
together_client = None
try:
    if TOGETHER_API_KEY and TOGETHER_API_KEY != "your_together_ai_api_key_here":
        together_client = TogetherAIClient(TOGETHER_API_KEY, logger)
        logger.info(log_message("TogetherAI client initialized successfully"))
    else:
        logger.warning(log_message("TogetherAI API key not configured or using placeholder value"))
except Exception as e:
    logger.error(log_message(f"Failed to initialize TogetherAI client: {e}"))
    together_client = None

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
        
        logger.info(log_message(f"Received chat message: {user_message}"))
        logger.info(log_message(f"TogetherAI client available: {together_client is not None}"))
        logger.info(log_message(f"API key set: {TOGETHER_API_KEY is not None}"))
        
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
        logger.error(log_message(f"Chat error: {e}"))
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/status')
def mcp_status():
    """Get MCP client status"""
    try:
        status = mcp_client_manager.get_status()
        return jsonify(status)
    except Exception as e:
        logger.error(log_message(f"MCP status error: {e}"))
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/servers')
def mcp_servers():
    """Get list of MCP servers and their tools"""
    try:
        status = mcp_client_manager.get_status()
        return jsonify(status.get("servers", []))
    except Exception as e:
        logger.error(log_message(f"MCP servers error: {e}"))
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
        logger.error(log_message(f"MCP execute error: {e}"))
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/subprocess/start', methods=['POST'])
def mcp_subprocess_start():
    """Start MCP client subprocess"""
    try:
        if mcp_client_manager.process and mcp_client_manager.process.poll() is None:
            return jsonify({"error": "MCP client subprocess is already running"}), 400
        
        success = mcp_client_manager.start_mcp_client()
        if success:
            status = mcp_client_manager.get_status()
            logger.info(log_message("MCP client subprocess started via API"))
            return jsonify({
                "message": "MCP client subprocess started successfully",
                "status": status,
                "success": True
            })
        else:
            return jsonify({"error": "Failed to start MCP client subprocess"}), 500
            
    except Exception as e:
        logger.error(log_message(f"MCP subprocess start error: {e}"))
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/subprocess/stop', methods=['POST'])
def mcp_subprocess_stop():
    """Stop MCP client subprocess"""
    try:
        if not mcp_client_manager.process or mcp_client_manager.process.poll() is not None:
            return jsonify({"error": "MCP client subprocess is not running"}), 400
        
        mcp_client_manager.stop()
        logger.info(log_message("MCP client subprocess stopped via API"))
        return jsonify({
            "message": "MCP client subprocess stopped successfully",
            "success": True
        })
        
    except Exception as e:
        logger.error(log_message(f"MCP subprocess stop error: {e}"))
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/subprocess/restart', methods=['POST'])
def mcp_subprocess_restart():
    """Restart MCP client subprocess"""
    try:
        # Stop if running
        if mcp_client_manager.process and mcp_client_manager.process.poll() is None:
            mcp_client_manager.stop()
            time.sleep(2)  # Give it time to stop
        
        # Start again
        success = mcp_client_manager.start_mcp_client()
        if success:
            status = mcp_client_manager.get_status()
            logger.info(log_message("MCP client subprocess restarted via API"))
            return jsonify({
                "message": "MCP client subprocess restarted successfully",
                "status": status,
                "success": True
            })
        else:
            return jsonify({"error": "Failed to restart MCP client subprocess"}), 500
            
    except Exception as e:
        logger.error(log_message(f"MCP subprocess restart error: {e}"))
        return jsonify({"error": str(e)}), 500

@app.route('/api/mcp/subprocess/info')
def mcp_subprocess_info():
    """Get detailed MCP client subprocess information"""
    try:
        info = {
            "process_running": mcp_client_manager.process and mcp_client_manager.process.poll() is None,
            "process_pid": mcp_client_manager.process.pid if mcp_client_manager.process else None,
            "mcp_client_path": mcp_client_manager.mcp_client_path,
            "config_path": mcp_client_manager.config_path,
            "is_running": mcp_client_manager.is_running
        }
        
        # Add process details if running
        if info["process_running"] and mcp_client_manager.process:
            try:
                import psutil
                process = psutil.Process(mcp_client_manager.process.pid)
                info.update({
                    "memory_usage": process.memory_info().rss / 1024 / 1024,  # MB
                    "cpu_percent": process.cpu_percent(),
                    "create_time": process.create_time(),
                    "status": process.status()
                })
            except ImportError:
                logger.warning(log_message("psutil not available for detailed process info"))
            except Exception as e:
                logger.warning(log_message(f"Error getting process details: {e}"))
        
        return jsonify(info)
        
    except Exception as e:
        logger.error(log_message(f"MCP subprocess info error: {e}"))
        return jsonify({"error": str(e)}), 500

@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    logger.info(log_message(f"Client connected: {request.sid}"))
    emit('status', {'message': 'Connected to chatbot'})
    
    # Send current MCP status
    status = mcp_client_manager.get_status()
    emit('mcp_status', status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection"""
    logger.info(log_message(f"Client disconnected: {request.sid}"))

def cleanup():
    """Cleanup function"""
    if mcp_client_manager:
        mcp_client_manager.stop()

import atexit
atexit.register(cleanup)

if __name__ == '__main__':
    # Start MCP client subprocess
    logger.info("=" * 60)
    logger.info(log_message("Starting AI Admin Chatbot with MCP Integration"))
    logger.info("=" * 60)
    
    mcp_started = mcp_client_manager.start_mcp_client()
    if not mcp_started:
        logger.warning(log_message("Failed to start MCP client - running without MCP integration"))
        logger.warning(log_message("Make sure mcp-client/ai-admin-refactored.py and mcp-client/config.json exist"))
    else:
        logger.info(log_message("MCP client subprocess started successfully"))
    
    # Run Flask app
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(log_message(f"Starting Flask chatbot on port {port}"))
    logger.info(log_message(f"TogetherAI API key exists: {TOGETHER_API_KEY is not None}"))
    logger.info(log_message(f"TogetherAI client initialized: {together_client is not None}"))
    logger.info(log_message(f"MCP client status: {mcp_client_manager.get_status()}"))
    
    try:
        socketio.run(app, host='0.0.0.0', port=port, debug=debug)
    except KeyboardInterrupt:
        logger.info(log_message("Shutting down..."))
    finally:
        # Ensure MCP client is stopped on exit
        mcp_client_manager.stop()
