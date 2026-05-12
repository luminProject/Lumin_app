import os
import sys
import json
import requests
from datetime import date, timedelta
from dotenv import load_dotenv
import supabase as supabase_

load_dotenv()

db = supabase_.create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)

USER_ID = "f4cbdd41-e112-443f-87b6-c21d50ea4817"
BASE_URL = "http://127.0.0.1:8000"

REAL_HOME_USAGE = [
    70, 62, 42, 61, 48, 59, 24,
    38, 46, 64, 78, 97, 140, 72,
    57, 79, 75, 74, 55, 57, 70,
    35, 45, 31, 27, 55, 93, 81,
]


def get_demo_dates(checkpoint_day=7):
    today = date.today()
    cycle_start = today - timedelta(days=checkpoint_day)
    last_billing_end_date = cycle_start - timedelta(days=1)
    return today, last_billing_end_date, cycle_start


def profile():
    rows = (
        db.table("users")
        .select("user_id, last_billing_end_date")
        .eq("user_id", USER_ID)
        .execute()
    ).data

    print("\n=== USER PROFILE ===")
    print(json.dumps(rows, indent=2, ensure_ascii=False))


def reset(checkpoint_day=7):
    db.table("energycalculation").delete().eq("user_id", USER_ID).execute()
    db.table("billprediction").delete().eq("user_id", USER_ID).execute()
    db.table("notification").delete().eq("user_id", USER_ID).execute()

    today, last_billing_end_date, cycle_start = get_demo_dates(checkpoint_day)

    result = (
        db.table("users")
        .update({"last_billing_end_date": last_billing_end_date.isoformat()})
        .eq("user_id", USER_ID)
        .execute()
    )

    print("USER UPDATE RESULT:", result.data)
    print("\n✅ Reset done")
    print(f"Today: {today}")
    print(f"Checkpoint day: {checkpoint_day}")
    print(f"Last billing end date: {last_billing_end_date}")
    print(f"Cycle start: {cycle_start}")


def add(days: int, checkpoint_day=7):
    _, _, cycle_start = get_demo_dates(checkpoint_day)

    values = REAL_HOME_USAGE[:days]

    if len(values) < days:
        raise ValueError("Not enough real household usage values.")

    rows = []

    for i, consumption in enumerate(values):
        d = cycle_start + timedelta(days=i)

        rows.append({
            "user_id": USER_ID,
            "date": d.isoformat(),
            "total_consumption": consumption,
            "solar_production": 0,
            "total_cost": round(consumption * 0.18, 2),
            "cost_savings": 0,
            "carbon_reduction": 0,
        })

    db.table("energycalculation").upsert(
        rows,
        on_conflict="user_id,date"
    ).execute()

    print(f"✅ Added first {days} real household usage day(s)")
    print(f"Data range: {cycle_start} → {cycle_start + timedelta(days=days - 1)}")
    print(f"Usage values: {values}")


def set_limit(limit: float, checkpoint_day=7):
    _, _, cycle_start = get_demo_dates(checkpoint_day)

    rows = (
        db.table("billprediction")
        .select("*")
        .eq("user_id", USER_ID)
        .eq("cycle_start", cycle_start.isoformat())
        .execute()
    ).data

    if rows:
        (
            db.table("billprediction")
            .update({"limit_amount": limit})
            .eq("user_id", USER_ID)
            .eq("cycle_start", cycle_start.isoformat())
            .execute()
        )
    else:
        db.table("billprediction").insert({
            "user_id": USER_ID,
            "cycle_start": cycle_start.isoformat(),
            "limit_amount": limit,
            "predicted_bill": 0,
            "predicted_usage_kwh": 0,
            "actual_bill": 0,
            "current_usage_kwh": 0,
            "forecast_available": False,
            "last_checkpoint_day": None,
        }).execute()

    print(f"✅ Limit set to {limit} SAR")


def run_checkpoint():
    url = f"{BASE_URL}/internal/run-bill-checkpoint"

    try:
        r = requests.post(url, timeout=60)
        print("STATUS:", r.status_code)

        try:
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception:
            print(r.text)

    except Exception as e:
        print("❌ Could not reach backend")
        print(e)
        print("Make sure uvicorn is running")


def bill():
    rows = (
        db.table("billprediction")
        .select("*")
        .eq("user_id", USER_ID)
        .order("limit_id", desc=True)
        .execute()
    ).data

    print("\n=== BILLPREDICTION ===")
    print(json.dumps(rows, indent=2, ensure_ascii=False))


def notifications():
    rows = (
        db.table("notification")
        .select("*")
        .eq("user_id", USER_ID)
        .order("timestamp", desc=True)
        .execute()
    ).data

    print("\n=== NOTIFICATIONS ===")
    print(json.dumps(rows, indent=2, ensure_ascii=False))


