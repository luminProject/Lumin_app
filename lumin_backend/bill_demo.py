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
    os.getenv("SUPABASE_KEY"),
)

USER_ID = "f4cbdd41-e112-443f-87b6-c21d50ea4817"
BASE_URL = "http://127.0.0.1:8000"


def get_demo_dates():
    today = date.today()
    last_billing_end_date = today - timedelta(days=8)
    cycle_start = last_billing_end_date + timedelta(days=1)
    return today, last_billing_end_date, cycle_start


def reset():
    db.table("energycalculation").delete().eq("user_id", USER_ID).execute()
    db.table("billprediction").delete().eq("user_id", USER_ID).execute()
    db.table("notification").delete().eq("user_id", USER_ID).execute()

    today, last_billing_end_date, cycle_start = get_demo_dates()

    db.table("users").update({
        "last_billing_end_date": last_billing_end_date.isoformat()
    }).eq("user_id", USER_ID).execute()

    print("✅ Reset done")
    print(f"Today: {today}")
    print(f"Last billing end date: {last_billing_end_date}")
    print(f"Cycle start: {cycle_start}")


def add(days: int, consumption: float):
    _, _, cycle_start = get_demo_dates()

    rows = []
    for i in range(days):
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

    db.table("energycalculation").upsert(rows).execute()

    print(f"✅ Added {days} day(s), consumption={consumption} kWh/day")
    print(f"Data range: {cycle_start} → {cycle_start + timedelta(days=days - 1)}")


def set_limit(limit: float):
    _, _, cycle_start = get_demo_dates()

    rows = (
        db.table("billprediction")
        .select("*")
        .eq("user_id", USER_ID)
        .eq("cycle_start", cycle_start.isoformat())
        .execute()
    ).data

    if rows:
        db.table("billprediction").update({
            "limit_amount": limit
        }).eq("user_id", USER_ID).eq("cycle_start", cycle_start.isoformat()).execute()
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


def reset_checkpoint():
    db.table("billprediction").update({
        "last_checkpoint_day": None,
        "forecast_available": False,
    }).eq("user_id", USER_ID).execute()

    print("✅ Checkpoint reset")


# =========================================================
# DEMO CASES
# =========================================================

def demo_no_limit():
    print("\n===== DEMO: NO LIMIT SET =====")

    db.table("energycalculation").delete().eq("user_id", USER_ID).execute()
    db.table("billprediction").delete().eq("user_id", USER_ID).execute()
    db.table("notification").delete().eq("user_id", USER_ID).execute()

    today, last_billing_end_date, cycle_start = get_demo_dates()

    db.table("users").update({
        "last_billing_end_date": last_billing_end_date.isoformat()
    }).eq("user_id", USER_ID).execute()

    print("✅ User has billing cycle")
    print("❌ No bill limit set yet")
    print(f"Today: {today}")
    print(f"Last billing end date: {last_billing_end_date}")
    print(f"Cycle start: {cycle_start}")

    bill()
    notifications()


def demo_not_enough_data():
    print("\n===== DEMO: NOT ENOUGH DATA =====")
    reset()
    set_limit(50)
    add(6, 10)
    run_checkpoint()
    bill()
    notifications()


def demo_warning():
    print("\n===== DEMO: BILL WARNING =====")
    reset()
    set_limit(20)
    add(7, 30)
    run_checkpoint()
    bill()
    notifications()


def demo_safe_update():
    print("\n===== DEMO: SAFE BILL UPDATE =====")
    reset()
    set_limit(200)
    add(7, 10)
    run_checkpoint()
    bill()
    notifications()


def demo_no_duplicate():
    print("\n===== DEMO: NO DUPLICATE NOTIFICATION =====")
    reset()
    set_limit(20)
    add(7, 30)

    print("\n--- First run ---")
    run_checkpoint()

    print("\n--- Second run, should NOT duplicate notification ---")
    run_checkpoint()

    bill()
    notifications()


HELP = """
Usage:

Basic:
  python bill_demo.py reset
  python bill_demo.py add 7 10
  python bill_demo.py limit 50
  python bill_demo.py run
  python bill_demo.py bill
  python bill_demo.py notifications
  python bill_demo.py resetcp

Demo cases:
  python bill_demo.py demo_no_limit
  python bill_demo.py demo_no_data
  python bill_demo.py demo_safe
  python bill_demo.py demo_warning
  python bill_demo.py demo_duplicate
"""


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(HELP)
        sys.exit(0)

    cmd = sys.argv[1]

    if cmd == "reset":
        reset()

    elif cmd == "add":
        days = int(sys.argv[2])
        consumption = float(sys.argv[3]) if len(sys.argv) > 3 else 10
        add(days, consumption)

    elif cmd == "limit":
        limit = float(sys.argv[2])
        set_limit(limit)

    elif cmd == "run":
        run_checkpoint()

    elif cmd == "bill":
        bill()

    elif cmd == "notifications":
        notifications()

    elif cmd == "resetcp":
        reset_checkpoint()

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

    else:
        print(HELP)