# app/core/llm_utils.py
"""
LLM Utilities - Using OpenAI API only

Setup:
  1. Get API key from: https://platform.openai.com/api/keys
  2. Add to .env: OPENAI_API_KEY=sk-proj-your-key-here
  3. Make sure openai package is installed: pip install openai
"""

import os
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================
# ⚠️  IMPORTANT: API KEY SETUP
# ============================================================
# Add your OpenAI API key to .env file:
#
#   OPENAI_API_KEY=sk-proj-your-key-here
#
# Get your key from: https://platform.openai.com/api/keys
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

if not OPENAI_API_KEY:
    print("⚠️  WARNING: OPENAI_API_KEY not set!")
    print("   Add to .env file: OPENAI_API_KEY=sk-proj-...")
    print("   Get key from: https://platform.openai.com/api/keys")


def call_openai(
    prompt: str = None,
    messages: List[Dict[str, str]] = None,
    model: str = "gpt-4o-mini",
    max_tokens: int = 500,
    temperature: float = 0.7,
    json_mode: bool = False
) -> Optional[str]:
    """
    Call OpenAI API (api.openai.com) - ONLY PROVIDER NOW
    
    Args:
        prompt: Simple string prompt (backward compatible)
        messages: Chat format messages list
        model: Model name (default: gpt-4o-mini for cost efficiency)
                Options: gpt-4o-mini, gpt-4o, gpt-4-turbo, gpt-3.5-turbo
        max_tokens: Max response length
        temperature: Creativity level (0.0=deterministic, 1.0=creative)
        json_mode: Whether response is JSON
    
    Returns:
        Response text, or None if error
    
    Examples:
        # Simple prompt
        result = call_openai("What is 2+2?")
        
        # Chat format
        result = call_openai(
            messages=[
                {"role": "user", "content": "Hello!"}
            ],
            temperature=0.3
        )
    """
    try:
        import openai
        
        # Create client with API key
        client = openai.OpenAI(
            api_key=OPENAI_API_KEY
        )
        
        # Convert prompt to messages if needed
        if messages is None:
            if prompt is None:
                raise ValueError("Either 'prompt' or 'messages' must be provided")
            messages = [{"role": "user", "content": prompt}]
        
        # Call OpenAI API
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        print(f"❌ OpenAI error: {e}")
        return None


def call_llm(
    prompt: str = None,
    messages: List[Dict[str, str]] = None,
    model: str = "gpt-4o-mini",
    max_tokens: int = 500,
    temperature: float = 0.7,
    provider: Optional[str] = None  # Kept for backward compatibility, ignored
) -> Optional[str]:
    """
    Main LLM wrapper - calls OpenAI only
    
    This replaces the old multi-provider logic.
    Now uses OpenAI exclusively for simplicity and reliability.
    
    Args:
        prompt: String prompt
        messages: Chat messages format
        model: OpenAI model name
        max_tokens: Response length limit
        temperature: Creativity (0.0-1.0)
        provider: Deprecated (ignored, kept for backward compatibility)
    
    Returns:
        LLM response or None
    """
    if provider and provider != "openai":
        print(f"⚠️  Provider '{provider}' is no longer supported.")
        print("   Now using OpenAI only. To use other providers, edit this file.")
    
    return call_openai(
        prompt=prompt,
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature
    )
