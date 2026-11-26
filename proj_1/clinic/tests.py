from django.test import SimpleTestCase
from .models import (
    User,
    Client,
    Employee,
    Product,
    Procedure,
    Order,
    OrderProduct,
    OrderProcedure,
    EmployeeProcedure,
    EmployeeRating,
)


class ClinicModelsTest(SimpleTestCase):

    def test_models_use_existing_database_tables(self):
        models = [
            User,
            Client,
            Employee,
            Product,
            Procedure,
            Order,
            OrderProduct,
            OrderProcedure,
            EmployeeProcedure,
            EmployeeRating,
        ]

        for model in models:
            self.assertFalse(model._meta.managed)

    def test_models_have_correct_table_names(self):
        expected_tables = {
            User: "users",
            Client: "clients",
            Employee: "employees",
            Product: "products",
            Procedure: "procedures",
            Order: "orders",
            OrderProduct: "order_products",
            OrderProcedure: "order_procedures",
            EmployeeProcedure: "employee_procedures",
            EmployeeRating: "employee_rating",
        }

        for model, table_name in expected_tables.items():
            self.assertEqual(model._meta.db_table, table_name)            
