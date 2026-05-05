# 📡 Lumin Sensors

This folder contains two Python scripts that feed live sensor data into the Lumin backend.

- **`sensor_simulator.py`** — Use this if you do NOT have the Arduino hardware.
- **`sensor_uploader.py`** — Use this when the Arduino prototype is connected.

Both scripts send data to the same backend endpoint (`POST /realtime-reading`) every 5 seconds.

---

## ⚙️ Requirements

Make sure Python 3.10+ is installed, then run:

```bash
pip install requests pyserial
```

---

## 🚀 How to Run

### Option 1 — No Hardware (Simulator)

Generates realistic fake readings without needing the Arduino.

```bash
python sensor_simulator.py
```

What it simulates:
| Device | Watts |
|--------|-------|
| Lightbulb | ~12 W |
| Fan | ~75 W |
| Heater | ~1500 W |
| Solar Panel | Bell curve 0–2500 W based on time of day |

---

### Option 2 — With Arduino

Reads real current values from the Arduino via USB and scales them to represent real household appliances.

**Step 1** — Connect the Arduino to your laptop via USB.

**Step 2** — Find your COM port:
- Open Arduino IDE → Tools → Port
- It will say something like `COM3`, `COM7`, `COM11`

**Step 3** — Open `sensor_uploader.py` and update the PORT at the top:

```python
PORT = "COM11"   ← change this to your port
```

**Step 4** — Run:

```bash
python sensor_uploader.py
```

---

## 🔢 Scaling (Arduino only)

The Arduino sensors produce small values (lab scale). The uploader multiplies them to simulate real household appliances:

| Arduino Device | Scaling Factor | Simulates |
|----------------|----------------|-----------|
| LED | × 23 | LED Light Bulb (~12 W) |
| Motor | × 22 | Ceiling Fan (~75 W) |
| Heater | × 500 | Water Heater (~1500 W) |

Formula:
```
scaled_watts = (current_A × voltage_V) × scaling_factor
```

---

## ☀️ Solar Panel

There is no physical solar sensor on the Arduino. Both scripts simulate solar production using a realistic bell curve based on the current time:

```
Peak: ~2500 W at 12:00 noon
Zero: before 06:00 AM and after 06:00 PM
```

---

## ✅ How to Verify It's Working

1. Make sure the backend is running:
   ```bash
   cd ../lumin_backend
   uvicorn app.main:app --reload
   ```

2. Run either script in a second terminal.

3. You should see output like:
   ```
   [14:30:22]
      LIGHTBULB  ON     12.3 W
      FAN        ON     74.5 W
      HEATER     OFF     0.0 W
      SOLAR      ON   2475.3 W
   ```

4. Open the Lumin app — the Home page values should update every 5 seconds.

---

## 📁 Files

| File | Purpose |
|------|---------|
| `sensor_simulator.py` | Simulates all devices without hardware |
| `sensor_uploader.py` | Reads from real Arduino via USB serial |
| `README.md` | This file |

---

## ⚠️ Notes

- Both scripts require the **backend to be running** before you start them.
- The backend URL is `http://127.0.0.1:8000` by default. If your backend runs on a different port, update the `BACKEND` variable at the top of each script.
- Solar production shows `0 W` at night — this is expected and realistic.
