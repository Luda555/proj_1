import pytest
from datetime import date, datetime, time, timedelta
from service_manager.models.client import Client, Admin, Employee
from service_manager.exceptions import InvalidDataError, AccessDeniedError
from service_manager.models.service import Service
from service_manager.models.order import ProcedureAppointment
from service_manager.models.inventory import Inventory
from service_manager import scheduler
from types import SimpleNamespace


@pytest.fixture
def settings():
    return {
        "open_hour": 9,
        "close_hour": 18,
        "working_days": [0, 1, 2, 3, 4, 5],
        "date_overrides": {},
    }


@pytest.fixture
def employees():
    employee1 = SimpleNamespace(username="Olena", rating=4.5)
    employee2 = SimpleNamespace(username="Ira", rating=4.9)

    return [employee1, employee2]


@pytest.fixture
def freeze_today(monkeypatch):
    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2026, 11, 2, 12, 0)

    monkeypatch.setattr(scheduler, "datetime", FixedDateTime)


# ---------- get_schedule_for_date ----------

def test_get_schedule_for_working_day(settings):
    result = scheduler.get_schedule_for_date(
        settings,
        date(2026, 11, 3)
    )

    assert result == (9, 18)


def test_get_schedule_for_day_off(settings):
    result = scheduler.get_schedule_for_date(
        settings,
        date(2026, 11, 8)
    )

    assert result is None


def test_get_schedule_for_closed_override(settings):
    settings["date_overrides"]["2026-11-03"] = {
        "closed": True
    }

    result = scheduler.get_schedule_for_date(
        settings,
        date(2026, 11, 3)
    )

    assert result is None


def test_get_schedule_for_custom_hours(settings):
    settings["date_overrides"]["2026-11-03"] = {
        "open_hour": 10,
        "close_hour": 16
    }

    result = scheduler.get_schedule_for_date(
        settings,
        date(2026, 11, 3)
    )

    assert result == (10, 16)


def test_schedule_override_opens_day_off(settings):
    settings["date_overrides"]["2026-11-08"] = {
        "open_hour": 10,
        "close_hour": 15
    }

    result = scheduler.get_schedule_for_date(
        settings,
        date(2026, 11, 8)
    )

    assert result == (10, 15)


# ---------- get_free_slots_for_all_suitable_staff ----------

def test_no_suitable_employees(freeze_today, monkeypatch):
    monkeypatch.setattr(
        scheduler,
        "load_clinic_settings",
        lambda: {
            "open_hour": 9,
            "close_hour": 18,
            "working_days": [0, 1, 2, 3, 4, 5],
            "date_overrides": {},
        }
    )

    result = scheduler.get_free_slots_for_all_suitable_staff(
        appointments=[],
        total_duration_minutes=60,
        suitable_employees=[]
    )

    assert result == []


@pytest.mark.parametrize(
    "duration",
    [0, -30, 1.5, "60", True]
)
def test_invalid_appointment_duration(duration):
    with pytest.raises(ValueError):
        scheduler.get_free_slots_for_all_suitable_staff(
            appointments=[],
            total_duration_minutes=duration,
            suitable_employees=[]
        )


def test_slots_use_clinic_schedule(
    freeze_today,
    monkeypatch,
    employees
):
    monkeypatch.setattr(
        scheduler,
        "load_clinic_settings",
        lambda: {
            "open_hour": 9,
            "close_hour": 18,
            "working_days": [0, 1, 2, 3, 4, 5],
            "date_overrides": {},
        }
    )

    result = scheduler.get_free_slots_for_all_suitable_staff(
        appointments=[],
        total_duration_minutes=60,
        suitable_employees=employees
    )

    assert result
    assert result[0]["date_str"] == "2026-11-03"
    assert result[0]["time_str"] == "09:00"


def test_slots_respect_custom_hours(
    freeze_today,
    monkeypatch,
    employees
):
    monkeypatch.setattr(
        scheduler,
        "load_clinic_settings",
        lambda: {
            "open_hour": 9,
            "close_hour": 18,
            "working_days": [0, 1, 2, 3, 4, 5],
            "date_overrides": {
                "2026-11-03": {
                    "open_hour": 10,
                    "close_hour": 12
                }
            },
        }
    )

    result = scheduler.get_free_slots_for_all_suitable_staff(
        appointments=[],
        total_duration_minutes=60,
        suitable_employees=employees
    )

    target_slots = [
        slot for slot in result
        if slot["date_str"] == "2026-11-03"
    ]

    assert [slot["time_str"] for slot in target_slots] == [
        "10:00",
        "10:00",
        "10:30",
        "10:30",
        "11:00",
        "11:00"
    ]

    assert len(target_slots) == 6

