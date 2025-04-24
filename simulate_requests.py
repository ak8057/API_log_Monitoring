import requests
import time
import random

base_url = "http://127.0.0.1:8000"
endpoints = ["/submit", "/update", "/delete", "/fetch", "/authenticate"]
methods = ["GET", "POST", "PUT", "DELETE"]

def send_request():
    endpoint = random.choice(endpoints)
    method = random.choice(methods)
    url = f"{base_url}{endpoint}"

    data = {
        "name": random.choice(["Alice", "Bob", "Charlie", "David"]),
        "value": random.randint(20, 50)
    }

    try:
        if method == "GET" or method == "DELETE":
            response = requests.request(method, url)
        else:
            response = requests.request(method, url, json=data)
        
        print(f"{method} {url} | Sent: {data if method in ['POST', 'PUT'] else ''} | Status: {response.status_code}")
    except Exception as e:
        print(f"Error calling {method} {url}: {e}")

while True:
    send_request()
    time.sleep(random.uniform(0.5, 2))
