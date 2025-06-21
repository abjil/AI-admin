from datetime import datetime

datetime_format = "%Y-%m-%d %H:%M:%S"

def log_message(message: str)->str:
    """Log a message with timestamp"""
    return f"[{datetime.now().strftime(datetime_format)}] {message}"