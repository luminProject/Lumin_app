from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType, timedelta


from zoneinfo import ZoneInfo
import datetime
@dataclass
class BillPrediction:
    _user_id: str

    _actual_bill: float = 0.0
    _predicted_bill: float = 0.0
    _limit_amount: float = 0.0

    _actual_usage_kwh: float = 0.0
    _predicted_usage_kwh: float = 0.0
    _forecast_available: bool = False

    _days_passed: int = 0
    _days_in_month: int = 30

    _limit_id: int = 0
    _last_checkpoint_day: int | None = None
    _cycle_start: DateType | None = None


    def get_last_checkpoint(self):
        """
        Return last processed checkpoint.

        Used to prevent duplicate notifications.
        """
        return self._last_checkpoint_day

    def Get_predicted_bill(self) -> str:
        """
        Return predicted bill as a display range.

        Example:
        predicted_bill = 250
        returns: "240 - 260"
        """
        min_value = self._predicted_bill - 10
        if min_value < 0:
            min_value = 0

        max_value = self._predicted_bill + 10
        return f"{int(min_value)} - {int(max_value)}"

    def Get_limit_amount(self) -> int:
        """
        Return limit amount for notification messages.
        """
        return int(self._limit_amount)

    def setLimit(self, limit: int | float) -> None:
        """
        Validate and set user bill limit.
        """
        if limit is None:
            raise ValueError("Please enter your monthly bill limit.")

        try:
            limit = float(limit)
        except (TypeError, ValueError):
            raise ValueError("Bill limit must be a number.")

        if limit <= 0:
            raise ValueError("Bill limit must be greater than 0.")
        if limit < 10:
            raise ValueError("Bill limit must be at least 10 SAR.")

        if limit > 10_000:
            raise ValueError("Bill limit cannot exceed 10,000 SAR.")

        self._limit_amount = limit

    def calculateBill(self, consumption: float) -> float:
        """
        Calculate bill using Saudi electricity tariff:
        - 0.18 SAR for the first 6000 kWh
        - 0.30 SAR for usage above 6000 kWh
        """
        consumption = max(float(consumption), 0.0)

        if consumption <= 6000:
            return round(consumption * 0.18, 2)

        first_tier_bill = 6000 * 0.18
        remaining_usage = consumption - 6000
        second_tier_bill = remaining_usage * 0.30

        return round(first_tier_bill + second_tier_bill, 2)

    def PredictBill(self, bill_data: dict | None) -> int | None:
        # =========================
        # 1) VALIDATION
        # =========================

        # If no data is provided OR billing cycle start is missing → cannot proceed
        if bill_data is None or self._cycle_start is None:
            return None

        # Get today's date using Saudi Arabia timezone
        today = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).date()

        # Calculate number of completed days since cycle_start
        # Note: Today is NOT counted (it may be incomplete)
        completed_days = max((today - self._cycle_start).days, 0)

        # Stop if:
        # - No full day has passed
        # - Cycle is already finished
        if completed_days <= 0 or completed_days > self._days_in_month:
            return None

        # Get the last processed checkpoint (to avoid duplicates)
        last_checkpoint = int(self._last_checkpoint_day or 0)

        # =========================
        # 2) DETERMINE CHECKPOINT
        # =========================

        checkpoint_day = None  # No checkpoint selected yet

        # Iterate from highest to lowest checkpoint
        # This ensures we process only the latest missed checkpoint
        for day in (28, 21, 14, 7):
            if completed_days >= day and last_checkpoint < day:
                checkpoint_day = day
                break  # Stop at the first valid checkpoint

        # If no checkpoint is due → exit
        if checkpoint_day is None:
            return None

        # =========================
        # 3) LOAD DATA
        # =========================

        # Extract daily dates from input
        daily_dates = bill_data.get("daily_dates") or []

        # Extract daily net usage values (consumption - solar)
        daily_values = bill_data.get("daily_net_values") or []

        # If missing data → cannot calculate
        if not daily_dates or not daily_values:
            return None

        # Compute actual calendar date of the checkpoint
        checkpoint_date = self._cycle_start + timedelta(days=checkpoint_day - 1)

        # =========================
        # 4) CLEAN & BUILD DAILY MAP
        # =========================

        # Dictionary: {date → total usage for that day}
        daily_by_date: dict[DateType, float] = {}

        for raw_date, raw_value in zip(daily_dates, daily_values):
            try:
                # Convert raw date string to Date object
                row_date = DateType.fromisoformat(str(raw_date)[:10])

                # Convert value to float
                # Replace None with 0
                # Prevent negative values
                value = max(float(raw_value or 0.0), 0.0)

            except Exception:
                # Skip invalid records
                continue

            # Only keep data within the current cycle AND up to checkpoint_date
            if not (self._cycle_start <= row_date <= checkpoint_date):
                continue

            # Aggregate duplicate entries for the same day
            daily_by_date[row_date] = daily_by_date.get(row_date, 0.0) + value

        # If no valid data remains → stop
        if not daily_by_date:
            return None

        # =========================
        # 5) ACTUAL USAGE
        # =========================

        # Calculate total usage from cycle_start until checkpoint_date
        actual_usage_until_checkpoint = round(sum(daily_by_date.values()), 2)

        # =========================
        # 6) SELECT SMA WINDOW
        # =========================

        if checkpoint_day == 7:
            # ---- CASE 1: FIRST CHECKPOINT ----

            # Must have ALL first 7 days (strict requirement)
            required_dates = [
                self._cycle_start + timedelta(days=i)
                for i in range(7)
            ]

            # If any day is missing → do not calculate
            if any(day not in daily_by_date for day in required_dates):
                return None

            sma_dates = required_dates

        else:
            # ---- CASE 2: LATER CHECKPOINTS (14, 21, 28) ----

            # Take last 8 days as a buffer
            # This allows one missing day while still calculating SMA-7
            recent_8_dates = [
                checkpoint_date - timedelta(days=i)
                for i in range(7, -1, -1)
            ]

            # Keep only available dates
            available_dates = [
                day for day in recent_8_dates
                if day in daily_by_date
            ]

            # Require at least 7 available days out of 8
            if len(available_dates) < 7:
                return None

            # Select the latest 7 valid days
            sma_dates = available_dates[-7:]

        # =========================
        # 7) CALCULATE SMA-7
        # =========================

        # Convert selected dates into usage values
        sma_values = [
            daily_by_date[day]
            for day in sma_dates
        ]

        # Safety check: must always be exactly 7 values
        if len(sma_values) != 7:
            return None

        # Compute Simple Moving Average
        sma_7 = sum(sma_values) / 7

        # =========================
        # 8) PREDICTION
        # =========================

        # Remaining days in the billing cycle
        remaining_days = max(self._days_in_month - checkpoint_day, 0)

        # Predict total usage:
        # actual usage + (average × remaining days)
        self._predicted_usage_kwh = round(
            actual_usage_until_checkpoint + (sma_7 * remaining_days),
            2,
        )

        # Convert predicted usage into bill amount
        self._predicted_bill = self.calculateBill(self._predicted_usage_kwh)

        # =========================
        # 9) SAVE STATE
        # =========================

        # Mark forecast as available
        self._forecast_available = True

        # Store checkpoint to avoid recalculating it again
        self._last_checkpoint_day = checkpoint_day

        # =========================
        # 10) RETURN RESULT
        # =========================

        return checkpoint_day
    def compareActualWithPredicted(self) -> int:
        """
        Compare predicted bill with user limit.

        Returns:
        - 1 if predicted bill may exceed limit
        - 0 otherwise
        """
        if self._limit_amount <= 0:
            return 0

        if not self._forecast_available:
            return 0

        return 1 if self._predicted_bill + 10 >= self._limit_amount else 0

    def load_and_sync_state(
        self,
        db_row: dict | None,
        live_data: dict | None = None,
        cycle_start: DateType | None = None,
    ) -> None:
        """
        Load saved DB state and sync current live usage.

        db_row can be:
        - a full billprediction row for current cycle
        - or {"limit_amount": ...} carried from previous cycle
        """

        today = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).date()

        
        self._cycle_start = cycle_start

        # For GET /bill display, include today's current/live usage.
        # This is UI state, not scheduler checkpoint state.
        if self._cycle_start is not None:
            self._days_passed = max((today - self._cycle_start).days + 1, 0)

        if db_row:
            self._limit_id = int(db_row.get("limit_id") or 0)
            self._limit_amount = float(db_row.get("limit_amount") or 0.0)
            self._predicted_bill = float(db_row.get("predicted_bill") or 0.0)
            self._predicted_usage_kwh = float(db_row.get("predicted_usage_kwh") or 0.0)
            self._forecast_available = bool(db_row.get("forecast_available") or False)
            self._last_checkpoint_day = db_row.get("last_checkpoint_day")

            if self._cycle_start is None and db_row.get("cycle_start"):
                self._cycle_start = DateType.fromisoformat(str(db_row.get("cycle_start"))[:10])
                self._days_passed = max((today - self._cycle_start).days + 1, 0)

        if isinstance(live_data, dict):
            self._actual_usage_kwh = float(live_data.get("current_usage_kwh") or 0.0)
            self._actual_bill = self.calculateBill(self._actual_usage_kwh)

    def build_db_payload(self) -> dict:
        """
        Build payload for billprediction table.

        Important:
        - Do not include columns that do not exist in DB.
        - billing_month is intentionally not included.
        """
        return {
            "user_id": self._user_id,
            "limit_amount": self._limit_amount if self._limit_amount > 0 else None,
            "actual_bill": round(self._actual_bill, 2),
            "predicted_bill": round(self._predicted_bill, 2),
            "cycle_start": self._cycle_start.isoformat() if self._cycle_start else None,
            "current_usage_kwh": round(self._actual_usage_kwh, 2),
            "predicted_usage_kwh": round(self._predicted_usage_kwh, 2),
            "forecast_available": self._forecast_available,
            "days_passed": self._days_passed,
            "days_in_month": self._days_in_month,
            "last_checkpoint_day": self._last_checkpoint_day,
        }

    def to_dict(self) -> dict:
        """
        Build response returned to Flutter.
        """
        return {
            "user_id": self._user_id,
            "limit_id": self._limit_id,
            "limit_amount": self._limit_amount if self._limit_amount > 0 else None,
            "actual_bill": round(self._actual_bill, 2),
            "predicted_bill": round(self._predicted_bill, 2),
            "limit_warning": self.compareActualWithPredicted() == 1,
            "current_usage_kwh": round(self._actual_usage_kwh, 2),
            "predicted_usage_kwh": round(self._predicted_usage_kwh, 2),
            "forecast_available": self._forecast_available,
            "days_passed": self._days_passed,
            "days_in_month": self._days_in_month,
            "last_checkpoint_day": self._last_checkpoint_day,
            "cycle_start": self._cycle_start.isoformat() if self._cycle_start else None,
            "setup_required": False,
        }