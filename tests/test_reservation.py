
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "proj_1"))

from service_manager.models.inventory import Inventory
from service_manager.models.client import Client
from service_manager.models.service import Service
from service_manager.models.order import ProcedureAppointment


def test_product_reservation():
    client = Client("Anna", "+380991112233")

    service = Service(
        service_code="PEEL-01",
        name="Facial Cleansing",
        category="Face",
        base_price=800,
        duration_minutes=60
    )

    inventory = Inventory("Face Mask", 10, 200)

    appointment = ProcedureAppointment(
        client_user=client,
        services_list=[service],
        date="2099-05-20",
        start_time="10:00"
    )

    # Додаємо 3 одиниці товару
    appointment.add_product(inventory, client, quantity=3)

    assert inventory.quantity == 10
    assert inventory.reserved_quantity == 3
    assert inventory.available_quantity == 7

    # Змінюємо кількість на 5
    appointment.change_product_quantity("Face Mask", 5, client)

    assert inventory.quantity == 10
    assert inventory.reserved_quantity == 5
    assert inventory.available_quantity == 5
    assert appointment.product_quantity == 5
def test_product_reservation_released_after_cancellation():
    client = Client("Anna", "+380991112233")

    service = Service(
        service_code="PEEL-01",
        name="Facial Cleansing",
        category="Face",
        base_price=800,
        duration_minutes=60
    )

    inventory = Inventory("Face Mask", 10, 200)

    appointment = ProcedureAppointment(
        client_user=client,
        services_list=[service],
        date="2099-05-20",
        start_time="10:00"
    )

    appointment.add_product(inventory, client, quantity=3)

    appointment.cancel_by_client(client)

    assert appointment.status == "Cancelled"
    assert inventory.quantity == 10
    assert inventory.reserved_quantity == 0
    assert inventory.available_quantity == 10