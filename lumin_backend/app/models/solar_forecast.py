"""
SolarForecast
=============
Manages the solar forecasting process for a user.

Per updated class diagram (Change Log Section 3.3 & 3.4):
- monthly_ghi_forecast  replaces  predicted_production_kwh
- bias_corrected        replaces  confidence_level
- getForecastForSite()  replaces  getResult()
- loadModel()           replaces  trainModel()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from app.models.forecast_model import ForecastModel


@dataclass
class SolarForecast:
    """
    Attributes (updated class diagram)
    ------------------------------------
    forecast_id           : int
    monthly_ghi_forecast  : Dict[str, Dict[int, float]]
        { site_name: { month: ghi_value } }
    bias_corrected        : bool
        True when applyBiasCorrection was applied to the raw predictions
    model                 : ForecastModel (optional)
        The XGBoostSolarModel instance injected at construction
    """

    forecast_id: int
    monthly_ghi_forecast: Dict[str, Dict[int, float]] = field(default_factory=dict)
    bias_corrected: bool = False
    model: Optional[ForecastModel] = None

    # ── loadModel ─────────────────────────────────────────────────────────────
    def loadModel(self) -> None:
        """
        Delegate to the injected ForecastModel to load its data.
        Called once at startup — not per user request.
        """
        if self.model is not None:
            self.model.loadModel()

    # ── getForecastForSite ────────────────────────────────────────────────────
    def getForecastForSite(self, site: str, year: int) -> List[float]:
        """
        Return the 12-month GHI forecast list for a given site and year.

        Parameters
        ----------
        site : str  — site name from the 41 trained sites
        year : int  — 2026, 2027, or 2028

        Returns
        -------
        List[float] — 12 values, index 0 = January, index 11 = December
                      Each value is GHI in Wh/m²/day (bias-corrected)
        """
        if self.model is None:
            return [0.0] * 12

        return [self.model.predict(site, month, year) for month in range(1, 13)]

    # ── getAnnualAvg ─────────────────────────────────────────────────────────
    def getAnnualAvg(self, site: str, year: int) -> float:
        """
        Return the annual average GHI (Wh/m²/day) for a site and year.
        Convenience wrapper over getForecastForSite.
        """
        monthly = self.getForecastForSite(site, year)
        if not any(monthly):
            return 0.0
        return round(sum(monthly) / len(monthly), 1)

    # ── getNearestSite ────────────────────────────────────────────────────────
    def getNearestSite(self, lat: float, lng: float) -> str:
        """
        Map user coordinates to the nearest trained site.
        Delegates to the model's getNearestSite (Haversine distance).
        """
        if self.model is None:
            raise RuntimeError("No model loaded — call loadModel() first.")
        return self.model.getNearestSite(lat, lng)