"""
Simple async LLM client for OpenAI calls
"""

import logging
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


class LLMClient:
    """Async LLM client for OpenAI API calls"""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize with OpenAI API key"""
        self.api_key = api_key or OPENAI_API_KEY
        if not self.api_key:
            logger.warning("⚠️ OPENAI_API_KEY not configured")
    
    async def call_openai_async(
        self,
        prompt: str,
        model: str = "gpt-4o-mini",
        max_tokens: int = 2048,
        temperature: float = 0.7,
    ) -> Optional[str]:
        """
        Call OpenAI API asynchronously
        
        Args:
            prompt: User prompt
            model: Model name (gpt-4o-mini, gpt-4o, etc.)
            max_tokens: Max response length
            temperature: Creativity level
            
        Returns:
            LLM response or None if error
        """
        if not self.api_key:
            logger.warning("LLM API key not configured, using mock response")
            return "[LLM response not available - API key not configured]"
        
        try:
            import openai
            
            # Create async client
            client = openai.AsyncOpenAI(api_key=self.api_key)
            
            # Call API
            response = await client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            
            result = response.choices[0].message.content
            logger.info(f"✅ LLM response received ({len(result)} chars)")
            return result
        
        except Exception as e:
            logger.error(f"❌ LLM API call failed: {e}")
            return None
