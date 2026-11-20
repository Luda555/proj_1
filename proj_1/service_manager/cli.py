
import os

from service_manager.admin_panel import admin_menu
from service_manager.scheduler import get_free_slots_for_all_suitable_staff
from service_manager.models.client import Client
from service_manager.models.order import Order, ProcedureAppointment
from telegram_storage import load_data, save_data, create_link_code
from service_manager.exceptions import (
    InvalidDataError,
    AccessDeniedError,
)
from service_manager.checkout import (
    select_payment_method,
    select_fulfillment_method,
    enter_delivery_address,
)


def get_or_create_client(clients):
    """Find an existing client or register a new one."""
    name = input("Enter your first and last name: ").strip()
    phone = input("Enter your phone number: ").strip()

    client = next((c for c in clients if c.phone == phone), None)

    if client:
        print(f"Welcome back, {client.username}!")
        return client, False

    email = input("Enter email (optional, or press Enter): ").strip()

    client = Client(
        username=name,
        phone=phone,
        email=email or None
    )

    return client, True


def select_products(inventories):
    """Let the client select products."""
    selected_products = []

    available_products = [
        item for item in inventories
        if item.quantity - item.reserved_quantity > 0
    ]

    if not available_products:
        print("\nThere are currently no products available.")
        return selected_products

    while True:
        print("\nAvailable Products")

        for index, product in enumerate(available_products, 1):
            available_quantity = (
                product.quantity - product.reserved_quantity
            )
            print(
                f"{index} - {product.product_name} | "
                f"Price: ${product.price_per_item:.2f} | "
                f"Available: {available_quantity}"
            )

        print("0 - Finish selecting products")

        choice = input("Select product number: ").strip()

        if choice == "0":
            break

        try:
            product_index = int(choice) - 1

            if not 0 <= product_index < len(available_products):
                print("Invalid product selection.")
                continue

            product = available_products[product_index]

            quantity = int(input("Enter quantity: ").strip())

            if quantity <= 0:
                print("Quantity must be greater than zero.")
                continue

            available_quantity = (
                product.quantity - product.reserved_quantity
            )

            already_selected = sum(
                item["quantity"]
                for item in selected_products
                if item["inventory_item"] is product
            )

            if quantity + already_selected > available_quantity:
                print(
                    f"Not enough stock. Available quantity: "
                    f"{available_quantity - already_selected}"
                )
                continue

            selected_products.append({
                "inventory_item": product,
                "quantity": quantity
            })

            print(
                f"Added {quantity} x {product.product_name}"
            )

        except ValueError:
            print("Please enter a valid number.")

    return selected_products


def add_selected_products(order, selected_products, client):
    """Add selected products to an order."""
    for item in selected_products:
        order.add_product(
            item["inventory_item"],
            client,
            item["quantity"]
        )


def save_new_client_link(client, is_new_client):
    """Generate Telegram linking code for a new client."""
    if not is_new_client:
        return

    data = load_data()
    data.setdefault("link_codes", {})

    link_code = create_link_code()
    data["link_codes"][link_code] = {
        "phone": client.phone
    }

    save_data(data)

    print(
        "\nTo link your Telegram account, open the bot "
        "and send this command:"
    )
    print(f"/link {link_code}")


def show_main_menu():
    print("\nWelcome to Beauty Clinic")
    print("1 - Show clinic services")
    print("2 - Create appointment")
    print("3 - Show my appointments")
    print("4 - Cancel appointment")
    print("5 - Buy products")
    print("6 - Close App")


