"""
sensor_uploader.py

Reads sensor readings from Arduino (via Serial port) and sends them
to the backend /realtime-reading endpoint.

Run:
  python sensor_uploader.py
"""

import serial
import time
import requests
import math
import urllib3
from datetime import datetime, timezone

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ─── CONFIG ──────────────────────────────────────────────────

PORT      = "COM11"
BAUD_RATE = 9600
BACKEND   = "http://127.0.0.1:8000"
INTERVAL  = 5

DEVICE_HEATER    = 45
DEVICE_SOLAR     = 46
DEVICE_LIGHTBULB = 47
DEVICE_FAN       = 48


# ─── SCALING ─────────────────────────────────────────────────
# Arduino readings are small lab values.
# We scale them to represent real household appliances.
#
# How scaling is calculated:
#   LED:    actual ~0.5W  → target 12W    → ×23
#   Motor:  actual ~3.4W  → target 75W    → ×22
#   Heater: actual ~3W    → target 1500W  → ×500
#
# Formula: watts_scaled = (current_A × voltage_V) × scaling_factor

SCALING = {
    "led":    23,   # ~0.5W × 23  = ~12W   (LED bulb)
    "motor":  22,   # ~3.4W × 22  = ~75W   (ceiling fan)
    "heater": 500,  # ~3.0W × 500 = ~1500W (water heater)
}

DEVICE_MAP = {
    "led":    DEVICE_LIGHTBULB,
    "motor":  DEVICE_FAN,
    "heater": DEVICE_HEATER,
}


def fake_solar_watts() -> float:
    now  = datetime.now()
    hour = now.hour + now.minute / 60.0
    if hour < 6 or hour > 18:
        return 0.0
    return 2500.0 * math.exp(-((hour - 12) ** 2) / 8.0)


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
    print(f"Connecting to Arduino on {PORT}...")
    arduino = serial.Serial(PORT, BAUD_RATE, timeout=5)
    time.sleep(2)
    arduino.flushInput()

    print(f"Connected. Sending to {BACKEND}/realtime-reading every {INTERVAL}s")
    print(f"Scaling: LED x{SCALING['led']}, Motor x{SCALING['motor']}, Heater x{SCALING['heater']}")
    print("Press Ctrl+C to stop\n")

    last_send  = time.time()
    accum      = {"led": [], "motor": [], "heater": []}
    last_voltage = 220.0

    try:
        while True:
            line = arduino.readline().decode("utf-8", errors="ignore").strip()
            if "," not in line:
                continue
            values = line.split(",")
            if len(values) != 4:
                continue
            try:
                voltage = float(values[0])
                i_led   = float(values[1])
                i_mot   = float(values[2])
                i_htr   = float(values[3])
            except ValueError:
                continue

            last_voltage = voltage if voltage > 0 else 220.0
            accum["led"].append(i_led)
            accum["motor"].append(i_mot)
            accum["heater"].append(i_htr)

            now     = time.time()
            elapsed = now - last_send

            if elapsed >= INTERVAL:
                avg   = {k: (sum(v) / len(v) if v else 0.0) for k, v in accum.items()}
                # Calculate actual watts from Arduino (V × A)
                actual_watts = {k: avg[k] * last_voltage for k in avg}
                # Apply scaling to simulate real household appliances
                watts = {k: actual_watts[k] * SCALING[k] for k in actual_watts}

                ts = datetime.now().strftime("%H:%M:%S")
                print(f"[{ts}] V={last_voltage:.1f}V")

                for key, device_id in DEVICE_MAP.items():
                    label  = key.upper().ljust(7)
                    w      = watts[key]
                    status = "ON " if w > 1.0 else "OFF"
                    print(f"   {label} {status}  {w:7.1f}W")
                    send_reading(device_id, w)

                solar_w = fake_solar_watts()
                print(f"   SOLAR   {'ON ' if solar_w > 0 else 'OFF'}  {solar_w:7.1f}W")
                send_reading(DEVICE_SOLAR, solar_w)

                print()
                accum     = {"led": [], "motor": [], "heater": []}
                last_send = now

    except KeyboardInterrupt:
        print("\nStopped.")
        arduino.close()


if __name__ == "__main__":
    main()