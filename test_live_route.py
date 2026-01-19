"""Test script to verify /live route works."""
from app import app

with app.test_client() as client:
    print("Testing /live route...")
    response = client.get('/live')
    print(f"Status code: {response.status_code}")
    print(f"Response length: {len(response.data)} bytes")
    if response.status_code == 200:
        print("Route works! Status: 200 OK")
        print(f"First 200 chars: {response.data[:200]}")
    else:
        print(f"Route failed: {response.data.decode()}")
