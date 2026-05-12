from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType
import datetime
from zoneinfo import ZoneInfo
from typing import Any, List
from uuid import UUID
from app.models.observer import Observer


@dataclass
class EnergyCalculation(Observer):
    """
    EnergyCalculation — per class diagram.

    Responsibilities:
      1. Calculate net energy usage for bill prediction (existing)
      2. Aggregate energy data for the Home screen statistics chart (Sprint 2)
         via viewSummary(interval, anchor) — delegates to StatsService internally.

    Sprint 2 note:
      viewSummary() was already declared in the class diagram.
      StatsService is used here as an internal implementation detail —
      it does not appear as a separate class in the diagram.
      See Change Log v4, Section 3.18.
    """

    # ── Attributes from class diagram ─────────────────────────
    Energy_id:         int
    date:              DateType
    total_consumption: float
    total_production:  float
    cost_savings:      float
    carbon_reduction:  float
    user_id:           UUID | str
    TARIF:             List[float] | None = None

    # supabase — injected when viewSummary (stats chart) is needed.
    # Optional: bill prediction callers pass None.
    supabase: Any = None

    def __init__(self, user_id: str, supabase: Any = None):
        self.Energy_id         = 0
        self.date              = DateType.today()
        self.total_consumption = 0.0
        self.total_production  = 0.0
        self.cost_savings      = 0.0
        self.carbon_reduction  = 0.0
        self.user_id           = user_id
        self.TARIF             = [0.18, 0.30]
        self.supabase          = supabase

    # ── Methods from class diagram ─────────────────────────────

    def calculateEnergy(self) -> None:
        self.calculateCarbonReduction()
        self.cost_savings = float(self.calculateCostSavings())

    def getEnergyId(self) -> int:
        return int(self.Energy_id)

    def calculateCostSavings(self) -> float:
        return float(self.cost_savings)

    def calculateCarbonReduction(self) -> None:
        return None

    def displayRealTimeEnergy(self) -> dict:
        return self.viewSummary(None)

    def update(self, o=None) -> None:
        """Observer pattern — called when device data updates."""
        self.calculateEnergy()

    # ── SOLAR FORECAST — Statistics Chart ─────────────────────────────────────
    # viewSummary() aggregates energycalculation rows for the Home screen chart.
    # Called by the GET /stats/{user_id} endpoint via LuminFacade (not Solar Forecast).
    # Included here because it reads solar_production from the same energycalculation
    # table that Solar Forecast writes to — shared data source.
    # Delegates to StatsService internally (not a separate diagram class).

    def viewSummary(self, interval: Any = None, anchor: str = None) -> dict:
        """
        Returns aggregated solar and grid energy data for the Home screen chart.

            Input:
            interval : str — "week" | "month" | "year"
            anchor   : str — reference string:
                        week  → YYYY-MM-DD (any day in the target week)
                        month → YYYY-MM
                        year  → YYYY

            Output:
            {"range": str, "points": [{x, solar, grid, label}, ...]}
            Returns {} if supabase, interval, or anchor is None.

            Processing:
            Delegates entirely to StatsService.get_stats().
            StatsService reads solar_production and total_consumption from
            the energycalculation table and aggregates by the requested range.
        """
        if self.supabase is None or interval is None or anchor is None:
            return {}

        # StatsService is used internally — not exposed as a separate class
        from app.core.stats_helper import StatsService
        stats = StatsService(self.supabase)
        return stats.get_stats(
            user_id=str(self.user_id),
            range_type=interval,
            anchor=anchor,
        )


    # ── END OF SOLAR FORECAST ──────────────────────────────────────────────────
    
    
    # ── Bill prediction  ─────────────────────────────────
    # Called by LuminFacade for billing cycle calculations.

    def get_cycle_usage_summary (self, energy_rows: list[dict] | None = None) -> dict:
 
        today = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).date()

        if not energy_rows:
            return {
                "user_id": str(self.user_id),
                "energy_id": self.Energy_id,
                "date": today.isoformat(),
                "daily_net_values": [],
                "daily_dates": [],
                "current_usage_kwh": 0.0,
            }

        daily_map: dict[str, float] = {}

        for row in energy_rows:
            row_date = row.get("date")
            if not row_date:
                continue

            day_str = str(row_date)[:10]
            daily_consumption = float(row.get("total_consumption") or 0.0)
            daily_solar = float(row.get("solar_production") or 0.0)

            # Net grid usage used later by bill prediction.
            daily_grid_consumption = max(daily_consumption - daily_solar, 0.0)

            daily_map[day_str] = daily_map.get(day_str, 0.0) + daily_grid_consumption

        sorted_days = sorted(daily_map.keys())
        daily_net_values = [round(daily_map[day], 2) for day in sorted_days]
        current_usage_kwh = round(sum(daily_net_values), 2)

        self.total_consumption = current_usage_kwh

        return {
            "user_id": str(self.user_id),
            "energy_id": self.Energy_id,
            "date": today.isoformat(),
            "daily_net_values": daily_net_values,
            "daily_dates": sorted_days,
            "current_usage_kwh": current_usage_kwh,
        }