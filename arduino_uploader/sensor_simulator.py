"""
sensor_simulator.py

Simulates Arduino sensor readings WITHOUT needing the real hardware.
Sends readings to the backend /realtime-reading endpoint.

Run:
  python sensor_simulator.py
"""

import time
import requests
import random
import math
import urllib3
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── CONFIG ──────────────────────────────────────────────────

BACKEND  = "http://127.0.0.1:8000"
INTERVAL = 5  # seconds between updates

DEVICE_HEATER    = 45
DEVICE_SOLAR     = 46
DEVICE_LIGHTBULB = 47
DEVICE_FAN       = 48

WATTAGE = {
    "lightbulb": 12,    # ~12W LED bulb
    "fan":       75,    # ~75W ceiling fan
    "heater":    1500,  # ~1500W water heater
}

# Note: simulator generates realistic watts directly (no scaling needed)
# These values already represent real household appliances

device_state = {
    "lightbulb": True,
    "fan":       True,
    "heater":    False,
}

toggle_chance = {
    "lightbulb": 0.05,
    "fan":       0.03,
    "heater":    0.20,
}


def fake_solar_watts() -> float:
    now  = datetime.now()
    hour = now.hour + now.minute / 60.0
    if hour < 6 or hour > 18:
        return 0.0
    return 2500.0 * math.exp(-((hour - 12) ** 2) / 8.0)


def maybe_toggle(device: str):
    if random.random() < toggle_chance[device]:
        device_state[device] = not device_state[device]


def get_current_watts(device: str) -> float:
    if not device_state[device]:
        return 0.0
    base  = WATTAGE[device]
    noise = random.uniform(-0.1, 0.1) * base
    return max(0.0, base + noise)


def send_reading(device_id: int, watts: float) -> bool:
    try:
        payload = {
            "device_id":    device_id,
            "watts":        round(watts, 2),
            "reading_time": datetime.now(timezone.utc).isoformat(),
        }
        response = requests.post(
            f"{BACKEND}/realtime-reading",
            json=payload,
            timeout=5,
            verify=False,
        )
        if response.status_code == 200:
            return True
        print(f"   Backend error {response.status_code}: {response.text[:80]}")
        return False
    except Exception as e:
        print(f"   Failed to send: {e}")
        return False


def main():
    print("SIMULATOR MODE - no hardware required")
    print(f"Sending to {BACKEND}/realtime-reading every {INTERVAL}s")
    print("Press Ctrl+C to stop\n")

    try:
        while True:
            for d in device_state:
                maybe_toggle(d)

            w_light  = get_current_watts("lightbulb")
            w_fan    = get_current_watts("fan")
            w_heater = get_current_watts("heater")
            w_solar  = fake_solar_watts()

            ts = datetime.now().strftime("%H:%M:%S")
            print(f"[{ts}]")

            for label, watts, dev_id in [
                ("LIGHTBULB", w_light,  DEVICE_LIGHTBULB),
                ("FAN      ", w_fan,    DEVICE_FAN),
                ("HEATER   ", w_heater, DEVICE_HEATER),
                ("SOLAR    ", w_solar,  DEVICE_SOLAR),
            ]:
                is_on  = watts > 0
                status = "ON " if is_on else "OFF"
                print(f"   {label} {status}  {watts:7.1f}W")
                send_reading(dev_id, watts)

            print()
            time.sleep(INTERVAL)

    except KeyboardInterrupt:
        print("\nSimulator stopped.")


if __name__ == "__main__":
    main()