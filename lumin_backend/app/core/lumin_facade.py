from datetime import date, datetime as dt, timedelta, timezone
import datetime
from typing import List, Dict, Any
from app.supabase_client import supabase
from app.models.user import User

from app.models.energy_calculation import EnergyCalculation
from app.models.notification import Notification
from app.models.bill_prediction import BillPrediction
from app.models.recommendation import Recommendation
from app.core.database_manager import DatabaseManager
from app.core.fcm_service import FCMService
from app.core.device_factory import DeviceFactory

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

        # Verify device exists and fetch current energy fields
        device_res = (
            self.supabase.table("device")
            .select("device_id, user_id, device_type, production, consumption, total_energy")
            .eq("device_id", int(device_id))
            .limit(1)
            .execute()
        )

        device_rows = getattr(device_res, "data", None) or []
        if not device_rows:
            raise ValueError("Device not found")

        device = device_rows[0]
        device_type = device.get("device_type")
        if device_type not in {"production", "consumption"}:
            raise ValueError("Invalid device_type for device")

        reading_value = float(kwh_value)
        current_total = float(device.get("total_energy") or 0)
        new_total = current_total + reading_value

        # 1) Save the historical reading
        sensor_row = {
            "device_id": int(device_id),
            "reading_time": reading_time_iso,
            "kwh_value": reading_value,
        }
        sensor_result = self.supabase.table("sensor_data").insert(sensor_row).execute()

        # 2) Update current reading + cumulative total on device
        update_payload = {
            "total_energy": new_total,
        }

        if device_type == "production":
            update_payload["production"] = reading_value
            update_payload["consumption"] = 0
        else:
            update_payload["consumption"] = reading_value
            update_payload["production"] = 0

        device_update_result = (
            self.supabase.table("device")
            .update(update_payload)
            .eq("device_id", int(device_id))
            .execute()
        )

        return {
            "status": "stored",
            "sensor_data": getattr(sensor_result, "data", None),
            "device_update": getattr(device_update_result, "data", None),
            "current_reading": reading_value,
            "new_total_energy": new_total,
            "device_type": device_type,
        }

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
    # Pattern: Facade → Model → DatabaseManager
    # -----------------------------

    def viewRecommendations(self, user_id: str, recommendation_type: str = "auto") -> Dict[str, Any]:
        """
        Generate + save recommendation. Automatically creates a notification + push.

        Scheduler delivery (Saudi time):
          - Solar users:
              * Saturday 3 PM → custom solar recommendation
              * Tuesday  7 PM → general tip
          - Grid-only users:
              * Monday   4 PM → general tip
              * Thursday 8 PM → general tip

        recommendation_type:
          - "solar"   → force solar recommendation
          - "general" → force general recommendation
          - "auto"    → decide based on user type (used for manual API calls)
        """
        # Force general
        if recommendation_type == "general":
            return self._generate_general_recommendation(user_id)

        # Force solar (or auto with solar user)
        if recommendation_type == "solar":
            user_profile = self.db.get_user_profile(user_id)
            if Recommendation.userHasSolar(user_profile):
                return self._generate_solar_recommendation(user_id)
            # Solar user without solar config → fall back to general
            return self._generate_general_recommendation(user_id)

        # Auto (manual API): decide based on profile
        user_profile = self.db.get_user_profile(user_id)
        if Recommendation.userHasSolar(user_profile):
            return self._generate_solar_recommendation(user_id)
        return self._generate_general_recommendation(user_id)

    def _generate_solar_recommendation(self, user_id: str) -> Dict[str, Any]:
        """Generate a solar-based recommendation. Falls back to general if data is missing."""
        end_date = dt.now(timezone.utc)
        start_date = end_date - timedelta(days=7)

        # Get production devices
        production_devices = self.db.get_devices_by_type(user_id, "production")
        if not production_devices:
            return self._generate_general_recommendation(user_id, fallback_reason="NO_PRODUCTION_DEVICES")

        production_device_ids = [d["device_id"] for d in production_devices]

        # Get solar readings for last 7 days
        solar_rows = self.db.get_sensor_rows_for_devices(
            device_ids=production_device_ids,
            start_date=start_date,
            end_date=end_date,
        )
        if not solar_rows:
            return self._generate_general_recommendation(user_id, fallback_reason="NO_SOLAR_READINGS")

        # Get shiftable consumption devices and their readings
        shiftable_devices = self.db.get_shiftable_consumption_devices(user_id)

        device_readings_by_id: Dict[int, List[Dict[str, Any]]] = {}
        if shiftable_devices:
            shiftable_ids = [d["device_id"] for d in shiftable_devices]
            all_device_rows = self.db.get_sensor_rows_for_devices(
                device_ids=shiftable_ids,
                start_date=start_date,
                end_date=end_date,
            )
            for row in all_device_rows:
                did = row.get("device_id")
                if did is not None:
                    device_readings_by_id.setdefault(did, []).append(row)

        # Build recommendation using the Model
        recommendation = Recommendation(user_id=user_id)
        success = recommendation.buildSolarFromReadings(
            solar_rows=solar_rows,
            shiftable_devices=shiftable_devices,
            device_readings_by_id=device_readings_by_id,
        )

        if not success:
            return self._generate_general_recommendation(user_id, fallback_reason="BEST_PERIOD_NOT_FOUND")

        # Save via DatabaseManager
        saved = self.db.insert_recommendation(recommendation.build_db_payload())

        # Send notification + push
        self._send_notification_and_push(user_id, recommendation.recommendation_text)

        response = recommendation.to_response_dict()
        response.update({
            "success": True,
            "status": "success",
            "code": "RECOMMENDATION_GENERATED",
            "message": "Recommendation generated successfully.",
            "user_id": user_id,
            "user_type": "solar",
            "window_days": 7,
            "recommendation": saved,
        })
        return response

    def _generate_general_recommendation(self, user_id: str, fallback_reason: str = None) -> Dict[str, Any]:
        """Pick a random general tip from the database and save it."""
        general_text = self.db.get_random_general_recommendation_text()
        if not general_text:
            return {
                "success": False,
                "status": "empty",
                "code": "NO_GENERAL_RECOMMENDATIONS",
                "message": "No general recommendations found in the database.",
                "user_id": user_id,
                "user_type": "grid_only",
                "recommendation": None,
            }

        # Build via Model
        recommendation = Recommendation(user_id=user_id)
        recommendation.buildFromGeneralText(general_text)

        # Save via DatabaseManager
        saved = self.db.insert_recommendation(recommendation.build_db_payload())

        # Send notification + push
        self._send_notification_and_push(user_id, general_text)

        return {
            "success": True,
            "status": "success",
            "code": "GENERAL_RECOMMENDATION_GENERATED",
            "message": "General recommendation generated successfully.",
            "user_id": user_id,
            "user_type": "grid_only",
            "fallback_reason": fallback_reason,
            "recommendation": saved,
        }

    def _send_notification_and_push(self, user_id: str, recommendation_text: str) -> None:
        """Save a notification to DB and trigger an FCM push if a token exists."""
        notification = Notification.forRecommendation(user_id, recommendation_text)

        # Save via DatabaseManager
        self.db.insert_notification(notification.build_db_payload())

        # Send FCM push (silent on failure)
        try:
            fcm_token = self.db.get_user_fcm_token(user_id)
            if fcm_token:
                FCMService.send_push(
                    fcm_token=fcm_token,
                    title=notification.getPushTitle(),
                    body=notification.getPushBody(),
                )
        except Exception:
            pass

    def getLatestRecommendation(self, user_id: str) -> Dict[str, Any]:
        data = self.db.get_latest_recommendation(user_id)
        if not data:
            return {
                "success": False,
                "status": "empty",
                "code": "NO_RECOMMENDATIONS",
                "message": "No recommendations found for this user.",
                "data": None,
            }
        return {
            "success": True,
            "status": "success",
            "code": "LATEST_RECOMMENDATION_FETCHED",
            "message": "Latest recommendation fetched successfully.",
            "data": data,
        }

    def getAllRecommendations(self, user_id: str) -> Dict[str, Any]:
        data = self.db.get_all_recommendations(user_id)
        return {
            "success": True,
            "status": "success",
            "code": "RECOMMENDATIONS_FETCHED",
            "message": "Recommendations fetched successfully.",
            "data": data,
        }

    def getNotifications(self, user_id: str) -> Dict[str, Any]:
        data = self.db.get_user_notifications(user_id)
        return {
            "success": True,
            "status": "success",
            "code": "NOTIFICATIONS_FETCHED",
            "message": "Notifications fetched successfully." if data else "No notifications found for this user.",
            "data": data,
        }

    def getLatestNotification(self, user_id: str) -> Dict[str, Any]:
        data = self.db.get_latest_notification(user_id)
        if not data:
            return {
                "success": False,
                "status": "empty",
                "code": "NO_NOTIFICATIONS",
                "message": "No notifications found for this user.",
                "data": None,
            }
        return {
            "success": True,
            "status": "success",
            "code": "LATEST_NOTIFICATION_FETCHED",
            "message": "Latest notification fetched successfully.",
            "data": data,
        }

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