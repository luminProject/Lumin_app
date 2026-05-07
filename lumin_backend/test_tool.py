"""
test_tool.py — أداة تست Solar Forecast
===========================================
sensor_data removed — last_reading_at updated directly on device table.

المنطق:
  - يحتفظ بـ "تاريخ افتراضي" في test_state.json
  - collect N  → يضيف N يوم بيانات للأمام، يحدّث last_reading_at على الجهاز
  - offline N  → يحرك التاريخ N يوم بدون بيانات (last_reading_at ما يتغيّر)
  - reconnect  → يحدّث last_reading_at في التاريخ الحالي
  - reset      → يمسح energycalculation ويطلب تاريخ بداية جديد
  - status     → يعرض الـ JSON من الـ API بالتاريخ الحالي
"""

import os
import sys
import json
import urllib.request
from datetime import date, datetime, timedelta, timezone
from dotenv import load_dotenv
import supabase as supabase_

load_dotenv()
db = supabase_.create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

USER_ID    = "7f5f8815-f3f4-49f2-927b-31fb2dce6396"
BASE_URL   = "http://127.0.0.1:8000"
STATE_FILE = "test_state.json"


# ═══════════════════════════════════════════════
#  STATE
# ═══════════════════════════════════════════════

def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

def get_current_date() -> date:
    state = load_state()
    if "current_date" in state:
        return date.fromisoformat(state["current_date"])
    return date.today()

def set_current_date(d: date):
    state = load_state()
    state["current_date"] = d.isoformat()
    save_state(state)


# ═══════════════════════════════════════════════
#  HELPER
# ═══════════════════════════════════════════════

def get_device(user_id: str) -> dict | None:
    rows = (
        db.table("device")
        .select("device_id, installation_date")
        .eq("user_id", user_id)
        .eq("device_type", "production")
        .limit(1)
        .execute()
    ).data
    return rows[0] if rows else None

def print_status_line(current: date):
    print(f"\n📅 Current virtual date: {current}")


# ═══════════════════════════════════════════════
#  COMMANDS
# ═══════════════════════════════════════════════

def cmd_collect(user_id: str, days: int):
    """
    يضيف N يوم بيانات للأمام من التاريخ الافتراضي الحالي.
    يحدّث last_reading_at على الجهاز بدل sensor_data.
    """
    device = get_device(user_id)
    if not device:
        print("❌ No production device found"); return

    current   = get_current_date()
    device_id = device["device_id"]

    rows = []
    for i in range(days):
        d = current + timedelta(days=i + 1)
        rows.append({
            "user_id":           user_id,
            "date":              d.isoformat(),
            "solar_production":  round(15.0 + (i % 5), 1),
            "total_consumption": 25.0,
            "total_cost":        4.5,
            "carbon_reduction":  7.8,
            "cost_savings":      2.7,
        })

    for i in range(0, len(rows), 20):
        db.table("energycalculation").upsert(rows[i:i + 20]).execute()

    new_date = current + timedelta(days=days)

    # قيم سيمولايشن للجهاز
    daily_kwh   = 15.0          # إنتاج يومي ثابت للتست
    total_daily = daily_kwh     # total_energy_daily = إنتاج آخر يوم
    total_month = daily_kwh * days  # total_energy = مجموع إنتاج الأيام

    # تحديث device بكل الأعمدة الحقيقية
    reading_time = f"{new_date.isoformat()}T12:00:00+00:00"
    db.table("device").update({
        "last_reading_at":    reading_time,
        "production":         500.0,    # Watts لحظية (سيمولايشن)
        "is_on":              True,
        "total_energy_daily": total_daily,
        "total_energy":       total_month,
    }).eq("device_id", device_id).execute()

    set_current_date(new_date)
    print(f"✅ Collected {days} day(s)")
    print(f"   Added energycalculation rows: {current + timedelta(1)} → {new_date}")
    print(f"   Updated device: last_reading_at={new_date}, production=500W, is_on=True")
    print(f"   total_energy_daily={total_daily} kWh, total_energy={total_month} kWh")
    print_status_line(new_date)


