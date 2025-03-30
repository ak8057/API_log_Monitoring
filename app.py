from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import json
import logging
import random
import time
from datetime import datetime
from fastapi.responses import JSONResponse
import httpx

app = FastAPI()

# ✅ Enable CORS for frontend (localhost:5173)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Configure JSON-based logging
log_file = "api_logs.json"
class JsonFileHandler(logging.FileHandler):
    def emit(self, record):
        log_entry = self.format(record)
        with open(log_file, "a") as f:
            f.write(log_entry + "\n")

logger = logging.getLogger("api_logger")
logger.setLevel(logging.INFO)
file_handler = JsonFileHandler(log_file)
formatter = logging.Formatter('%(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

# Define possible API behaviors
status_codes = [200, 201, 400, 403, 404, 500, 503]
methods = ["GET", "POST", "PUT", "DELETE"]
endpoints = ["/submit", "/update", "/delete", "/fetch", "/authenticate"]
error_messages = {
    400: "Bad Request: Invalid input",
    403: "Forbidden: Access denied",
    404: "Not Found: Resource missing",
    500: "Internal Server Error",
    503: "Service Unavailable: Try later",
}

# Function to log API request & response
async def log_request_response(request: Request, response_data, status_code, response_time):
    request_info = {
        "timestamp": str(datetime.utcnow()),
        "method": request.method,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client_ip": request.client.host,
        "request_body": await request.json() if request.method in ["POST", "PUT"] else None,
        "response_body": response_data,
        "status_code": status_code,
        "response_time_ms": response_time
    }
    logger.info(json.dumps(request_info))

# ✅ Dynamic API Endpoint
@app.post("/submit")
async def submit_data(request: Request):
    """Handles API requests with dynamic behavior."""
    
    start_time = datetime.utcnow()

    # Simulate response delay (50ms - 2s)
    response_time = round(random.uniform(50, 2000), 2)
    time.sleep(response_time / 1000)

    # Randomly choose a status code
    status_code = random.choice(status_codes)

    try:
        data = await request.json()
    except Exception:
        data = None

    response_data = {"status": "Received", "data": data} if status_code < 400 else {
        "error": error_messages.get(status_code, "Unknown Error")
    }

    # Log API request
    await log_request_response(request, response_data, status_code, response_time)

    return JSONResponse(content=response_data, status_code=status_code)

# ✅ API to Fetch Logs for Dashboard
@app.get("/logs")
async def get_logs():
    try:
        with open(log_file, "r") as file:
            logs = [json.loads(line.strip()) for line in file.readlines()]
        return JSONResponse(content=logs)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ✅ Simulated Traffic Generator (Run Separately for Continuous Requests)
@app.get("/simulate")
async def simulate_requests():
    """Simulates API requests dynamically for testing."""
    simulated_logs = []

    async with httpx.AsyncClient() as client:
        for _ in range(5):  # Reduce to 5 requests per call
            method = random.choice(methods)
            endpoint = random.choice(endpoints)
            url = f"http://127.0.0.1:8000{endpoint}"
            headers = {"User-Agent": "TestClient", "Accept": "application/json"}
            payload = {"test_key": "test_value"} if method in ["POST", "PUT"] else None

            try:
                if method == "GET":
                    response = await client.get(url, headers=headers)
                elif method == "POST":
                    response = await client.post(url, json=payload, headers=headers)
                elif method == "PUT":
                    response = await client.put(url, json=payload, headers=headers)
                else:
                    response = await client.delete(url, headers=headers)

                log_entry = {
                    "timestamp": str(datetime.utcnow()),
                    "method": method,
                    "url": url,
                    "status_code": response.status_code,
                }
                simulated_logs.append(log_entry)

            except Exception as e:
                simulated_logs.append({"error": str(e)})

    return {"message": "Simulation Completed", "logs": simulated_logs}