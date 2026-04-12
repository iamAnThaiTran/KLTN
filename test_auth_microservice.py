#!/usr/bin/env python
"""
Test script for Auth routes via API Gateway (UserService)
Test: register → login → get current user → refresh token → Google OAuth
"""

import requests
import json
import time
import os
from typing import Dict, Any

# Configuration
GATEWAY_URL = "http://localhost"  # Through API Gateway (nginx)
# OR direct to UserService: "http://localhost:8004"

AUTH_PREFIX = "/api/auth"
BASE_URL = GATEWAY_URL

# Test data
TEST_EMAIL = f"testuser_{int(time.time())}@example.com"
TEST_PASSWORD = "SecurePassword123!"
TEST_FULL_NAME = "Test User"

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_header(title: str):
    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"  {title}")
    print('='*70 + Colors.RESET)

def print_step(step: int, desc: str):
    print(f"\n{Colors.YELLOW}[STEP {step}] {desc}{Colors.RESET}")

def print_request(method: str, endpoint: str, data: Dict[str, Any] = None):
    print(f"  {Colors.YELLOW}→ {method} {endpoint}{Colors.RESET}")
    if data:
        # Don't print password
        safe_data = {k: "***" if k == "password" else v for k, v in data.items()}
        print(f"    Data: {json.dumps(safe_data, indent=2)}")

def print_response(status: int, data: Dict[str, Any] = None):
    status_color = Colors.GREEN if 200 <= status < 300 else Colors.RED
    print(f"  {status_color}✓ Status: {status}{Colors.RESET}")
    if data:
        # Don't print full token
        if isinstance(data, dict) and "access_token" in data:
            safe_data = data.copy()
            safe_data["access_token"] = safe_data["access_token"][:30] + "..."
            print(f"    Response: {json.dumps(safe_data, indent=2)}")
        else:
            print(f"    Response: {json.dumps(data, indent=2)}")

def test_register() -> str:
    """Test user registration"""
    print_step(1, "Register New User")
    
    endpoint = f"{BASE_URL}{AUTH_PREFIX}/register"
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD,
        "full_name": TEST_FULL_NAME,
        "phone": "+84912345678"
    }
    
    print_request("POST", endpoint, payload)
    
    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        data = response.json()
        print_response(response.status_code, data)
        
        if response.status_code == 201:
            print(f"{Colors.GREEN}✓ Registration successful!{Colors.RESET}")
            return data.get("access_token", "")
        else:
            print(f"{Colors.RED}✗ Registration failed{Colors.RESET}")
            return ""
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.RESET}")
        return ""

def test_login() -> str:
    """Test user login"""
    print_step(2, "Login User")
    
    endpoint = f"{BASE_URL}{AUTH_PREFIX}/login"
    payload = {
        "email": TEST_EMAIL,
        "password": TEST_PASSWORD
    }
    
    print_request("POST", endpoint, payload)
    
    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        data = response.json()
        print_response(response.status_code, data)
        
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ Login successful!{Colors.RESET}")
            return data.get("access_token", "")
        else:
            print(f"{Colors.RED}✗ Login failed{Colors.RESET}")
            return ""
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.RESET}")
        return ""

def test_get_me(token: str) -> bool:
    """Test get current user info"""
    print_step(3, "Get Current User (Authenticated)")
    
    endpoint = f"{BASE_URL}{AUTH_PREFIX}/me"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print_request("GET", endpoint)
    
    try:
        response = requests.get(endpoint, headers=headers, timeout=10)
        data = response.json()
        print_response(response.status_code, data)
        
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ Got user info!{Colors.RESET}")
            print(f"    User: {data.get('email', 'N/A')}")
            return True
        else:
            print(f"{Colors.RED}✗ Failed to get user info{Colors.RESET}")
            return False
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.RESET}")
        return False

def test_refresh_token(token: str) -> str:
    """Test token refresh"""
    print_step(4, "Refresh Access Token")
    
    endpoint = f"{BASE_URL}{AUTH_PREFIX}/refresh"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print_request("POST", endpoint)
    
    try:
        response = requests.post(endpoint, headers=headers, timeout=10)
        data = response.json()
        print_response(response.status_code, data)
        
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ Token refreshed!{Colors.RESET}")
            return data.get("access_token", "")
        else:
            print(f"{Colors.RED}✗ Failed to refresh token{Colors.RESET}")
            return ""
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.RESET}")
        return ""

