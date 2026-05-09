from datetime import timedelta
from unittest.mock import MagicMock
from zoneinfo import ZoneInfo
import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.core.lumin_facade import LuminFacade


client = TestClient(app)


def test_post_consumption_device_endpoint_routes_to_facade(monkeypatch):
    mock_add_new_device = MagicMock(
        return_value={
            "status": "device_added",
            "data": [
                {
                    "device_id": 1,
                    "user_id": "user-123",
                    "device_name": "Washing Machine",
                    "device_type": "consumption",
                    "room": "Bathroom",
                    "is_shiftable": True,
                }
            ],
        }
    )
    monkeypatch.setattr("app.main.facade.add_new_device", mock_add_new_device)

    response = client.post(
        "/devices/user-123",
        json={
            "name": "Washing Machine",
            "device_type": "consumption",
            "room": "Bathroom",
            "is_shiftable": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["status"] == "device_added"

    mock_add_new_device.assert_called_once_with(
        "user-123",
        "Washing Machine",
        "consumption",
        panel_capacity=None,
        room="Bathroom",
        is_shiftable=True,
    )


def test_post_production_device_endpoint_routes_panel_capacity(monkeypatch):
    mock_add_new_device = MagicMock(
        return_value={
            "status": "device_added",
            "data": [
                {
                    "device_id": 2,
                    "user_id": "user-123",
                    "device_name": "Solar Panel",
                    "device_type": "production",
                    "panel_capacity": 500.0,
                    "room": None,
                    "is_shiftable": False,
                }
            ],
        }
    )
    monkeypatch.setattr("app.main.facade.add_new_device", mock_add_new_device)

    response = client.post(
        "/devices/user-123",
        json={
            "name": "Solar Panel",
            "device_type": "production",
            "panel_capacity": 500.0,
            "room": "Bathroom",
            "is_shiftable": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    mock_add_new_device.assert_called_once_with(
        "user-123",
        "Solar Panel",
        "production",
        panel_capacity=500.0,
        room="Bathroom",
        is_shiftable=True,
    )


def test_get_devices_endpoint_returns_user_devices(monkeypatch):
    mock_devices = [
        {
            "device_id": 1,
            "device_name": "Fridge",
            "device_type": "consumption",
            "room": "Kitchen",
            "consumption": 0,
            "production": 0,
            "is_shiftable": False,
        },
        {
            "device_id": 2,
            "device_name": "Solar Panel",
            "device_type": "production",
            "room": None,
            "consumption": 0,
            "production": 500,
            "is_shiftable": False,
        },
    ]
    mock_view_devices = MagicMock(return_value=mock_devices)
    monkeypatch.setattr("app.main.facade.view_devices", mock_view_devices)

    response = client.get("/devices/user-123")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert len(body["data"]) == 2
    assert body["data"][0]["room"] == "Kitchen"
    assert body["data"][1]["production"] == 500

    mock_view_devices.assert_called_once_with("user-123")


def test_patch_consumption_device_endpoint_updates_room(monkeypatch):
    mock_update_device = MagicMock(
        return_value={
            "status": "device_updated",
            "data": [
                {
                    "device_id": 1,
                    "device_name": "Updated Washer",
                    "device_type": "consumption",
                    "room": "Bathroom",
                    "panel_capacity": None,
                }
            ],
        }
    )
    monkeypatch.setattr("app.main.facade.update_device_settings", mock_update_device)

    response = client.patch(
        "/devices/1",
        json={
            "name": "Updated Washer",
            "device_type": "consumption",
            "room": "Bathroom",
            "panel_capacity": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    mock_update_device.assert_called_once_with(
        device_id=1,
        name="Updated Washer",
        device_type="consumption",
        room="Bathroom",
        panel_capacity=None,
    )


def test_patch_production_device_endpoint_updates_panel_capacity(monkeypatch):
    mock_update_device = MagicMock(
        return_value={
            "status": "device_updated",
            "data": [
                {
                    "device_id": 2,
                    "device_name": "Updated Solar Panel",
                    "device_type": "production",
                    "room": None,
                    "panel_capacity": 1000.0,
                }
            ],
        }
    )
    monkeypatch.setattr("app.main.facade.update_device_settings", mock_update_device)

    response = client.patch(
        "/devices/2",
        json={
            "name": "Updated Solar Panel",
            "device_type": "production",
            "room": "Kitchen",
            "panel_capacity": 1000.0,
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "success"

    mock_update_device.assert_called_once_with(
        device_id=2,
        name="Updated Solar Panel",
        device_type="production",
        room="Kitchen",
        panel_capacity=1000.0,
    )


def test_delete_device_endpoint_routes_to_facade(monkeypatch):
    mock_delete_device = MagicMock(
        return_value={
            "status": "device_deleted",
            "device_id": 1,
        }
    )
    monkeypatch.setattr("app.main.facade.delete_device", mock_delete_device)

    response = client.delete("/devices/1")

    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["data"]["device_id"] == 1

    mock_delete_device.assert_called_once_with(1)


class FakeBillingDatabase:
    def __init__(self, last_billing_end_date):
        self.last_billing_end_date = last_billing_end_date
        self.updated_dates = []

    def get_user_last_billing_end_date(self, user_id):
        return self.last_billing_end_date

    def update_user_last_billing_end_date(self, user_id, new_date):
        self.updated_dates.append((user_id, new_date))
        self.last_billing_end_date = new_date


def test_billing_cycle_advancement_triggers_device_energy_reset():
    today = datetime.datetime.now(ZoneInfo("Asia/Riyadh")).date()
    old_last_billing_end_date = today - timedelta(days=35)

    facade = LuminFacade(None)
    facade.db = FakeBillingDatabase(old_last_billing_end_date)
    facade.reset_total_energy_for_user = MagicMock(
        return_value={"status": "bill_cycle_total_energy_reset_done"}
    )

    cycle_start, cycle_end = facade._get_current_cycle_dates("user-123")

    assert facade.db.updated_dates
    facade.reset_total_energy_for_user.assert_called_with("user-123")
    assert cycle_start <= today <= cycle_end