def cmd_offline(user_id: str, days: int):
    """
    يحرك التاريخ الافتراضي N يوم بدون إضافة بيانات.
    يصفّر production و is_on عشان يعكس الانقطاع.
    last_reading_at ما يتغيّر — هذا اللي يحسب days_offline.
    """
    device = get_device(user_id)
    if not device:
        print("❌ No production device found"); return

    # صفّر القراءات اللحظية عشان يبيّن الجهاز منقطع
    db.table("device").update({
        "production":         0.0,
        "is_on":              False,
        "total_energy_daily": 0.0,
    }).eq("device_id", device["device_id"]).execute()

    current  = get_current_date()
    new_date = current + timedelta(days=days)
    set_current_date(new_date)

    print(f"✅ Advanced {days} day(s) offline — production=0, is_on=False")
    print_status_line(new_date)
    if days >= 15:
        print(f"   ⚠ Total offline may trigger feature_disabled — check status")


def cmd_reconnect(user_id: str):
    """
    يحدّث last_reading_at في التاريخ الافتراضي الحالي.
    """
    device = get_device(user_id)
    if not device:
        print("❌ No production device found"); return

    current   = get_current_date()
    device_id = device["device_id"]
    reading_time = f"{current.isoformat()}T12:00:00+00:00"

    db.table("device").update({
        "last_reading_at": reading_time
    }).eq("device_id", device_id).execute()

    print(f"✅ Reconnect: updated last_reading_at = {reading_time}")
    print(f"   → days_offline = 0 (from virtual today's perspective)")
    print_status_line(current)


def cmd_reset(user_id: str):
    """
    ريست كامل:
    - يمسح energycalculation
    - يصفّر last_reading_at على الجهاز
    - يطلب تاريخ بداية جديد
    """
    device = get_device(user_id)
    if not device:
        print("❌ No production device found"); return

    device_id = device["device_id"]
    db.table("energycalculation").delete().eq("user_id", user_id).execute()

    print("🗑  Cleared energycalculation")
    print("Enter start date (YYYY-MM-DD), e.g. 2026-03-01:")
    raw = input("> ").strip()
    try:
        start = date.fromisoformat(raw)
    except ValueError:
        print("❌ Invalid date format"); return

    # ريست كل أعمدة الجهاز دفعة وحدة
    db.table("device").update({
        "installation_date":  start.isoformat(),
        "last_reading_at":    None,
        "production":         0.0,
        "is_on":              False,
        "total_energy_daily": 0.0,
        "total_energy":       0.0,
    }).eq("device_id", device_id).execute()

    set_current_date(start)
    print(f"✅ Reset complete — installation_date={start}")
    print_status_line(start)


def cmd_status(user_id: str):
    current = get_current_date()
    url = f"{BASE_URL}/solar-forecast/{user_id}?test_date={current}"
    try:
        with urllib.request.urlopen(url, timeout=5) as r:
            data = json.loads(r.read())
        payload = data.get("data") or data
        print(f"📡 {url}\n")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ Could not reach {url}: {e}")
        print("   → تأكدي أن uvicorn شغال")
    print_status_line(current)


def cmd_date():
    print_status_line(get_current_date())


HELP = """
استخدامي:
  python test_tool.py collect <days>    أضف N يوم بيانات (يحرك التاريخ للأمام)
  python test_tool.py offline <days>    N يوم بدون بيانات (يحرك التاريخ للأمام)
  python test_tool.py reconnect         حدّث last_reading_at في التاريخ الحالي
  python test_tool.py reset             ريست كامل + اختار تاريخ بداية
  python test_tool.py status            اعرض JSON من API بالتاريخ الحالي
  python test_tool.py date              اعرض التاريخ الافتراضي الحالي
"""

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(HELP); sys.exit(0)

    cmd = sys.argv[1]

    if   cmd == "collect":   cmd_collect(USER_ID,  int(sys.argv[2]) if len(sys.argv) > 2 else 10)
    elif cmd == "offline":   cmd_offline(USER_ID,  int(sys.argv[2]) if len(sys.argv) > 2 else 1)
    elif cmd == "reconnect": cmd_reconnect(USER_ID)
    elif cmd == "reset":     cmd_reset(USER_ID)
    elif cmd == "status":    cmd_status(USER_ID)
    elif cmd == "date":      cmd_date()
    else:
        print(f"❌ Unknown command: {cmd}"); print(HELP)