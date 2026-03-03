from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
import uuid
from dotenv import load_dotenv
from app.routes import router as profile_router
from app.core.lumin_facade import LuminFacade

import supabase as supabase_


load_dotenv()
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")

supabase = supabase_.create_client(SUPABASE_URL, SUPABASE_KEY)
facade = LuminFacade(supabase)

app = FastAPI(title="LUMIN Backend")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Profile routes
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


class DeviceCreate(BaseModel):
    name: str
    device_type: str


@app.get("/")
def root():
    return {"message": "Lumin backend is running"}


@app.post("/sensor-readings")
def ingest_sensor_reading(payload: SensorReadingIn):
    # 0) Extract values with backward compatibility
    kwh_value = payload.kwh_value if payload.kwh_value is not None else payload.kwh
    reading_time = payload.reading_time if payload.reading_time is not None else payload.recorded_at

    if kwh_value is None:
        raise HTTPException(status_code=400, detail="Missing kwh_value (or kwh)")

    try:
        return facade.ingest_sensor_reading(
            device_id=payload.device_id,
            kwh_value=float(kwh_value),
            reading_time_iso=(reading_time or datetime.utcnow()).isoformat(),
        )
    except ValueError as e:
        msg = str(e)
        if msg == "Device not found":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)


@app.get("/energy/{user_id}")
def get_energy(user_id: str):
    try:
        return facade.get_energy(user_id=user_id)
    except ValueError as e:
        msg = str(e)
        if msg in ("No devices found", "No valid device_id found", "No energy data found"):
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)

# =============================
# FACADE ROUTES
# =============================

@app.get("/devices/{user_id}")
def get_devices(user_id: str):
    try:
        return {
            "status": "success",
            "data": facade.view_devices(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/devices/{user_id}")
def add_device(user_id: str, device: DeviceCreate):
    try:
        res = facade.add_new_device(user_id, device.name, device.device_type)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# New DELETE endpoint for deleting a device
@app.delete("/devices/{device_id}")
def delete_device(device_id: int):
    try:
        return {
            "status": "success",
            "data": facade.delete_device(device_id)
        }
    except ValueError as e:
        msg = str(e)
        if msg == "Device not found":
            raise HTTPException(status_code=404, detail=msg)
        raise HTTPException(status_code=400, detail=msg)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/bill/{user_id}")
def get_bill(user_id: str):
    try:
        return {
            "status": "success",
            "data": facade.get_my_current_bill(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/solar-forecast/{user_id}")
def get_solar_forecast(user_id: str):
    try:
        return {
            "status": "success",
            "data": facade.get_solar_prediction(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: str):
    try:
        return {
            "status": "success",
            "data": facade.view_recommendations(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))