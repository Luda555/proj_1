
import re
import math

from service_manager.exceptions import InvalidDataError


class User:
    """Base class for all users (Client, Admin, Employee)"""

    def __init__(self, username, phone):
        if not isinstance(username, str) or not username.strip():
            raise InvalidDataError("Username cannot be empty.")

        phone_pattern = r"^\+?[\d\s\-]{7,15}$"
        if not re.fullmatch(phone_pattern, str(phone).strip()):
            raise InvalidDataError(
                f"Invalid phone number format: {phone}"
            )

        self.username = username.strip()
        self.phone = str(phone).strip()

    @property
    def is_admin(self):
        """By default, the user is not an admin"""
        return False


class Client(User):
    def __init__(self, username, phone, email=None, telegram_id=None):
        super().__init__(username, phone)

        if email is not None:
            if not isinstance(email, str):
                raise InvalidDataError("Email must be a string.")

            email = email.strip()

            if email and ("@" not in email or "." not in email):
                raise InvalidDataError(
                    f"Invalid email format: {email}"
                )

        self.email = email
        self.telegram_id = telegram_id
        self.order_history = []  # list of all client orders

    def add_to_order_history(self, order):
        self.order_history.append(order)

    def __str__(self):
        return (
            f"Client: {self.username} | Phone: {self.phone} | "
            f"Active Orders: {len(self.order_history)}"
        )


class Admin(User):
    def __init__(self, username, phone, employee_id):
        super().__init__(username, phone)

        if employee_id is None or not str(employee_id).strip():
            raise InvalidDataError("Employee ID cannot be empty.")

        self.employee_id = str(employee_id).strip()

    @property
    def is_admin(self):
        """Admin is always True"""
        return True

    def __str__(self):
        return f"Admin: {self.username} (ID: {self.employee_id})"


class Employee(User):
    def __init__(
        self,
        username,
        phone,
        specialization,
        base_rate=20000,
        procedure_percent=30,
        sales_percent=10
    ):
        super().__init__(username, phone)

        if (
            not isinstance(specialization, str)
            or not specialization.strip()
        ):
            raise InvalidDataError(
                "Specialization cannot be empty."
            )

        # Validate the employee's base rate and commission percentages.
        self.__validate_number(
            base_rate, "Base rate", minimum=0
        )
        self.__validate_number(
            procedure_percent,
            "Procedure percent",
            minimum=0,
            maximum=100
        )
        self.__validate_number(
            sales_percent,
            "Sales percent",
            minimum=0,
            maximum=100
        )

        self.specialization = specialization.strip()
        self._ratings = []
        self.services_can_do = []

        self.base_rate = base_rate
        self.procedure_percent = procedure_percent
        self.sales_percent = sales_percent

    @staticmethod
    def __validate_number(
        value, field_name, minimum=0, maximum=None
    ):
        """Validate a numeric value and its allowed range."""
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < minimum
            or (maximum is not None and value > maximum)
        ):
            if maximum is None:
                raise InvalidDataError(
                    f"{field_name} must be a number "
                    f"greater than or equal to {minimum}."
                )

            raise InvalidDataError(
                f"{field_name} must be between "
                f"{minimum} and {maximum}."
            )

    def add_rating(self, score):
        try:
            if isinstance(score, bool):
                raise ValueError

            if isinstance(score, float) and not score.is_integer():
                raise ValueError

            if not re.fullmatch(r"[+-]?\d+", str(score).strip()):
                raise ValueError

            val = int(score)

            if val < 1 or val > 5:
                raise InvalidDataError(
                    "Rating must be an integer between 1 and 5."
                )

            self._ratings.append(val)

        except (ValueError, TypeError):
            raise InvalidDataError(
                "Rating must be a valid whole number."
            ) from None

    @property
    def rating(self):
        if not self._ratings:
            return 0.0

        return round(sum(self._ratings) / len(self._ratings), 1)

    @property
    def is_admin(self):
        return False

    def calculate_salary(self, procedure_revenue, sales_revenue):
        # Check that revenue values are valid and non-negative.
        self.__validate_number(
            procedure_revenue, "Procedure revenue", minimum=0
        )
        self.__validate_number(
            sales_revenue, "Sales revenue", minimum=0
        )

        bonus_procedures = procedure_revenue * (
            self.procedure_percent / 100
        )
        bonus_sales = sales_revenue * (
            self.sales_percent / 100
        )
        total_salary = (
            self.base_rate + bonus_procedures + bonus_sales
        )

        return total_salary

    def __str__(self):
        rating_display = (
            "New" if self.rating == 0.0 else f"{self.rating}"
        )
        services_str = (
            ", ".join(self.services_can_do)
            if self.services_can_do
            else "None"
        )

        return (
            f"Specialist: {self.username} ({self.specialization}) | "
            f"Rating: {rating_display} | Phone: {self.phone} | "
            f"Can do: [{services_str}]"
        )




