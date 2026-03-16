#!/usr/bin/env python
"""
Test script for authentication routes (register, login, me, logout, refresh)
"""

import requests
import json
from datetime import datetime
import time

# Configuration
BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/auth"

# Test data
TEST_USER = {
    "email": f"testuser_{int(time.time())}@example.com",
    "password": "TestPassword123",
    "full_name": "Test User",
    "phone": "+84912345678"
}

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_step(step_num, description):
    print(f"\n{Colors.BLUE}{'='*60}")
    print(f"STEP {step_num}: {description}")
    print('='*60 + Colors.RESET)

def print_request(method, endpoint, data=None, headers=None):
    print(f"\n{Colors.YELLOW}REQUEST:{Colors.RESET}")
    print(f"  Method: {method}")
    print(f"  Endpoint: {endpoint}")
    if data:
        print(f"  Data: {json.dumps(data, indent=4)}")
    if headers:
        print(f"  Headers: {json.dumps(headers, indent=4)}")

def print_response(status_code, response_data):
    status_color = Colors.GREEN if 200 <= status_code < 300 else Colors.RED
    print(f"\n{Colors.YELLOW}RESPONSE:{Colors.RESET}")
    print(f"  Status Code: {status_color}{status_code}{Colors.RESET}")
    print(f"  Data: {json.dumps(response_data, indent=4)}")

def print_success(message):
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message):
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

# Test 1: Register
def test_register():
    print_step(1, "Register New User")
    
    endpoint = f"{BASE_URL}{API_PREFIX}/register"
    print_request("POST", endpoint, TEST_USER)
    
    try:
        response = requests.post(endpoint, json=TEST_USER)
        response_data = response.json()
        print_response(response.status_code, response_data)
        
        if response.status_code == 201:
            print_success("User registered successfully")
            return response_data
        else:
            print_error(f"Registration failed: {response_data.get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None

# Test 2: Login
def test_login():
    print_step(2, "Login User")
    
    endpoint = f"{BASE_URL}{API_PREFIX}/login"
    login_data = {
        "email": TEST_USER["email"],
        "password": TEST_USER["password"]
    }
    print_request("POST", endpoint, login_data)
    
    try:
        response = requests.post(endpoint, json=login_data)
        response_data = response.json()
        print_response(response.status_code, response_data)
        
        if response.status_code == 200:
            print_success("Login successful")
            return response_data
        else:
            print_error(f"Login failed: {response_data.get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None

# Test 3: Get Current User
def test_get_current_user(token):
    print_step(3, "Get Current User Info")
    
    endpoint = f"{BASE_URL}{API_PREFIX}/me"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print_request("GET", endpoint, headers=headers)
    
    try:
        response = requests.get(endpoint, headers=headers)
        response_data = response.json()
        print_response(response.status_code, response_data)
        
        if response.status_code == 200:
            print_success("Retrieved current user info successfully")
            return response_data
        else:
            print_error(f"Failed to get user info: {response_data.get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None

# Test 4: Refresh Token
def test_refresh_token(token):
    print_step(4, "Refresh Access Token")
    
    endpoint = f"{BASE_URL}{API_PREFIX}/refresh"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print_request("POST", endpoint, headers=headers)
    
    try:
        response = requests.post(endpoint, headers=headers)
        response_data = response.json()
        print_response(response.status_code, response_data)
        
        if response.status_code == 200:
            print_success("Token refreshed successfully")
            return response_data
        else:
            print_error(f"Token refresh failed: {response_data.get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None

# Test 5: Logout
def test_logout(token):
    print_step(5, "Logout User")
    
    endpoint = f"{BASE_URL}{API_PREFIX}/logout"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print_request("POST", endpoint, headers=headers)
    
    try:
        response = requests.post(endpoint, headers=headers)
        response_data = response.json()
        print_response(response.status_code, response_data)
        
        if response.status_code == 200:
            print_success("Logout successful")
            return response_data
        else:
            print_error(f"Logout failed: {response_data.get('detail', 'Unknown error')}")
            return None
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return None

# Test 6: Test Protected Route After Logout (should fail)
def test_protected_route_after_logout(token):
    print_step(6, "Test Protected Route After Logout (should fail)")
    
    endpoint = f"{BASE_URL}{API_PREFIX}/me"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    print_request("GET", endpoint, headers=headers)
    print("  (This should fail with 401 Unauthorized)")
    
    try:
        response = requests.get(endpoint, headers=headers)
        response_data = response.json()
        print_response(response.status_code, response_data)
        
        if response.status_code == 401:
            print_success("Protected route properly requires valid token")
            return True
        else:
            print_error("Expected 401 Unauthorized but got different status")
            return False
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False

# Test Invalid Credentials
def test_invalid_login():
    print_step(7, "Test Invalid Login (should fail)")
    
    endpoint = f"{BASE_URL}{API_PREFIX}/login"
    invalid_login = {
        "email": "nonexistent@example.com",
        "password": "WrongPassword123"
    }
    print_request("POST", endpoint, invalid_login)
    
    try:
        response = requests.post(endpoint, json=invalid_login)
        response_data = response.json()
        print_response(response.status_code, response_data)
        
        if response.status_code == 401:
            print_success("Invalid login properly rejected")
            return True
        else:
            print_error(f"Expected 401 but got {response.status_code}")
            return False
    except Exception as e:
        print_error(f"Exception: {str(e)}")
        return False

def main():
    print(f"{Colors.BLUE}{'='*60}")
    print("AUTHENTICATION ROUTES TEST SUITE")
    print("="*60 + Colors.RESET)
    print(f"Base URL: {BASE_URL}")
    print(f"Test User Email: {TEST_USER['email']}")
    
    # Test flow
    register_response = test_register()
    if not register_response:
        print_error("Registration failed. Stopping tests.")
        return
    
    # Get token from registration
    register_token = register_response.get("access_token")
    register_user = register_response.get("user")
    
    # Test login with new credentials
    login_response = test_login()
    if not login_response:
        print_error("Login failed. Skipping remaining tests.")
        return
    
    login_token = login_response.get("access_token")
    login_user = login_response.get("user")
    
    # Test get current user
    user_info = test_get_current_user(login_token)
    
    # Test refresh token
    refresh_response = test_refresh_token(login_token)
    if refresh_response:
        new_token = refresh_response.get("access_token")
    else:
        new_token = login_token
    
    # Test logout
    logout_response = test_logout(new_token)
    
    # Test protected route after logout (optional - depends on implementation)
    # test_protected_route_after_logout(new_token)
    
    # Test invalid login
    test_invalid_login()
    
    # Summary
    print(f"\n{Colors.BLUE}{'='*60}")
    print("TEST SUITE COMPLETED")
    print('='*60 + Colors.RESET)
    print(f"\nRegister Response User: {json.dumps(register_user, indent=2, default=str)}")
    print(f"\nLogin Response User: {json.dumps(login_user, indent=2, default=str)}")

if __name__ == "__main__":
    main()
