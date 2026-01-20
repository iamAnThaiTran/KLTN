# app/utils/llm_utils.py

import os
from typing import Optional

def call_llm(
    prompt: str, 
    max_tokens: int = 500,
    json_mode: bool = False
) -> str:
    """
    Wrapper để gọi LLM (Claude hoặc GPT)
    
    Bạn có thể thay đổi implementation tùy theo API bạn dùng
    """
    
    # Option 1: Dùng Anthropic Claude
    try:
        import anthropic
        
        client = anthropic.Anthropic(
            api_key=os.environ.get("ANTHROPIC_API_KEY")
        )
        
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=max_tokens,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text
    
    except ImportError:
        pass
    
    # Option 2: Dùng OpenAI GPT
    try:
        import openai
        
        client = openai.OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY")
        )
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Hoặc gpt-4o
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=max_tokens,
            response_format={"type": "json_object"} if json_mode else None
        )
        
        return response.choices[0].message.content
    
    except ImportError:
        pass
    
    # Fallback: Mock response cho testing
    return "LLM response placeholder"


def call_llm_streaming(prompt: str, max_tokens: int = 500):
    """
    Streaming version (nếu cần real-time response)
    """
    import anthropic
    
    client = anthropic.Anthropic(
        api_key=os.environ.get("ANTHROPIC_API_KEY")
    )
    
    with client.messages.stream(
        model="claude-sonnet-4-20250514",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    ) as stream:
        for text in stream.text_stream:
            yield text