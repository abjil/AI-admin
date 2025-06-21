@echo off
echo Starting AI Admin Chatbot...
echo.

REM Check if .env file exists
if not exist .env (
    echo Error: .env file not found!
    echo Please copy config.example to .env and configure your API keys.
    pause
    exit /b 1
)

REM Start the Flask application
echo Starting Flask application on http://localhost:5000
echo Press Ctrl+C to stop
echo.
python app.py

pause 