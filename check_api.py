import requests
import json
import time

BASE_URL = "http://127.0.0.1:8082"
HANDLE = "tourist"

def test_routes():
    print(f"Testing /openapi.json...")
    try:
        res = requests.get(f"{BASE_URL}/openapi.json")
        if res.status_code == 200:
            data = res.json()
            paths = list(data.get("paths", {}).keys())
            print(f"REGISTERED ROUTES: {paths}")
        else:
            print(f"FAILURE: /openapi.json returned {res.status_code}")
    except Exception as e:
         print(f"FAILURE: {e}")

def test_daily_count():
    # Use standard /user path
    print(f"\nTesting /user/{HANDLE}...")
    try:
        res = requests.get(f"{BASE_URL}/user/{HANDLE}")
        if res.status_code == 200:
            data = res.json()
            if "daily_solved_count" in data:
                print(f"SUCCESS: daily_solved_count found: {data['daily_solved_count']}")
            else:
                print("FAILURE: daily_solved_count NOT found in response keys:", data.keys())
        else:
            print(f"FAILURE: Status code {res.status_code}")
    except Exception as e:
        print(f"FAILURE: Connection error: {e}")

def test_refresh():
    print(f"\nTesting /analysis/weaknesses refresh...")
    try:
        # First call
        res1 = requests.get(f"{BASE_URL}/analysis/weaknesses", params={"handle": HANDLE, "refresh": "true"})
        if res1.status_code != 200:
             print(f"FAILURE: Call 1 Status {res1.status_code}")
             print(f"Response: {res1.text[:200]}")
             return

        data1 = res1.json()
        ids1 = [p["problem_id"] for p in data1.get("upsolve_suggestions", [])]
        
        # Second call
        res2 = requests.get(f"{BASE_URL}/analysis/weaknesses", params={"handle": HANDLE, "refresh": "true"})
        data2 = res2.json()
        ids2 = [p["problem_id"] for p in data2.get("upsolve_suggestions", [])]
        
        print(f"Call 1 IDs: {ids1[:3]}...")
        print(f"Call 2 IDs: {ids2[:3]}...")
        
        if ids1 != ids2:
             print("SUCCESS: Suggestions changed (Refresh workings)")
        else:
             print("WARNING: Suggestions same (Might be coincidental or shuffle broken)")

    except Exception as e:
        print(f"FAILURE: Connection error: {e}")

if __name__ == "__main__":
    time.sleep(1)
    test_routes()
    test_daily_count()
    test_refresh()