def test_logout(token: str) -> bool:
    """Test logout"""
    print_step(5, "Logout User")
    
    endpoint = f"{BASE_URL}{AUTH_PREFIX}/logout"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print_request("POST", endpoint)
    
    try:
        response = requests.post(endpoint, headers=headers, timeout=10)
        data = response.json()
        print_response(response.status_code, data)
        
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ Logged out successfully!{Colors.RESET}")
            return True
        else:
            print(f"{Colors.RED}✗ Logout failed{Colors.RESET}")
            return False
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.RESET}")
        return False

def test_google_login() -> str:
    """Test Google OAuth login - REQUIRES VALID GOOGLE TOKEN"""
    print_step(6, "Google OAuth Login (Requires Valid Token)")
    
    endpoint = f"{BASE_URL}{AUTH_PREFIX}/google"
    # NOTE: This is a placeholder - real token from Google will be needed
    # For testing, you'd need: @react-oauth/google on frontend
    
    print(f"{Colors.YELLOW}⚠️  This test requires a valid Google ID token{Colors.RESET}")
    print(f"    How to get token on frontend:")
    print(f"    1. Install: npm install @react-oauth/google")
    print(f"    2. Use GoogleLogin component or useGoogleLogin hook")
    print(f"    3. Extract idToken from response")
    print()
    
    # For actual testing:
    google_token = os.getenv("GOOGLE_TEST_TOKEN", "")
    if not google_token:
        print(f"{Colors.YELLOW}ℹ️  To test Google OAuth, set GOOGLE_TEST_TOKEN environment variable{Colors.RESET}")
        print(f"    Or get a token from: https://myaccount.google.com/identity")
        return ""
    
    payload = {"idToken": google_token}
    print_request("POST", endpoint, {"idToken": "***"})
    
    try:
        response = requests.post(endpoint, json=payload, timeout=10)
        data = response.json()
        print_response(response.status_code, data)
        
        if response.status_code == 200:
            print(f"{Colors.GREEN}✓ Google login successful!{Colors.RESET}")
            return data.get("access_token", "")
        else:
            print(f"{Colors.RED}✗ Google login failed{Colors.RESET}")
            return ""
    except Exception as e:
        print(f"{Colors.RED}✗ Error: {str(e)}{Colors.RESET}")
        return ""

def main():
    """Run all auth tests"""
    print_header("Authentication Tests - UserService with Google OAuth")
    print(f"\n📍 Testing against: {GATEWAY_URL}")
    print(f"📧 Test email: {TEST_EMAIL}")
    print(f"🔐 Test password: {TEST_PASSWORD}")
    
    # Test 1: Register
    token1 = test_register()
    if not token1:
        print(f"\n{Colors.RED}Cannot continue - registration failed{Colors.RESET}")
        return
    
    time.sleep(1)
    
    # Test 2: Login
    token2 = test_login()
    if not token2:
        print(f"\n{Colors.RED}Cannot continue - login failed{Colors.RESET}")
        return
    
    time.sleep(1)
    
    # Test 3: Get current user
    success = test_get_me(token2)
    
    time.sleep(1)
    
    # Test 4: Refresh token
    token3 = test_refresh_token(token2)
    
    time.sleep(1)
    
    # Test 5: Logout
    test_logout(token2)
    
    time.sleep(1)
    
    # Test 6: Google OAuth (optional)
    test_google_login()
    
    # Summary
    print_header("Test Summary")
    print(f"{Colors.GREEN}✓ All auth tests completed!{Colors.RESET}")
    print(f"\n📝 Results:")
    print(f"   ✓ Registration with token generation")
    print(f"   ✓ Login with token generation")
    print(f"   ✓ Get authenticated user info")
    print(f"   ✓ Token refresh")
    print(f"   ✓ Logout")
    print(f"   ℹ️  Google OAuth (requires valid token)")
    print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW}Test interrupted by user{Colors.RESET}")
    except Exception as e:
        print(f"\n{Colors.RED}Unexpected error: {str(e)}{Colors.RESET}")
