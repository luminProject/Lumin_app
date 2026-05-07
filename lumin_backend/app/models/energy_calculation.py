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

    # ── viewSummary — Sprint 2 stats chart ────────────────────
    # Already declared in the class diagram as viewSummary(interval: Duration).
    # Delegates to StatsService for aggregation logic.
    # StatsService is an internal implementation detail — not a
    # separate class in the diagram.

    def viewSummary(self, interval: Any = None, anchor: str = None) -> dict:
        """
        Return aggregated energy data for the Home screen statistics chart.

        Parameters
        ----------
        interval : str — "week" | "month" | "year"
                   Maps to the chart tab the user selected.
        anchor   : str — reference string for the time range:
                   week  → YYYY-MM-DD
                   month → YYYY-MM
                   year  → YYYY

        Returns
        -------
        dict with 'range' and 'points' keys for the Flutter chart widget.

        Delegates to StatsService which contains the aggregation logic.
        Called by LuminFacade.get_stats() endpoint.
        """
        if self.supabase is None or interval is None or anchor is None:
            return {}

        # StatsService is used internally — not exposed as a separate class
        from app.services.stats_service import StatsService
        stats = StatsService(self.supabase)
        return stats.get_stats(
            user_id=str(self.user_id),
            range_type=interval,
            anchor=anchor,
        )

    # ── Bill prediction helper ─────────────────────────────────
    # Called by LuminFacade for billing cycle calculations.

    def get_current_month_usage(self, rows: list[dict] | None = None) -> dict:
        """
        Transform raw energy rows into a monthly usage summary for bill prediction.

        Rows are pre-filtered by billing cycle (not calendar month).
        """
        today        = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).date()
        days_in_month = 30

        if not rows:
            return {
                "user_id":           str(self.user_id),
                "energy_id":         self.Energy_id,
                "date":              today.isoformat(),
                "days_in_month":     days_in_month,
                "daily_net_values":  [],
                "daily_dates":       [],
                "current_usage_kwh": 0.0,
            }

        daily_map: dict[str, float] = {}

        for row in rows:
            row_date = row.get("date")
            if not row_date:
                continue

            day_str          = str(row_date)[:10]
            daily_consumption = float(row.get("total_consumption") or 0.0)
            daily_solar       = float(row.get("solar_production")  or 0.0)

            # Net grid usage used by bill prediction
            daily_grid = max(daily_consumption - daily_solar, 0.0)
            daily_map[day_str] = daily_map.get(day_str, 0.0) + daily_grid

        sorted_days       = sorted(daily_map.keys())
        daily_net_values  = [round(daily_map[day], 2) for day in sorted_days]
        current_usage_kwh = round(sum(daily_net_values), 2)

        self.total_consumption = current_usage_kwh

        return {
            "user_id":           str(self.user_id),
            "energy_id":         self.Energy_id,
            "date":              today.isoformat(),
            "days_in_month":     days_in_month,
            "daily_net_values":  daily_net_values,
            "daily_dates":       sorted_days,
            "current_usage_kwh": current_usage_kwh,
        }