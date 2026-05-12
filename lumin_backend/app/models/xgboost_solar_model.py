"""
xgboost_solar_model.py

XGBoostSolarModel — loads and serves GHI predictions from the pre-computed
solar forecast JSON file.

The JSON was exported from the training pipeline with bias correction already
applied (GHI_predicted_corrected). No cluster lookup is needed at runtime —
the nearest of 41 weather stations is resolved via Haversine directly.

Key responsibilities:
  - loadModel()       : load JSON once at startup, keep in memory
  - getNearestSite()  : map user coordinates to nearest of 41 sites (Haversine)
  - predict()         : return GHI (Wh/m²/day) for a given site/month/year
  - getAnnualAvgGhi() : return annual average GHI for a site/year
  - getSiteInfo()     : return lat/lon/cluster metadata for a site

Input data:
  solar_forecast_2026_2028.json — pre-computed, bias-corrected monthly GHI
  values for 41 Saudi weather stations across years 2026–2028.

Training features (reference only, not used at runtime — 15 total):
  Latitude, Longitude, Month_sin, Month_cos, Year,
  Air Temperature, Relative Humidity, Wind Speed At 3M, Wind Direction At 3M,
  Barometric Pressure, Dhi, Dni, Std Dhi, Std Dni, Std Ghi.
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_JSON_PATH = os.path.join(_DATA_DIR, "solar_forecast_2026_2028.json")


@dataclass
class XGBoostSolarModel:
    """
    Serves GHI predictions from the pre-computed JSON forecast file.

    Attributes
    ----------
    model_path : str — path to solar_forecast_2026_2028.json
    """

    model_path:     str  = field(default_factory=lambda: _JSON_PATH)
    _forecast_data: Dict = field(default_factory=dict, repr=False)
    _loaded:        bool = field(default=False,        repr=False)

    # ── loadModel ─────────────────────────────────────────────────────────────
    def loadModel(self) -> None:
        """
        Loads the forecast JSON from disk into memory.

        Input : none
        Output: none — populates _forecast_data and sets _loaded = True

        Processing:
        Reads solar_forecast_2026_2028.json once. All subsequent calls
        to predict(), getNearestSite(), etc. use the in-memory dict.
        JSON values are already bias-corrected — no further adjustment needed.
        Raises FileNotFoundError if the JSON file is missing from app/data/.
        """
        if self._loaded:
            return
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Forecast JSON not found: {self.model_path}\n"
                "Place solar_forecast_2026_2028.json in lumin_backend/app/data/"
            )
        with open(self.model_path, "r", encoding="utf-8") as f:
            self._forecast_data = json.load(f)
        self._loaded = True

    # ── getNearestSite ────────────────────────────────────────────────────────
    def getNearestSite(self, lat: float, lng: float) -> str:
        """
        Maps user coordinates to the nearest of 41 Saudi weather stations.

        Input:
        lat : float — user latitude
        lng : float — user longitude

        Output:
        str — site name key as it appears in the forecast JSON

        Processing:
        Iterates all 41 sites and computes Haversine distance to each.
        Returns the site with the minimum distance. Always returns a result
        since the JSON covers all of Saudi Arabia.
        """
        self._ensure_loaded()
        best_site, best_dist = None, float("inf")
        for site_name, site_data in self._forecast_data.items():
            dist = _haversine(lat, lng, site_data["latitude"], site_data["longitude"])
            if dist < best_dist:
                best_dist = dist
                best_site = site_name
        return best_site or list(self._forecast_data.keys())[0]

    # ── predict ───────────────────────────────────────────────────────────────
    def predict(self, site: str, month: int, year: int) -> float:
        """
        Returns GHI (Wh/m²/day) for a given site, month, and year.

        Input:
        site  : str — one of the 41 site names from the forecast JSON
        month : int — 1–12
        year  : int — 2026, 2027, or 2028

        Output:
        float — GHI in Wh/m²/day (bias-corrected, read directly from JSON)

        Raises:
        ValueError — if site not found or year/month not in JSON range
        """
        self._ensure_loaded()
        site_data = self._forecast_data.get(site)
        if not site_data:
            raise ValueError(f"Site '{site}' not in forecast data.")
        try:
            return float(
                site_data["predictions"][str(year)]["monthly_ghi"][str(month)]
            )
        except KeyError:
            raise ValueError(
                f"No forecast for site={site}, year={year}, month={month}"
            )

    # ── getAnnualAvgGhi ───────────────────────────────────────────────────────
    def getAnnualAvgGhi(self, site: str, year: int) -> float:
        """
        Returns the annual average GHI (Wh/m²/day) for a site and year.

        Input:
        site : str — site name
        year : int — 2026, 2027, or 2028

        Output:
        float — average of the 12 monthly GHI values, rounded to 1 decimal
        """
        monthly = [self.predict(site, m, year) for m in range(1, 13)]
        return round(sum(monthly) / 12, 1)

    # ── getSiteInfo ───────────────────────────────────────────────────────────
    def getSiteInfo(self, site: str) -> Dict:
        """
        Returns location and cluster metadata for a given site.

        Input:
        site : str — site name

        Output:
        {"latitude": float, "longitude": float, "cluster": int}
        """
        self._ensure_loaded()
        d = self._forecast_data.get(site, {})
        return {
            "latitude":  d.get("latitude"),
            "longitude": d.get("longitude"),
            "cluster":   d.get("cluster"),
        }

    # ── _ensure_loaded ────────────────────────────────────────────────────────
    def _ensure_loaded(self) -> None:
        """Load model if not already loaded. Called at the start of every public method."""
        if not self._loaded:
            self.loadModel()


# ── Haversine distance (km) ───────────────────────────────────────────────────
def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two points on Earth (km)."""
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))