def test_slots_skip_closed_day(
    freeze_today,
    monkeypatch,
    employees
):
    monkeypatch.setattr(
        scheduler,
        "load_clinic_settings",
        lambda: {
            "open_hour": 9,
            "close_hour": 18,
            "working_days": [0, 1, 2, 3, 4, 5],
            "date_overrides": {
                "2026-11-03": {
                    "closed": True
                }
            },
        }
    )

    result = scheduler.get_free_slots_for_all_suitable_staff(
        appointments=[],
        total_duration_minutes=60,
        suitable_employees=employees
    )

    target_slots = [
        slot for slot in result
        if slot["date_str"] == "2026-11-03"
    ]

    assert target_slots == []


def test_slots_are_sorted_by_rating(
    freeze_today,
    monkeypatch,
    employees
):
    monkeypatch.setattr(
        scheduler,
        "load_clinic_settings",
        lambda: {
            "open_hour": 9,
            "close_hour": 18,
            "working_days": [0, 1, 2, 3, 4, 5],
            "date_overrides": {},
        }
    )

    result = scheduler.get_free_slots_for_all_suitable_staff(
        appointments=[],
        total_duration_minutes=60,
        suitable_employees=employees
    )

    assert result
    assert result[0]["employee"].username == "Ira"


def test_slots_do_not_exceed_working_hours(
    freeze_today,
    monkeypatch,
    employees
):
    monkeypatch.setattr(
        scheduler,
        "load_clinic_settings",
        lambda: {
            "open_hour": 9,
            "close_hour": 18,
            "working_days": [0, 1, 2, 3, 4, 5],
            "date_overrides": {},
        }
    )

    result = scheduler.get_free_slots_for_all_suitable_staff(
        appointments=[],
        total_duration_minutes=120,
        suitable_employees=employees
    )

    assert result

    for slot in result:
        start = datetime.strptime(slot["time_str"], "%H:%M").time()

        end = (
            datetime.combine(date.today(), start)
            + timedelta(minutes=120)
        ).time()

        assert start.hour >= 9
        assert end.hour <= 18


def test_client_create():
    client = Client("Anna", "380939593854")
    assert client.username == "Anna"
    assert client.phone == "380939593854"

def test_client_empty_username():
    with pytest.raises(InvalidDataError):
        client = Client("", "380939593854")

def test_client_empty_phone():
    with pytest.raises(InvalidDataError):
        client = Client("Anna", "")        

def test_client__wrong_phone():
    with pytest.raises(InvalidDataError):
        client = Client("Anna", "abd")

def test_service_create():
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    assert service.name == "Facial Cleansing"
    assert service.base_price == 800 
    assert service.duration_minutes == 60     

def test_service_invalid_price():
    with pytest.raises(InvalidDataError):
       service = Service("peel-01", "Facial Cleansing", "Face", -10, 60)

def test_service_invalid_duration():
    with pytest.raises(InvalidDataError):
       service = Service("peel-01", "Facial Cleansing", "Face", 800, 0)  

def test_service_empty_name():
    with pytest.raises(InvalidDataError):
       service = Service("peel-01", "", "Face", 800, 60)    

def test_employee_create():
    employee = Employee("Olena", "380939593854", "dermatolog")
    assert employee.username == "Olena"
    assert employee.phone == "380939593854"                     
    assert employee.specialization == "dermatolog"

def test_empty_username_employee(): 
    with pytest.raises(InvalidDataError): 
        employee = Employee("", "380939593854", "dermatolog")  

def test_invalid_phone_employee(): 
    with pytest.raises(InvalidDataError): 
        employee = Employee("Olena", "eyr", "dermatolog")

def test_invalid_specialization_employee(): 
    with pytest.raises(InvalidDataError): 
        employee = Employee("Olena", "380939593854", 123)

def test_admin_create():
    admin = Admin("Ira", "380964763481", "ADMIN")
    assert admin.username == "Ira"
    assert admin.phone == "380964763481"
    assert admin.employee_id == "ADMIN"
    assert admin.is_admin

def test_admin_empty_username():
    with pytest.raises(InvalidDataError):
        admin = Admin("", "380964763481", "ADMIN")

def test_admin_invalid_phone():
    with pytest.raises(InvalidDataError):
        admin = Admin("Ira", "qqq", "ADMIN")

def test_admin_empty_employee_id():
    with pytest.raises(InvalidDataError):
        admin = Admin("Ira", "380964763481", "")

