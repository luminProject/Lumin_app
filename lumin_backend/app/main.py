"""
LUMIN Backend - Main Application

This file is the entry point of the FastAPI backend.
It initializes the server, connects to Supabase, and defines
API endpoints used by the Flutter application.

Responsibilities:
- Initialize FastAPI application
- Configure CORS
- Create Supabase connection
- Initialize LuminFacade
- Register profile routes
- Provide endpoints for devices, energy, billing, forecasts, etc.
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import os
from dotenv import load_dotenv

from app.routers import router as profile_router
from app.routers.recommendation_router import router as recommendation_router
from app.core.lumin_facade import LuminFacade
import supabase as supabase_


# -----------------------------
# Environment Configuration
# -----------------------------
"""
Load environment variables from .env file.
These contain Supabase credentials.
"""
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError("Missing SUPABASE_URL or SUPABASE_KEY in .env")


# -----------------------------
# Supabase Client Initialization
# -----------------------------
"""
Create a Supabase client that will be used by the system
to interact with the database.
"""
supabase = supabase_.create_client(SUPABASE_URL, SUPABASE_KEY)

# Facade instance (central system interface)
facade = LuminFacade(supabase)


# -----------------------------
# FastAPI Application
# -----------------------------
app = FastAPI(title="LUMIN Backend")


# -----------------------------
# CORS Configuration
# -----------------------------
"""
Allows the Flutter application to communicate with this backend
from any origin.
"""
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Register profile routes
app.include_router(profile_router)

# Register recommendation routes
app.include_router(recommendation_router)


# -----------------------------
# Request Models
# -----------------------------
class SensorReadingIn(BaseModel):
    """
    Model used when sending a new sensor reading.

    Supports old and new field names for compatibility.
    """

    device_id: int

    # New field name
    kwh_value: float | None = None

    # Old field name
    kwh: float | None = None

    # New timestamp
    reading_time: datetime | None = None

    # Old timestamp
    recorded_at: datetime | None = None


class DeviceCreate(BaseModel):
    """
    Model used when creating a new device.
    """
    name: str
    device_type: str


# -----------------------------
# Root Endpoint
# -----------------------------
@app.get("/")
def root():
    """
    Simple health check endpoint.
    """
    return {"message": "Lumin backend is running"}


# -----------------------------
# Sensor Reading Endpoint
# -----------------------------
@app.post("/sensor-readings")
def ingest_sensor_reading(payload: SensorReadingIn):
    """
    Store energy readings coming from IoT devices.
    """

    kwh_value = payload.kwh_value if payload.kwh_value is not None else payload.kwh
    reading_time = payload.reading_time if payload.reading_time is not None else payload.recorded_at

    if kwh_value is None:
        raise HTTPException(status_code=400, detail="Missing kwh_value")

    try:
        return facade.ingest_sensor_reading(
            device_id=payload.device_id,
            kwh_value=float(kwh_value),
            reading_time_iso=(reading_time or datetime.utcnow()).isoformat(),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# Energy Endpoint
# -----------------------------
@app.get("/energy/{user_id}")
def get_energy(user_id: str):
    """
    Returns total energy consumption for the user.
    """
    try:
        return facade.get_energy(user_id=user_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# -----------------------------
# Device Management Endpoints
# -----------------------------
@app.get("/devices/{user_id}")
def get_devices(user_id: str):
    """
    Retrieve all devices belonging to a user.
    """
    try:
        return {
            "status": "success",
            "data": facade.view_devices(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/devices/{user_id}")
def add_device(user_id: str, device: DeviceCreate):
    """
    Add a new smart device to the user account.
    """
    try:
        res = facade.add_new_device(user_id, device.name, device.device_type)
        return {"status": "success", "data": res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.delete("/devices/{device_id}")
def delete_device(device_id: int):
    """
    Delete a device from the system.
    """
    try:
        return {
            "status": "success",
            "data": facade.delete_device(device_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Billing Endpoint
# -----------------------------
@app.get("/bill/{user_id}")
def get_bill(user_id: str):
    """
    Calculate current electricity bill estimate.
    """
    try:
        return {
            "status": "success",
            "data": facade.get_my_current_bill(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Solar Forecast Endpoint
# -----------------------------
@app.get("/solar-forecast/{user_id}")
def get_solar_forecast(user_id: str):
    """
    Returns solar energy production prediction.
    """
    try:
        return {
            "status": "success",
            "data": facade.get_solar_prediction(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# -----------------------------
# Recommendations Endpoint
# -----------------------------
@app.get("/recommendations/{user_id}")
def get_recommendations(user_id: str):
    """
    Returns AI energy recommendations for the user.
    """
    try:
        return {
            "status": "success",
            "data": facade.view_recommendations(user_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))