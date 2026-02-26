# lumin_backend/app/models/bill_prediction.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import date as DateType
from typing import Protocol


# --- BillCalculationStrategy (Interface) ---
class BillCalculationStrategy(Protocol):
    # +calculateBill(consumption: double): double
    def calculateBill(self, consumption: float) -> float: ...


# --- Tariff018Strategy ---
@dataclass
class Tariff018Strategy:
    # -TARIFF_RATE: double = 0.18
    TARIFF_RATE: float = 0.18

    # +calculateBill(consumption: double): double
    def calculateBill(self, consumption: float) -> float:
        return float(consumption) * float(self.TARIFF_RATE)


# --- Tariff030Strategy ---
@dataclass
class Tariff030Strategy:
    # -TARIFF_RATE: double = 0.30
    TARIFF_RATE: float = 0.30

    # +calculateBill(consumption: double): double
    def calculateBill(self, consumption: float) -> float:
        return float(consumption) * float(self.TARIFF_RATE)


# --- BillPrediction ---
@dataclass
class BillPrediction:
    # -strategy: BillCalculationStrategy
    strategy: BillCalculationStrategy

    # -limit_id: int
    limit_id: int

    # -actual_bill: float
    actual_bill: float

    # -predicted_bill: float
    predicted_bill: float

    # -user_id: int
    user_id: int

    # -set_date: date
    set_date: DateType

    # -limit_amount: float
    limit_amount: float

    # +BillPrediction(strategy: BillCalculationStrategy): BillPrediction
    # (في بايثون: constructor ضمن dataclass، لكن نضيف classmethod بنفس الاسم في الرسم)
    @classmethod
    def BillPrediction(cls, strategy: BillCalculationStrategy) -> "BillPrediction":
        return cls(
            strategy=strategy,
            limit_id=0,
            actual_bill=0.0,
            predicted_bill=0.0,
            user_id=0,
            set_date=DateType.today(),
            limit_amount=0.0,
        )

    # +setStrategy(strategy: BillCalculationStrategy): void
    def setStrategy(self, strategy: BillCalculationStrategy) -> None:
        self.strategy = strategy
        return None

    # +executeStrategy(consumption: double): double
    def executeStrategy(self, consumption: float) -> float:
        return float(self.strategy.calculateBill(consumption))

    # +setLimit(limit: int): void
    def setLimit(self, limit: int) -> None:
        self.limit_id = int(limit)
        return None

    # +compareActualWithPredicted(): int
    def compareActualWithPredicted(self) -> int:
        # نرجّع int زي الرسم بدون “اختراع”
        # -1 إذا actual < predicted، 0 إذا equal، 1 إذا actual > predicted
        if self.actual_bill < self.predicted_bill:
            return -1
        if self.actual_bill > self.predicted_bill:
            return 1
        return 0

    # +updatePrediction(actualBill: string): void
    def updatePrediction(self, actualBill: str) -> None:
        # الرسم كاتب string، فنحوّله لـ float
        try:
            self.actual_bill = float(actualBill)
        except ValueError:
            # لو نص غير صالح نخليه كما هو (بدون اختراع errors)
            return None
        return None

    # +calculateBill(consumption: double): double
    def calculateBill(self, consumption: float) -> float:
        self.predicted_bill = float(self.executeStrategy(consumption))
        return float(self.predicted_bill)