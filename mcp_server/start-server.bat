@echo off
REM MCP Remote Admin Server Startup Script for Windows

setlocal EnableDelayedExpansion

REM Set default values
set CONFIG_FILE=server_config.json
set PORT=
set HOST=
set TRANSPORT=
set ARGS=

REM Parse command line arguments
:parse_args
if "%1"=="" goto start_server
if "%1"=="-c" (
    set CONFIG_FILE=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--config" (
    set CONFIG_FILE=%2
    shift
    shift
    goto parse_args
)
if "%1"=="-p" (
    set PORT=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--port" (
    set PORT=%2
    shift
    shift
    goto parse_args
)
if "%1"=="-h" (
    set HOST=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--host" (
    set HOST=%2
    shift
    shift
    goto parse_args
)
if "%1"=="-t" (
    set TRANSPORT=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--transport" (
    set TRANSPORT=%2
    shift
    shift
    goto parse_args
)
if "%1"=="--help" (
    goto show_usage
)
echo Unknown option: %1
goto show_usage

:show_usage
echo Usage: %0 [OPTIONS]
echo.
echo Options:
echo   -c, --config FILE      Configuration file (default: server_config.json)
echo   -p, --port PORT        Override port from config
echo   -h, --host HOST        Override host from config
echo   -t, --transport MODE   Transport mode: stdio, sse, streamable-http
echo   --help                Show this help message
echo.
echo Environment Variables:
echo   MCP_AUTH_TOKEN       Authentication token for the server
echo.
echo Transport Modes:
echo   stdio (default)        For local MCP clients like Claude Desktop
echo   sse                   For web clients using Server-Sent Events
echo   streamable-http       For modern web clients (recommended)
echo.
echo Examples:
echo   %0                                    # STDIO mode (default)
echo   %0 -t sse                            # SSE web mode
echo   %0 -t streamable-http                # Modern web mode
echo   %0 -c production.json -t sse         # Custom config + SSE
echo   %0 -t sse -p 9090                   # SSE mode, custom port
echo   set MCP_AUTH_TOKEN=secret123 ^& %0 -t sse  # With authentication
goto :eof

:start_server
REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    exit /b 1
)

REM Check if config file exists
if not exist "%CONFIG_FILE%" (
    echo Warning: Config file '%CONFIG_FILE%' not found
    echo The server will use default configuration
)

REM Build command arguments
set ARGS=--config %CONFIG_FILE%

if not "%PORT%"=="" (
    set ARGS=%ARGS% --port %PORT%
)

if not "%HOST%"=="" (
    set ARGS=%ARGS% --host %HOST%
)

if not "%TRANSPORT%"=="" (
    set ARGS=%ARGS% --transport %TRANSPORT%
)

REM Check for authentication token
if "%MCP_AUTH_TOKEN%"=="" (
    echo Warning: MCP_AUTH_TOKEN not set - server will run without authentication
)

REM Start the server
echo Starting MCP Remote Admin Server...
echo Config file: %CONFIG_FILE%
echo Arguments: %ARGS%
echo.

python remote_admin_server.py %ARGS% 