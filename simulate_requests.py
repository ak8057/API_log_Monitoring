import requests
import time
import random

URL = "http://127.0.0.1:8000/submit"

def send_request():
    data = {
        "name": random.choice(["Alice", "Bob", "Charlie", "David"]),
        "value": random.randint(20, 50)
    }
    response = requests.post(URL, json=data)
    print(f"Sent: {data}, Response: {response.json()}")

while True:
    send_request()
    time.sleep(random.uniform(0.5, 1))  # Wait 0.5 to 3 seconds before next request
