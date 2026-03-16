

from datetime import date
import datetime
from typing import List, Dict, Any
from app.supabase_client import supabase
from app.models.user import User

from app.models.energy_calculation import EnergyCalculation
from app.models.notification import Notification
from app.models.bill_prediction import BillPrediction, Tariff018Strategy
class LuminFacade:
    """
    Single Facade that aggregates all subsystems as required in the LUMIN report
    (SmartEnergyFacade).

    Responsibilities (from report):
    - addNewDevice
    - viewDevices
    - getMyCurrentBill
    - viewEnergyEnergyCalculation
    - getSolarPrediction
    - viewRecommendations
    - getNotifications
    """
    def __init__(self, supabase_client):
        self.supabase = supabase_client

    # -----------------------------
    # SENSOR READING (Week 3: Sensor Reading endpoint support)
    # -----------------------------
    def ingest_sensor_reading(
        self,
        *,
        device_id: int,
        kwh_value: float,
        reading_time_iso: str,
    ) -> Dict[str, Any]:
        """Store a sensor reading for a device (used by /sensor-readings endpoint)."""

        # Verify device exists
        device_res = (
            self.supabase.table("device")
            .select("user_id")
            .eq("device_id", device_id)
            .limit(1)
            .execute()
        )

        if not getattr(device_res, "data", None):
            raise ValueError("Device not found")

        row = {
            "device_id": int(device_id),
            "reading_time": reading_time_iso,
            "kwh_value": float(kwh_value),
        }

        result = self.supabase.table("sensor_data").insert(row).execute()
        return {"status": "stored", "data": getattr(result, "data", None)}

    # -----------------------------
    # ENERGY (optional helper for a simple /energy endpoint)
    # -----------------------------
    def get_energy(self, *, user_id: str) -> Dict[str, Any]:
        """Return simple aggregated energy (sum of readings for user's devices)."""

        devices_res = (
            self.supabase.table("device")
            .select("device_id")
            .eq("user_id", user_id)
            .execute()
        )

        device_rows = getattr(devices_res, "data", None) or []
        if not device_rows:
            raise ValueError("No devices found")

        device_ids = [d["device_id"] for d in device_rows if d.get("device_id") is not None]
        if not device_ids:
            raise ValueError("No valid device_id found")

        readings_res = (
            self.supabase.table("sensor_data")
            .select("kwh_value, reading_time, device_id")
            .in_("device_id", device_ids)
            .order("reading_time", desc=True)
            .execute()
        )

        readings = getattr(readings_res, "data", None) or []
        if not readings:
            raise ValueError("No energy data found")

        total_kwh = sum(float(r.get("kwh_value") or 0) for r in readings)

        return {
            "user_id": user_id,
            "total_kwh": total_kwh,
            "latest": readings[0],
        }

    # -----------------------------
    # PROFILE (for Shrooq page)
    # -----------------------------
    def get_profile(self, user_id: str) -> dict:
        user = User.get_profile(self.supabase, user_id)
        return user.to_dict()

    def update_profile(self, user_id: str, info: Dict[str, Any]) -> dict:
        user = User.update_profile(self.supabase, user_id, info)
        return user.to_dict()
    # -----------------------------
    # DEVICE MANAGEMENT (DeviceFactory & Device Classes)
    # -----------------------------
    def add_new_device(self, user_id: str, name: str, device_type: str, panel_capacity: float | None = None) -> Dict[str, Any]:
        """
        إضافة جهاز جديد (سواء كان جهاز استهلاك ConsumptionDevice أو إنتاج ProductionDevice)
        """
        res = (
            self.supabase
            .table("device")
            .insert({
                "user_id": user_id,
                "device_name": name,
                "device_type": device_type,  # e.g., 'consumption' or 'production'
                "panel_capacity": panel_capacity,
            })
            .execute()
        )
        return {"status": "device_added", "data": res.data}

    def view_devices(self, user_id: str) -> List[Dict[str, Any]]:
        res = (
            self.supabase
            .table("device")
            .select("*")
            .eq("user_id", user_id)
            .execute()
        )
        return res.data or []

    def delete_device(self, device_id: int) -> Dict[str, Any]:
        """Delete a device by device_id (used by DELETE /devices/{device_id})."""
        res = (
            self.supabase
            .table("device")
            .delete()
            .eq("device_id", int(device_id))
            .execute()
        )
        return {"status": "device_deleted", "data": res.data}

    # -----------------------------
    # ENERGY MONITORING (EnergyCalculation Class)
    # -----------------------------
    def view_energy_energy_calculation(self, user_id: str) -> Dict[str, Any]:
        """
        حسب التقرير، كلاس EnergyCalculation يقوم بحساب:
        total consumption, total production, cost savings, and carbon reduction.
        """
        devices = (
            supabase
            .table("device")
            .select("device_id, device_type")
            .eq("user_id", user_id)
            .execute()
        ).data or []

        if not devices:
            return {
                "total_consumption_kwh": 0, 
                "total_production_kwh": 0, 
                "cost_savings_sar": 0,
                "carbon_reduction_percent": 0
            }

        device_ids = [d["device_id"] for d in devices]
        
        # جلب القراءات (SensorDataReading)
        readings = (
            supabase
            .table("sensor_data")
            .select("device_id, kwh_value, reading_time")
            .in_("device_id", device_ids)
            .order("reading_time", desc=True)
            .execute()
        ).data or []

        # فصل حسابات الاستهلاك والإنتاج
        consumption_ids = [d["device_id"] for d in devices if d["device_type"] == "consumption"]
        production_ids = [d["device_id"] for d in devices if d["device_type"] == "production"]

        total_consumption = sum(r["kwh_value"] for r in readings if r["device_id"] in consumption_ids)
        total_production = sum(r["kwh_value"] for r in readings if r["device_id"] in production_ids)

        # حساب التوفير المالي (الإنتاج المستفاد منه * التعرفة الأساسية)
        cost_savings = total_production * 0.18 
        
        # نسبة تقليل الكربون (عملية حسابية تقريبية كمثال بناءً على متطلبات النظام)
        carbon_reduction_percent = (total_production / total_consumption * 100) if total_consumption > 0 else 0

        return {
            "user_id": user_id,
            "total_consumption_kwh": round(total_consumption, 2),
            "total_production_kwh": round(total_production, 2),
            "cost_savings_sar": round(cost_savings, 2),
            "carbon_reduction_percent": round(carbon_reduction_percent, 2),
            "latest_reading": readings[0] if readings else None
        }

    # -----------------------------
    # BILL PREDICTION
    # -----------------------------
    def set_bill_limit(self, user_id: str, limit: int) -> Dict[str, Any]:
        bill_manager = BillPrediction(
            strategy=Tariff018Strategy(),
            limit_id=0,
            actual_bill=0.0,
            predicted_bill=0.0,
            user_id=user_id,
            set_date=date.today(),
            limit_amount=0.0,
            supabase=self.supabase,
        )
        bill_manager.loadCurrentMonth()
        bill_manager.setLimit(limit)

        return {
            "user_id": user_id,
            "limit_id": bill_manager.limit_id,
            "limit_amount": bill_manager.limit_amount,
            "set_date": bill_manager.set_date.isoformat(),
        }

    def get_my_current_bill(self, user_id: str) -> Dict[str, Any]:
        energy_monitor = EnergyCalculation(
            Energy_id=0,
            date=date.today(),
            total_consumption=0.0,
            total_production=0.0,
            cost_savings=0.0,
            carbon_reduction=0.0,
            user_id=user_id,
            supabase=self.supabase,
        )
        bill_data = energy_monitor.viewSummary()

        bill_manager = BillPrediction(
            strategy=Tariff018Strategy(),
            limit_id=0,
            actual_bill=0.0,
            predicted_bill=0.0,
            user_id=user_id,
            set_date=date.today(),
            limit_amount=0.0,
            supabase=self.supabase,
        )
        bill_manager.loadCurrentMonth()
        bill_manager.updatePrediction(bill_data)

        warning_status = bill_manager.compareActualWithPredicted()

        if warning_status == 1:
            notification = Notification(
                notification_id=0,
                content="",
                notification_type="bill_warning",
                timestamp=datetime.utcnow(),
                user_id=user_id,
                supabase=self.supabase,
            )
            notification.setContent(
                f"Your predicted bill ({bill_manager.predicted_bill} SAR) may exceed your limit ({bill_manager.limit_amount} SAR)."
            )
            notification.sendNotification()

        return {
    "user_id": user_id,
    "limit_id": bill_manager.limit_id,
    "limit_amount": bill_manager.limit_amount,
    "actual_bill": bill_manager.actual_bill,
    "predicted_bill": bill_manager.predicted_bill,
    "set_date": bill_manager.set_date.isoformat(),
    "tariff_strategy": bill_manager.strategy.__class__.__name__,
    "limit_warning": True if warning_status == 1 else False,
    "current_usage_kwh": bill_manager.actual_usage_kwh,
    "predicted_usage_kwh": bill_manager.predicted_usage_kwh,
    "days_passed": bill_data.get("days_passed", 0),
    "days_in_month": bill_data.get("days_in_month", 30),
    "forecast_available": bill_data.get("days_passed", 0) >= 7,
}
    # -----------------------------
    # FORECASTING, RECOMMENDATIONS, & NOTIFICATIONS 
    # -----------------------------
    def get_solar_prediction(self, user_id: str) -> Dict[str, Any]:
        """
        يستخدم الـ SolarForecast و ForecastModel لجلب تنبؤات الطاقة الشمسية السنوية 
        ومستوى الثقة (confidence level).
        """
        res = (
            supabase
            .table("solar_forecast")
            .select("predicted_production_kwh, confidence_level, forecast_year")
            .eq("user_id", user_id)
            .order("forecast_year", desc=True)
            .limit(1)
            .execute()
        )
        if res.data:
            return res.data[0]
        return {"message": "No solar prediction available for this user yet."}

    def view_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        الـ Recommendation class يخزن نص التوصية (recommendation_text)، وقت إنشائها (creation_time)، و id المستخدم.
        """
        res = (
            supabase
            .table("recommendation")
            .select("recommendation_text, creation_time")
            .eq("user_id", user_id)
            .order("creation_time", desc=True)
            .execute()
        )
        return res.data or []

    def get_notifications(self, user_id: str) -> List[Dict[str, Any]]:

        """
        الـ Notification class يخزن محتوى الإشعار (content)، نوعه (type)، وقته (time).
        """
        res = (
            supabase
            .table("notification")
            .select("content, type, time")
            .eq("user_id", user_id)
            .order("time", desc=True)
            .execute()
        )
        return res.data or []
  
