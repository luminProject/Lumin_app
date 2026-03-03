import random
import time
from datetime import datetime, timezone
import requests

BASE_URL = "http://127.0.0.1:8000"
DEVICE_ID = 4  # جهازك الحالي

def post_reading():
    payload = {
        "device_id": DEVICE_ID,
        "kwh_value": round(random.uniform(0.3, 2.5), 3),
        "reading_time": datetime.now(timezone.utc).isoformat(),
    }

    r = requests.post(f"{BASE_URL}/sensor-readings", json=payload)
    print(r.status_code, r.text)

for i in range(10):
    post_reading()
    time.sleep(1)