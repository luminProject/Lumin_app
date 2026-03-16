from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType
from typing import List, Any
from uuid import UUID
from calendar import monthrange
from app.models.observer import Observer

@dataclass
class EnergyCalculation(Observer):
    # -Energy_id: int
    Energy_id: int

    # -date: Date
    date: DateType

    # -total_consumption: float
    total_consumption: float

    # -total_production: float
    total_production: float

    # -cost_savings: float
    cost_savings: float

    # -carbon_reduction: float
    carbon_reduction: float

    # -user_id: uuid
    user_id: UUID | str

    # -TARIF : double[] [2] = {0.18,0.30}
    TARIF: List[float] | None = None

    # ربط Supabase
    supabase: Any = None

    def __post_init__(self):
        if self.TARIF is None:
            self.TARIF = [0.18, 0.30]

    # +calculateEnergy():void
    def calculateEnergy(self) -> None:
        self.calculateCarbonReduction()
        self.cost_savings = float(self.calculateCostSavings())
        return None

    # +getEnergyId():int
    def getEnergyId(self) -> int:
        return int(self.Energy_id)

    # +calculateCostSavings():float
    def calculateCostSavings(self) -> float:
        return float(self.cost_savings)

    # +calculateCarbonReduction():void
    def calculateCarbonReduction(self) -> None:
        return None

    # +viewSummary(interval: Duration):void

    def viewSummary(self, interval=None) -> dict:
        if self.supabase is None:
            today = DateType.today()
            days_in_month = monthrange(today.year, today.month)[1]
            return {
                "user_id": str(self.user_id),
                "energy_id": self.Energy_id,
                "date": today.isoformat(),
                "days_passed": 0,
                "days_in_month": days_in_month,
                "daily_net_values": [],
                "current_usage_kwh": 0.0,
            }

        today = DateType.today()
        month_start = today.replace(day=1)

        if today.month == 12:
            next_month_start = DateType(today.year + 1, 1, 1)
        else:
            next_month_start = DateType(today.year, today.month + 1, 1)

        rows = (
            self.supabase
            .table("energycalculation")
            .select("calculation_id, date, total_consumption, solar_production")
            .eq("user_id", str(self.user_id))
            .gte("date", month_start.isoformat())
            .lt("date", next_month_start.isoformat())
            .order("date", desc=False)
            .execute()
        ).data or []

        daily_map = {}
        latest_calculation_id = 0

        for row in rows:
            row_date = row.get("date")
            if not row_date:
                continue

            day_str = str(row_date)[:10]
            daily_consumption = float(row.get("total_consumption") or 0)
            daily_solar = float(row.get("solar_production") or 0)
            daily_grid_consumption = max(daily_consumption - daily_solar, 0)

            daily_map[day_str] = daily_map.get(day_str, 0.0) + daily_grid_consumption
            latest_calculation_id = int(row.get("calculation_id") or latest_calculation_id)

        sorted_days = sorted(daily_map.keys())
        daily_net_values = [round(daily_map[day], 2) for day in sorted_days]
        current_usage_kwh = round(sum(daily_net_values), 2)

        self.Energy_id = latest_calculation_id
        self.total_consumption = current_usage_kwh
        self.total_production = 0.0

        days_in_month = monthrange(today.year, today.month)[1]

        return {
            "user_id": str(self.user_id),
            "energy_id": self.Energy_id,
            "date": today.isoformat(),
            "days_passed": len(sorted_days),
            "days_in_month": days_in_month,
            "daily_net_values": daily_net_values,
            "current_usage_kwh": current_usage_kwh,
        }
    # +displayRealTimeEnergy():void
    def displayRealTimeEnergy(self) -> dict:
        return self.viewSummary(None)

    # +update():void
    def update(self, o=None) -> None:
        self.calculateEnergy()
        return None

    # ميثود عملية مخصصة للبيل
    def getMonthlyBillData(self) -> dict:
        return self.viewSummary(None)
    
    