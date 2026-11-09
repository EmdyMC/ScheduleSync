import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_tests():
    # 1. Test Root Page
    r_root = client.get("/")
    assert r_root.status_code == 200, f"Root status {r_root.status_code}"
    print("PASS: Root / renders 200 OK")

    # 2. Test Login
    r_login = client.post("/api/auth/login", json={"username_or_email": "michael", "password": "password123"})
    assert r_login.status_code == 200, f"Login status {r_login.status_code}: {r_login.text}"
    token = r_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("PASS: Auth /api/auth/login returns token for Michael")

    # 3. Test Timetable Slots Retrieval
    r_slots = client.get("/api/timetable/my-slots", headers=headers)
    assert r_slots.status_code == 200, f"Slots error: {r_slots.text}"
    slots_data = r_slots.json()
    assert len(slots_data["matrix"]) == 5 and len(slots_data["matrix"][0]) == 11
    print("PASS: Timetable slots retrieved with 5x11 matrix")

    # 4. Test Heatmap for Group 1
    r_heat = client.get("/api/groups/1/heatmap", headers=headers)
    assert r_heat.status_code == 200, f"Heatmap error: {r_heat.text}"
    data = r_heat.json()
    assert len(data["grid"]) == 5 and len(data["grid"][0]) == 11
    print(f"PASS: Heatmap 5x11 grid computed for {data['total_users']} members with {len(data['best_slots'])} free slots")

    # 5. Test Friends Listing
    r_friends = client.get("/api/friends", headers=headers)
    assert r_friends.status_code == 200, f"Friends error: {r_friends.text}"
    print(f"PASS: Friends API returned {len(r_friends.json()['friends'])} friends")

    # 6. Test Groups Listing
    r_groups = client.get("/api/groups", headers=headers)
    assert r_groups.status_code == 200, f"Groups error: {r_groups.text}"
    print(f"PASS: Groups API returned {len(r_groups.json()['groups'])} groups")

    # 7. Test Public Share Link
    r_share = client.get("/api/share/demo-team04")
    assert r_share.status_code == 200, f"Share error: {r_share.text}"
    print("PASS: Public share link /api/share/demo-team04 works!")

    print("\nALL BACKEND & API TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()
