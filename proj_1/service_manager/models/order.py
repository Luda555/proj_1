
from datetime import datetime
from abc import ABC, abstractmethod

from service_manager.exceptions import (
    InvalidDataError,
    AccessDeniedError,
)


ALLOWED_STATUSES = {
    "Scheduled",
    "In Progress",
    "Completed",
    "Cancelled",
}


class Order(ABC):
    def __init__(
        self,
        client_user,
        services_list,
        status="Scheduled",
        date=None,
        start_time=None,
        employee=None,
    ):
        if not hasattr(client_user, "order_history"):
            raise TypeError(
                "client_user must be a Client instance."
            )

        if services_list is None:
            raise InvalidDataError(
                "At least one service must be selected."
            )

        if isinstance(services_list, (list, tuple)):
            self._services = list(services_list)
        else:
            self._services = [services_list]

        if not self._services:
            raise InvalidDataError(
                "At least one service must be selected."
            )

        if any(service is None for service in self._services):
            raise InvalidDataError(
                "The service list contains an invalid service."
            )

        self._client_user = client_user

        if hasattr(employee, "username"):
            self._staff_username = employee.username
        elif employee:
            self._staff_username = str(employee)
        else:
            self._staff_username = "Unknown"

        self.__validate_date(date)
        self.__validate_status(status)

        self._date = date
        self._status = status
        self.start_time = self.__validate_start_time(start_time)
        self.total_price = 0.0

    @staticmethod
    def __validate_status(status):
        if status not in ALLOWED_STATUSES:
            raise InvalidDataError(
                f"Invalid appointment status: {status!r}."
            )

    @staticmethod
    def __validate_start_time(start_time):
        if start_time is None:
            return None

        if not isinstance(start_time, str):
            raise InvalidDataError(
                "Start time must use HH:MM format."
            )

        try:
            datetime.strptime(start_time, "%H:%M")
        except ValueError as exc:
            raise InvalidDataError(
                "Invalid start time. Use HH:MM format."
            ) from exc

        return start_time

    @staticmethod
    def __validate_date(date_str):
        if not date_str:
            raise InvalidDataError(
                "Appointment date cannot be empty."
            )

        if not isinstance(date_str, str):
            raise InvalidDataError(
                "Appointment date must use YYYY-MM-DD format."
            )

        try:
            input_date = datetime.strptime(
                date_str,
                "%Y-%m-%d",
            ).date()
        except ValueError as exc:
            raise InvalidDataError(
                "Invalid date format. Use YYYY-MM-DD."
            ) from exc

        if input_date < datetime.now().date():
            raise InvalidDataError(
                "Appointment date cannot be in the past."
            )

    @property
    def staff(self):
        return self._staff_username

    @property
    def service(self):
        return ", ".join(
            getattr(service, "name", str(service))
            for service in self._services
        )

    @property
    def services(self):
        return self._services

    @property
    def total_duration_minutes(self):
        return sum(
            service.duration_minutes
            for service in self._services
        )

    @property
    def date(self):
        return self._date

    @property
    def status(self):
        return self._status

    def get_client_name(self, viewer_user):
        if (
            getattr(viewer_user, "is_admin", False)
            or viewer_user == self._client_user
        ):
            return self._client_user.username

        raise AccessDeniedError("Access denied.")

    def change_client(self, new_client_user, user):
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can change the client."
            )

        if not hasattr(new_client_user, "order_history"):
            raise TypeError(
                "The new client must be a Client instance."
            )

        self._client_user = new_client_user

    def change_date(self, new_date, user):
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can change the date."
            )

        self.__validate_date(new_date)
        self._date = new_date

    def change_status(self, new_status, user):
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can change appointment status."
            )

        self.__validate_status(new_status)

        if self._status == "Completed" and new_status != "Completed":
            raise InvalidDataError(
                "A completed appointment cannot be reopened or cancelled."
            )

        if self._status == "Cancelled" and new_status != "Cancelled":
            raise InvalidDataError(
                "A cancelled appointment cannot be reactivated."
            )

        old_status = self._status
        self._status = new_status

        print(
            f"Status changed from '{old_status}' "
            f"to '{new_status}'."
        )

    def cancel_by_client(self, user):
        if user != self._client_user:
            raise AccessDeniedError(
                "You can only cancel your own appointments."
            )

        if self._status in ("Completed", "Cancelled"):
            raise InvalidDataError(
                f"Cannot cancel an appointment that is "
                f"already {self._status}."
            )

        self._status = "Cancelled"

    def _set_and_validate_price(self, price):
        if isinstance(price, bool) or not isinstance(
            price, (int, float)
        ):
            raise InvalidDataError(
                "Price must be a number."
            )

        if price < 0:
            raise InvalidDataError(
                "Order price cannot be negative."
            )

        self.total_price = float(price)

    @abstractmethod
    def calculate_price(self):
        raise NotImplementedError

    def __str__(self):
        return (
            f"[{self._date} {self.start_time}] "
            f"Client: {self._client_user.username} | "
            f"Services: {self.service} | "
            f"Staff: {self.staff} | "
            f"Price: ${self.total_price:.2f} | "
            f"Status: [{self.status}]"
        )


