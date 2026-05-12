

from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models.bill_prediction import BillPrediction, BillValidationError


USER_ID = "test-user-1"


# =========================================================
# Helpers
# =========================================================

def mock_today(monkeypatch, target_module, fixed_date: date) -> None:
    """
    Mock datetime.datetime.now() inside the target module.
    """

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(
                fixed_date.year,
                fixed_date.month,
                fixed_date.day,
                12,
                0,
                0,
                tzinfo=tz,
            )

    monkeypatch.setattr(target_module.datetime, "datetime", FixedDateTime)



# =========================================================
# 1) BillPrediction.setLimit()
# =========================================================

class TestSetLimit:
    """
    Tests bill limit validation.
    """

    def test_valid_limit_is_saved(self):
        bill = BillPrediction(USER_ID)

        bill.setLimit(300)

        assert bill.Get_limit_amount() == 300

    def test_limit_must_not_be_none(self):
        bill = BillPrediction(USER_ID)

        with pytest.raises(BillValidationError):
            bill.setLimit(None)

    def test_limit_must_be_number(self):
        bill = BillPrediction(USER_ID)

        with pytest.raises(BillValidationError):
            bill.setLimit("abc")

    def test_limit_must_be_at_least_10(self):
        bill = BillPrediction(USER_ID)

        with pytest.raises(BillValidationError):
            bill.setLimit(5)

    def test_limit_must_not_exceed_10000(self):
        bill = BillPrediction(USER_ID)

        with pytest.raises(BillValidationError):
            bill.setLimit(10001)


# =========================================================
# 2) BillPrediction.calculateBill()
# =========================================================

class TestCalculateBill:
    """
    Tests bill tariff calculation.
    """

    def test_calculates_first_tariff_tier(self):
        bill = BillPrediction(USER_ID)

        result = bill.calculateBill(1000)

        assert result == 180.0

    def test_calculates_boundary_at_6000_kwh(self):
        bill = BillPrediction(USER_ID)

        result = bill.calculateBill(6000)

        assert result == 1080.0

    def test_calculates_second_tariff_tier_after_6000_kwh(self):
        bill = BillPrediction(USER_ID)

        result = bill.calculateBill(7000)

        assert result == 1380.0

    def test_negative_consumption_is_treated_as_zero(self):
        bill = BillPrediction(USER_ID)

        result = bill.calculateBill(-50)

        assert result == 0.0

    def test_invalid_consumption_raises_error(self):
        bill = BillPrediction(USER_ID)

        with pytest.raises(BillValidationError):
            bill.calculateBill("wrong")


