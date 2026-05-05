"""
XGBoostSolarModel
=================
Concrete implementation of ForecastModel interface.

Per updated class diagram (Change Log Section 3.1):
- Loads solar_forecast_2026_2028.json at startup (loadModel)
- Maps user coordinates to nearest trained site (getNearestSite)
- Returns bias-corrected GHI prediction (predict)
- Bias correction applied per climate cluster and season (applyBiasCorrection)
"""

from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass, field
from typing import Dict, List

_MONTH_TO_SEASON: Dict[int, str] = {
    12: "Winter", 1: "Winter",  2: "Winter",
    3:  "Spring", 4: "Spring",  5: "Spring",
    6:  "Summer", 7: "Summer",  8: "Summer",
    9:  "Autumn", 10: "Autumn", 11: "Autumn",
}

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
_JSON_PATH = os.path.join(_DATA_DIR, "solar_forecast_2026_2028.json")


@dataclass
class XGBoostSolarModel:
    """
    Attributes (updated class diagram)
    ------------------------------------
    model_path       : str
    feature_columns  : List[str]   — 15 features used in training
    bias_corrections : Dict[cluster, Dict[season, float]]
    cluster_map      : Dict[site_name, cluster_name]
    """

    model_path: str = field(default_factory=lambda: _JSON_PATH)

    feature_columns: List[str] = field(default_factory=lambda: [
        "Latitude", "Longitude", "Month_sin", "Month_cos", "Year",
        "Air Temperature", "Relative Humidity", "Wind Speed At 3M",
        "Wind Direction At 3M", "Barometric Pressure (Mb (Hpa Equiv))",
        "Dhi", "Dni",
        "Standard Deviation Dhi", "Standard Deviation Dni", "Standard Deviation Ghi",
    ])

    # Cluster names match exactly what is in solar_forecast_2026_2028.json
    bias_corrections: Dict[str, Dict[str, float]] = field(default_factory=lambda: {
        "South Tropical (C3)":    {"Winter": -0.045, "Spring": -0.030, "Summer": -0.025, "Autumn": -0.035},
        "South Mountainous (C2)": {"Winter": -0.085, "Spring": -0.060, "Summer": -0.055, "Autumn": -0.070},
        "East Coastal (C0)":      {"Winter": -0.038, "Spring": -0.022, "Summer": -0.018, "Autumn": -0.028},
        "East Coastal (C4)":      {"Winter": -0.040, "Spring": -0.025, "Summer": -0.022, "Autumn": -0.030},
        "North Arid (C5)":        {"Winter": -0.042, "Spring": -0.028, "Summer": -0.020, "Autumn": -0.032},
        "Central Arid (C1)":      {"Winter": -0.035, "Spring": -0.020, "Summer": -0.015, "Autumn": -0.025},
    })

    cluster_map: Dict[str, str] = field(default_factory=dict)
    _forecast_data: Dict = field(default_factory=dict, repr=False)
    _loaded: bool = field(default=False, repr=False)

    def loadModel(self) -> None:
        """Load JSON from disk. Called once at server startup."""
        if self._loaded:
            return
        if not os.path.exists(self.model_path):
            raise FileNotFoundError(
                f"Forecast JSON not found: {self.model_path}\n"
                "Place solar_forecast_2026_2028.json in lumin_backend/app/data/"
            )
        with open(self.model_path, "r", encoding="utf-8") as f:
            self._forecast_data = json.load(f)
        for site_name, site_data in self._forecast_data.items():
            self.cluster_map[site_name] = site_data.get("cluster", "Central Arid (C1)")
        self._loaded = True

    def getNearestSite(self, lat: float, lng: float) -> str:
        """Return nearest of 41 sites to given coordinates (Haversine)."""
        self._ensure_loaded()
        best_site, best_dist = None, float("inf")
        for site_name, site_data in self._forecast_data.items():
            dist = _haversine(lat, lng, site_data["latitude"], site_data["longitude"])
            if dist < best_dist:
                best_dist = dist
                best_site = site_name
        return best_site or list(self._forecast_data.keys())[0]

    def predict(self, site: str, month: int, year: int) -> float:
        """Return bias-corrected GHI (Wh/m²/day) for site/month/year."""
        self._ensure_loaded()
        site_data = self._forecast_data.get(site)
        if not site_data:
            raise ValueError(f"Site '{site}' not in forecast data.")
        try:
            raw_ghi = site_data["predictions"][str(year)]["monthly_ghi"][str(month)]
        except KeyError:
            raise ValueError(f"No forecast for site={site}, year={year}, month={month}")
        cluster = self.cluster_map.get(site, "Central Arid (C1)")
        season  = _MONTH_TO_SEASON[month]
        return round(self.applyBiasCorrection(float(raw_ghi), cluster, season), 1)

    def applyBiasCorrection(self, ghi: float, cluster: str, season: str) -> float:
        """corrected = raw / (1 + bias_factor)"""
        bias = self.bias_corrections.get(cluster, {}).get(season, -0.030)
        return ghi / (1.0 + bias)

    def getAnnualAvgGhi(self, site: str, year: int) -> float:
        monthly = [self.predict(site, m, year) for m in range(1, 13)]
        return round(sum(monthly) / 12, 1)

    def getSiteInfo(self, site: str) -> Dict:
        self._ensure_loaded()
        d = self._forecast_data.get(site, {})
        return {"latitude": d.get("latitude"), "longitude": d.get("longitude"), "cluster": d.get("cluster")}

    def _ensure_loaded(self) -> None:
        if not self._loaded:
            self.loadModel()


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlam/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))