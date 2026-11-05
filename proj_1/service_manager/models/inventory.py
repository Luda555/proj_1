
from service_manager.exceptions import InvalidDataError, AccessDeniedError


class Inventory:
    def __init__(self, product_name, quantity, price_per_item):
        self.__validate_quantity(quantity)
        self.__validate_price_per_item(price_per_item)

        self._product_name = product_name.strip()
        self._quantity = quantity
        self._price_per_item = price_per_item
        self._reserved_quantity = 0

    def __validate_price_per_item(self, price):
        if price <= 0:
            raise InvalidDataError("Product price must be greater than zero.")

    def __validate_quantity(self, quantity):
        if quantity <= 0:
            raise InvalidDataError("Quantity must be greater than zero.")

    @property
    def product_name(self):
        return self._product_name

    @property
    def quantity(self):
        return self._quantity

    @property
    def price_per_item(self):
        return self._price_per_item

    @property
    def reserved_quantity(self):
        return self._reserved_quantity

    @property
    def available_quantity(self):
        return self._quantity - self._reserved_quantity

    def reserve_product(self, amount):
        if amount <= 0:
            raise InvalidDataError("Amount must be greater than zero.")

        if self.available_quantity < amount:
            raise InvalidDataError("Not enough available products to reserve.")

        self._reserved_quantity += amount

    def release_reserved_product(self, amount):
        if amount <= 0:
            raise InvalidDataError("Amount must be greater than zero.")

        if self._reserved_quantity < amount:
            raise InvalidDataError("Not enough reserved products to release.")

        self._reserved_quantity -= amount

    def use_reserved_product(self, amount):
        if amount <= 0:
            raise InvalidDataError("Amount must be greater than zero.")

        if self._reserved_quantity < amount:
            raise InvalidDataError("Not enough reserved products.")

        self._quantity -= amount
        self._reserved_quantity -= amount

        if self.available_quantity < 5:
            print(
                f"WARNING: Low stock for {self._product_name}! "
                f"Only {self.available_quantity} left."
            )

    def use_product(self, amount):
        if amount <= 0:
            raise InvalidDataError("Amount must be greater than zero.")

        if self.available_quantity < amount:
            raise InvalidDataError("Not enough products in inventory.")

        self._quantity -= amount

        if self.available_quantity < 5:
            print(
                f"WARNING: Low stock for {self._product_name}! "
                f"Only {self.available_quantity} left."
            )

    def restock(self, amount, user):
        if not user.is_admin:
            raise AccessDeniedError("Only an administrator can change quantity.")

        if amount <= 0:
            raise InvalidDataError("Amount must be greater than zero.")

        self._quantity += amount

        



    