from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

res = client.get("/api/health")
print("Health check status:", res.status_code, res.json())

# Test demo sheet data
demo_res = client.get("/api/v1/sheets/demo")
print("Demo sheet status:", demo_res.status_code, f"Rows: {demo_res.json().get('total_rows')}")

# Test projects list
proj_res = client.get("/api/v1/projects")
print("Projects list status:", proj_res.status_code, f"Count: {len(proj_res.json())}")
