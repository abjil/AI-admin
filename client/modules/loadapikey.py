"""
This module is used to load the API key from the .env file, and it was created because of some bugs in loading it in the app.py file.
"""

from dotenv import load_dotenv
import os
import logging
from .utils import log_message

class LoadAPIKey:
    """Load the API key from the .env file"""
    def __init__(self, env_path: str, logger: logging.Logger):
        self.api_key = None
        self.env_path = env_path
        self.logger = logger

    def simple_load_api_key(self):
        load_dotenv("../.env")
        self.api_key = os.getenv('TOGETHER_API_KEY')
        self.logger.info(log_message(f"API key loaded: {self.api_key}"))
    

