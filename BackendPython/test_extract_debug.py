#!/usr/bin/env python3
from app.core.dynamic_schema import AVAILABLE_CATEGORIES
from app.core.llm_utils import call_openai

categories_text = ", ".join(AVAILABLE_CATEGORIES)
user_input = "tôi muốn mua nước ngọt cocacola"

prompt = f"""User says: "{user_input}"

Product categories: {categories_text}

Which category does user want? Return ONLY the category name or "none" if unclear."""

print("PROMPT TO LLM:")
print(prompt)
print("\n" + "="*60 + "\n")

response = call_openai(prompt, model="gpt-4o-mini", temperature=0.0, max_tokens=10)
print(f"LLM Response: '{response.strip()}'")