def run():
    clients = []
    services = []
    appointments = []
    orders = []
    inventories = []
    employees = []

    while True:
        show_main_menu()

        action = input("Select an action: ").strip()

        if action == "1":
            if not services:
                print("\nThe clinic's price list is currently empty.")
            else:
                print("\nPrice list Beauty Clinic")
                for index, service in enumerate(services, 1):
                    print(f"{index} - {service}")

        elif action == "2":
            print("\nCreating an appointment for a procedure")

            if not services:
                print(
                    "Price list is empty. "
                    "Administrator must add services first."
                )
                continue

            try:
                client, is_new_client = get_or_create_client(clients)

                selected_services = []

                while True:
                    print("\nAvailable Services")

                    for index, service in enumerate(services, 1):
                        print(
                            f"{index} - [{service.service_code}] "
                            f"{service.name} "
                            f"(${service.base_price}) | "
                            f"Duration: {service.duration_minutes} min"
                        )

                    print("0 - Finish selecting services")

                    choice = input(
                        "Select service number to add: "
                    ).strip()

                    if choice == "0":
                        if not selected_services:
                            print("You must select at least one service!")
                            continue
                        break

                    try:
                        numbers = [
                            int(number.strip())
                            for number in choice.split(",")
                        ]

                        if any(
                            number < 1 or number > len(services)
                            for number in numbers
                        ):
                            print("Invalid selection.")
                            continue

                        for number in dict.fromkeys(numbers):
                            service = services[number - 1]

                            if service in selected_services:
                                print(
                                    f"{service.name} is already selected."
                                )
                            else:
                                selected_services.append(service)
                                print(f"Added: {service.name}")

                    except ValueError:
                        print("Enter valid service numbers.")

                selected_products = select_products(inventories)

                total_duration = sum(
                    service.duration_minutes
                    for service in selected_services
                )

                required_codes = {
                    service.service_code.casefold()
                    for service in selected_services
                }

                suitable_employees = [
                    employee for employee in employees
                    if required_codes.issubset({
                        str(code).casefold()
                        for code in employee.services_can_do
                    })
                ]

                if not suitable_employees:
                    print(
                        "\nNo employee is assigned to all selected services."
                    )
                    continue

                free_slots = get_free_slots_for_all_suitable_staff(
                    appointments,
                    total_duration,
                    suitable_employees
                )

                if not free_slots:
                    print("\nNo available appointment slots were found.")
                    continue

                print("\nAvailable appointment slots:")

                for index, slot in enumerate(free_slots, 1):
                    print(f"{index} - {slot['display']}")

                print("0 - Cancel booking")

                while True:
                    try:
                        choice = input(
                            "Choose an appointment slot: "
                        ).strip()

                        if choice == "0":
                            print("Booking cancelled.")
                            break

                        slot_index = int(choice) - 1

                        if not 0 <= slot_index < len(free_slots):
                            print("Invalid selection.")
                            continue

                        slot = free_slots[slot_index]

                        appointment = ProcedureAppointment(
                            client_user=client,
                            services_list=selected_services,
                            status="Scheduled",
                            date=slot["date_str"],
                            start_time=slot["time_str"],
                            employee=slot["employee"]
                        )

                        add_selected_products(
                            appointment,
                            selected_products,
                            client
                        )

                        appointment.validate_items()

                        appointment.payment_method = select_payment_method()

                        if appointment.product_items:
                            appointment.fulfillment_method = select_fulfillment_method()
                            appointment.delivery_address = enter_delivery_address(
                                appointment.fulfillment_method
                            )

                        if is_new_client:
                            clients.append(client)

                        appointments.append(appointment)
                        orders.append(appointment)
                        client.add_to_order_history(appointment)

                        data = load_data()
                        data.setdefault("appointments", [])

                        data["appointments"].append({
                            "phone": client.phone,
                            "date": str(appointment.date),
                            "start_time": str(appointment.start_time),
                            "status": appointment.status,
                        })

                        save_data(data)
                        save_new_client_link(client, is_new_client)

                        print("\nAppointment successfully booked!")
                        print(f"Client: {client.username}")
                        print(f"Services: {appointment.service}")
                        print(f"Date: {appointment.date}")
                        print(f"Time: {appointment.start_time}")
                        print(f"Employee: {appointment.staff}")

                        print("\nOrder items:")
                        for item in appointment.items:
                            print(
                                f"{item['type']}: {item['name']} x "
                                f"{item['quantity']} — "
                                f"${item['unit_price']:.2f}"
                            )

                        print(
                            f"Total price: ${appointment.total_price:.2f}"
                        )
                        print(f"Status: {appointment.status}")
                        print(f"Payment method: {appointment.payment_method}")
                        print(f"Payment status: {appointment.payment_status}")

                        if appointment.fulfillment_method:
                            print(f"Fulfillment method: {appointment.fulfillment_method}")
                            print(f"Delivery address: {appointment.delivery_address}")
                        break

                    except ValueError:
                        print("Please enter a valid slot number.")

            except (InvalidDataError, TypeError, ValueError) as error:
                print(f"Could not create appointment: {error}")

        elif action == "3":
            print("\nShow My Appointments")
            phone = input("Enter your phone number: ").strip()

            client = next(
                (c for c in clients if c.phone == phone),
                None
            )

            if client:
                print(f"\nAppointments for {client.username}")

                if not client.order_history:
                    print("You don't have any appointments yet.")
                else:
                    for index, appointment in enumerate(
                        client.order_history, 1
                    ):
                        print(f"{index}. {appointment}")
            else:
                print("Client with this phone number was not found.")

        elif action == "4":
            print("\nCancel Appointment")
            phone = input("Enter your phone number: ").strip()

            client = next(
                (c for c in clients if c.phone == phone),
                None
            )

            if not client:
                print("Client with this phone number was not found.")
                continue

            active_appointments = [
                appointment for appointment in client.order_history
                if appointment.status in ("Scheduled", "In Progress")
            ]

            if not active_appointments:
                print("You don't have any active appointments.")
                continue

            for index, appointment in enumerate(active_appointments, 1):
                print(
                    f"{index} - {appointment.service} "
                    f"({appointment.date}) "
                    f"[{appointment.status}]"
                )

            try:
                choice = int(
                    input("Select appointment number to cancel: ")
                ) - 1

                if not 0 <= choice < len(active_appointments):
                    print("Invalid selection.")
                    continue

                selected = active_appointments[choice]
                selected.cancel_by_client(client)

                data = load_data()

                for saved in data.get("appointments", []):
                    if (
                        saved.get("phone") == client.phone
                        and saved.get("date") == str(selected.date)
                        and saved.get("start_time") == str(selected.start_time)
                    ):
                        saved["status"] = selected.status
                        break

                save_data(data)
                print("Appointment successfully cancelled.")

            except ValueError:
                print("Please enter a valid number.")
            except AccessDeniedError as error:
                print(f"Access denied: {error}")
            except InvalidDataError as error:
                print(f"Cannot cancel appointment: {error}")

        elif action == "5":
            print("\nBuy Products")

            if not inventories:
                print("There are currently no products in the inventory.")
                continue

            try:
                client, is_new_client = get_or_create_client(clients)

                selected_products = select_products(inventories)

                if not selected_products:
                    print("No products selected. Purchase cancelled.")
                    continue

                order = Order(
                    client_user=client,
                    status="Scheduled",
                )

                add_selected_products(
                    order,
                    selected_products,
                    client
                )

                order.validate_items()

                order.payment_method = select_payment_method()
                order.fulfillment_method = select_fulfillment_method()
                order.delivery_address = enter_delivery_address(
                    order.fulfillment_method
                )

                if is_new_client:
                    clients.append(client)

                orders.append(order)
                client.add_to_order_history(order)

                print("\nPurchase successfully created!")
                print(f"Client: {client.username}")
                print("\nPurchased products:")

                for item in order.items:
                    print(
                        f"{item['name']} x {item['quantity']} — "
                        f"${item['unit_price']:.2f}"
                    )

                print(f"Total price: ${order.total_price:.2f}")
                print(f"Status: {order.status}")
                print(f"Payment method: {order.payment_method}")
                print(f"Payment status: {order.payment_status}")

                if order.fulfillment_method:
                    print(f"Fulfillment method: {order.fulfillment_method}")
                    print(f"Delivery address: {order.delivery_address}")

                save_new_client_link(client, is_new_client)

            except (InvalidDataError, TypeError, ValueError) as error:
                print(f"Could not complete purchase: {error}")

        elif action == "admin":
            entered_id = input("Enter administrator ID: ").strip()
            secret_id = os.getenv("EMPLOYEE_ID")

            if secret_id and entered_id == secret_id:
                print("Administrator login successful!")
                admin_menu(
                    services,
                    inventories,
                    appointments,
                    employees
                )
            else:
                print("Access denied!")

        elif action == "6":
            print("\nThank you for visiting Beauty Clinic. Goodbye!")
            break

        else:
            print("Invalid action. Please select an option from the menu.")


if __name__ == "__main__":
    run()
