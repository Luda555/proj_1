
import os

from service_manager.models.client import Admin, Employee
from service_manager.models.service import Service
from service_manager.exceptions import (
    InvalidDataError,
    AccessDeniedError,
)


VALID_STATUSES = {
    "Scheduled",
    "In Progress",
    "Completed",
    "Cancelled",
}


def _pause():
    input("\nPress Enter to continue...")


def _clear_screen():
    os.system("cls" if os.name == "nt" else "clear")


def _read_number(prompt, number_type=int, minimum=None):
    """Read and validate a numeric value."""
    while True:
        try:
            value = number_type(input(prompt).strip())

            if minimum is not None and value < minimum:
                print(f"Value must be at least {minimum}.")
                continue

            return value

        except ValueError:
            print("Invalid input. Please enter a valid number.")


def _normalize_phone(phone):
    """Normalize a phone number for employee lookup."""
    digits = "".join(char for char in str(phone) if char.isdigit())

    # Treat Ukrainian +380XXXXXXXXX and 0XXXXXXXXX as equivalent.
    if digits.startswith("380") and len(digits) == 12:
        digits = "0" + digits[3:]

    return digits


def _add_service(services):
    print("\n--- Add New Service ---")

    service_code = input("Enter service code (e.g., PEEL-01): ").strip()
    name = input("Enter service name: ").strip()
    category = input("Enter category: ").strip()

    if not service_code or not name:
        print("Service code and name cannot be empty.")
        return

    # Prevent duplicate service codes.
    existing_codes = {
        service.service_code.casefold()
        for service in services
    }

    if service_code.casefold() in existing_codes:
        print(f"Service code '{service_code}' already exists.")
        return

    base_price = _read_number(
        "Enter base price ($): ",
        float,
        minimum=0.01,
    )

    duration_minutes = _read_number(
        "Enter duration (minutes): ",
        int,
        minimum=1,
    )

    description = input(
        "Enter description (optional, press Enter to skip): "
    ).strip()

    new_service = Service(
        service_code=service_code,
        name=name,
        category=category,
        base_price=base_price,
        duration_minutes=duration_minutes,
        description=description or None,
    )

    services.append(new_service)

    print(f"Service '{new_service.name}' successfully added.")


def _view_inventory(inventory_list):
    print("\n--- Clinic Inventory ---")

    if not inventory_list:
        print("The inventory is currently empty.")
        return

    for index, item in enumerate(inventory_list, start=1):
        print(
            f"{index}. {item.product_name} | "
            f"Quantity: {item.quantity} | "
            f"Price per item: ${item.price_per_item:.2f}"
        )


def _financial_report(appointments):
    print("\n--- Clinic Financial Report ---")

    completed_revenue = 0.0
    projected_revenue = 0.0
    completed_count = 0
    projected_count = 0

    for appointment in appointments:
        price = float(getattr(appointment, "total_price", 0))

        if appointment.status == "Completed":
            completed_revenue += price
            completed_count += 1

        elif appointment.status in ("Scheduled", "In Progress"):
            projected_revenue += price
            projected_count += 1

    print(
        f"Completed revenue: ${completed_revenue:.2f} "
        f"({completed_count} appointments)"
    )
    print(
        f"Projected revenue: ${projected_revenue:.2f} "
        f"({projected_count} appointments)"
    )
    print(
        f"Total business volume: "
        f"${completed_revenue + projected_revenue:.2f}"
    )


def _change_appointment_status(appointments, inventory_list):
    print("\n--- Change Appointment Status ---")

    if not appointments:
        print("No appointments found.")
        return

    for index, appointment in enumerate(appointments, start=1):
        print(f"{index}. {appointment}")

    appointment_number = _read_number(
        "Enter appointment number from the list: ",
        int,
        minimum=1,
    )

    if appointment_number > len(appointments):
        print("Invalid appointment selection.")
        return

    appointment = appointments[appointment_number - 1]
    old_status = appointment.status

    print("\nAvailable statuses:")
    for status in sorted(VALID_STATUSES):
        print(f"- {status}")

    new_status = input("Enter new status: ").strip()

    if new_status not in VALID_STATUSES:
        print("Invalid status. Please select one of the listed statuses.")
        return

    if new_status == old_status:
        print("The appointment already has this status.")
        return

    if old_status in ("Completed", "Cancelled"):
        print(
            f"Cannot change an appointment that is already "
            f"{old_status}."
        )
        return

    # Check stock before completing an appointment.
    product_to_deduct = None
    quantity_to_deduct = 0

    if new_status == "Completed":
        products = getattr(appointment, "products", [])
        quantity = getattr(appointment, "product_quantity", 0)

        if products and quantity > 0:
            # The current ProcedureAppointment model stores one shared
            # quantity for all products. It cannot reliably represent
            # separate quantities for multiple different products.
            if len(products) > 1:
                print(
                    "Cannot safely deduct stock: this appointment contains "
                    "multiple products, but the current order model stores "
                    "only one shared product quantity. Update the order "
                    "model to track each product and its quantity separately."
                )
                return

            product_name = products[0]

            product_to_deduct = next(
                (
                    item for item in inventory_list
                    if item.product_name.casefold()
                    == product_name.casefold()
                ),
                None,
            )

            if product_to_deduct is None:
                print(
                    f"Product '{product_name}' was not found in inventory. "
                    "The appointment status was not changed."
                )
                return

            if product_to_deduct.quantity < quantity:
                print(
                    f"Not enough '{product_name}' in stock. "
                    f"Available: {product_to_deduct.quantity}; "
                    f"required: {quantity}. "
                    "The appointment status was not changed."
                )
                return

            quantity_to_deduct = quantity

    admin_user = Admin(
        username="Admin",
        phone="380000000000",
        employee_id="ADMIN_ID",
    )

    # Deduct stock only after checking availability.
    try:
        if product_to_deduct is not None:
            product_to_deduct.use_product(quantity_to_deduct)

        appointment.change_status(new_status, admin_user)

        # The current Order.change_status method does not validate statuses
        # itself, so this function validates them before calling it.
        if appointment.status != new_status:
            print("The appointment status was not changed.")
            return

        print(f"Appointment status updated to '{new_status}'.")

    except (InvalidDataError, AccessDeniedError, ValueError) as error:
        print(f"Could not update appointment: {error}")


