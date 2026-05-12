import pytest
from unittest.mock import MagicMock

from app.core.lumin_facade import LuminFacade, ProfileValidationError


TEST_USER_ID = "test-user-1"


def fake_profile_row():
    return {
        "user_id": TEST_USER_ID,
        "username": "Shorouq Test",
        "phone_number": "+966512345678",
        "location": None,
        "avatar_url": None,
        "energy_source": "Grid only",
        "has_solar_panels": None,
        "latitude": None,
        "longitude": None,
        "last_billing_end_date": "2026-04-30",
    }


@pytest.fixture
def facade():
    mock_supabase = MagicMock()
    facade = LuminFacade(mock_supabase)

    row = fake_profile_row()

    facade.db.get_user_profile_row = MagicMock(return_value=row)
    facade.db.insert_user_profile_row = MagicMock(return_value=row)
    facade.db.update_user_profile_row = MagicMock(return_value=row)

    return facade


def valid_profile_payload():
    return {
        "username": "Shorouq Test",
        "phone_number": "+966512345678",
        "energy_source": "Grid only",
        "has_solar_panels": None,
        "last_billing_end_date": "2026-04-30",
    }


# ══════════════════════════════════════════════════════════════════
# TEST CLASS 1: update_profile — Valid Input
#
# WHAT WE TEST:
#   update_profile() accepts valid profile data.
#
# WHY THIS MATTERS:
#   The profile page must save correct user information without
#   raising validation errors.
# ══════════════════════════════════════════════════════════════════

class TestUpdateProfileValidInput:

    def test_valid_grid_profile_does_not_raise_error(self, facade):
        payload = valid_profile_payload()

        try:
            result = facade.update_profile(TEST_USER_ID, payload)
        except ProfileValidationError:
            pytest.fail("Valid profile payload should not raise ProfileValidationError.")

        assert result["user_id"] == TEST_USER_ID

    def test_valid_solar_profile_does_not_raise_error(self, facade):
        payload = valid_profile_payload()
        payload["energy_source"] = "Grid + Solar"
        payload["has_solar_panels"] = True

        updated_row = fake_profile_row()
        updated_row["energy_source"] = "Grid + Solar"
        updated_row["has_solar_panels"] = True
        facade.db.update_user_profile_row.return_value = updated_row

        try:
            result = facade.update_profile(TEST_USER_ID, payload)
        except ProfileValidationError:
            pytest.fail("Valid solar profile payload should not raise ProfileValidationError.")

        assert result["energy_source"] == "Grid + Solar"
        assert result["has_solar_panels"] is True


# ══════════════════════════════════════════════════════════════════
# TEST CLASS 2: update_profile — Username Validation
#
# WHAT WE TEST:
#   update_profile() rejects invalid usernames.
#
# WHY THIS MATTERS:
#   The system should not save empty or too-short names.
# ══════════════════════════════════════════════════════════════════

class TestUpdateProfileUsernameValidation:

    def test_username_must_be_at_least_3_characters(self, facade):
        payload = valid_profile_payload()
        payload["username"] = "Sh"

        with pytest.raises(ProfileValidationError):
            facade.update_profile(TEST_USER_ID, payload)

    def test_username_spaces_are_rejected(self, facade):
        payload = valid_profile_payload()
        payload["username"] = "   "

        with pytest.raises(ProfileValidationError):
            facade.update_profile(TEST_USER_ID, payload)


# ══════════════════════════════════════════════════════════════════
# TEST CLASS 3: update_profile — Phone Validation
#
# WHAT WE TEST:
#   update_profile() rejects invalid phone numbers.
#
# WHY THIS MATTERS:
#   The phone number must be usable and numeric.
# ══════════════════════════════════════════════════════════════════

class TestUpdateProfilePhoneValidation:

    def test_phone_number_must_not_be_empty(self, facade):
        payload = valid_profile_payload()
        payload["phone_number"] = ""

        with pytest.raises(ProfileValidationError):
            facade.update_profile(TEST_USER_ID, payload)

    def test_phone_number_must_contain_numbers_only(self, facade):
        payload = valid_profile_payload()
        payload["phone_number"] = "+966ABC123"

        with pytest.raises(ProfileValidationError):
            facade.update_profile(TEST_USER_ID, payload)

    def test_phone_number_must_not_be_too_short(self, facade):
        payload = valid_profile_payload()
        payload["phone_number"] = "123"

        with pytest.raises(ProfileValidationError):
            facade.update_profile(TEST_USER_ID, payload)

    def test_phone_number_must_not_be_too_long(self, facade):
        payload = valid_profile_payload()
        payload["phone_number"] = "+96651234567899999"

        with pytest.raises(ProfileValidationError):
            facade.update_profile(TEST_USER_ID, payload)


# ══════════════════════════════════════════════════════════════════
# TEST CLASS 4: update_profile — Energy Source Validation
#
# WHAT WE TEST:
#   update_profile() only accepts supported energy sources.
#
# WHY THIS MATTERS:
#   The bill and solar logic depend on known energy source values.
# ══════════════════════════════════════════════════════════════════

class TestUpdateProfileEnergySourceValidation:

    def test_energy_source_must_be_valid(self, facade):
        payload = valid_profile_payload()
        payload["energy_source"] = "Solar only"

        with pytest.raises(ProfileValidationError):
            facade.update_profile(TEST_USER_ID, payload)


# ══════════════════════════════════════════════════════════════════
# TEST CLASS 5: update_profile — Payload Cleaning
#
# WHAT WE TEST:
#   update_profile() ignores user_id inside the payload.
#
# WHY THIS MATTERS:
#   The user_id must come from the route/session, not from user input.
# ══════════════════════════════════════════════════════════════════

class TestUpdateProfilePayloadCleaning:

    def test_user_id_is_removed_from_payload_before_saving(self, facade):
        payload = valid_profile_payload()
        payload["user_id"] = "wrong-user"

        facade.update_profile(TEST_USER_ID, payload)

        update_payload = facade.db.update_user_profile_row.call_args[0][1]

        assert "user_id" not in update_payload
        