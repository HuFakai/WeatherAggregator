import requests
import time
import sys

BASE_URL = "http://127.0.0.1:18050"
ADMIN_KEY = "sk-snkjcx970506"  # Updated from .env
TEST_CLIENT_KEY_NAME = "Test_Verification_Key"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def test_admin_login():
    log("Testing Admin Login...")
    url = f"{BASE_URL}/api/v1/admin/login"
    resp = requests.post(url, json={"key": ADMIN_KEY})
    if resp.status_code == 200:
        log("Admin Login Success", "PASS")
        return True
    else:
        log(f"Admin Login Failed: {resp.text}", "FAIL")
        return False

def test_create_client_key():
    log("Testing Create Client Key...")
    url = f"{BASE_URL}/api/v1/admin/keys"
    headers = {"X-Admin-Key": ADMIN_KEY}
    resp = requests.post(url, json={"name": TEST_CLIENT_KEY_NAME}, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        log(f"Created Key: {data['key']}", "PASS")
        return data['key']
    else:
        log(f"Create Key Failed: {resp.text}", "FAIL")
        return None

def test_weather_api(api_key):
    log("Testing Weather API...")
    url = f"{BASE_URL}/api/v1/weather"
    params = {"city": "北京", "key": api_key}
    resp = requests.get(url, params=params)
    if resp.status_code == 200:
        data = resp.json()
        if "sources" in data:
            log("Weather API Success", "PASS")
            return True
    log(f"Weather API Failed: {resp.status_code} - {resp.text}", "FAIL")
    return False

def test_rate_limiting(api_key):
    log("Testing Rate Limiting (QPM)...")
    # 1. Set Limit to 5 QPM
    update_url = f"{BASE_URL}/api/v1/admin/keys/{api_key}"
    headers = {"X-Admin-Key": ADMIN_KEY}
    requests.put(update_url, json={"qpm_limit": 5}, headers=headers)
    
    # 2. Fire 6 requests
    success_count = 0
    blocked_count = 0
    
    url = f"{BASE_URL}/api/v1/weather"
    params = {"city": "上海", "key": api_key}
    
    for i in range(7):
        resp = requests.get(url, params=params)
        if resp.status_code == 200:
            success_count += 1
        elif resp.status_code == 429:
            blocked_count += 1
            
    if success_count <= 5 and blocked_count >= 1:
        log(f"Rate Limiting Working (Success: {success_count}, Blocked: {blocked_count})", "PASS")
        return True
    else:
        log(f"Rate Limiting Failed (Success: {success_count}, Blocked: {blocked_count})", "FAIL")
        return False

def test_ip_whitelist(api_key):
    log("Testing IP Whitelist...")
    # 1. Enable Whitelist but add a dummy IP, and RESET QPM limit
    update_url = f"{BASE_URL}/api/v1/admin/keys/{api_key}"
    headers = {"X-Admin-Key": ADMIN_KEY}
    requests.put(update_url, json={
        "ip_whitelist_enabled": True,
        "ip_whitelist": ["1.1.1.1"],
        "qpm_limit": 0  # Reset limit to avoid 429 from previous test
    }, headers=headers)
    
    # 2. Request should fail
    url = f"{BASE_URL}/api/v1/weather"
    params = {"city": "广州", "key": api_key}
    resp = requests.get(url, params=params)
    
    if resp.status_code == 403:
        log("IP Whitelist Blocking Working", "PASS")
    else:
        log(f"IP Whitelist Blocking Failed: {resp.status_code}", "FAIL")
        return False
        
    # 3. Add localhost to whitelist
    requests.put(update_url, json={
        "ip_whitelist": ["127.0.0.1", "::1"]
    }, headers=headers)
    
    # 4. Request should succeed
    resp = requests.get(url, params=params)
    if resp.status_code == 200:
        log("IP Whitelist Allowing Working", "PASS")
        return True
    else:
        log(f"IP Whitelist Allowing Failed: {resp.status_code}", "FAIL")
        return False

def cleanup(api_key):
    log("Cleaning up...")
    url = f"{BASE_URL}/api/v1/admin/keys/{api_key}"
    headers = {"X-Admin-Key": ADMIN_KEY}
    requests.delete(url, headers=headers)
    log("Cleanup Done", "INFO")

def main():
    if not test_admin_login():
        sys.exit(1)
        
    api_key = test_create_client_key()
    if not api_key:
        sys.exit(1)
        
    try:
        if not test_weather_api(api_key):
            sys.exit(1)
            
        if not test_rate_limiting(api_key):
            sys.exit(1)
            
        if not test_ip_whitelist(api_key):
            sys.exit(1)
            
        log("ALL TESTS PASSED", "SUCCESS")
        
    finally:
        cleanup(api_key)

if __name__ == "__main__":
    main()
