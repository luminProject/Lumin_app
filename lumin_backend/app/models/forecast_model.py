"""
ForecastModel Interface
=======================
Defines the contract that any solar forecasting model must implement.

Per updated class diagram (Change Log Section 3.1 & 3.4):
- loadModel()  replaces  trainModel()   — model is pre-trained offline
- predict(site, month, year)  replaces  predict(weather: WeatherData)
"""

from __future__ import annotations
from typing import List, Protocol, runtime_checkable


@runtime_checkable
class ForecastModel(Protocol):
    """
    <<Interface>> ForecastModel

    Any class that implements this interface can be plugged into
    SolarForecast without changing the rest of the system.
    """

    def loadModel(self) -> None:
        """
        Load the pre-trained model from disk or data file.
        Called once at server startup — NOT at runtime per user request.
        """
        ...

    def predict(self, site: str, month: int, year: int) -> float:
        """
        Return predicted GHI (Wh/m²/day) for a given site, month, and year.

        Parameters
        ----------
        site  : str  — one of the 41 trained site names
        month : int  — 1..12
        year  : int  — 2026, 2027, or 2028

        Returns
        -------
        float — predicted GHI in Wh/m²/day (bias-corrected)
        """
        ...

    def getNearestSite(self, lat: float, lng: float) -> str:
        """
        Map any user coordinate to the nearest of the 41 trained sites
        using Haversine distance.

        Parameters
        ----------
        lat : float — user latitude
        lng : float — user longitude

        Returns
        -------
        str — site name from the trained dataset
        """
        ...