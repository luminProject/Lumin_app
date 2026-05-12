"""
rec_demo_tool.py — Recommendations Demo Tool
=============================================
Simulates solar panel data and generates a real recommendation from the system.

Commands:
  seed_solar      -> Injects sensor_data readings for the past 7 days (solar peak at midday)
  seed_device     -> Adds a shiftable consumption device for the user
  generate        -> Generates a real solar recommendation via the API
  generate_twice  -> Proves the daily limit works (blocks duplicate recommendations)
  show_result     -> Shows the latest recommendation + notification from the database
  clean           -> Clears all test data
  demo            -> Runs all steps in order with explanations (for committee presentation)
"""

import os
import sys
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone, date
from dotenv import load_dotenv
import supabase as supabase_

load_dotenv()
db = supabase_.create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

# ===============================================
#  <- Set these values before running
# ===============================================
USER_ID       = "03216c06-e206-4413-a62a-b4fe49787a29"
USER_EMAIL       = "fcm@gmail.com"     # <- paste the user email here
USER_PASSWORD    = "qwerty2@"  # <- paste the user password here
BASE_URL         = "http://127.0.0.1:8000"
DEMO_DEVICE_NAME = "Washing Machine"


# ===============================================
#  HELPERS
# ===============================================

def _get_jwt_token() -> str:
    """Sign in to Supabase and return a JWT token for API requests."""
    try:
        response = db.auth.sign_in_with_password({
            "email":    USER_EMAIL,
            "password": USER_PASSWORD,
        })
        return response.session.access_token
    except Exception as e:
        print(f"ERROR: Could not sign in to get JWT token: {e}")
        print("       Check USER_EMAIL and USER_PASSWORD at the top of the file.")
        sys.exit(1)

JWT_TOKEN = None

def _ensure_token():
    global JWT_TOKEN
    if JWT_TOKEN is None:
        JWT_TOKEN = _get_jwt_token()


def _check_backend():
    try:
        with urllib.request.urlopen(f"{BASE_URL}/", timeout=3) as r:
            if r.status != 200:
                raise Exception()
    except Exception:
        print("ERROR: Backend is not running.")
        print("       Start it with: uvicorn app.main:app --reload")
        sys.exit(1)