def test_ProcedureAppointment_create():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment (client, service, "Scheduled", "2099-05-20","10:00", "Ira")
    assert order.status == "Scheduled"
    assert order.date == "2099-05-20"
    assert order.start_time == "10:00"
    assert order.total_price == 800
    assert order.total_duration_minutes == 60

def test_ProcedureAppointment_сancelled():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment (client, service, "Cancelled", "2099-05-20","10:00", "Ira")
    assert order.status == "Cancelled" 

def test_ProcedureAppointment_wrong_date():
    with pytest.raises(InvalidDataError):
        client = Client("Anna", "380939593854")
        service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
        order = ProcedureAppointment (client, service, "Scheduled", "2016-05-20","10:00", "Ira")       

def test_ProcedureAppointment_empty_name():
    with pytest.raises(InvalidDataError):
        client = Client("Anna", "380939593854")
        service = Service("peel-01", "", "Face", 800, 60)
        order = ProcedureAppointment (client, service, "Scheduled", "2030-05-20","10:00", "Ira")

def test_ProcedureAppointment_wrong_start_time():
    with pytest.raises(InvalidDataError):
        client = Client("Anna", "380939593854")
        service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
        order = ProcedureAppointment (client, service, "Scheduled", "2030-05-20","26:00", "Ira")

def test_ProcedureAppointment_wrong_status():
    with pytest.raises(InvalidDataError):
        client = Client("Anna", "380939593854")
        service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
        order = ProcedureAppointment (client, service, "Writting", "2030-05-20","10:00", "Ira")

def test_ProcedureAppointment_without_client():
    with pytest.raises(InvalidDataError):
        service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
        order = ProcedureAppointment(
            None, service, "Scheduled", "2030-05-20", "10:00", "Ira"
        )

def test_ProcedureAppointment_multiple_services_price():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    service2 = Service("mask-02", "Face Mask", "Face", 300, 30)
    order = ProcedureAppointment (client, [service, service2], "Scheduled", "2099-05-20","10:00", "Ira")
    assert order.status == "Scheduled"
    assert order.date == "2099-05-20"
    assert order.start_time == "10:00"
    assert order.total_price == 1100
    assert order.total_duration_minutes == 90
    assert order.calculate_price() == 1100


def test_ProcedureAppointment_without_services():
        with pytest.raises(InvalidDataError):
            client = Client("Anna", "380939593854")
            order = ProcedureAppointment (client, [], "Scheduled", "2030-05-20","10:00", "Ira")


def test_ProcedureAppointment_add_product_price():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")
    admin = Admin("Ira", "380964763481", "ADMIN")
    product = Inventory("Face Mask", 10, 200)

    order.add_product(product, admin)
    assert order.total_price == 1000


def test_ProcedureAppointment_add_product_by_client():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")
    product = Inventory("Face Mask", 10, 200)

    order.add_product(product, client)
    assert order.total_price == 1000


def test_ProcedureAppointment_add_product_invalid_price():
    with pytest.raises(InvalidDataError):
        Inventory("Face Mask", 10, -200)


def test_ProcedureAppointment_add_product_invalid_quantity():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")
    admin = Admin("Ira", "380964763481", "ADMIN")
    product = Inventory("Face Mask", 10, 200)

    with pytest.raises(InvalidDataError):
        order.add_product(product, admin, quantity=0)


def test_ProcedureAppointment_add_empty_product_name():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")
    admin = Admin("Ira", "380964763481", "ADMIN")
    product = Inventory("", 10, 200)

    with pytest.raises(InvalidDataError):
        order.add_product(product, admin)


def test_ProcedureAppointment_change_status():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")
    admin = Admin("Ira", "380964763481", "ADMIN")

    order.change_status("Completed", admin)
    assert order.status == "Completed"


def test_ProcedureAppointment_change_status_by_client():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    with pytest.raises(AccessDeniedError):
        order.change_status("Completed", client)


def test_ProcedureAppointment_change_status_invalid_status():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    admin = Admin("Ira", "380964763481", "ADMIN")
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    with pytest.raises(InvalidDataError):
        order.change_status("Written", admin)


def test_ProcedureAppointment_change_date():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    admin = Admin("Ira", "380964763481", "ADMIN")
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    order.change_date("2099-05-15", admin)
    assert order.date == "2099-05-15"


def test_ProcedureAppointment_change_date_by_client():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    order.change_date("2099-05-15", client)
    assert order.date == "2099-05-15"


def test_ProcedureAppointment_change_date_by_another_client():
    client = Client("Anna", "380939593854")
    another_client = Client("Olga", "380671234567")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    with pytest.raises(AccessDeniedError):
        order.change_date("2099-05-15", another_client)


