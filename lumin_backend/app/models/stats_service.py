"""
app/services/stats_service.py

StatsService — aggregates energycalculation rows for the Home screen
statistics chart (Week / Month / Year views).

Data source: energycalculation table (via DatabaseManager)
  - solar_production  : float8  — kWh produced by solar panels that day
  - total_consumption : float8  — kWh consumed from the grid that day
  - date              : date    — one row per user per day

Aggregation rules:
  week  — 7 daily points (Sat → Fri), anchor = YYYY-MM-DD (any day in week)
  month — 4 weekly buckets (W1=days 1–7, W2=8–14, W3=15–21, W4=22+),
           anchor = YYYY-MM
  year  — 12 monthly totals (Jan → Dec), anchor = YYYY

Missing days return 0.0 for both series (no data = no production/consumption).
"""

import calendar
from datetime import date, timedelta

from app.core.database_manager import DatabaseManager


class StatsService:
    """Aggregates energycalculation data for the statistics chart."""

    def __init__(self, supabase):
        self.db = DatabaseManager(supabase)

    # ─────────────────────────────────────────
    #  PUBLIC
    # ─────────────────────────────────────────

    def get_stats(self, user_id: str, range_type: str, anchor: str) -> dict:
        """
        Return aggregated chart data for a given range and anchor.

        Parameters
        ----------
        user_id    : str — target user UUID
        range_type : str — "week" | "month" | "year"
        anchor     : str — reference string:
                           week  → YYYY-MM-DD (any day within the week)
                           month → YYYY-MM
                           year  → YYYY

        Returns
        -------
        {
            "range":  str,
            "points": [
                {"x": int, "solar": float, "grid": float, "label": str},
                ...
            ]
        }
        """
        if range_type == "week":
            return self._get_week(user_id, anchor)
        elif range_type == "month":
            return self._get_month(user_id, anchor)
        elif range_type == "year":
            return self._get_year(user_id, anchor)
        else:
            raise ValueError(f"Invalid range_type '{range_type}'. Use week | month | year.")

    # ─────────────────────────────────────────
    #  PRIVATE: range builders
    # ─────────────────────────────────────────

    def _get_week(self, user_id: str, anchor: str) -> dict:
        """7 daily points: Sat(0) → Fri(6)."""
        anchor_date = date.fromisoformat(anchor)

        # Python weekday: Mon=0 … Sat=5, Sun=6
        days_since_sat = (anchor_date.weekday() - 5) % 7
        week_start     = anchor_date - timedelta(days=days_since_sat)
        week_end       = week_start + timedelta(days=6)

        rows    = self.db.get_energy_rows_for_range(user_id, week_start, week_end)
        row_map = {r["date"]: r for r in rows}

        labels = ["Sat", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri"]
        points = []
        for i in range(7):
            d   = week_start + timedelta(days=i)
            row = row_map.get(d.isoformat(), {})
            points.append({
                "x":     i,
                "solar": round(float(row.get("solar_production")  or 0), 2),
                "grid":  round(float(row.get("total_consumption") or 0), 2),
                "label": labels[i],
            })

        return {"range": "week", "points": points}

    def _get_month(self, user_id: str, anchor: str) -> dict:
        """
        4 weekly buckets within a month.
          W1 = days  1 –  7
          W2 = days  8 – 14
          W3 = days 15 – 21
          W4 = days 22 – end
        """
        parts      = anchor.split("-")
        year, mon  = int(parts[0]), int(parts[1])
        first_day  = date(year, mon, 1)
        last_day   = date(year, mon, calendar.monthrange(year, mon)[1])

        rows    = self.db.get_energy_rows_for_range(user_id, first_day, last_day)
        buckets = {i: {"solar": 0.0, "grid": 0.0} for i in range(4)}

        for row in rows:
            day_num  = int(row["date"].split("-")[2])
            week_idx = min((day_num - 1) // 7, 3)
            buckets[week_idx]["solar"] += float(row.get("solar_production")  or 0)
            buckets[week_idx]["grid"]  += float(row.get("total_consumption") or 0)

        points = [
            {
                "x":     i,
                "solar": round(buckets[i]["solar"], 2),
                "grid":  round(buckets[i]["grid"],  2),
                "label": f"W{i + 1}",
            }
            for i in range(4)
        ]

        return {"range": "month", "points": points}

    def _get_year(self, user_id: str, anchor: str) -> dict:
        """12 monthly totals: Jan(0) → Dec(11)."""
        year   = int(anchor)
        start  = date(year, 1,  1)
        end    = date(year, 12, 31)

        rows   = self.db.get_energy_rows_for_range(user_id, start, end)
        months = {m: {"solar": 0.0, "grid": 0.0} for m in range(1, 13)}

        for row in rows:
            m = int(row["date"].split("-")[1])
            months[m]["solar"] += float(row.get("solar_production")  or 0)
            months[m]["grid"]  += float(row.get("total_consumption") or 0)

        labels = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
        points = [
            {
                "x":     i,
                "solar": round(months[i + 1]["solar"], 2),
                "grid":  round(months[i + 1]["grid"],  2),
                "label": labels[i],
            }
            for i in range(12)
        ]

        return {"range": "year", "points": points}