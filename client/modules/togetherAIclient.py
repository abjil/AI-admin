from together import Together
from typing import List, Dict
import logging
from .utils import log_message

class TogetherAIClient:
    """Client for TogetherAI API using the Together library"""
    
    def __init__(self, together_api_key: str, logger: logging.Logger):
        if not together_api_key:
            raise ValueError("TOGETHER_API_KEY environment variable not set")
        self.client = Together(api_key=together_api_key)
        self.logger = logger
    
    async def chat_completion(self, messages: List[Dict], model: str = "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free") -> str:
        """Get chat completion from TogetherAI"""
        try:
            response = self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=1000,
                temperature=0.0
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            self.logger.error(log_message(f"TogetherAI API error: {e}"))
            return f"Error: {str(e)}"