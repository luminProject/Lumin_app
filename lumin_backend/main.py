from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import os
import uuid

from dotenv import load_dotenv
from supabase import create_client
from app.routes import router as profile_router

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="LUMIN Backend")
app.include_router(profile_router)


class SensorReadingIn(BaseModel):
    # device_id في قاعدة البيانات int4
    device_id: int

    # ن支持 الاسم الجديد (kwh_value) + الاسم القديم (kwh) للتوافق
    kwh_value: float | None = None
    kwh: float | None = None

    # ن支持 الاسم الجديد (reading_time) + الاسم القديم (recorded_at) للتوافق
    reading_time: datetime | None = None
    recorded_at: datetime | None = None


@app.get("/")
def root():
    return {"message": "Lumin backend is running"}


@app.post("/sensor-readings")
def ingest_sensor_reading(payload: SensorReadingIn):
    # 0) استخرج القيم مع دعم التوافق للخلف
    kwh_value = payload.kwh_value if payload.kwh_value is not None else payload.kwh
    reading_time = payload.reading_time if payload.reading_time is not None else payload.recorded_at

    if kwh_value is None:
        raise HTTPException(status_code=400, detail="Missing kwh_value (or kwh)")

    # 1) تحقق أن الجهاز موجود وجيب user_id (حسب ERD: device.user_id)
    device_res = (
        supabase.table("device")
        .select("user_id")
        .eq("device_id", payload.device_id)
        .limit(1)
        .execute()
    )

    if not device_res.data:
        raise HTTPException(status_code=404, detail="Device not found")

    # 2) خزّن القراءة في sensor_data (حسب الأعمدة: device_id, reading_time, kwh_value)
    row = {
        "device_id": payload.device_id,
        "reading_time": (reading_time or datetime.utcnow()).isoformat(),
        "kwh_value": float(kwh_value),
    }

    result = supabase.table("sensor_data").insert(row).execute()
    return {"status": "stored", "data": result.data}


@app.get("/energy/{user_id}")
def get_energy(user_id: str):
    # 1) جيب كل أجهزة المستخدم
    devices_res = (
        supabase.table("device")
        .select("device_id")
        .eq("user_id", user_id)
        .execute()
    )

    if not devices_res.data:
        raise HTTPException(status_code=404, detail="No devices found for this user")

    device_ids = [d["device_id"] for d in devices_res.data if d.get("device_id") is not None]

    if not device_ids:
        raise HTTPException(status_code=404, detail="No valid device_id found for this user")

    # 2) جيب قراءات السنسور لهذه الأجهزة
    result = (
        supabase.table("sensor_data")
        .select("kwh_value, reading_time, device_id")
        .in_("device_id", device_ids)
        .order("reading_time", desc=True)
        .execute()
    )

    if not result.data:
        raise HTTPException(status_code=404, detail="No energy data found")

    total_today = sum(float(item.get("kwh_value") or 0) for item in result.data)
    total_month = total_today  # مؤقت (نحسبها لاحقًا حسب الشهر)

    latest = result.data[0]

    return {
        "user_id": user_id,
        "total_kwh_today": total_today,
        "total_kwh_month": total_month,
        "latest": latest,
    }