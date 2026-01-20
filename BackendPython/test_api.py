#!/usr/bin/env python
# test_api.py

import requests
import json

API_URL = "http://localhost:8000"

# Test 1: Health check
print("=" * 50)
print("Test 1: Health Check")
print("=" * 50)
try:
    response = requests.get(f"{API_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Query endpoint
print("\n" + "=" * 50)
print("Test 2: Query Endpoint")
print("=" * 50)
try:
    response = requests.post(
        f"{API_URL}/api/query",
        json={
            "user_input": "tôi muốn mua giày",
            "conversation_id": None
        }
    )
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")

print("\nAll tests completed!")