def _add_employee(employees):
    print("\n--- Register New Employee ---")

    username = input("Enter employee name: ").strip()
    phone = input("Enter employee phone: ").strip()
    specialization = input("Enter specialization: ").strip()

    normalized_phone = _normalize_phone(phone)

    if any(
        _normalize_phone(employee.phone) == normalized_phone
        for employee in employees
    ):
        print("An employee with this phone number already exists.")
        return

    employee = Employee(
        username=username,
        phone=phone,
        specialization=specialization,
    )

    employees.append(employee)

    print(
        f"Employee '{employee.username}' "
        f"({employee.specialization}) successfully registered."
    )



def _assign_service(services, employees):
    print("\n--- Assign Services to Employee ---")

    if not employees:
        print("No employees found. Register an employee first.")
        return

    if not services:
        print("The service list is empty. Add a service first.")
        return

    print("\nEmployees:")

    for index, employee in enumerate(employees, start=1):
        assigned_codes = (
            ", ".join(employee.services_can_do)
            if employee.services_can_do
            else "None"
        )

        print(
            f"{index}. {employee.username} "
            f"({employee.specialization}) | "
            f"Phone: {employee.phone} | "
            f"Assigned service codes: {assigned_codes}"
        )

    employee_phone = input(
        "\nEnter employee phone number: "
    ).strip()

    normalized_phone = _normalize_phone(employee_phone)

    selected_employee = next(
        (
            employee for employee in employees
            if _normalize_phone(employee.phone) == normalized_phone
        ),
        None,
    )

    if selected_employee is None:
        print("Employee not found. Check the phone number and try again.")
        return

    print(
        f"\nSelected employee: {selected_employee.username} "
        f"({selected_employee.phone})"
    )

    print("\nAvailable services:")

    for index, service in enumerate(services, start=1):
        print(
            f"{index}. [{service.service_code}] "
            f"{service.name} | ${service.base_price:.2f}"
        )

    service_numbers = input(
        "\nEnter service numbers separated by commas "
        "(e.g. 1, 3, 4): "
    ).strip()

    if not service_numbers:
        print("You must select at least one service.")
        return

    try:
        selected_numbers = [
            int(number.strip())
            for number in service_numbers.split(",")
        ]
    except ValueError:
        print("Invalid input. Enter service numbers separated by commas.")
        return

    if any(
        number < 1 or number > len(services)
        for number in selected_numbers
    ):
        print("One or more service numbers are invalid.")
        return

    # Remove duplicate selections while preserving their order.
    selected_numbers = list(dict.fromkeys(selected_numbers))

    assigned_codes = {
        code.casefold()
        for code in selected_employee.services_can_do
    }

    added_services = []
    already_assigned = []

    for number in selected_numbers:
        selected_service = services[number - 1]
        service_code = selected_service.service_code

        if service_code.casefold() in assigned_codes:
            already_assigned.append(selected_service.name)
            continue

        selected_employee.services_can_do.append(service_code)
        assigned_codes.add(service_code.casefold())
        added_services.append(selected_service.name)

    if added_services:
        print(
            f"\nSuccessfully assigned to {selected_employee.username}:"
        )
        for service_name in added_services:
            print(f"- {service_name}")

    if already_assigned:
        print("\nThese services were already assigned:")
        for service_name in already_assigned:
            print(f"- {service_name}")

    if not added_services and already_assigned:
        print("No new services were added.")



def admin_menu(services, inventory_list, appointments, employees):
    """Display the clinic administrator menu."""

    while True:
        _clear_screen()

        print("\n--- Admin Cabinet ---")
        print("1 - Add new service")
        print("2 - View inventory")
        print("3 - View financial report")
        print("4 - Change appointment status")
        print("5 - Add new employee")
        print("6 - Assign Service to Employee")
        print("7 - Back to main menu")

        choice = input("Select admin action: ").strip()

        try:
            if choice == "1":
                _add_service(services)
                _pause()

            elif choice == "2":
                _view_inventory(inventory_list)
                _pause()

            elif choice == "3":
                _financial_report(appointments)
                _pause()

            elif choice == "4":
                _change_appointment_status(
                    appointments,
                    inventory_list,
                )
                _pause()

            elif choice == "5":
                _add_employee(employees)
                _pause()

            elif choice == "6":
                _assign_service(services, employees)
                _pause()

            elif choice == "7":
                print("Returning to main menu...")
                break

            else:
                print("Invalid choice. Select an option from 1 to 7.")
                _pause()

        except (InvalidDataError, AccessDeniedError, ValueError) as error:
            print(f"Error: {error}")
            _pause()