def demo_no_end_date():
    print("\n===== DEMO: NO BILLING END DATE =====")

    db.table("energycalculation").delete().eq("user_id", USER_ID).execute()
    db.table("billprediction").delete().eq("user_id", USER_ID).execute()
    db.table("notification").delete().eq("user_id", USER_ID).execute()

    db.table("users").update({
        "last_billing_end_date": None
    }).eq("user_id", USER_ID).execute()

    print("❌ No billing end date configured")
    print("Expected behavior:")
    print("- setup_required = true")
    print("- No bill prediction")
    print("- User must configure billing info first")

    profile()
    bill()
    notifications()


def demo_no_limit():
    print("\n===== DEMO: NO LIMIT SET =====")

    db.table("energycalculation").delete().eq("user_id", USER_ID).execute()
    db.table("billprediction").delete().eq("user_id", USER_ID).execute()
    db.table("notification").delete().eq("user_id", USER_ID).execute()

    today, last_billing_end_date, cycle_start = get_demo_dates(7)

    db.table("users").update({
        "last_billing_end_date": last_billing_end_date.isoformat()
    }).eq("user_id", USER_ID).execute()

    print("✅ User has billing period")
    print("❌ No bill limit set yet")
    print(f"Today: {today}")
    print(f"Last billing end date: {last_billing_end_date}")
    print(f"Period start: {cycle_start}")

    profile()
    bill()
    notifications()


def demo_not_enough_data():
    print("\n===== DEMO: NOT ENOUGH DATA =====")

    reset(7)
    set_limit(50, 7)

    # First 6 days only, so prediction should not be generated.
    add(6, 7)

    run_checkpoint()
    bill()
    notifications()


def demo_warning():
    print("\n===== DEMO: BILL WARNING =====")

    reset(7)
    set_limit(20, 7)

    # First 7 real usage days.
    add(7, 7)

    run_checkpoint()
    bill()
    notifications()


def demo_safe_update():
    print("\n===== DEMO: SAFE BILL UPDATE =====")

    reset(7)
    set_limit(400, 7)

    # First 7 real usage days.
    add(7, 7)

    run_checkpoint()
    bill()
    notifications()


def demo_no_duplicate():
    print("\n===== DEMO: NO DUPLICATE NOTIFICATION =====")

    reset(7)
    set_limit(20, 7)
    add(7, 7)

    print("\n--- First run ---")
    run_checkpoint()

    print("\n--- Second run ---")
    run_checkpoint()

    bill()
    notifications()


def demo_checkpoint_14():
    print("\n===== DEMO: CHECKPOINT 14 =====")

    reset(14)
    set_limit(20, 14)

    # First 14 real usage days.
    add(14, 14)

    run_checkpoint()
    bill()
    notifications()


def demo_checkpoint_21():
    print("\n===== DEMO: CHECKPOINT 21 =====")

    reset(21)
    set_limit(20, 21)

    # First 21 real usage days.
    add(21, 21)

    run_checkpoint()
    bill()
    notifications()


def demo_checkpoint_28():
    print("\n===== DEMO: CHECKPOINT 28 =====")

    reset(28)
    set_limit(20, 28)

    # First 28 real usage days.
    add(28, 28)

    run_checkpoint()
    bill()
    notifications()


HELP = """
Main demos:
  python bill_demo.py demo_no_end_date
  python bill_demo.py demo_no_limit
  python bill_demo.py demo_no_data
  python bill_demo.py demo_warning
  python bill_demo.py demo_safe
  python bill_demo.py demo_duplicate

Extra checkpoints:
  python bill_demo.py demo_cp14
  python bill_demo.py demo_cp21
  python bill_demo.py demo_cp28

View:
  python bill_demo.py profile
  python bill_demo.py bill
  python bill_demo.py notifications
"""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(HELP)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "demo_no_end_date":
        demo_no_end_date()

    elif cmd == "demo_no_limit":
        demo_no_limit()

    elif cmd == "demo_no_data":
        demo_not_enough_data()

    elif cmd == "demo_warning":
        demo_warning()

    elif cmd == "demo_safe":
        demo_safe_update()

    elif cmd == "demo_duplicate":
        demo_no_duplicate()

    elif cmd == "demo_cp14":
        demo_checkpoint_14()

    elif cmd == "demo_cp21":
        demo_checkpoint_21()

    elif cmd == "demo_cp28":
        demo_checkpoint_28()

    elif cmd == "profile":
        profile()

    elif cmd == "bill":
        bill()

    elif cmd == "notifications":
        notifications()

    else:
        print(HELP)