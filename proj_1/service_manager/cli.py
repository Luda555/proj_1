import os

from service_manager.admin_panel import admin_menu
from service_manager.scheduler import get_free_slots_for_all_suitable_staff
from service_manager.models.client import Client, Admin, Employee
from service_manager.models.inventory import Inventory
from service_manager.models.order import ProcedureAppointment
from service_manager.models.service import Service
from telegram_storage import load_data, save_data, create_link_code
from service_manager.exceptions import (
    InvalidDataError,
    AccessDeniedError,
    ItemNotFoundError,
)


def run():
    clients = []
    services = []
    appointments = []
    inventories = []
    employees = []

    while True:
        print("\nWelcome to Beauty Clinic")
        print("1 - Show clinic services")
        print("2 - Create appointment")
        print("3 - Show my appointments")
        print("4 - Cancel appointment")
        print("5 - Close App")

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

            name = input("Enter your first and last name: ").strip()
            phone = input("Enter your phone number: ").strip()
            email_input = input(
                "Enter email (optional, or press Enter): "
            ).strip()

            try:
                # Find an existing client by phone number.
                client = next(
                    (c for c in clients if c.phone == phone),
                    None
                )

                # Register a new client.
                if client is None:
                    client = Client(
                        username=name,
                        phone=phone,
                        email=email_input or None
                    )
                    is_new_client = True
                else:
                    is_new_client = False
                    print(f"Welcome back, {client.username}!")

                selected_services_for_appointment = []

                while True:
                    print("\nAvailable Services")

                    for index, service in enumerate(services, 1):
                        print(
                            f"{index} - [{service.service_code}] "
                            f"{service.name} (${service.base_price}) | "
                            f"Duration: {service.duration_minutes} min"
                        )

                    print("0 - Finish selecting services")

                    choice_input = input(
                        "Select service number to add "
                        "(or 0 to finish): "
                    ).strip()

                    if choice_input == "0":
                        if not selected_services_for_appointment:
                            print("You must select at least one service!")
                            continue
                        break

                    try:
                        choice_numbers = [
                            int(number.strip())
                            for number in choice_input.split(",")
                        ]

                        if any(
                            number < 1 or number > len(services)
                            for number in choice_numbers
                        ):
                            print("Invalid selection. Try again.")
                            continue

                        for choice_number in dict.fromkeys(choice_numbers):
                            chosen_service = services[choice_number - 1]

                            if chosen_service in selected_services_for_appointment:
                                print(
                                    f"'{chosen_service.name}' "
                                    "is already selected."
                                )
                            else:
                                selected_services_for_appointment.append(
                                    chosen_service
                                )
                                print(f"Added: {chosen_service.name}")

                    except ValueError:
                        print(
                            "Please enter valid service numbers "
                            "separated by commas."
                        )

                total_duration = sum(
                    service.duration_minutes
                    for service in selected_services_for_appointment
                )

                total_price = sum(
                    service.base_price
                    for service in selected_services_for_appointment
                )

                print(
                    "\nYour selection: "
                    + ", ".join(
                        service.name
                        for service in selected_services_for_appointment
                    )
                )
                print(f"Total duration: {total_duration} minutes")
                print(f"Total base price: ${total_price:.2f}")

                # Find employees who can perform ALL selected services.
                required_codes = {
                    service.service_code.casefold()
                    for service in selected_services_for_appointment
                }

                suitable_employees = [
                    employee
                    for employee in employees
                    if required_codes.issubset({
                        str(code).casefold()
                        for code in employee.services_can_do
                    })
                ]

                if not suitable_employees:
                    print(
                        "\nNo employee is assigned to all selected services."
                    )
                    print(
                        "Ask the administrator to register an employee "
                        "and assign the required services."
                    )
                    continue

                # Find available appointment slots.
                free_slots = get_free_slots_for_all_suitable_staff(
                    appointments,
                    total_duration,
                    suitable_employees
                )

                if not free_slots:
                    print(
                        "\nNo available appointment slots were found "
                        "for the selected services."
                    )
                    continue

                print("\nAvailable appointment slots:")

                for index, slot in enumerate(free_slots, 1):
                    print(f"{index} - {slot['display']}")

                print("0 - Cancel booking")

                while True:
                    slot_input = input(
                        "Choose an appointment slot: "
                    ).strip()

                    if slot_input == "0":
                        print("Booking cancelled.")
                        break

                    try:
                        slot_idx = int(slot_input) - 1

                        if not 0 <= slot_idx < len(free_slots):
                            print("Invalid selection. Try again.")
                            continue

                        chosen_slot = free_slots[slot_idx]

                        # Create the appointment.
                        appointment = ProcedureAppointment(
                            client_user=client,
                            services_list=selected_services_for_appointment,
                            status="Scheduled",
                            date=chosen_slot["date_str"],
                            start_time=chosen_slot["time_str"],
                            employee=chosen_slot["employee"]
                        )

                        # Save the client and appointment in memory.
                        if is_new_client:
                            clients.append(client)

                        appointments.append(appointment)
                        client.add_to_order_history(appointment)

                        # Save appointment data for Telegram reminders.
                        data = load_data()
                        data.setdefault("appointments", [])

                        data["appointments"].append({
                            "phone": client.phone,
                            "date": str(appointment.date),
                            "start_time": str(appointment.start_time),
                            "status": appointment.status,
                        })

                        # Generate a Telegram link code for a new client.
                        if is_new_client:
                            link_code = create_link_code()
                            data.setdefault("link_codes", {})
                            data["link_codes"][link_code] = {
                                "phone": client.phone
                            }

                        save_data(data)

                        if is_new_client:
                            print(
                                "\nTo link your Telegram account, open "
                                "the bot and send this command:"
                            )
                            print(f"/link {link_code}")

                        # Show appointment confirmation.
                        print("\nAppointment successfully booked!")
                        print(f"Client: {client.username}")
                        print(f"Services: {appointment.service}")
                        print(f"Date: {appointment.date}")
                        print(f"Time: {appointment.start_time}")
                        print(f"Employee: {appointment.staff}")
                        print(
                            f"Total price: ${appointment.total_price:.2f}"
                        )
                        print(f"Status: {appointment.status}")

                        # Wait for the user to enter 0.
                        while True:
                            choice = input(
                                "\nEnter 0 to return to the main menu: "
                            ).strip()

                            if choice == "0":
                                break

                            print("Invalid choice. Please enter 0.")

                        # Return from the slot selection loop.
                        break

                    except ValueError:
                        print(
                            "Please enter a valid appointment slot number."
                        )

            except (InvalidDataError, TypeError) as e:
                print(f"Could not create appointment: {e}")

        elif action == "3":
            print("\nShow My Appointments")
            search_phone = input(
                "Enter your phone number to find appointments: "
            ).strip()

            found_client = None

            for client in clients:
                if client.phone == search_phone:
                    found_client = client
                    break

            if found_client:
                print(
                    f"\nAppointments for client: {found_client.username}"
                )

                if not found_client.order_history:
                    print("You don't have any appointments scheduled yet.")
                else:
                    for index, appointment in enumerate(
                        found_client.order_history, 1
                    ):
                        print(f"{index}. {appointment}")
            else:
                print("Client with this phone number was not found.")

        elif action == "4":
            print("\nCancel Appointment")
            search_phone = input("Enter your phone number: ").strip()

            found_client = None

            for client in clients:
                if client.phone == search_phone:
                    found_client = client
                    break

            if found_client:
                active_appointments = [
                    appointment
                    for appointment in found_client.order_history
                    if appointment.status in ("Scheduled", "In Progress")
                ]

                if not active_appointments:
                    print(
                        "You don't have any active appointments "
                        "that can be cancelled."
                    )
                else:
                    print("\nYour active appointments:")

                    for index, appointment in enumerate(
                        active_appointments, 1
                    ):
                        print(
                            f"{index} - {appointment.service} "
                            f"({appointment.date}) "
                            f"[Status: {appointment.status}]"
                        )

                    try:
                        choice_idx = int(
                            input(
                                "Select the appointment number to cancel: "
                            )
                        ) - 1

                        if not 0 <= choice_idx < len(active_appointments):
                            print("Invalid selection.")
                        else:
                            selected_app = active_appointments[choice_idx]
                            selected_app.cancel_by_client(found_client)

                            # Update the appointment status for Telegram.
                            data = load_data()

                            for saved_appointment in data.get(
                                "appointments", []
                            ):
                                if (
                                    saved_appointment.get("phone")
                                    == found_client.phone
                                    and saved_appointment.get("date")
                                    == str(selected_app.date)
                                    and saved_appointment.get("start_time")
                                    == str(selected_app.start_time)
                                ):
                                    saved_appointment["status"] = (
                                        selected_app.status
                                    )
                                    break

                            save_data(data)

                            print(
                                "Your appointment has been "
                                "successfully cancelled."
                            )

                    except ValueError:
                        print(
                            "Input error: Please enter a valid number."
                        )
                    except AccessDeniedError as e:
                        print(f"Access denied: {e}")
                    except InvalidDataError as e:
                        print(f"Cannot cancel appointment: {e}")

            else:
                print("Client with this phone number was not found.")

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

        elif action == "5":
            print("\nThank you for visiting Beauty Clinic. Goodbye!")
            break

        else:
            print("Invalid action. Please select an option from the menu.")


if __name__ == "__main__":
    run()


            

            
       