def test_ProcedureAppointment_cancel_by_client():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    order.cancel_by_client(client)
    assert order.status == "Cancelled"


def test_ProcedureAppointment_cancel_by_another_client():
    client = Client("Anna", "380939593854")
    another_client = Client("Olga", "380671234567")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    with pytest.raises(AccessDeniedError):
        order.cancel_by_client(another_client)


def test_ProcedureAppointment_cancel_by_client_Completed():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Completed", "2099-05-20", "10:00", "Ira")

    with pytest.raises(InvalidDataError):
        order.cancel_by_client(client)


def test_ProcedureAppointment_cancel_by_client_Cancelled():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Cancelled", "2099-05-20", "10:00", "Ira")

    with pytest.raises(InvalidDataError):
        order.cancel_by_client(client)


def test_ProcedureAppointment_get_client_name_by_another_client():
    client = Client("Anna", "380939593854")
    another_client = Client("Olga", "380671234567")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    with pytest.raises(AccessDeniedError):
        order.get_client_name(another_client)


def test_ProcedureAppointment_get_client_name_by_admin():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    admin = Admin("Ira", "380964763481", "ADMIN")
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    assert order.get_client_name(admin) == "Anna"


def test_ProcedureAppointment_change_client():
    client = Client("Anna", "380939593854")
    olga = Client("Olga", "380939592763")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    admin = Admin("Ira", "380964763481", "ADMIN")
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    order.change_client(olga, admin)
    assert order.get_client_name(admin) == "Olga"


def test_ProcedureAppointment_change_client_by_client():
    client = Client("Anna", "380939593854")
    olga = Client("Olga", "380939592763")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")

    with pytest.raises(AccessDeniedError):
        order.change_client(olga, client)


def test_ProcedureAppointment_change_product_quantity():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")
    admin = Admin("Ira", "380964763481", "ADMIN")
    product = Inventory("Face Mask", 10, 200)

    order.add_product(product, admin, quantity=1)
    order.change_product_quantity("Face Mask", 3, admin)

    assert order.product_quantity == 3
    assert order.total_price == 1400


def test_ProcedureAppointment_change_product_quantity_by_client():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")
    product = Inventory("Face Mask", 10, 200)

    order.add_product(product, client, quantity=1)
    order.change_product_quantity("Face Mask", 3, client)

    assert order.product_quantity == 3
    assert order.total_price == 1400


def test_ProcedureAppointment_change_product_quantity_by_another_client():
    client = Client("Anna", "380939593854")
    another_client = Client("Olga", "380671234567")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(client, service, "Scheduled", "2099-05-20", "10:00", "Ira")
    product = Inventory("Face Mask", 10, 200)

    order.add_product(product, client, quantity=1)

    with pytest.raises(AccessDeniedError):
        order.change_product_quantity("Face Mask", 3, another_client)

        #Перевіряємо списання товару
def test_inventory_use_product():
    product = Inventory("Cream", 10, 100)
    product.use_product(3)
    assert product.quantity == 7

def test_inventory_use_product_not_enough():
    product = Inventory("Cream", 5, 100)
    with pytest.raises(InvalidDataError):
        product.use_product(7)
    assert product.quantity == 5  

def test_inventory_use_product_zero_amount():
    product = Inventory("Cream", 10, 100)
    with pytest.raises(InvalidDataError):
        product.use_product(0)
    assert product.quantity == 10  

def test_inventory_use_product_negative_amount():
    product = Inventory("Cream", 10, 100)
    with pytest.raises(InvalidDataError):
        product.use_product(-3)
    assert product.quantity == 10   

    #Поповнення товарів на складі

def test_inventory_restock():
    product = Inventory("Cream", 10, 100)
    admin = Admin("Ira", "380964763481", "ADMIN")
    product.restock(5, admin)
    assert product.quantity == 15    

def test_inventory_restock_by_client():
    product = Inventory("Cream", 10, 100)
    client = Client("Anna", "380939593854")
    with pytest.raises(AccessDeniedError):
        product.restock(5, client)
    assert product.quantity == 10

def test_inventory_restock_negativ():
    product = Inventory("Cream", 10, 100)
    admin = Admin("Ira", "380964763481", "ADMIN")
    with pytest.raises(InvalidDataError):
        product.restock(-5, admin)
    assert product.quantity == 10    

def test_create_product():
    product = Inventory("Cream", 10, 100)
    assert product.product_name == "Cream"
    assert product.quantity == 10
    assert product.price_per_item == 100

def test_create_zero_product():
    with pytest.raises(InvalidDataError):
        product = Inventory("Cream", 0, 100)  

