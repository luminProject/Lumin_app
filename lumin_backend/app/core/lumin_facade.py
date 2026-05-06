from datetime import date, datetime as dt, timedelta, timezone
import datetime
from typing import List, Dict, Any
from app.supabase_client import supabase
from app.models.user import User
from zoneinfo import ZoneInfo
from datetime import date as DateType
from app.models.energy_calculation import EnergyCalculation
from app.models.notification import Notification
from app.models.bill_prediction import BillPrediction
from app.models.recommendation import Recommendation
from app.core.database_manager import DatabaseManager
from app.core.fcm_service import FCMService
from app.core.device_factory import DeviceFactory
from app.models.realtime_reading import RealtimeReading, RealtimeSummary

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
    # PROFILE 
    # -----------------------------
    def get_profile(self, user_id: str) -> dict:
        """
        Get user profile.

        Facade handles:
        - reading raw row from DatabaseManager
        - creating default row if missing
        - converting row into User model
        """

        row = self.db.get_user_profile_row(user_id)

        if not row:
            default_row = {
                "user_id": user_id,
                "username": "",
                "phone_number": "",
                "location": None,
                "avatar_url": None,
                "energy_source": "Grid only",
                "has_solar_panels": None,
                "latitude": None,
                "longitude": None,
                "last_billing_end_date": None,
            }

            row = self.db.insert_user_profile_row(default_row)

        user = User(**row)
        return user.to_dict()

    def update_profile(self, user_id: str, info: Dict[str, Any]) -> dict:
        """
        Update user profile.

        Facade handles profile business rules.
        DatabaseManager only performs read/write.
        """

        clean_info = dict(info)
        clean_info.pop("user_id", None)

        if clean_info.get("energy_source") == "Grid only":
            clean_info["has_solar_panels"] = None

        if clean_info.get("last_billing_end_date"):
            selected = clean_info["last_billing_end_date"]

            if isinstance(selected, str):
                selected = DateType.fromisoformat(selected[:10])

            today = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).date()

            if selected > today:
                raise ProfileValidationError(
                    "Billing period end date cannot be in the future."
                )

            if selected < today - timedelta(days=45):
                raise ProfileValidationError(
                    "Billing period end date is too old. Please use a recent bill."
                ) 
            clean_info["last_billing_end_date"] = selected.isoformat()    
        row = self.db.get_user_profile_row(user_id)

        if not row:
            default_row = {
                "user_id": user_id,
                "username": "",
                "phone_number": "",
                "location": None,
                "avatar_url": None,
                "energy_source": "Grid only",
                "has_solar_panels": None,
                "latitude": None,
                "longitude": None,
                "last_billing_end_date": None,
            }

            row = self.db.insert_user_profile_row(default_row)

        if clean_info:
            row = self.db.update_user_profile_row(user_id, clean_info)

        user = User(**row)
        return user.to_dict()
   
   
    # -----------------------------
    # DEVICE MANAGEMENT (DeviceFactory & Device Classes)
    # -----------------------------
    def add_new_device(self, user_id: str, name: str, device_type: str, panel_capacity: float | None = None, room: str | None = None, is_shiftable: bool = False) -> Dict[str, Any]:
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
                "room": room if device_type == "consumption" else None,
                "is_shiftable": is_shiftable if device_type == "consumption" else False,
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

    def _get_current_cycle_dates(self, user_id: str) -> tuple[DateType, DateType]:
        """
        Get current billing cycle dates.

        users.last_billing_end_date = last day included in the previous bill.
        current cycle starts the next day.
        cycle length = 30 days.
        """
        today = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).date()

        last_end = self.db.get_user_last_billing_end_date(user_id)

        if last_end is None:
            raise ValueError(
                "Please set your last billing end date from your latest electricity bill."
            )

        cycle_start = last_end + timedelta(days=1)
        cycle_end = cycle_start + timedelta(days=29)

        # If current stored date is old, move cycle forward.
        # When the bill cycle moves forward, reset device total_energy for the same user
        # so device totals and bill prediction start from the same cycle.
        while today > cycle_end:
            last_end = cycle_end
            self.db.update_user_last_billing_end_date(user_id, last_end)
            self.reset_total_energy_for_user(user_id)

            cycle_start = last_end + timedelta(days=1)
            cycle_end = cycle_start + timedelta(days=29)

        return cycle_start, cycle_end


    # =========================
    # BILL LIMIT
    # =========================
    def set_bill_limit(self, user_id: str, limit: int | float) -> None:
        """
        Set or update the user's bill limit for the current billing cycle.

        Important:
        - Uses the current billing cycle.
        - If the current cycle row exists, it updates it.
        - If not, it carries only limit_amount from the latest old row.
        """
        if not user_id:
            raise ValueError("Your session has expired. Please sign in again.")

        cycle_start, cycle_end = self._get_current_cycle_dates(user_id)

        # Get exact row for current billing cycle.
        current_bill_row = self.db.get_bill_row_by_cycle(user_id, cycle_start)

        # If no current-cycle row exists, carry only limit_amount from latest row.
        # Do NOT carry old prediction/checkpoint data.
        if not current_bill_row:
            latest_bill_row = self.db.get_latest_bill_row(user_id)

            if latest_bill_row:
                current_bill_row = {
                    "limit_amount": latest_bill_row.get("limit_amount"),
                }

        energy_rows = self.db.get_current_cycle_energy_rows(
            user_id,
            cycle_start,
            cycle_end,
        )

        energy_monitor = EnergyCalculation(user_id)
        bill_data = energy_monitor.get_current_month_usage(rows=energy_rows)

        bill_manager = BillPrediction(user_id)
        bill_manager.load_and_sync_state(
            current_bill_row,
            bill_data,
            cycle_start=cycle_start,
        )

        bill_manager.setLimit(limit)

        payload = bill_manager.build_db_payload()
        self.db.save_current_cycle_bill(user_id, payload)


    # =========================
    # BILL GET
    # =========================
    def get_my_current_bill(self, user_id: str) -> Dict[str, Any]:
        """
        GET /bill.

        Responsibilities:
        - Calculate current billing cycle.
        - Sync current usage/current bill.
        - Save or update billprediction row.
        - Return setup_required if billing date is missing.
        """
        try:
            cycle_start, cycle_end = self._get_current_cycle_dates(user_id)

        except ValueError as e:
            return {
                "user_id": user_id,
                "limit_id": 0,
                "limit_amount": None,
                "actual_bill": 0.0,
                "predicted_bill": 0.0,
                "limit_warning": False,
                "current_usage_kwh": 0.0,
                "predicted_usage_kwh": 0.0,
                "forecast_available": False,
                "days_passed": 0,
                "days_in_month": 30,
                "last_checkpoint_day": None,
                "cycle_start": None,
                "setup_required": True,
                "setup_message": str(e),
            }

        energy_rows = self.db.get_current_cycle_energy_rows(
            user_id,
            cycle_start,
            cycle_end,
        )

        # Get exact row for current billing cycle.
        current_bill_row = self.db.get_bill_row_by_cycle(user_id, cycle_start)

        # If no current-cycle row exists, carry only limit_amount from latest row.
        # This prevents old forecast/checkpoint data from leaking into a new cycle.
        if not current_bill_row:
            latest_bill_row = self.db.get_latest_bill_row(user_id)

            if latest_bill_row:
                current_bill_row = {
                    "limit_amount": latest_bill_row.get("limit_amount"),
                }

        energy_monitor = EnergyCalculation(user_id)
        bill_data = energy_monitor.get_current_month_usage(rows=energy_rows)

        bill_manager = BillPrediction(user_id)
        bill_manager.load_and_sync_state(
            current_bill_row,
            bill_data,
            cycle_start=cycle_start,
        )

        payload = bill_manager.build_db_payload()
        
        self.db.save_current_cycle_bill(user_id, payload)

        return bill_manager.to_dict()


    # =========================
    # BILL CHECKPOINT SCHEDULER
    # =========================
    def run_bill_checkpoint_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Called by APScheduler daily.

        Important:
        - Facade only prepares data and sends notification.
        - BillPrediction.PredictBill decides if checkpoint 7/14/21/28 is due.
        - Forecast uses completed days only.
        """
        cycle_start, cycle_end = self._get_current_cycle_dates(user_id)

        energy_rows = self.db.get_current_cycle_energy_rows(
            user_id,
            cycle_start,
            cycle_end,
        )

        # Get exact row for current billing cycle.
        current_bill_row = self.db.get_bill_row_by_cycle(user_id, cycle_start)

        # If no current-cycle row exists, carry only limit_amount from latest row.
        # Do NOT carry predicted_bill, forecast_available, or last_checkpoint_day.
        if not current_bill_row:
            latest_bill_row = self.db.get_latest_bill_row(user_id)

            if latest_bill_row:
                current_bill_row = {
                    "limit_amount": latest_bill_row.get("limit_amount"),
                }

        energy_monitor = EnergyCalculation(user_id)
        bill_data = energy_monitor.get_current_month_usage(rows=energy_rows)

        bill_manager = BillPrediction(user_id)
        bill_manager.load_and_sync_state(
            current_bill_row,
            bill_data,
            cycle_start=cycle_start,
        )

        old_checkpoint = bill_manager.get_last_checkpoint()

        # PredictBill now decides internally whether a checkpoint is due.
        checkpoint_day = bill_manager.PredictBill(bill_data)

        if checkpoint_day is None:
            return bill_manager.to_dict()

        new_checkpoint = bill_manager.get_last_checkpoint()
        # Send notification only once per checkpoint.
        if new_checkpoint == checkpoint_day and old_checkpoint != checkpoint_day:

            if bill_manager.Get_limit_amount() <= 0 :
                payload = bill_manager.build_db_payload()
                self.db.save_current_cycle_bill(user_id, payload)
                return bill_manager.to_dict()
            current_warning = bill_manager.compareActualWithPredicted()

            notification_type = "bill_warning" if current_warning == 1 else "bill_update"

            if checkpoint_day == 28:
                if current_warning == 1:
                    content = (
                        f"Your estimated final bill is {bill_manager.Get_predicted_bill()} SAR, "
                        f"which is above your {bill_manager.Get_limit_amount()} SAR limit."
                    )
                else:
                    content = (
                        f"Your estimated final bill is {bill_manager.Get_predicted_bill()} SAR "
                        f"and is within your {bill_manager.Get_limit_amount()} SAR limit."
                    )
            else:
                if current_warning == 1:
                    content = (
                        f"Your predicted bill is {bill_manager.Get_predicted_bill()} SAR, "
                        f"which may exceed your {bill_manager.Get_limit_amount()} SAR limit. "
                        f"Monitor your usage."
                    )
                else:
                    content = (
                        f"Your predicted bill is {bill_manager.Get_predicted_bill()} SAR "
                        f"and is within your {bill_manager.Get_limit_amount()} SAR limit."
                    )

            notification = Notification(
                notification_id=None,
                user_id=user_id,
                notification_type=notification_type,
                content=content,
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            )
            notification_payload = notification.to_dict()
            self.db.insert_notification(notification_payload)
            fcm_token = self.db.get_user_fcm_token(user_id)

            if fcm_token:
                FCMService.send_push(
                    fcm_token=fcm_token,
                    title="LUMIN Bill Alert",
                    body=content[:100],
                )
        payload = bill_manager.build_db_payload()
        self.db.save_current_cycle_bill(user_id, payload)

        return bill_manager.to_dict()


    def run_bill_checkpoint_for_all_users(self) -> Dict[str, Any]:
        """
        Called by daily scheduler.

        Runs bill checkpoint logic for all users who have energy rows.
        One user failure should not stop the whole scheduler.
        """
        user_ids = self.db.get_users_with_energy()

        processed_users = 0
        skipped_users = 0
        errors: list[dict] = []

        for user_id in user_ids:
            try:
                self.run_bill_checkpoint_for_user(user_id)
                processed_users += 1

            except ValueError as e:
                skipped_users += 1
                errors.append({
                    "user_id": user_id,
                    "reason": str(e),
                })

            except Exception as e:
                skipped_users += 1
                errors.append({
                    "user_id": user_id,
                    "reason": str(e),
                })

        return {
            "status": "success",
            "processed_users": processed_users,
            "skipped_users": skipped_users,
            "errors": errors,
        }
   
   
   

    # -----------------------------
    # BILL CYCLE TOTAL ENERGY RESET
    # -----------------------------
    def reset_total_energy_for_user(self, user_id: str) -> Dict[str, Any]:
        """
        Reset total_energy for one user's devices when their billing cycle advances.
        Historical sensor_data readings are not deleted.
        """
        res = (
            self.supabase
            .table("device")
            .update({"total_energy": 0})
            .eq("user_id", user_id)
            .execute()
        )

        return {
            "status": "bill_cycle_total_energy_reset_done",
            "message": "Device total_energy reset for the new billing cycle.",
            "user_id": user_id,
            "data": res.data or [],
        }

    # -----------------------------
    # FORECASTING, RECOMMENDATIONS, & NOTIFICATIONS 
    # -----------------------------
    # -----------------------------
    # FORECASTING, RECOMMENDATIONS, & NOTIFICATIONS
    # -----------------------------
    def get_solar_prediction(self, user_id: str) -> Dict[str, Any]:
        """
        Solar Forecast — per updated class diagram (Change Log Section 3.3).

        Case 1 — No solar panels (has_solar_panels = False or NULL):
            Returns regional GHI estimate from the pre-built JSON
            based on the user's nearest site (lat/lng from users table).
            Includes estimated monthly production for a 5 kWp reference system.

        Case 2/3 — Has solar panels (has_solar_panels = True):
            Returns the personalized monthly GHI forecast for years 2026-2028,
            stored in solar_forecast table (monthly_ghi_forecast JSONB).
            If no stored forecast exists yet, falls back to regional estimate.
        """
        from app.models.xgboost_solar_model import XGBoostSolarModel
        from app.models.solar_forecast import SolarForecast

        # ── 1. Get user profile (location + solar panel status) ────────────────
        user_res = (
            self.supabase.table("users")
            .select("has_solar_panels, latitude, longitude, location")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not user_res.data:
            raise ValueError("User not found")

        user = user_res.data[0]
        has_panels = user.get("has_solar_panels") or False
        lat = user.get("latitude")
        lng = user.get("longitude")

        # ── 2. Load XGBoost model (reads JSON once) ────────────────────────────
        xgb_model = XGBoostSolarModel()
        xgb_model.loadModel()
        solar_forecast = SolarForecast(forecast_id=0, model=xgb_model)

        # ── 3. Find nearest site from user coordinates ─────────────────────────
        if lat is None or lng is None:
            # Fallback: use Jeddah KAU coordinates if user has no location set
            lat, lng = 21.4858, 39.1925

        nearest_site = xgb_model.getNearestSite(lat, lng)
        site_info    = xgb_model.getSiteInfo(nearest_site)

        # ── CASE 1: No solar panels ────────────────────────────────────────────
        if not has_panels:
            # Return regional GHI + estimated production for 5 kWp reference system
            # Formula: E (kWh/month) = GHI_daily (kWh/m²/day) × PR × P_nom × days
            # PR = 0.78 (Al-Shalabi et al., 2024 — Saudi PR range 77%-84.27%)
            # P_nom = 5.0 kWp (illustrative reference system, not a cited value)
            # Reference: Dobos (2014) PVWatts Version 5 Manual, NREL/TP-6A20-62641

            PR     = 0.78
            P_NOM  = 5.0   # kWp — illustrative only
            DAYS   = 30

            monthly_ghi_2026 = {}
            monthly_production_kwh = {}

            for month in range(1, 13):
                ghi_daily = xgb_model.predict(nearest_site, month, 2026)  # Wh/m²/day
                ghi_kwh   = ghi_daily / 1000                              # kWh/m²/day
                monthly_ghi_2026[str(month)]        = round(ghi_daily, 1)
                monthly_production_kwh[str(month)]  = round(ghi_kwh * PR * P_NOM * DAYS, 1)

            annual_avg_ghi = xgb_model.getAnnualAvgGhi(nearest_site, 2026)

            return {
                "case": "no_panels",
                "nearest_site": nearest_site,
                "cluster": site_info.get("cluster"),
                "annual_avg_ghi_wh_m2_day": annual_avg_ghi,
                "monthly_ghi_2026": monthly_ghi_2026,
                "estimated_monthly_production_kwh": monthly_production_kwh,
                "reference_system_kwp": P_NOM,
                "performance_ratio": PR,
                "note": "Production estimate uses a 5 kWp illustrative system. Actual output depends on installed capacity and site conditions.",
            }

        # ── CASE 2/3: Has solar panels ─────────────────────────────────────────
        # Try to return stored personalized forecast from solar_forecast table
        stored_res = (
            self.supabase.table("solar_forecast")
            .select("forecast_id, season, monthly_ghi_forecast, bias_corrected, is_personalized")
            .eq("user_id", user_id)
            .eq("is_personalized", True)
            .order("forecast_id", desc=True)
            .limit(1)
            .execute()
        )

        if stored_res.data:
            row = stored_res.data[0]
            return {
                "case": "has_panels_with_forecast",
                "nearest_site": nearest_site,
                "cluster": site_info.get("cluster"),
                "season": row.get("season"),
                "monthly_ghi_forecast": row.get("monthly_ghi_forecast"),
                "bias_corrected": row.get("bias_corrected"),
                "is_personalized": True,
            }

        # No stored forecast yet — return full 2026-2028 forecast from JSON
        forecast_2026 = solar_forecast.getForecastForSite(nearest_site, 2026)
        forecast_2027 = solar_forecast.getForecastForSite(nearest_site, 2027)
        forecast_2028 = solar_forecast.getForecastForSite(nearest_site, 2028)

        return {
            "case": "has_panels_no_stored_forecast",
            "nearest_site": nearest_site,
            "cluster": site_info.get("cluster"),
            "bias_corrected": True,
            "is_personalized": False,
            "forecast": {
                "2026": {str(m): v for m, v in enumerate(forecast_2026, 1)},
                "2027": {str(m): v for m, v in enumerate(forecast_2027, 1)},
                "2028": {str(m): v for m, v in enumerate(forecast_2028, 1)},
            },
            "annual_avg_ghi": {
                "2026": xgb_model.getAnnualAvgGhi(nearest_site, 2026),
                "2027": xgb_model.getAnnualAvgGhi(nearest_site, 2027),
                "2028": xgb_model.getAnnualAvgGhi(nearest_site, 2028),
            },
        }

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
            user_profile = self.db.get_user_profile_row(user_id)
            if Recommendation.userHasSolar(user_profile):
                return self._generate_solar_recommendation(user_id)
            # Solar user without solar config → fall back to general
            return self._generate_general_recommendation(user_id)

        # Auto (manual API): decide based on profile
        user_profile = self.db.get_user_profile_row(user_id)
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

    # -----------------------------
    # -----------------------------
    # REAL-TIME MONITORING
    # Pattern: Facade → Model → DatabaseManager
    # -----------------------------

    def ingestRealtimeReading(
        self,
        device_id: int,
        watts: float,
        reading_time_iso: str,
    ) -> Dict[str, Any]:
        """
        Process one live sensor reading.
        Coordinates between RealtimeReading model and DatabaseManager.
        """
        # 1) Get current device row from DB
        device = self.db.get_device_row(device_id)
        if not device:
            return {"success": False, "message": f"Device {device_id} not found."}

        # 2) Build Model — loads state from device row
        reading = RealtimeReading.fromDeviceRow(
            device_row=device,
            watts=watts,
            reading_time_iso=reading_time_iso,
        )

        # 3) Model does all calculations
        reading.process()

        # 4) Persist via DatabaseManager
        self.db.update_device_realtime(device_id, reading.build_db_payload())

        # 5) Return response
        return reading.to_response_dict()

    def getRealtimeData(self, user_id: str) -> Dict[str, Any]:
        """
        Returns cumulative daily energy totals for all user devices.
        Used by the Home page to show:
          - solar_production_kwh  → total_energy_daily of production devices
          - total_consumption_kwh → total_energy_daily of consumption devices
          - grid_kwh              → max(0, consumption - solar)
          - instant_watts         → current live watts per device (for is_on status)
        """
        rows = self.db.get_user_devices_realtime(user_id)

        if not rows:
            return {
                "success": True,
                "status":  "empty",
                "code":    "NO_DEVICES",
                "message": "No devices found for this user.",
                "data": {
                    "solar_production_kwh":  0.0,
                    "total_consumption_kwh": 0.0,
                    "grid_kwh":              0.0,
                    "devices":               [],
                },
            }

        # Use Model for aggregation
        summary = RealtimeSummary(rows)
        summary.compute()

        return summary.to_response_dict()

    def resetDailyEnergy(self) -> None:
        """Reset total_energy_daily for all devices. Called at midnight."""
        self.db.reset_all_daily_energy()


class ProfileValidationError(Exception):
    """Raised when profile input is invalid"""
    pass