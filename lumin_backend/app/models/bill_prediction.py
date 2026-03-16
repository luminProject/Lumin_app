from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType
from typing import Protocol, Any


class BillCalculationStrategy(Protocol):
    def calculateBill(self, consumption: float) -> float: ...


@dataclass
class Tariff018Strategy:
    TARIFF_RATE: float = 0.18

    def calculateBill(self, consumption: float) -> float:
        return round(float(consumption) * float(self.TARIFF_RATE), 2)


@dataclass
class Tariff030Strategy:
    TARIFF_RATE: float = 0.30

    def calculateBill(self, consumption: float) -> float:
        return round(float(consumption) * float(self.TARIFF_RATE), 2)


@dataclass
class BillPrediction:
    strategy: BillCalculationStrategy
    limit_id: int
    actual_bill: float
    predicted_bill: float
    user_id: str
    set_date: DateType
    limit_amount: float
    actual_usage_kwh: float = 0.0
    predicted_usage_kwh: float = 0.0
    supabase: Any = None

    @classmethod
    def BillPrediction(cls, strategy: BillCalculationStrategy) -> "BillPrediction":
        return cls(
            strategy=strategy,
            limit_id=0,
            actual_bill=0.0,
            predicted_bill=0.0,
            user_id="",
            set_date=DateType.today(),
            limit_amount=0.0,
            actual_usage_kwh=0.0,
            predicted_usage_kwh=0.0,
            supabase=None,
        )

    def setStrategy(self, strategy: BillCalculationStrategy) -> None:
        self.strategy = strategy
        return None

    def executeStrategy(self, consumption: float) -> float:
        return float(self.strategy.calculateBill(consumption))

    def _get_current_month_row(self):
        if self.supabase is None:
            return None

        today = DateType.today()
        month_start = today.replace(day=1).isoformat()

        if today.month == 12:
            next_month_start = DateType(today.year + 1, 1, 1).isoformat()
        else:
            next_month_start = DateType(today.year, today.month + 1, 1).isoformat()

        rows = (
            self.supabase
            .table("billprediction")
            .select("limit_id, limit_amount, actual_bill, predicted_bill, set_date")
            .eq("user_id", self.user_id)
            .gte("set_date", month_start)
            .lt("set_date", next_month_start)
            .order("set_date", desc=True)
            .limit(1)
            .execute()
        ).data or []

        return rows[0] if rows else None

    def loadCurrentMonth(self) -> None:
        row = self._get_current_month_row()
        if not row:
            return

        self.limit_id = int(row.get("limit_id") or 0)
        self.limit_amount = float(row["limit_amount"]) if row.get("limit_amount") is not None else 0.0
        self.actual_bill = float(row["actual_bill"]) if row.get("actual_bill") is not None else 0.0
        self.predicted_bill = float(row["predicted_bill"]) if row.get("predicted_bill") is not None else 0.0

        row_date = row.get("set_date")
        if row_date:
            try:
                self.set_date = DateType.fromisoformat(str(row_date))
            except ValueError:
                self.set_date = DateType.today()

    def setLimit(self, limit: int) -> None:
        self.limit_amount = float(limit)
        self.set_date = DateType.today()

        if self.supabase is None:
            return None

        current_month_row = self._get_current_month_row()

        if current_month_row:
            self.limit_id = int(current_month_row.get("limit_id") or 0)
            (
                self.supabase
                .table("billprediction")
                .update({
                    "limit_amount": self.limit_amount,
                    "set_date": self.set_date.isoformat(),
                })
                .eq("limit_id", self.limit_id)
                .execute()
            )
        else:
            result = (
                self.supabase
                .table("billprediction")
                .insert({
                    "user_id": self.user_id,
                    "limit_amount": self.limit_amount,
                    "actual_bill": self.actual_bill,
                    "predicted_bill": self.predicted_bill,
                    "set_date": self.set_date.isoformat(),
                    "tariff_strategy": self.strategy.__class__.__name__,
                })
                .execute()
            )

            data = getattr(result, "data", None) or []
            if data:
                self.limit_id = int(data[0].get("limit_id") or 0)

        return None

    def compareActualWithPredicted(self) -> int:
        if not self.limit_amount:
            return 0

        if self.predicted_bill >= self.limit_amount:
            return 1
        return 0

    def updatePrediction(self, bill_data) -> None:
        if not isinstance(bill_data, dict):
            return None

        self.actual_usage_kwh = float(bill_data.get("current_usage_kwh") or 0)
        daily_net_values = bill_data.get("daily_net_values") or []
        days_in_month = int(bill_data.get("days_in_month") or 30)
        days_passed = int(bill_data.get("days_passed") or 0)

        self.actual_bill = float(self.calculateBill(self.actual_usage_kwh))

        if days_passed < 7 or len(daily_net_values) < 7:
            self.predicted_usage_kwh = 0.0
            self.predicted_bill = 0.0
            self.set_date = DateType.today()
        else:
            window = daily_net_values[-7:]
            sma_daily = sum(window) / 7
            remaining_days = max(days_in_month - days_passed, 0)
            predicted_remaining = sma_daily * remaining_days
            self.predicted_usage_kwh = round(self.actual_usage_kwh + predicted_remaining, 2)
            self.predicted_bill = float(self.calculateBill(self.predicted_usage_kwh))
            self.set_date = DateType.today()

        if self.supabase is None:
            return None

        current_month_row = self._get_current_month_row()

        if current_month_row:
            self.limit_id = int(current_month_row.get("limit_id") or 0)

            if current_month_row.get("limit_amount") is not None:
                self.limit_amount = float(current_month_row["limit_amount"])

            (
                self.supabase
                .table("billprediction")
                .update({
                    "actual_bill": self.actual_bill,
                    "predicted_bill": self.predicted_bill,
                    "set_date": self.set_date.isoformat(),
                    "tariff_strategy": self.strategy.__class__.__name__,
                })
                .eq("limit_id", self.limit_id)
                .execute()
            )
        else:
            result = (
                self.supabase
                .table("billprediction")
                .insert({
                    "user_id": self.user_id,
                    "limit_amount": self.limit_amount if self.limit_amount else None,
                    "actual_bill": self.actual_bill,
                    "predicted_bill": self.predicted_bill,
                    "set_date": self.set_date.isoformat(),
                    "tariff_strategy": self.strategy.__class__.__name__,
                })
                .execute()
            )

            data = getattr(result, "data", None) or []
            if data:
                self.limit_id = int(data[0].get("limit_id") or 0)

        return None

    def calculateBill(self, consumption: float) -> float:
        consumption = float(consumption)

        if consumption <= 6000:
            self.setStrategy(Tariff018Strategy())
            return float(self.executeStrategy(consumption))

        first_part = Tariff018Strategy().calculateBill(6000)
        second_part = Tariff030Strategy().calculateBill(consumption - 6000)
        self.setStrategy(Tariff030Strategy())
        return float(round(first_part + second_part, 2))