def test_create_zero_price_product():
    with pytest.raises(InvalidDataError):
        product = Inventory("Cream", 10, 0)  


        # Перевірка бонусної системи


def test_ProcedureAppointment_bonus_system_without_bonuses():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(
        client, service, "Scheduled", "2099-05-20", "10:00", "Ira"
    )

    result = order.process_bonus_system(0)

    assert result == (800.0, 0.0, 80.0)


def test_ProcedureAppointment_bonus_system_with_bonuses():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(
        client, service, "Scheduled", "2099-05-20", "10:00", "Ira"
    )

    result = order.process_bonus_system(200)

    assert result == (600.0, 200.0, 60.0)


def test_ProcedureAppointment_bonus_system_max_discount():
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(
        client, service, "Scheduled", "2099-05-20", "10:00", "Ira"
    )

    result = order.process_bonus_system(1000)

    assert result == (400.0, 400.0, 640.0)


@pytest.mark.parametrize("balance", [-100, "200", None, True])
def test_ProcedureAppointment_bonus_system_invalid_balance(balance):
    client = Client("Anna", "380939593854")
    service = Service("peel-01", "Facial Cleansing", "Face", 800, 60)
    order = ProcedureAppointment(
        client, service, "Scheduled", "2099-05-20", "10:00", "Ira"
    )

    with pytest.raises(InvalidDataError):
        order.process_bonus_system(balance)

        # Перевірка рейтингу
@pytest.mark.parametrize("scores, expected_rating", [([2, 4, 5], 3.7),([5, 5, 5], 5.0),([1, 2, 3], 2.0)])
def test_Employee_rating(scores, expected_rating):
    employee = Employee("Olena", "380939593854", "dermatolog")
    for score in scores:
        employee.add_rating(score)
    assert employee.rating == expected_rating

@pytest.mark.parametrize("scores", [0, 7, 3.3])
def test_Employee_invalid_rating(scores):
    employee = Employee("Olena", "380939593854", "dermatolog")
    with pytest.raises(InvalidDataError):
        employee.add_rating(scores) 

def test_Employee_rating_without_scores():
    employee = Employee("Olena", "380939593854", "dermatolog")
    assert employee.rating == 0.0     

    # Перевірка нарахування заробітної плати


def test_change_compensation_settings():
    employee = Employee("Olena", "380939593854", "dermatolog")
    admin = Admin("Ira", "380939593855", "ADMIN")
    employee.change_compensation_settings(admin, base_rate=25000, procedure_percent=35, sales_percent=15)
    assert employee.base_rate == 25000
    assert employee.procedure_percent == 35
    assert employee.sales_percent == 15

def test_change_compensation_settings_by_employee():
    employee = Employee("Olena", "380939593854", "dermatolog")
    with pytest.raises(AccessDeniedError):
        employee.change_compensation_settings(employee, base_rate=25000, procedure_percent=35, sales_percent=15)
    assert employee.base_rate == 20000
    assert employee.procedure_percent == 30
    assert employee.sales_percent == 10 


@pytest.mark.parametrize("base_rate, procedure_percent, sales_percent", [(-100000, None, None), (None, -10, None), (None, 120, None), (None, None, -20)])
def test_invalid_change_compensation_settings(base_rate, procedure_percent, sales_percent):
    employee = Employee("Olena", "380939593854", "dermatolog")
    admin = Admin("Ira", "380939593855", "ADMIN")
    with pytest.raises(InvalidDataError):
        employee.change_compensation_settings(admin, base_rate=base_rate, procedure_percent=procedure_percent, sales_percent=sales_percent)
    assert employee.base_rate == 20000
    assert employee.procedure_percent == 30
    assert employee.sales_percent == 10    

def test_calculate_salary():
    employee = Employee("Olena", "380939593854", "dermatolog")
    admin = Admin("Ira", "380939593855", "ADMIN")
    employee.change_compensation_settings(admin, base_rate=25000, procedure_percent=35, sales_percent=15)
    assert employee.calculate_salary(10000, 5000) == 29250  

def test_change_procedure_percent():
    employee = Employee("Olena", "380939593854", "dermatolog")
    admin = Admin("Ira", "380939593855", "ADMIN")
    employee.change_compensation_settings(admin, procedure_percent=40)
    assert employee.base_rate == 20000
    assert employee.procedure_percent == 40
    assert employee.sales_percent == 10  

     
def test_calculate_salary_without_bonus():
    employee = Employee("Olena", "380939593854", "dermatolog")
    assert employee.calculate_salary(0, 0) == 20000

   