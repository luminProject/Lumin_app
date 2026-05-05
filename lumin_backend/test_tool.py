"""
test_tool.py — أداة تست Solar Forecast
احذفي هذا الملف قبل النشر للإنتاج
===========================================
المنطق:
  - يحتفظ بـ "تاريخ افتراضي" في test_state.json
  - collect N  → يضيف N يوم بيانات للأمام من التاريخ الحالي، يحرك التاريخ
  - offline N  → يحرك التاريخ N يوم بدون بيانات
  - reconnect  → يضيف قراءة sensor في التاريخ الحالي
  - reset      → يمسح كل شيء ويطلب تاريخ بداية جديد
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
STATE_FILE = "test_state.json"   # يُحفظ جانب test_tool.py


# ═══════════════════════════════════════════════
#  STATE — يحفظ التاريخ الافتراضي بين الأوامر
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
    يحرك التاريخ الافتراضي للأمام بمقدار N.
    يضيف sensor_data لآخر يوم (إشارة أن الجهاز شغال).
    """
    device = get_device(user_id)
    if not device:
        print("❌ No production device found"); return

    current = get_current_date()
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

    # أضف sensor_data لآخر يوم
    reading_time = f"{new_date.isoformat()}T12:00:00+00:00"
    db.table("sensor_data").insert({
        "device_id":    device_id,
        "reading_time": reading_time,
        "kwh_value":    12.5,
    }).execute()

    set_current_date(new_date)
    print(f"✅ Collected {days} day(s)")
    print(f"   Added energycalculation rows: {current + timedelta(1)} → {new_date}")
    print(f"   Added sensor reading at {new_date}")
    print_status_line(new_date)


def cmd_offline(user_id: str, days: int):
    """
    يحرك التاريخ الافتراضي N يوم بدون إضافة بيانات.
    يمثل مرور أيام الجهاز فيها منقطع.
    """
    current  = get_current_date()
    new_date = current + timedelta(days=days)
    set_current_date(new_date)

    print(f"✅ Advanced {days} day(s) offline — no data added")
    print_status_line(new_date)
    if days >= 15:
        print(f"   ⚠ Total offline may trigger feature_disabled — check status")


def cmd_reconnect(user_id: str):
    """
    يضيف قراءة sensor_data في التاريخ الافتراضي الحالي.
    لا يمسح ولا يعدل أي شيء آخر.
    """
    device = get_device(user_id)
    if not device:
        print("❌ No production device found"); return

    current   = get_current_date()
    device_id = device["device_id"]
    reading_time = f"{current.isoformat()}T12:00:00+00:00"

    db.table("sensor_data").insert({
        "device_id":    device_id,
        "reading_time": reading_time,
        "kwh_value":    12.5,
    }).execute()

    print(f"✅ Reconnect reading added at {reading_time}")
    print(f"   → days_offline = 0 (from virtual today's perspective)")
    print(f"   → collected_days و days_missed لا يتأثران")
    print_status_line(current)


def cmd_reset(user_id: str):
    """
    ريست كامل:
    - يمسح sensor_data و energycalculation
    - يطلب تاريخ بداية جديد
    - يحفظه كـ current_date في الـ state
    """
    device = get_device(user_id)
    if not device:
        print("❌ No production device found"); return

    device_id = device["device_id"]
    db.table("sensor_data").delete().eq("device_id", device_id).execute()
    db.table("energycalculation").delete().eq("user_id", user_id).execute()

    print("🗑  Cleared sensor_data and energycalculation")
    print("Enter start date (YYYY-MM-DD), e.g. 2026-03-01:")
    raw = input("> ").strip()
    try:
        start = date.fromisoformat(raw)
    except ValueError:
        print("❌ Invalid date format"); return

    # installation_date = تاريخ البداية
    db.table("device").update({
        "installation_date": start.isoformat()
    }).eq("device_id", device_id).execute()

    set_current_date(start)
    print(f"✅ Reset complete — installation_date={start}")
    print_status_line(start)


def cmd_status(user_id: str):
    """
    GET /solar-forecast/{user_id}?test_date=<current_virtual_date>
    """
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
    """اعرض التاريخ الافتراضي الحالي"""
    print_status_line(get_current_date())


# ═══════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════

HELP = """
استخدامي:
  python test_tool.py collect <days>    أضف N يوم بيانات (يحرك التاريخ للأمام)
  python test_tool.py offline <days>    N يوم بدون بيانات (يحرك التاريخ للأمام)
  python test_tool.py reconnect         أضف قراءة في التاريخ الحالي
  python test_tool.py reset             ريست كامل + اختار تاريخ بداية
  python test_tool.py status            اعرض JSON من API بالتاريخ الحالي
  python test_tool.py date              اعرض التاريخ الافتراضي الحالي

مثال:
  python test_tool.py reset              ← اختاري 2026-03-01
  python test_tool.py collect 10         ← 10 أيام بيانات، التاريخ صار 2026-03-11
  python test_tool.py offline 5          ← 5 أيام انقطاع، التاريخ صار 2026-03-16
  python test_tool.py status             ← يعرض الحالة في 2026-03-16
  python test_tool.py reconnect          ← إعادة اتصال في 2026-03-16
  python test_tool.py status             ← يعرض days_offline=0
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