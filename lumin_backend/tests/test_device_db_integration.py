

import os
import uuid

import pytest
from dotenv import load_dotenv
from supabase import create_client

from app.core.lumin_facade import LuminFacade


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
TEST_USER_ID = os.getenv("DEVICE_TEST_USER_ID") or os.getenv("TEST_USER_ID")


@pytest.fixture(scope="module")
def supabase_client():
    if not SUPABASE_URL or not (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY):
        pytest.skip("Supabase credentials are not available in the environment.")

    key = SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY
    return create_client(SUPABASE_URL, key)


@pytest.fixture(scope="module")
def test_user_id(supabase_client):
    if not TEST_USER_ID:
        pytest.skip("Set DEVICE_TEST_USER_ID or TEST_USER_ID before running DB integration tests.")

    user_res = (
        supabase_client
        .table("users")
        .select("user_id")
        .eq("user_id", TEST_USER_ID)
        .limit(1)
        .execute()
    )

    if not user_res.data:
        pytest.skip(f"Test user {TEST_USER_ID} was not found in the users table.")

    return TEST_USER_ID


@pytest.fixture
def db_context(supabase_client, test_user_id):
    """
    Provides a real LuminFacade connected to Supabase and removes only the test
    devices created by this test file after each test.
    """
    test_prefix = f"pytest-device-{uuid.uuid4().hex[:8]}"
    facade = LuminFacade(supabase_client)
    created_device_ids = []

    yield facade, supabase_client, test_user_id, test_prefix, created_device_ids

    for device_id in created_device_ids:
        (
            supabase_client
            .table("device")
            .delete()
            .eq("device_id", device_id)
            .execute()
        )

    # Extra safety cleanup by unique generated name prefix.
    (
        supabase_client
        .table("device")
        .delete()
        .eq("user_id", test_user_id)
        .ilike("device_name", f"{test_prefix}%")
        .execute()
    )


def _fetch_device(supabase_client, device_id):
    res = (
        supabase_client
        .table("device")
        .select("*")
        .eq("device_id", device_id)
        .single()
        .execute()
    )
    return res.data


def _remember_created_device(result, created_device_ids):
    assert result["status"] == "device_added"
    assert result["data"]
    device_id = result["data"][0]["device_id"]
    created_device_ids.append(device_id)
    return device_id


def test_db_add_consumption_device_saves_room_and_shiftable(db_context):
    facade, supabase_client, user_id, prefix, created_device_ids = db_context

    result = facade.add_new_device(
        user_id=user_id,
        name=f"{prefix}-washing-machine",
        device_type="consumption",
        room="Bathroom",
        is_shiftable=True,
    )

    device_id = _remember_created_device(result, created_device_ids)
    row = _fetch_device(supabase_client, device_id)

    assert row["user_id"] == user_id
    assert row["device_name"] == f"{prefix}-washing-machine"
    assert row["device_type"] == "consumption"
    assert row["room"] == "Bathroom"
    assert row["is_shiftable"] is True


def test_db_add_production_device_saves_capacity_and_clears_room_shiftable(db_context):
    facade, supabase_client, user_id, prefix, created_device_ids = db_context

    result = facade.add_new_device(
        user_id=user_id,
        name=f"{prefix}-solar-panel",
        device_type="production",
        panel_capacity=500.0,
        room="Kitchen",
        is_shiftable=True,
    )

    device_id = _remember_created_device(result, created_device_ids)
    row = _fetch_device(supabase_client, device_id)

    assert row["user_id"] == user_id
    assert row["device_name"] == f"{prefix}-solar-panel"
    assert row["device_type"] == "production"
    assert float(row["panel_capacity"]) == 500.0
    assert row["room"] is None
    assert row["is_shiftable"] is False


def test_db_view_devices_returns_created_user_devices(db_context):
    facade, supabase_client, user_id, prefix, created_device_ids = db_context

    first = facade.add_new_device(
        user_id=user_id,
        name=f"{prefix}-fridge",
        device_type="consumption",
        room="Kitchen",
        is_shiftable=False,
    )
    second = facade.add_new_device(
        user_id=user_id,
        name=f"{prefix}-solar",
        device_type="production",
        panel_capacity=750.0,
    )

    _remember_created_device(first, created_device_ids)
    _remember_created_device(second, created_device_ids)

    devices = facade.view_devices(user_id)
    names = {device["device_name"] for device in devices}

    assert f"{prefix}-fridge" in names
    assert f"{prefix}-solar" in names


def test_db_update_device_settings_updates_consumption_room(db_context):
    facade, supabase_client, user_id, prefix, created_device_ids = db_context

    result = facade.add_new_device(
        user_id=user_id,
        name=f"{prefix}-old-washer",
        device_type="consumption",
        room="Kitchen",
    )
    device_id = _remember_created_device(result, created_device_ids)

    update_result = facade.update_device_settings(
        device_id=device_id,
        name=f"{prefix}-updated-washer",
        device_type="consumption",
        room="Bathroom",
        panel_capacity=None,
    )

    assert update_result["status"] == "device_updated"

    row = _fetch_device(supabase_client, device_id)
    assert row["device_name"] == f"{prefix}-updated-washer"
    assert row["device_type"] == "consumption"
    assert row["room"] == "Bathroom"
    assert row["panel_capacity"] is None


def test_db_update_device_settings_updates_production_capacity(db_context):
    facade, supabase_client, user_id, prefix, created_device_ids = db_context

    result = facade.add_new_device(
        user_id=user_id,
        name=f"{prefix}-old-panel",
        device_type="production",
        panel_capacity=500.0,
    )
    device_id = _remember_created_device(result, created_device_ids)

    update_result = facade.update_device_settings(
        device_id=device_id,
        name=f"{prefix}-updated-panel",
        device_type="production",
        room="Bathroom",
        panel_capacity=1000.0,
    )

    assert update_result["status"] == "device_updated"

    row = _fetch_device(supabase_client, device_id)
    assert row["device_name"] == f"{prefix}-updated-panel"
    assert row["device_type"] == "production"
    assert row["room"] is None
    assert float(row["panel_capacity"]) == 1000.0


def test_db_reset_total_energy_for_user_filters_by_user(db_context):
    facade, supabase_client, user_id, prefix, created_device_ids = db_context

    result = facade.add_new_device(
        user_id=user_id,
        name=f"{prefix}-reset-device",
        device_type="consumption",
        room="Living Room",
    )
    device_id = _remember_created_device(result, created_device_ids)

    reset_result = facade.reset_total_energy_for_user(user_id)

    assert reset_result["status"] == "bill_cycle_total_energy_reset_done"
    assert reset_result["user_id"] == user_id

    row = _fetch_device(supabase_client, device_id)
    assert float(row.get("total_energy") or 0) == 0.0


def test_db_delete_device_removes_device_from_supabase(db_context):
    facade, supabase_client, user_id, prefix, created_device_ids = db_context

    result = facade.add_new_device(
        user_id=user_id,
        name=f"{prefix}-delete-device",
        device_type="consumption",
        room="Bedroom",
    )
    device_id = _remember_created_device(result, created_device_ids)

    delete_result = facade.delete_device(device_id)

    assert delete_result["status"] == "device_deleted"

    # The device has already been deleted, so remove it from fixture cleanup list.
    created_device_ids.remove(device_id)

    res = (
        supabase_client
        .table("device")
        .select("device_id")
        .eq("device_id", device_id)
        .execute()
    )

    assert res.data == []