# =========================================================
# 3) BillPrediction.PredictBill()
# =========================================================
class TestPredictBill:
    """
    Tests SMA-7 bill prediction and checkpoint behavior.
    """

    def test_no_prediction_before_day_7(self, monkeypatch):
        import app.models.bill_prediction as bill_module

        cycle_start = date(2026, 5, 1)
        mock_today(monkeypatch, bill_module, date(2026, 5, 7))

        bill = BillPrediction(USER_ID)

        bill.load_and_sync_state(
            {"limit_amount": 300},
            {"current_usage_kwh": 60},
            cycle_start,
        )

        usage_data = {
            "daily_dates": [
                "2026-05-01",
                "2026-05-02",
                "2026-05-03",
                "2026-05-04",
                "2026-05-05",
                "2026-05-06",
            ],
            "daily_net_values": [10, 10, 10, 10, 10, 10],
            "current_usage_kwh": 60,
        }

        checkpoint = bill.PredictBill(usage_data)

        assert checkpoint is None
        assert bill.to_dict()["forecast_available"] is False

    def test_day_7_prediction_is_calculated_when_7_days_exist(self, monkeypatch):
        import app.models.bill_prediction as bill_module

        cycle_start = date(2026, 5, 1)
        mock_today(monkeypatch, bill_module, date(2026, 5, 8))

        bill = BillPrediction(USER_ID)

        bill.load_and_sync_state(
            {"limit_amount": 300},
            {"current_usage_kwh": 70},
            cycle_start,
        )

        usage_data = {
            "daily_dates": [
                "2026-05-01",
                "2026-05-02",
                "2026-05-03",
                "2026-05-04",
                "2026-05-05",
                "2026-05-06",
                "2026-05-07",
            ],
            "daily_net_values": [10, 10, 10, 10, 10, 10, 10],
            "current_usage_kwh": 70,
        }

        checkpoint = bill.PredictBill(usage_data)

        result = bill.to_dict()

        assert checkpoint == 7
        assert result["forecast_available"] is True
        assert result["last_checkpoint_day"] == 7
        assert result["predicted_usage_kwh"] == 300.0
        assert result["predicted_bill"] == 54.0

    def test_day_7_requires_complete_first_7_days(self, monkeypatch):
        import app.models.bill_prediction as bill_module

        cycle_start = date(2026, 5, 1)
        mock_today(monkeypatch, bill_module, date(2026, 5, 8))

        bill = BillPrediction(USER_ID)

        bill.load_and_sync_state(
            {"limit_amount": 300},
            {"current_usage_kwh": 60},
            cycle_start,
        )

        usage_data = {
            "daily_dates": [
                "2026-05-01",
                "2026-05-02",
                "2026-05-03",
                "2026-05-04",
                "2026-05-05",
                "2026-05-07",
            ],
            "daily_net_values": [10, 10, 10, 10, 10, 10],
            "current_usage_kwh": 60,
        }

        checkpoint = bill.PredictBill(usage_data)

        assert checkpoint is None
        assert bill.to_dict()["forecast_available"] is False

    def test_checkpoint_is_not_repeated(self, monkeypatch):
        import app.models.bill_prediction as bill_module

        cycle_start = date(2026, 5, 1)
        mock_today(monkeypatch, bill_module, date(2026, 5, 8))

        bill = BillPrediction(USER_ID)

        bill.load_and_sync_state(
            {
                "limit_amount": 300,
                "last_checkpoint_day": 7,
                "forecast_available": True,
                "predicted_usage_kwh": 300,
                "predicted_bill": 54,
            },
            {"current_usage_kwh": 70},
            cycle_start,
        )

        usage_data = {
            "daily_dates": [
                "2026-05-01",
                "2026-05-02",
                "2026-05-03",
                "2026-05-04",
                "2026-05-05",
                "2026-05-06",
                "2026-05-07",
            ],
            "daily_net_values": [10, 10, 10, 10, 10, 10, 10],
            "current_usage_kwh": 70,
        }

        checkpoint = bill.PredictBill(usage_data)

        assert checkpoint is None
        assert bill.to_dict()["last_checkpoint_day"] == 7

# =========================================================
# 4) BillPrediction.is_predicted_bill_over_limit()
# =========================================================

class TestBillWarningDecision:
    """
    Tests bill warning decision.
    """

    def test_no_warning_when_limit_is_not_set(self):
        bill = BillPrediction(USER_ID)
        bill.load_and_sync_state(
            {
                "predicted_bill": 400,
                "forecast_available": True,
            },
            {"current_usage_kwh": 100},
            date(2026, 5, 1),
        )

        assert bill.is_predicted_bill_over_limit() == 0

    def test_warning_when_prediction_reaches_limit(self):
        bill = BillPrediction(USER_ID)
        bill.load_and_sync_state(
            {
                "limit_amount": 300,
                "predicted_bill": 310,
                "forecast_available": True,
            },
            {"current_usage_kwh": 100},
            date(2026, 5, 1),
        )

        assert bill.is_predicted_bill_over_limit() == 1

    def test_no_warning_when_prediction_below_limit(self):
        bill = BillPrediction(USER_ID)

        bill.load_and_sync_state(
            {
                "limit_amount": 300,
                "predicted_bill": 200,
                "forecast_available": True,
            },
            {"current_usage_kwh": 100},
            date(2026, 5, 1),
        )

        assert bill.is_predicted_bill_over_limit() == 0        