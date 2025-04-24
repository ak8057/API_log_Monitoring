from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from dotenv import load_dotenv
import json
import logging
import random
import time
from datetime import datetime
import os

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

log_file = "/Users/abhaykumar/codeit/projects/Machine_Learning/API_LOG/dock/logs/api_logs.json"

# Ensure log file exists
if not os.path.exists(log_file):
    with open(log_file, "w") as f:
        pass  # Create empty file

# Variables
status_codes = [200, 201, 400, 403, 404, 500, 503]
error_messages = {
    400: "Bad Request: Invalid input",
    403: "Forbidden: Access denied",
    404: "Not Found: Resource missing",
    500: "Internal Server Error",
    503: "Service Unavailable: Try later",
}

# Logging function (NDJSON)
async def log_request_response(request: Request, response_data, status_code, response_time):
    try:
        body = await request.json() if request.method in ["POST", "PUT"] else None
    except:
        body = None

    log_entry = {
        "timestamp": str(datetime.utcnow()),
        "method": request.method,
        "endpoint": request.url.path,
        "url": str(request.url),
        "headers": dict(request.headers),
        "client_ip": request.client.host,
        "request_body": body,
        "response_body": response_data,
        "status_code": status_code,
        "response_time_ms": response_time
    }

    # Write log as a single NDJSON line
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

# Dynamic behavior handler
async def handle_request(request: Request):
    start_time = datetime.utcnow()
    delay = round(random.uniform(50, 2000), 2)
    time.sleep(delay / 1000)

    try:
        body = await request.json()
    except:
        body = None

    # status_code = random.choice(status_codes)  //more anomalies

    roll = random.uniform(0, 1)
    if roll < 0.85:
        # 85% chance of 2xx success
        status_code = random.choice([200, 201, 202])
    elif roll < 0.95:
        # 10% chance of 4xx client errors
        status_code = random.choice([400, 401, 403, 404])
    else:
        # 5% chance of 5xx server errors
        status_code = random.choice([500, 502, 503])


    if status_code < 400:
        response_data = {"status": "success", "data": body}
    else:
        response_data = {"error": error_messages.get(status_code, "Unknown Error")}

    await log_request_response(request, response_data, status_code, delay)
    return JSONResponse(content=response_data, status_code=status_code)

# Register routes
endpoints = ["/submit", "/update", "/delete", "/fetch", "/authenticate"]
methods = ["GET", "POST", "PUT", "DELETE"]

for path in endpoints:
    for method in methods:
        app.add_api_route(
            path,
            handle_request,
            methods=[method],
            name=f"{method}_{path.strip('/')}"
        )

# Logs viewer
@app.get("/logs")
async def get_logs():
    try:
        with open(log_file, "r") as f:
            logs = [json.loads(line) for line in f if line.strip()]
        return JSONResponse(content=logs)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
