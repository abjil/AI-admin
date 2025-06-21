@echo off
REM MCP Remote Admin Controller Startup Script for Windows
REM This script sets up environment variables and starts the admin controller

REM Set environment variables for authentication tokens
REM These should be set securely in production (e.g., from secrets manager)
set PROD_WEB_01_TOKEN=prod-web-token-replace-with-real-token
set DEV_SERVER_TOKEN=dev-server-token-replace-with-real-token
set CI_SERVER_TOKEN=ci-server-token-replace-with-real-token
set DB_PRIMARY_TOKEN=db-primary-token-replace-with-real-token

REM Optional: Set custom config file path
if "%1"=="" (
    set CONFIG_FILE=config.json
) else (
    set CONFIG_FILE=%1
)

REM Check if config file exists
if not exist "%CONFIG_FILE%" (
    echo Config file %CONFIG_FILE% not found!
    echo Creating example config from config.example.json...
    
    if exist "config.example.json" (
        copy config.example.json "%CONFIG_FILE%"
        echo Example config copied to %CONFIG_FILE%
        echo Please edit %CONFIG_FILE% with your actual server details and tokens
        pause
        exit /b 1
    ) else (
        echo config.example.json not found either. Please create a config file.
        pause
        exit /b 1
    )
)

echo Starting MCP Remote Admin Controller...
echo Config file: %CONFIG_FILE%
echo Available environment variables:
echo   PROD_WEB_01_TOKEN: %PROD_WEB_01_TOKEN:~0,10%...
echo   DEV_SERVER_TOKEN: %DEV_SERVER_TOKEN:~0,10%...
echo   CI_SERVER_TOKEN: %CI_SERVER_TOKEN:~0,10%...
echo   DB_PRIMARY_TOKEN: %DB_PRIMARY_TOKEN:~0,10%...

REM Start the admin controller with auto-loading enabled
python ai-admin.py --config "%CONFIG_FILE%" --verbose

pause 