def _post(path: str) -> dict:
    _ensure_token()
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, method="POST", data=b"")
    req.add_header("Authorization", f"Bearer {JWT_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}
    except Exception as e:
        print(f"ERROR: Request failed: {e}")
        sys.exit(1)


def _get(path: str) -> dict:
    _ensure_token()
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url)
    req.add_header("Authorization", f"Bearer {JWT_TOKEN}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"error": e.code, "detail": e.read().decode()}
    except Exception as e:
        print(f"ERROR: Request failed: {e}")
        sys.exit(1)


def _get_production_device() -> dict | None:
    rows = (
        db.table("device")
        .select("device_id, device_name")
        .eq("user_id", USER_ID)
        .eq("device_type", "production")
        .limit(1)
        .execute()
    ).data
    return rows[0] if rows else None


def _get_shiftable_device() -> dict | None:
    rows = (
        db.table("device")
        .select("device_id, device_name")
        .eq("user_id", USER_ID)
        .eq("device_type", "consumption")
        .eq("is_shiftable", True)
        .limit(1)
        .execute()
    ).data
    return rows[0] if rows else None


def _print_section(title: str):
    print(f"\n{'='*55}")
    print(f"  {title}")
    print(f"{'='*55}")


def _print_step(step: str):
    print(f"\n{'-'*55}")
    print(f"  {step}")
    print(f"{'-'*55}")


def _count_today_recs() -> int:
    today = date.today().isoformat()
    rows = (
        db.table("recommendation")
        .select("recommendation_id")
        .eq("user_id", USER_ID)
        .gte("timestamp", f"{today}T00:00:00+00:00")
        .execute()
    ).data or []
    return len(rows)


# ===============================================
#  COMMANDS
# ===============================================

def cmd_seed_solar():
    """
    Injects sensor_data readings for the past 7 days for the production device.
    Data distribution: peak at midday so the system picks it as the best period.
      - Morning   (8 AM):  8  kWh
      - Midday   (12 PM): 18 kWh  <- highest (system will pick this)
      - Afternoon (3 PM): 12 kWh
    """
    _print_step("Step 1: Injecting solar panel readings (7 days)")

    device = _get_production_device()
    if not device:
        print("ERROR: No production device found for this user.")
        print("       Make sure the user has a device with device_type='production'")
        return

    device_id = device["device_id"]
    print(f"   Device: {device['device_name']} (ID: {device_id})")

    now  = datetime.now(timezone.utc)
    rows = []

    periods = [
        {"hour": 8,  "kwh": 8.0,  "label": "Morning   (8 AM)        "},
        {"hour": 12, "kwh": 18.0, "label": "Midday   (12 PM) <- peak"},
        {"hour": 15, "kwh": 12.0, "label": "Afternoon (3 PM)        "},
    ]

    for day_offset in range(1, 8):
        day = now - timedelta(days=day_offset)
        for p in periods:
            reading_time = day.replace(
                hour=p["hour"], minute=0, second=0, microsecond=0
            )
            rows.append({
                "device_id":    device_id,
                "reading_time": reading_time.isoformat(),
                "kwh_value":    p["kwh"],
            })

    db.table("sensor_data").insert(rows).execute()

    print(f"\n   [OK] Injected {len(rows)} readings (7 days x 3 periods)")
    print(f"\n   Daily production distribution:")
    for p in periods:
        bar = "#" * int(p["kwh"] / 2)
        print(f"   {p['label']}  {p['kwh']:4} kWh  {bar}")
    print(f"\n   The system will detect midday as the peak production period.")


def cmd_seed_device():
    """
    Adds 3 shiftable consumption devices with different midday consumption levels.
    The system compares all of them against the solar peak (18 kWh)
    and picks the closest one — Washing Machine (16.5 kWh).

    Device          Midday avg   Diff from solar peak (18 kWh)
    --------------  ----------   -----------------------------
    Washing Machine   16.5 kWh   1.5  <- closest -> system picks this
    Air Conditioner   12.0 kWh   6.0
    Dishwasher         8.0 kWh  10.0  <- furthest
    """
    _print_step("Step 2: Adding 3 shiftable consumption devices")

    # Define the 3 demo devices
    demo_devices = [
        {"name": "Washing Machine",  "room": "Laundry",  "kwh": 16.5},
        {"name": "Air Conditioner",  "room": "Living Room", "kwh": 12.0},
        {"name": "Dishwasher",       "room": "Kitchen",  "kwh": 8.0},
    ]

    now = datetime.now(timezone.utc)
    added_devices = []

    for dev in demo_devices:
        # Check if device already exists
        existing = (
            db.table("device")
            .select("device_id, device_name")
            .eq("user_id", USER_ID)
            .eq("device_name", dev["name"])
            .eq("is_shiftable", True)
            .limit(1)
            .execute()
        ).data

        if existing:
            device_id = existing[0]["device_id"]
            print(f"   Device already exists: {dev['name']} (ID: {device_id})")
        else:
            res = (
                db.table("device")
                .insert({
                    "user_id":      USER_ID,
                    "device_name":  dev["name"],
                    "device_type":  "consumption",
                    "is_shiftable": True,
                    "room":         dev["room"],
                })
                .execute()
            )
            device_id = res.data[0]["device_id"]
            print(f"   [OK] Added: {dev['name']} (ID: {device_id})")

        added_devices.append({"device_id": device_id, "name": dev["name"], "kwh": dev["kwh"]})

        # Insert 7 days of midday readings for this device
        rows = []
        for day_offset in range(1, 8):
            day          = now - timedelta(days=day_offset)
            reading_time = day.replace(hour=12, minute=30, second=0, microsecond=0)
            rows.append({
                "device_id":    device_id,
                "reading_time": reading_time.isoformat(),
                "kwh_value":    dev["kwh"],
            })
        db.table("sensor_data").insert(rows).execute()

    # Summary table
    solar_peak = 18.0
    print(f"\n   Devices added with 7 days of midday readings:")
    print(f"\n   {'Device':<20} {'Midday avg':>12}   {'Diff from solar peak (18 kWh)':>30}")
    print(f"   {'-'*20}  {'-'*12}   {'-'*30}")
    for d in added_devices:
        diff   = abs(solar_peak - d["kwh"])
        marker = "  <- system will pick this" if d["kwh"] == 16.5 else ""
        print(f"   {d['name']:<20} {d['kwh']:>10} kWh   {diff:>6.1f} kWh difference{marker}")

    print(f"\n   The system calculates the difference between each device's")
    print(f"   midday consumption and the solar peak production (18 kWh),")
    print(f"   then picks the device with the smallest difference.")


def cmd_generate():
    """
    Calls the API and generates a real solar recommendation.
    Displays the result clearly for the committee.
    """
    _print_step("Step 3: Generating the recommendation")
    print("   -> POST /recommendations/generate/{user_id}")
    print("   Analyzing the past 7 days of solar data...")

    result = _post(f"/recommendations/generate/{USER_ID}")
    code   = result.get("code", "")

    print(f"\n   Result code: {code}")

    if code == "RECOMMENDATION_GENERATED":
        rec  = result.get("recommendation", {})
        text = rec.get("recommendation_text", "")

        print(f"\n   [OK] Solar recommendation generated successfully!")
        print(f"\n   +{'-'*52}+")
        print(f"   | >> {text[:48]:<48} |")
        if len(text) > 48:
            print(f"   |    {text[48:96]:<48} |")
        print(f"   +{'-'*52}+")

        print(f"\n   Analysis details:")
        print(f"   Best period:       {result.get('best_period', '-')}")
        print(f"   Avg production:    {result.get('best_period_avg_production', '-')} kWh")

        period_avgs = result.get("period_averages", {})
        if period_avgs:
            print(f"\n   Production average per period:")
            for period, avg in period_avgs.items():
                bar    = "#" * int(float(avg) / 2)
                marker = " <- best" if period == result.get("best_period") else ""
                print(f"   {period:12} {avg:5} kWh  {bar}{marker}")

        matched = result.get("matched_device")
        if matched:
            print(f"\n   Matched device:      {matched.get('device_name')}")
            print(f"   Device consumption:  {matched.get('avg_consumption')} kWh (at midday)")
            print(f"   Solar production:    {matched.get('target_production')} kWh (at midday)")

    elif code == "GENERAL_RECOMMENDATION_GENERATED":
        rec  = result.get("recommendation", {})
        text = rec.get("recommendation_text", "")
        why  = result.get("fallback_reason", "")
        print(f"\n   [FALLBACK] General recommendation generated (reason: {why})")
        print(f"   Text: {text[:80]}")

    elif code == "DAILY_LIMIT_REACHED":
        print(f"\n   [SKIPPED] User already received a recommendation today.")
        print(f"   Run clean first: python rec_demo_tool.py clean")

    else:
        print(f"\n   [UNEXPECTED] Response:")
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))


