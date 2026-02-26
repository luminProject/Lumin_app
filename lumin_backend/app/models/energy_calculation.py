# lumin_backend/app/models/energy_calculation.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType
from typing import List
from uuid import UUID

from app.core.interfaces import Observer


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

    # -user_id: uuid (مطابق لجدول users في Supabase)
    user_id: UUID

    # -TARIF : double[] [2] = {0.18,0.30}
    TARIF: List[float] = None

    def __post_init__(self):
        if self.TARIF is None:
            self.TARIF = [0.18, 0.30]

    # +calculateEnergy():void
    def calculateEnergy(self) -> None:
        # (بدون اختراع معادلات من راسنا) نخليها “تحديث” للقيم لو كانت محسوبة مسبقًا
        # تقدرون لاحقًا تربطونها بمنطق التسعير الحقيقي
        self.calculateCarbonReduction()
        self.cost_savings = float(self.calculateCostSavings())
        return None

    # +getEnergy():int
    def getEnergy(self) -> int:
        # الرسم يقول int — بنرجّع صافي الطاقة بشكل عدد صحيح
        net = (self.total_consumption - self.total_production)
        return int(round(net))

    # +calculateCostSavings():float
    def calculateCostSavings(self) -> float:
        # بدون تفاصيل معادلة بالرسم: نخليها “قيمة محفوظة/محسوبة لاحقًا”
        return float(self.cost_savings)

    # +calculateCarbonReduction():void
    def calculateCarbonReduction(self) -> None:
        # بدون معادلة محددة في الرسم: نخليها قيمة محفوظة/تتحدث لاحقًا
        return None

    # +viewSummary(interval: Duration):void
    def viewSummary(self, interval) -> None:
        # placeholder حسب الرسم (Duration في Python ما عندنا نوع ثابت هنا)
        return None

    # +displayRealTimeEnergy():void
    def displayRealTimeEnergy(self) -> None:
        return None

    # +update():void
    def update(self, o) -> None:
        # Observer update (الرسم كاتب update():void)
        # نخليه يعيد حساب الطاقة وقت وصول تحديث
        self.calculateEnergy()
        return None