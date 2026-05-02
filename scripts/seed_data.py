import requests
import time
import random
import uuid

API_BASE = "http://localhost:8000"

COMPONENTS = ["auth-service", "payment-gateway", "user-db", "redis-cache", "image-processor"]
SEVERITIES = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

def trigger_signal(comp_id):
    payload = {
        "component_id": comp_id,
        "payload": {
            "error_rate": random.uniform(0.1, 0.9),
            "latency": random.randint(100, 2000),
            "status": "unhealthy",
            "trace_id": str(uuid.uuid4())
        }
    }
    try:
        resp = requests.post(f"{API_BASE}/signals", json=payload)
        if resp.status_code == 202:
            print(f"Signal sent for {comp_id}")
        else:
            print(f"Failed to send signal: {resp.status_code} - {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

def seed():
    print("Seeding Incident Hub with sample data...")
    
    # 1. Trigger multiple signals to create incidents
    for _ in range(10):
        comp = random.choice(COMPONENTS)
        trigger_signal(comp)
        # Small sleep to allow worker to process
        time.sleep(0.5)

    print("\nWaiting for worker to process signals...")
    time.sleep(2)

    # 2. Get dashboard to see what was created
    resp = requests.get(f"{API_BASE}/dashboard")
    if resp.status_code == 200:
        data = resp.json()
        incidents = data.get("incidents", [])
        print(f"\nCreated {len(incidents)} active incidents.")
        
        # 3. Randomly advance some incidents
        for inc in incidents[:3]:
            wid = inc["workitem_id"]
            print(f"\nAdvancing {wid} to INVESTIGATING...")
            requests.patch(f"{API_BASE}/workitems/{wid}/transition", json={"target_state": "INVESTIGATING"})
            
    print("\nSeeding complete!")

if __name__ == "__main__":
    seed()
