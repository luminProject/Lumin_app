from datetime import date
import datetime
from typing import List, Dict, Any
from app.supabase_client import supabase
from app.models.user import User

from app.models.energy_calculation import EnergyCalculation
from app.models.notification import Notification
from app.models.bill_prediction import BillPrediction
from app.core.database_manager import DatabaseManager
from app.services.device_factory import DeviceFactory
from app.services.notification_service import NotificationService
from app.services.recommendation_service import RecommendationService
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
        self.db = DatabaseManager(supabase_client)
        self.device_factory = DeviceFactory()
        self.recommendation_service = RecommendationService(supabase_client)
        self.notification_service = NotificationService(supabase_client)

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

    def get_device_readings(self, device_id: int) -> List[Dict[str, Any]]:
        """
        Get all sensor readings for a specific device ordered by time (latest first).
        """
        res = (
            self.supabase
            .table("sensor_data")
            .select("device_id, kwh_value, reading_time")
            .eq("device_id", int(device_id))
            .order("reading_time", desc=True)
            .execute()
        )

        return res.data or []

    def get_latest_reading(self, device_id: int) -> Dict[str, Any]:
        """
        Get the latest sensor reading for a specific device.
        """
        res = (
            self.supabase
            .table("sensor_data")
            .select("device_id, kwh_value, reading_time")
            .eq("device_id", int(device_id))
            .order("reading_time", desc=True)
            .limit(1)
            .execute()
        )

        data = res.data or []
        return data[0] if data else {}

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

    def update_device_settings(
        self,
        *,
        device_id: int,
        name: str,
        device_type: str,
        room: str | None = None,
        panel_capacity: str | None = None,
    ) -> Dict[str, Any]:
        """
        Update editable device settings only.
        Does NOT modify created_at.
        - consumption: update device_name and room, panel_capacity -> None
        - production: update device_name and panel_capacity, room -> None
        """
        update_payload = {
            "device_name": name,
            "device_type": device_type,
            "room": None if device_type == "production" else room,
            "panel_capacity": panel_capacity if device_type == "production" else None,
        }

        res = (
            self.supabase
            .table("device")
            .update(update_payload)
            .eq("device_id", int(device_id))
            .execute()
        )
        return {"status": "device_updated", "data": res.data}

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

    def set_bill_limit(self, user_id: str, limit: int | float) -> None:
        current_bill_row = self.db.get_current_month_bill_row(user_id)

        bill_manager = BillPrediction(user_id)
        bill_manager.loadCurrentMonth(current_bill_row)
        bill_manager.setLimit(limit)

        payload = bill_manager.build_db_payload()
        saved_limit_id = self.db.save_current_month_bill(user_id, payload)
        bill_manager.setLimitId(saved_limit_id)

       

    def get_my_current_bill(self, user_id: str) -> Dict[str, Any]:
        """
        GET /bill:
        update current values only
        """
        energy_rows = self.db.get_current_month_energy_rows(user_id)
        current_bill_row = self.db.get_current_month_bill_row(user_id)

        energy_monitor = EnergyCalculation(user_id)
        bill_data = energy_monitor.get_current_month_usage(rows=energy_rows)

        bill_manager = BillPrediction(user_id)
        bill_manager.loadCurrentMonth(current_bill_row)
        bill_manager.syncActualFromBillData(bill_data)

        payload = bill_manager.build_db_payload()
        saved_limit_id = self.db.save_current_month_bill(user_id, payload)
        bill_manager.setLimitId(saved_limit_id)

        return bill_manager.to_dict()

        


    def run_bill_checkpoint_for_user(self, user_id: str, checkpoint_day: int) -> Dict[str, Any]:
        """
        Called by APScheduler.
        Official forecast logic stays inside BillPrediction.
        """

        # 1) get all current month rows
        energy_rows = self.db.get_current_month_energy_rows(user_id)
        current_bill_row = self.db.get_current_month_bill_row(user_id)

        # 2) build cutoff date = end of checkpoint day
        today = DateType.today()
        cutoff_date = today.replace(day=checkpoint_day)

        # 3) keep only rows up to checkpoint day
        filtered_rows = []
        for row in energy_rows:
            row_date = row.get("date")
            if not row_date:
                continue

            row_date_only = DateType.fromisoformat(str(row_date)[:10])

            if row_date_only <= cutoff_date:
                filtered_rows.append(row)

        # 4) build monthly summary only from filtered rows
        energy_monitor = EnergyCalculation(user_id)
        bill_data = energy_monitor.get_current_month_usage(rows=filtered_rows)

        # 5) load current bill state
        bill_manager = BillPrediction(user_id)
        bill_manager.loadCurrentMonth(current_bill_row)

        # 6) run scheduled checkpoint
        bill_manager.runScheduledCheckpoint(
            checkpoint_day=checkpoint_day,
            bill_data=bill_data,
        )

        # 7) optional warning notification
        current_warning = bill_manager.compareActualWithPredicted()

        if current_warning == 1:
            notification = Notification(
                notification_id=0,
                content="",
                notification_type="bill_warning",
                timestamp=datetime.datetime.utcnow(),
                user_id=user_id,
                supabase=self.supabase,
            )
            notification.setContent(
                f"Warning: your predicted bill range ({bill_manager.Get_predicted_bill()} SAR) may exceed your monthly limit ({bill_manager.Get_limit_amount()} SAR)."
            )
            notification.sendNotification()

        # 8) save updated state
        payload = bill_manager.build_db_payload()
        saved_limit_id = self.db.save_current_month_bill(user_id, payload)
        bill_manager.setLimitId(saved_limit_id)

        return bill_manager.to_dict()
    def run_bill_checkpoint_for_all_users(self, checkpoint_day: int) -> Dict[str, Any]:
        if checkpoint_day not in [7, 14, 21, 28]:
            raise ValueError("checkpoint_day must be one of: 7, 14, 21, 28")

        user_ids = self.db.get_users_with_current_month_energy()
        processed_users = 0

        for user_id in user_ids:
            self.run_bill_checkpoint_for_user(user_id, checkpoint_day)
            processed_users += 1

        return {
            "status": "success",
            "checkpoint_day": checkpoint_day,
            "processed_users": processed_users,
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

    # -----------------------------
    # SMART RECOMMENDATIONS & NOTIFICATIONS (Mana's feature)
    # -----------------------------

    def viewRecommendations(self, user_id: str) -> Dict[str, Any]:
        """
        Generate + save recommendation based on user type (Solar or Grid only).
        Automatically creates a notification after generation.
        Called by the scheduler at 3 PM and 7 PM Saudi time.
        """
        result = self.recommendation_service.generate_for_user(user_id)

        # Create notification if recommendation was generated
        if result.get("success") and result.get("recommendation"):
            recommendation_text = result["recommendation"].get("recommendation_text")
            if recommendation_text:
                self.notification_service.create_recommendation_notification(
                    user_id=user_id,
                    recommendation_text=recommendation_text,
                )

        return result

    def getLatestRecommendation(self, user_id: str) -> Dict[str, Any]:
        return self.recommendation_service.get_latest_recommendation(user_id)

    def getAllRecommendations(self, user_id: str) -> Dict[str, Any]:
        return self.recommendation_service.get_all_recommendations(user_id)

    def getNotifications(self, user_id: str) -> Dict[str, Any]:
        return self.notification_service.get_user_notifications(user_id)

    def getLatestNotification(self, user_id: str) -> Dict[str, Any]:
        return self.notification_service.get_latest_notification(user_id)

    # -----------------------------
    # SMART DEVICES (DeviceFactory)
    # -----------------------------

    def getUserDevices(self, user_id: str) -> Dict[str, Any]:
        """
        Fetch all user devices and convert them into objects using DeviceFactory.
        """
        response = (
            self.supabase.table("device")
            .select("*")
            .eq("user_id", user_id)
            .order("device_id")
            .execute()
        )

        rows = response.data or []

        if not rows:
            return {
                "success": True,
                "status": "empty",
                "code": "NO_DEVICES",
                "message": "No devices found for this user.",
                "data": [],
            }

        devices = [self.device_factory.createDevice(row) for row in rows]

        return {
            "success": True,
            "status": "success",
            "code": "DEVICES_FETCHED",
            "message": "Devices fetched successfully.",
            "data": devices,
        }

    def getUserDeviceInfos(self, user_id: str) -> Dict[str, Any]:
        """
        Returns simplified device information for UI/debugging.
        """
        devices_result = self.getUserDevices(user_id)

        if not devices_result["data"]:
            return devices_result

        info_list: List[Dict[str, Any]] = []
        for device in devices_result["data"]:
            info_list.append(
                {
                    "device_id": device.device_id,
                    "device_name": device.device_name,
                    "device_type": device.device_type,
                    "installation_date": (
                        device.installation_date.isoformat()
                        if device.installation_date
                        else None
                    ),
                    "user_id": device.user_id,
                    "device_info": device.getDeviceInfo(),
                }
            )

        return {
            "success": True,
            "status": "success",
            "code": "DEVICE_INFOS_FETCHED",
            "message": "Device information fetched successfully.",
            "data": info_list,
        }