def cmd_generate_twice():
    """
    Proves the system blocks two recommendations on the same day.
    """
    _print_step("Proving Daily Limit: two attempts on the same day")

    today_before = _count_today_recs()
    print(f"   Recommendations today (before): {today_before}")

    print(f"\n   <- Attempt 1:")
    r1    = _post(f"/recommendations/generate/{USER_ID}")
    code1 = r1.get("code", "")
    print(f"   code: {code1}")
    if code1 in ("RECOMMENDATION_GENERATED", "GENERAL_RECOMMENDATION_GENERATED"):
        print(f"   [OK] First attempt succeeded.")
    elif code1 == "DAILY_LIMIT_REACHED":
        print(f"   [SKIPPED] User already had a recommendation today.")

    print(f"\n   <- Attempt 2 (same day):")
    r2    = _post(f"/recommendations/generate/{USER_ID}")
    code2 = r2.get("code", "")
    print(f"   code: {code2}")

    today_after = _count_today_recs()
    print(f"\n   Recommendations today (after): {today_after}")

    if code2 == "DAILY_LIMIT_REACHED":
        print(f"\n   [OK] Daily limit works correctly — second attempt was blocked.")
        print(f"   Database unchanged: still {today_after} recommendation(s) today.")
    else:
        print(f"\n   [ERROR] Second attempt was NOT blocked. Code: {code2}")


def cmd_show_result():
    """
    Shows the latest recommendation and notification from the database.
    """
    _print_step("Verifying results in the database")

    rec_result = _get(f"/recommendations/latest/{USER_ID}")
    print(f"\n   Latest recommendation:")
    if rec_result.get("success"):
        data = rec_result.get("data", {})
        print(f"   Text:      {data.get('recommendation_text', '')}")
        print(f"   Timestamp: {data.get('timestamp', '')}")
        print(f"   device_id: {data.get('device_id') or 'NULL (general recommendation)'}")
    else:
        print(f"   No recommendations found yet.")

    notif_result = _get(f"/recommendations/notifications/latest/{USER_ID}")
    print(f"\n   Latest notification:")
    if notif_result.get("success"):
        data = notif_result.get("data", {})
        print(f"   Type:      {data.get('notification_type', '')}")
        print(f"   Content:   {data.get('content', '')[:80]}")
        print(f"   Timestamp: {data.get('timestamp', '')}")
    else:
        print(f"   No notifications found yet.")


