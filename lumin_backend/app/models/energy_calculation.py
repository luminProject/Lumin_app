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

    def __init__(self, user_id: str):
        self.Energy_id = 0
        self.date = DateType.today()
        self.total_consumption = 0.0
        self.total_production = 0.0
        self.cost_savings = 0.0
        self.carbon_reduction = 0.0
        self.user_id = user_id
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
        return None
    # +displayRealTimeEnergy():void
    def displayRealTimeEnergy(self) -> dict:
        return self.viewSummary(None)

    # +update():void
    def update(self, o=None) -> None:
        self.calculateEnergy()
        return None

# +getCurrentMonthUsage(): dict 
# this is the main method that transforms raw energy rows into a clean monthly usage summary for bill prediction.
    def get_current_month_usage(self, rows: list[dict] | None = None) -> dict:
        """
        Business logic only.

        Receives raw monthly energy rows that were already fetched
        by DatabaseManager, then transforms them into a clean monthly
        usage summary ready for bill prediction.
        """
        today = DateType.today()
        billing_month = today.replace(day=1)
        days_in_month = monthrange(today.year, today.month)[1]

        if not rows:
            return {
                "user_id": str(self.user_id),
                "energy_id": self.Energy_id,
                "date": today.isoformat(),
                "billing_month": billing_month.isoformat(),
                "days_passed": 0,
                "days_in_month": days_in_month,
                "daily_net_values": [],
                "current_usage_kwh": 0.0,
            }

        daily_map: dict[str, float] = {}
        latest_calculation_id = 0

        for row in rows:
            row_date = row.get("date")
            if not row_date:
                continue

            day_str = str(row_date)[:10]
            daily_consumption = float(row.get("total_consumption") or 0.0)
            daily_solar = float(row.get("solar_production") or 0.0)

            # Net grid usage used later by bill prediction.
            daily_grid_consumption = max(daily_consumption - daily_solar, 0.0)

            daily_map[day_str] = daily_map.get(day_str, 0.0) + daily_grid_consumption
            latest_calculation_id = int(row.get("calculation_id") or latest_calculation_id)

        sorted_days = sorted(daily_map.keys())
        daily_net_values = [round(daily_map[day], 2) for day in sorted_days]
        current_usage_kwh = round(sum(daily_net_values), 2)

        self.Energy_id = latest_calculation_id
        self.total_consumption = current_usage_kwh
        

        return {
            "user_id": str(self.user_id),
            "energy_id": self.Energy_id,
            "date": today.isoformat(),
            "billing_month": billing_month.isoformat(),
            "days_passed": len(sorted_days),
            "days_in_month": days_in_month,
            "daily_net_values": daily_net_values,
            "current_usage_kwh": current_usage_kwh,
        }
        