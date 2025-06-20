# AI Admin Chatbot

A Flask-based chatbot application that integrates with TogetherAI for LLM responses and connects to your MCP (Model Context Protocol) remote admin client for server management capabilities.

## Features

- **Two-Panel Interface**: 
  - Left panel: Chat interface with TogetherAI-powered responses
  - Right panel: MCP server status and available tools
  - Resizable panels with drag handle
- **Real-time Updates**: WebSocket integration for live chat and MCP status updates
- **MCP Integration**: Connects to your running ai-admin-refactored.py MCP client
- **Beautiful UI**: Modern, responsive design with animations

## Setup

### 1. Install Dependencies

```bash
cd ai-admin-chatbot
pip install -r requirements.txt
```

### 2. Configure Environment

Copy the example configuration:
```bash
cp config.example .env
```

Edit `.env` with your actual values:
```
TOGETHER_API_KEY=your_actual_together_ai_api_key
FLASK_SECRET_KEY=your_random_secret_key
FLASK_DEBUG=False
PORT=5000
```

### 3. Get TogetherAI API Key

1. Sign up at [TogetherAI](https://together.ai/)
2. Get your API key from the dashboard
3. Add it to your `.env` file

## Usage

### 1. Start Your MCP Client

First, make sure your MCP client is running:
```bash
cd ..
python ai-admin-refactored.py --config config.json
```

### 2. Start the Chatbot

In a new terminal:
```bash
cd ai-admin-chatbot
python app.py
```

### 3. Access the Application

Open your browser and go to: `http://localhost:5000`

## Interface

### Chat Panel (Left)
- Type messages to interact with the AI assistant
- The AI has context about your MCP server tools
- Supports multi-line input (Shift+Enter for new line, Enter to send)
- Shows typing indicators and message timestamps

### MCP Panel (Right)
- Shows connection status to your MCP client
- Lists all connected servers
- Displays available tools for each server
- Click on tools to add them to your chat input
- Real-time status updates

### Resizable Layout
- Drag the middle handle to resize panels
- Minimum width: 300px for each panel
- Layout persists during session

## API Endpoints

- `GET /` - Main chatbot interface
- `POST /api/chat` - Send chat messages
- `GET /api/mcp/status` - Get MCP client status
- `GET /api/mcp/servers` - List MCP servers and tools
- `POST /api/mcp/execute` - Execute MCP tools (planned)

## WebSocket Events

- `connect` - Client connection established
- `disconnect` - Client disconnected
- `mcp_status` - MCP status updates
- `chat_message` - Real-time chat messages
- `chat_response` - AI responses
- `error` - Error notifications

## Troubleshooting

### TogetherAI API Issues
- Verify your API key is correct
- Check your TogetherAI account has credits
- Ensure network connectivity

### MCP Connection Issues
- Make sure `ai-admin-refactored.py` is running
- Check that your MCP servers are connected
- Verify the MCP client process is accessible

### Flask Application Issues
- Check all dependencies are installed
- Verify the port is not in use
- Check the application logs for errors

## Development

### Adding New Features
1. Backend: Add routes in `app.py`
2. Frontend: Modify `templates/index.html`
3. Styling: Update the CSS in the template

### Extending MCP Integration
- The `MCPClientManager` class handles MCP communication
- Current implementation simulates MCP status
- TODO: Implement actual MCP client communication

## Security Notes

- Never commit your `.env` file
- Use strong secret keys in production
- Consider rate limiting for API endpoints
- Validate all user inputs

## License

This project is part of the AI-admin system. 