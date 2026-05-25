import requests

BASE_URL = "http://localhost:8000"
TEST_USER = "e2e_user"
TEST_PASS = "e2epassword"
TOKEN = "sk-_aEvH9G3i7KvWvqCG5laTA"

print("--- Testing Backend End-to-End ---")

# 1. Register
print("1. Registering user...")
resp = requests.post(f"{BASE_URL}/auth/register", json={"email": f"{TEST_USER}@example.com", "username": TEST_USER, "password": TEST_PASS})
if resp.status_code in [200, 201]:
    print("   Success")
elif resp.status_code == 400 and "already registered" in resp.text:
    print("   User already exists, proceeding...")
else:
    print(f"   Failed: {resp.status_code} {resp.text}")

# 2. Login
print("\n2. Logging in...")
resp = requests.post(f"{BASE_URL}/auth/login", json={"email": f"{TEST_USER}@example.com", "password": TEST_PASS})
if resp.status_code == 200:
    print("   Success")
    access_token = resp.json()["access_token"]
else:
    print(f"   Failed: {resp.status_code} {resp.text}")
    exit(1)

# 3. Recommend (Ingredients mode)
print("\n3. Testing /recommend (ingredients mode) with LLM...")
headers = {"Authorization": f"Bearer {access_token}"}
payload = {
    "mode": "ingredients",
    "ingredients": ["chicken", "rice"],
    "navigator_token": TOKEN
}
resp = requests.post(f"{BASE_URL}/recommend", json=payload, headers=headers)
if resp.status_code == 200:
    data = resp.json()
    recipes = data.get("recipes", [])
    print(f"   Success! Received {len(recipes)} recipes.")
    for r in recipes[:2]:
        print(f"     - {r.get('title')}: {r.get('match_explanation') or r.get('match_reason')}")
else:
    print(f"   Failed: {resp.status_code} {resp.text}")

print("\n--- Backend Test Completed ---")
