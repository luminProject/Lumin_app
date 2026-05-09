

from app.core.lumin_facade import LuminFacade


class FakeResponse:
    def __init__(self, data):
        self.data = data


class FakeQuery:
    def __init__(self, table_name, supabase):
        self.table_name = table_name
        self.supabase = supabase
        self.operation = None
        self.payload = None
        self.filters = []
        self.select_columns = None

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def select(self, columns):
        self.operation = "select"
        self.select_columns = columns
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def delete(self):
        self.operation = "delete"
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        return self

    def execute(self):
        self.supabase.last_query = self

        if self.operation == "insert":
            return FakeResponse([self.payload])

        if self.operation == "update":
            return FakeResponse([self.payload])

        if self.operation == "delete":
            return FakeResponse([{"deleted": True}])

        if self.operation == "select":
            return FakeResponse(self.supabase.fake_select_data)

        return FakeResponse([])


class FakeSupabase:
    def __init__(self):
        self.last_query = None
        self.fake_select_data = []

    def table(self, table_name):
        return FakeQuery(table_name, self)


def test_add_consumption_device_keeps_room_and_shiftable():
    fake_supabase = FakeSupabase()
    facade = LuminFacade(fake_supabase)

    result = facade.add_new_device(
        user_id="user-123",
        name="Washing Machine",
        device_type="consumption",
        room="Bathroom",
        is_shiftable=True,
    )

    query = fake_supabase.last_query

    assert result["status"] == "device_added"
    assert query.table_name == "device"
    assert query.operation == "insert"

    assert query.payload["user_id"] == "user-123"
    assert query.payload["device_name"] == "Washing Machine"
    assert query.payload["device_type"] == "consumption"
    assert query.payload["room"] == "Bathroom"
    assert query.payload["is_shiftable"] is True


def test_add_production_device_forces_room_none_and_shiftable_false():
    fake_supabase = FakeSupabase()
    facade = LuminFacade(fake_supabase)

    facade.add_new_device(
        user_id="user-123",
        name="Solar Panel",
        device_type="production",
        panel_capacity=500,
        room="Bathroom",
        is_shiftable=True,
    )

    query = fake_supabase.last_query

    assert query.table_name == "device"
    assert query.operation == "insert"

    assert query.payload["device_name"] == "Solar Panel"
    assert query.payload["device_type"] == "production"
    assert query.payload["panel_capacity"] == 500
    assert query.payload["room"] is None
    assert query.payload["is_shiftable"] is False


def test_view_devices_returns_user_devices():
    fake_supabase = FakeSupabase()
    fake_supabase.fake_select_data = [
        {
            "device_id": 1,
            "user_id": "user-123",
            "device_name": "Fridge",
            "device_type": "consumption",
            "room": "Kitchen",
            "consumption": 0,
            "production": 0,
        }
    ]

    facade = LuminFacade(fake_supabase)
    result = facade.view_devices("user-123")

    query = fake_supabase.last_query

    assert query.table_name == "device"
    assert query.operation == "select"
    assert ("user_id", "user-123") in query.filters

    assert len(result) == 1
    assert result[0]["device_name"] == "Fridge"
    assert result[0]["room"] == "Kitchen"


def test_update_consumption_device_sets_room_and_clears_panel_capacity():
    fake_supabase = FakeSupabase()
    facade = LuminFacade(fake_supabase)

    result = facade.update_device_settings(
        device_id=1,
        name="Updated Washer",
        device_type="consumption",
        room="Bathroom",
        panel_capacity=None,
    )

    query = fake_supabase.last_query

    assert result["status"] == "device_updated"
    assert query.table_name == "device"
    assert query.operation == "update"
    assert ("device_id", 1) in query.filters

    assert query.payload["device_name"] == "Updated Washer"
    assert query.payload["device_type"] == "consumption"
    assert query.payload["room"] == "Bathroom"
    assert query.payload["panel_capacity"] is None


def test_update_production_device_sets_panel_capacity_and_clears_room():
    fake_supabase = FakeSupabase()
    facade = LuminFacade(fake_supabase)

    facade.update_device_settings(
        device_id=2,
        name="Updated Solar Panel",
        device_type="production",
        room="Kitchen",
        panel_capacity=1000.0,
    )

    query = fake_supabase.last_query

    assert query.payload["device_name"] == "Updated Solar Panel"
    assert query.payload["device_type"] == "production"
    assert query.payload["room"] is None
    assert query.payload["panel_capacity"] == 1000.0


def test_delete_device_filters_by_device_id():
    fake_supabase = FakeSupabase()
    facade = LuminFacade(fake_supabase)

    result = facade.delete_device(5)

    query = fake_supabase.last_query

    assert result["status"] == "device_deleted"
    assert query.table_name == "device"
    assert query.operation == "delete"
    assert ("device_id", 5) in query.filters


def test_reset_total_energy_for_user_resets_only_that_user():
    fake_supabase = FakeSupabase()
    facade = LuminFacade(fake_supabase)

    result = facade.reset_total_energy_for_user("user-123")

    query = fake_supabase.last_query

    assert result["status"] == "bill_cycle_total_energy_reset_done"
    assert result["user_id"] == "user-123"

    assert query.table_name == "device"
    assert query.operation == "update"
    assert query.payload == {"total_energy": 0}
    assert ("user_id", "user-123") in query.filters