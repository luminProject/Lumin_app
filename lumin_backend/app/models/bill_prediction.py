from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType


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
    _billing_month: str | None = None
    _limit_id: int = 0
    _last_checkpoint_day: int | None = None

    def __init__(self, user_id: str):
        self._user_id = user_id
        self._actual_bill = 0.0
        self._predicted_bill = 0.0
        self._limit_amount = 0.0
        self._actual_usage_kwh = 0.0
        self._predicted_usage_kwh = 0.0
        self._forecast_available = False
        self._days_passed = 0
        self._days_in_month = 30
        self._billing_month = DateType.today().replace(day=1).isoformat()
        self._limit_id = 0
        self._last_checkpoint_day = None

    def Get_predicted_bill(self) -> str:
        min_value = self._predicted_bill - 10
        if min_value < 0:
            min_value = self._predicted_bill
        max_value = self._predicted_bill + 10
        return f"{int(min_value)} - {int(max_value)}"

    def Get_limit_amount(self) -> int:
        return int(self._limit_amount)

    def loadCurrentMonth(self, row: dict | None) -> None:
        if not row:
            self._billing_month = DateType.today().replace(day=1).isoformat()
            return

        self._limit_id = int(row.get("limit_id") or 0)
        self._limit_amount = float(row.get("limit_amount") or 0.0)
        self._actual_bill = float(row.get("actual_bill") or 0.0)
        self._predicted_bill = float(row.get("predicted_bill") or 0.0)
        self._actual_usage_kwh = float(row.get("current_usage_kwh") or 0.0)
        self._predicted_usage_kwh = float(row.get("predicted_usage_kwh") or 0.0)
        self._forecast_available = bool(row.get("forecast_available") or False)
        self._days_passed = int(row.get("days_passed") or 0)
        self._days_in_month = int(row.get("days_in_month") or 30)
        self._last_checkpoint_day = (
            int(row["last_checkpoint_day"])
            if row.get("last_checkpoint_day") is not None
            else None
        )
        self._billing_month = (
            row.get("billing_month")
            or DateType.today().replace(day=1).isoformat()
        )

    def setLimit(self, limit: int | float) -> None:
        self._limit_amount = max(float(limit), 0.0)

    def setLimitId(self, limit_id: int) -> None:
        self._limit_id = int(limit_id)

    def calculateBill(self, consumption: float) -> float:
        consumption = max(float(consumption), 0.0)

        if consumption <= 6000:
            return round(consumption * 0.18, 2)

        first_tier_bill = 6000 * 0.18
        remaining_usage = consumption - 6000
        second_tier_bill = remaining_usage * 0.30

        return round(first_tier_bill + second_tier_bill, 2)

    def _resetForecastOnly(self) -> None:
        self._predicted_usage_kwh = 0.0
        self._predicted_bill = 0.0
        self._forecast_available = False

    def syncActualFromBillData(self, bill_data: dict | None) -> None:
        """
        Update current values only.
        """
        if not isinstance(bill_data, dict):
            self._actual_usage_kwh = 0.0
            self._actual_bill = 0.0
            self._days_passed = 0
            self._days_in_month = 30
            self._billing_month = DateType.today().replace(day=1).isoformat()
            return

        daily_values = bill_data.get("daily_net_values") or []
        daily_values = [max(float(v or 0.0), 0.0) for v in daily_values]

        self._days_passed = len(daily_values)
        self._days_in_month = int(bill_data.get("days_in_month") or 30)
        self._billing_month = (
            bill_data.get("billing_month")
            or DateType.today().replace(day=1).isoformat()
        )

        self._actual_usage_kwh = round(
            float(bill_data.get("current_usage_kwh") or 0.0),
            2
        )
        self._actual_bill = self.calculateBill(self._actual_usage_kwh)

    def runScheduledCheckpoint(self, checkpoint_day: int, bill_data: dict | None) -> None:
        """
        Official scheduler-only forecast method.
        """
        valid_checkpoints = [7, 14, 21, 28]
        if checkpoint_day not in valid_checkpoints:
            raise ValueError("checkpoint_day must be one of: 7, 14, 21, 28")

        self.syncActualFromBillData(bill_data)

        if not isinstance(bill_data, dict):
            self._resetForecastOnly()
            return

        daily_values = bill_data.get("daily_net_values") or []
        daily_values = [max(float(v or 0.0), 0.0) for v in daily_values]

        if self._days_passed < 7:
            self._resetForecastOnly()
            return

        if self._days_passed < checkpoint_day:
            return

        if self._last_checkpoint_day == checkpoint_day:
            return

        last_7 = daily_values[-7:]
        if len(last_7) < 7:
            self._resetForecastOnly()
            return

        sma_7 = sum(last_7) / 7
        remaining_days = max(self._days_in_month - checkpoint_day, 0)

        self._predicted_usage_kwh = round(
            self._actual_usage_kwh + (sma_7 * remaining_days),
            2
        )
        self._predicted_bill = self.calculateBill(self._predicted_usage_kwh)
        self._forecast_available = True
        self._last_checkpoint_day = checkpoint_day

    def compareActualWithPredicted(self) -> int:
        if self._limit_amount <= 0:
            return 0

        if not self._forecast_available:
            return 0

        return 1 if self._predicted_bill + 10 >= self._limit_amount else 0

    def build_db_payload(self) -> dict:
        return {
            "user_id": self._user_id,
            "limit_amount": self._limit_amount if self._limit_amount > 0 else None,
            "actual_bill": round(self._actual_bill, 2),
            "predicted_bill": round(self._predicted_bill, 2),
            "billing_month": self._billing_month,
            "current_usage_kwh": round(self._actual_usage_kwh, 2),
            "predicted_usage_kwh": round(self._predicted_usage_kwh, 2),
            "forecast_available": self._forecast_available,
            "days_passed": self._days_passed,
            "days_in_month": self._days_in_month,
            "last_checkpoint_day": self._last_checkpoint_day,
        }

    def to_dict(self) -> dict:
        return {
            "user_id": self._user_id,
            "limit_id": self._limit_id,
            "limit_amount": self._limit_amount if self._limit_amount > 0 else None,
            "actual_bill": round(self._actual_bill, 2),
            "predicted_bill": round(self._predicted_bill, 2),
            "limit_warning": bool(self.compareActualWithPredicted()),
            "current_usage_kwh": round(self._actual_usage_kwh, 2),
            "predicted_usage_kwh": round(self._predicted_usage_kwh, 2),
            "forecast_available": self._forecast_available,
            "days_passed": self._days_passed,
            "days_in_month": self._days_in_month,
            "last_checkpoint_day": self._last_checkpoint_day,
            "billing_month": self._billing_month,
        }