class ProcedureAppointment(Order):
    def __init__(
        self,
        client_user=None,
        services_list=None,
        status="Scheduled",
        date=None,
        start_time=None,
        employee=None,
        product_name="None",
        product_price=0,
        product_quantity=0,
        **kwargs,
    ):
        actual_client = (
            client_user
            if client_user is not None
            else kwargs.get("client")
        )

        actual_services = (
            services_list
            if services_list is not None
            else kwargs.get("service")
        )

        actual_employee = (
            employee
            if employee is not None
            else kwargs.get("staff")
        )

        supplied_total_price = kwargs.get("total_price")

        super().__init__(
            client_user=actual_client,
            services_list=actual_services,
            status=status,
            date=date,
            start_time=start_time,
            employee=actual_employee,
        )

        self.__validate_quantity(product_quantity)
        self.__validate_product_price(product_price)

        self.products = []
        self._product_items = []
        self.product_price = float(product_price)
        self._product_quantity = product_quantity

        if product_name != "None" and product_name:
            self.products.append(product_name)
            if product_quantity > 0:
                self._product_items.append(
                    {
                        "name": product_name,
                        "unit_price": float(product_price),
                        "quantity": product_quantity,
                    }
                )

        if supplied_total_price is not None:
            self._set_and_validate_price(supplied_total_price)
        else:
            self._set_and_validate_price(self.calculate_price())

    @staticmethod
    def __validate_quantity(quantity):
        if (
            isinstance(quantity, bool)
            or not isinstance(quantity, int)
            or quantity < 0
        ):
            raise InvalidDataError(
                "Product quantity must be a non-negative integer."
            )

    @staticmethod
    def __validate_product_price(price):
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or price < 0
        ):
            raise InvalidDataError(
                "Product price must be a non-negative number."
            )

    @property
    def product_quantity(self):
        return self._product_quantity

    @property
    def product_items(self):
        """Return product names, unit prices and individual quantities."""
        return [item.copy() for item in self._product_items]

    def change_product_quantity(self, value, user):
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can change product quantity."
            )

        self.__validate_quantity(value)

        if len(self._product_items) > 1:
            raise InvalidDataError(
                "This appointment contains multiple product types. "
                "Update each product quantity individually."
            )

        if self._product_items:
            self._product_items[0]["quantity"] = value
            self._product_quantity = value
        elif value > 0:
            raise InvalidDataError(
                "Add a product before setting its quantity."
            )
        else:
            self._product_quantity = 0

        self._set_and_validate_price(self.calculate_price())

    def calculate_price(self):
        services_total = sum(
            service.base_price
            for service in self._services
        )

        products_total = sum(
            item["unit_price"] * item["quantity"]
            for item in self._product_items
        )

        return services_total + products_total

    def add_product(
        self,
        product_name,
        product_price,
        user,
        quantity=1,
    ):
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can add products."
            )

        if not isinstance(product_name, str) or not product_name.strip():
            raise InvalidDataError(
                "Product name cannot be empty."
            )

        self.__validate_quantity(quantity)
        self.__validate_product_price(product_price)

        if quantity == 0:
            raise InvalidDataError(
                "Product quantity must be greater than zero."
            )

        self.products.append(product_name)
        self._product_items.append(
            {
                "name": product_name,
                "unit_price": float(product_price),
                "quantity": quantity,
            }
        )

        self._product_quantity += quantity
        self.product_price = sum(
            item["unit_price"]
            for item in self._product_items
        )

        self._set_and_validate_price(self.calculate_price())

        print(
            f"Product added: {product_name}. "
            f"New total price: ${self.total_price:.2f}"
        )

    def process_bonus_system(self, current_bonuses):
        if (
            isinstance(current_bonuses, bool)
            or not isinstance(current_bonuses, (int, float))
            or current_bonuses < 0
        ):
            raise InvalidDataError(
                "Bonus balance must be a non-negative number."
            )

        order_price = self.calculate_price()
        max_discount = order_price * 0.5
        applied_discount = min(
            float(current_bonuses),
            max_discount,
        )

        final_price = order_price - applied_discount
        cashback = final_price * 0.1
        remaining_bonuses = (
            float(current_bonuses)
            - applied_discount
            + cashback
        )

        return (
            round(final_price, 2),
            round(applied_discount, 2),
            round(remaining_bonuses, 2),
        )

        





