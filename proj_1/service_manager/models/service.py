
import math

from service_manager.exceptions import InvalidDataError, AccessDeniedError


class Service:
    def __init__(
        self,
        service_code,
        name,
        category,
        base_price,
        duration_minutes,
        description=None
    ):
        self._service_code = self.__validate_text(
            service_code, "Service code"
        ).upper()

        self._name = self.__validate_text(name, "Service name")

        if category is not None and not isinstance(category, str):
            raise InvalidDataError("Service category must be a string.")

        self._category = category.strip() if category else ""

        self.__validate_price(base_price)
        self.__validate_duration(duration_minutes)

        self._base_price = base_price
        self._duration_minutes = duration_minutes

        if description is not None and not isinstance(description, str):
            raise InvalidDataError("Service description must be a string.")

        self._description = description.strip() if description else ""

        self.is_active = True

    @staticmethod
    def __validate_text(value, field_name):
        """Check that a required text field is a non-empty string."""
        if not isinstance(value, str) or not value.strip():
            raise InvalidDataError(
                f"{field_name} cannot be empty and must be a string."
            )

        return value.strip()

    @staticmethod
    def __validate_price(price):
        """Check that the service price is a positive finite number."""
        if (
            isinstance(price, bool)
            or not isinstance(price, (int, float))
            or not math.isfinite(price)
            or price <= 0
        ):
            raise InvalidDataError(
                "Service price must be a positive number."
            )

    @staticmethod
    def __validate_duration(duration_minutes):
        """Check that the service duration is a positive integer."""
        if (
            isinstance(duration_minutes, bool)
            or not isinstance(duration_minutes, int)
            or duration_minutes <= 0
        ):
            raise InvalidDataError(
                "Service duration must be a positive integer in minutes."
            )

    @property
    def service_code(self):
        return self._service_code

    @property
    def name(self):
        return self._name

    @property
    def category(self):
        return self._category

    @property
    def base_price(self):
        return self._base_price

    @property
    def duration_minutes(self):
        return self._duration_minutes

    @property
    def description(self):
        return self._description

    def change_price(self, new_price, user):
        """Change the price only if the user is an administrator."""
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can change the service price."
            )

        self.__validate_price(new_price)
        self._base_price = new_price

    def change_duration(self, new_duration_minutes, user):
        """Change the duration only if the user is an administrator."""
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can change the service duration."
            )

        self.__validate_duration(new_duration_minutes)
        self._duration_minutes = new_duration_minutes

    def change_name(self, new_name, user):
        """Change the service name only if the user is an administrator."""
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can change the service name."
            )

        self._name = self.__validate_text(new_name, "Service name")

    def change_category(self, new_category, user):
        """Change the category only if the user is an administrator."""
        if not getattr(user, "is_admin", False):
            raise AccessDeniedError(
                "Only an administrator can change the service category."
            )

        if new_category is not None and not isinstance(new_category, str):
            raise InvalidDataError("Service category must be a string.")

        self._category = new_category.strip() if new_category else ""

    def __str__(self):
        return (
            f"[{self.service_code}] {self.name} | "
            f"Price: ${self.base_price:.1f} | "
            f"Duration: {self.duration_minutes} min"
        )


  
