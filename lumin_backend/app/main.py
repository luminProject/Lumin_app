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
- Start the recommendation scheduler (3 PM + 7 PM Saudi time)
- Provide endpoints for devices, energy, billing, forecasts, etc.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header 
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.Bill_scheduler import setup_scheduler, shutdown_scheduler
from pydantic import BaseModel
from datetime import datetime
import os
import logging
from dotenv import load_dotenv
from app.supabase_client import extract_bearer, get_supabase_for_jwt, supabase_admin, verify_user_access
from app.routers import router as profile_router
from app.routers.recommendation_router import router as recommendation_router
from app.core.lumin_facade import LuminFacade
from app.scheduler import create_scheduler
import supabase as supabase_


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


from contextlib import asynccontextmanager
from fastapi import FastAPI
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
# Admin facade for system jobs/schedulers
admin_facade = LuminFacade(supabase_admin)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Start both schedulers when the server starts,
    and shut them down cleanly when the server stops.
    """

    # Recommendation scheduler
    recommendation_scheduler = create_scheduler()
    recommendation_scheduler.start()
    logger.info("✅ Recommendation scheduler started — runs at 3 PM and 7 PM Saudi time.")

    # Bill scheduler
    setup_scheduler(admin_facade)
    logger.info("✅ Bill scheduler started.")

    yield  # Server is running

    # Shutdown both schedulers
    recommendation_scheduler.shutdown()
    logger.info("🛑 Recommendation scheduler stopped.")

    shutdown_scheduler()
    logger.info("🛑 Bill scheduler stopped.")


app = FastAPI(title="LUMIN Backend", lifespan=lifespan)

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


# Model for updating device settings
class DeviceUpdate(BaseModel):
    name: str
    device_type: str
    room: str | None = None
    panel_capacity: str | None = None


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
# Sensor Readings Retrieval
# -----------------------------
@app.get("/sensor-readings/{device_id}")
def get_device_readings(device_id: int):
    """
    Get all readings for a specific device.
    """
    try:
        return {
            "status": "success",
            "data": facade.get_device_readings(device_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sensor-readings/latest/{device_id}")
def get_latest_reading(device_id: int):
    """
    Get the latest reading for a device.
    """
    try:
        return {
            "status": "success",
            "data": facade.get_latest_reading(device_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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


# PATCH endpoint for updating device settings (name, type, room, panel_capacity)
@app.patch("/devices/{device_id}")
def update_device(device_id: int, payload: DeviceUpdate):
    """
    Update editable device settings only (name, room, panel_capacity).
    Does NOT modify created_at.
    """
    try:
        return {
            "status": "success",
            "data": facade.update_device_settings(
                device_id=device_id,
                name=payload.name,
                device_type=payload.device_type,
                room=payload.room,
                panel_capacity=payload.panel_capacity,
            ),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# -----------------------------
# Billing Endpoint
# -----------------------------
class BillLimitIn(BaseModel):
    limit_amount: float
@app.get("/bill/{user_id}")
def get_my_current_bill(
    user_id: str,
    authorization: Optional[str] = Header(None),
):
    try: 
        verify_user_access(user_id, authorization)
        jwt = extract_bearer(authorization)
        user_supabase = get_supabase_for_jwt(jwt)
        bill_facade = LuminFacade(user_supabase)

        return {
            "status": "success",
            "data": bill_facade.get_my_current_bill(user_id),
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/bill/{user_id}")
def set_bill_limit(
    user_id: str,
    payload: BillLimitIn,
    authorization: Optional[str] = Header(None),
):
    try:
        verify_user_access(user_id, authorization)
        jwt = extract_bearer(authorization)
        user_supabase = get_supabase_for_jwt(jwt)
        bill_facade = LuminFacade(user_supabase)
        bill_facade.set_bill_limit(user_id, payload.limit_amount)

        return {
            "status": "success",
            "data": bill_facade.get_my_current_bill(user_id),
        }

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
@app.post("/internal/run-bill-checkpoint")
def run_bill_checkpoint():
    try:
        return {
            "status": "success",
            "data": admin_facade.run_bill_checkpoint_for_all_users()
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