def cmd_clean():
    """
    Clears all test data: sensor_data + recommendation + notification.
    Also removes sensor_data for all 3 demo shiftable devices.
    """
    _print_step("Cleaning up test data")

    rec_count   = (db.table("recommendation").select("recommendation_id").eq("user_id", USER_ID).execute()).data or []
    notif_count = (db.table("notification").select("notification_id").eq("user_id", USER_ID).eq("notification_type", "recommendation").execute()).data or []

    # Collect all devices for this user (production + shiftable consumption)
    all_devices = (
        db.table("device")
        .select("device_id, device_name")
        .eq("user_id", USER_ID)
        .execute()
    ).data or []

    sensor_total = 0
    for dev in all_devices:
        rows = (
            db.table("sensor_data")
            .select("device_id")
            .eq("device_id", dev["device_id"])
            .execute()
        ).data or []
        sensor_total += len(rows)
        if rows:
            db.table("sensor_data").delete().eq("device_id", dev["device_id"]).execute()

    db.table("recommendation").delete().eq("user_id", USER_ID).execute()
    db.table("notification").delete().eq("user_id", USER_ID).eq("notification_type", "recommendation").execute()

    print(f"   [OK] Cleared:")
    print(f"   recommendation: {len(rec_count)} -> 0")
    print(f"   notification:   {len(notif_count)} -> 0")
    print(f"   sensor_data:    {sensor_total} -> 0  (across {len(all_devices)} device(s))")
    print(f"\n   Ready for a fresh demo run.")


def cmd_demo():
    """
    Full demo for the committee — runs all steps in order with explanations.
    """
    _print_section("Demo: Smart Recommendations (Lumin)")
    print("""
  Goal: Demonstrate that the system analyzes real solar panel data
  and generates a personalized recommendation suggesting the best
  time for the user to run their household appliances.
    """)

    input("  Press Enter to begin...")

    # Step 0
    _print_section("Step 0: Clearing old test data")
    cmd_clean()
    input("\n  Press Enter to continue...")

    # Step 1
    _print_section("Step 1: Simulating solar panel readings")
    print("""
  Inserting sensor_data readings for the past 7 days.
  The data shows that solar production peaks at midday (12 PM).
    """)
    cmd_seed_solar()
    input("\n  Press Enter to continue...")

    # Step 2
    _print_section("Step 2: Adding 3 shiftable consumption devices")
    print("""
  Adding 3 devices with different midday consumption levels.
  The system will compare all of them against the solar peak
  and automatically pick the closest match.

    Washing Machine:  16.5 kWh  <- closest to solar peak (18 kWh)
    Air Conditioner:  12.0 kWh
    Dishwasher:        8.0 kWh  <- furthest
    """)
    cmd_seed_device()
    input("\n  Press Enter to continue...")

    # Step 3
    _print_section("Step 3: Generating the solar recommendation")
    print("""
  Calling the API. The system will analyze the 7-day sensor data,
  identify the best production period, and build a personalized recommendation.
    """)
    cmd_generate()
    input("\n  Press Enter to continue...")

    # Step 4
    _print_section("Step 4: Verifying the database")
    print("""
  Confirming that the recommendation and notification
  were saved correctly in the database.
    """)
    cmd_show_result()
    input("\n  Press Enter to continue...")

    # Step 5
    _print_section("Step 5: Proving the Daily Limit")
    print("""
  Demonstrating that the system prevents sending
  more than one recommendation per day to the same user.
    """)
    cmd_generate_twice()

    # Summary
    _print_section("Demo Complete")
    print("""
  What was demonstrated:
  1. The system analyzes 7 days of real solar panel sensor data
  2. It automatically identifies the best solar production period (midday)
  3. It compares ALL shiftable devices and picks the best match:
       Washing Machine:  16.5 kWh  <- picked (closest to solar peak)
       Air Conditioner:  12.0 kWh
       Dishwasher:        8.0 kWh
  4. It builds a personalized recommendation and saves it to the database
  5. It sends a notification to the user
  6. It prevents duplicate recommendations on the same day (daily limit)
    """)


# ===============================================
#  MAIN
# ===============================================

HELP = """
Usage:
  python rec_demo_tool.py seed_solar      Step 1: inject solar readings (7 days)
  python rec_demo_tool.py seed_device     Step 2: add a shiftable device
  python rec_demo_tool.py generate        Step 3: generate a recommendation
  python rec_demo_tool.py show_result     Step 4: show result from database
  python rec_demo_tool.py generate_twice  Step 5: prove daily limit
  python rec_demo_tool.py clean           Clear all test data
  python rec_demo_tool.py demo            <- Full demo for committee presentation
"""

if __name__ == "__main__":
    _check_backend()

    if len(sys.argv) < 2:
        print(HELP)
        sys.exit(0)

    cmd = sys.argv[1]

    if   cmd == "seed_solar":     cmd_seed_solar()
    elif cmd == "seed_device":    cmd_seed_device()
    elif cmd == "generate":       cmd_generate()
    elif cmd == "generate_twice": cmd_generate_twice()
    elif cmd == "show_result":    cmd_show_result()
    elif cmd == "clean":          cmd_clean()
    elif cmd == "demo":           cmd_demo()
    else:
        print(f"ERROR: Unknown command: {cmd}")
        print(HELP)