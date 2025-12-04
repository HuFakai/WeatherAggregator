import requests
import sys
import time
import random

BASE_URL = "http://127.0.0.1:8000"
ADMIN_API = f"{BASE_URL}/api/v1/admin"
WEATHER_API = f"{BASE_URL}/api/v1/weather"

def print_step(msg):
    print(f"\n{'='*10} {msg} {'='*10}")

def test_admin_api():
    print_step("Testing Admin API")
    
    # 1. List Channels
    print("1. Listing Channels...")
    try:
        res = requests.get(f"{ADMIN_API}/channels")
        if res.status_code == 200:
            channels = res.json()
            print(f"✅ Success: Found {len(channels)} channels")
            for c in channels:
                print(f"   - {c['name']} (Cron: {c.get('cron')})")
        else:
            print(f"❌ Failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
        return

    # 2. Add Key
    print("\n2. Adding Test Key...")
    test_key = f"test_key_{int(time.time())}"
    try:
        res = requests.post(f"{ADMIN_API}/channels/yiketianqi/keys", json={
            "key": test_key,
            "daily_limit": 100,
            "desc": "Automated Test Key"
        })
        if res.status_code == 200:
            print(f"✅ Success: Key {test_key} added")
        else:
            print(f"❌ Failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

    # 3. Remove Key
    print("\n3. Removing Test Key...")
    try:
        # Encode key just in case
        res = requests.delete(f"{ADMIN_API}/channels/yiketianqi/keys/{test_key}")
        if res.status_code == 200:
            print(f"✅ Success: Key {test_key} removed")
        else:
            print(f"❌ Failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_weather_api():
    print_step("Testing Weather API")
    
    # city_id = "820006" # Chaoyang
    city_id = "罗庄" # Chaoyang
    
    print(f"Querying weather for {city_id}...")
    try:
        res = requests.get(f"{WEATHER_API}/{city_id}")
        if res.status_code == 200:
            data = res.json()
            print(f"✅ Success: {data.get('city')}")
            
            sources = data.get("data", {}).get("sources", {})
            if sources:
                print(f"✅ Data Sources: {list(sources.keys())}")
            else:
                print("⚠️ No weather data sources found (Task might not have run yet)")
        else:
            print(f"❌ Failed: {res.status_code} - {res.text}")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_admin_page():
    print_step("Testing Admin Page")
    
    url = f"{BASE_URL}/admin"
    try:
        res = requests.get(url)
        if res.status_code == 200:
            if "Weather Aggregator Admin" in res.text:
                print("✅ Success: Admin page loaded")
            else:
                print("❌ Failed: Title not found in HTML")
        else:
            print(f"❌ Failed: {res.status_code}")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    print("⚠️ Make sure the server is running on http://127.0.0.1:8000")
    print("⚠️ Run: uvicorn app.main:app --reload --port 8000")
    
    # Simple check if server is up
    try:
        requests.get(BASE_URL, timeout=1)
    except:
        print("❌ Server not reachable. Please start the server first!")
        sys.exit(1)
        
    test_admin_api()
    test_weather_api()
    test_admin_page()
    print("\n✅ All tests completed.")
