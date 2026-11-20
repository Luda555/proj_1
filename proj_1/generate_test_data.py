
import os
import random
from datetime import date, time, timedelta
from decimal import Decimal
import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL is not set")


def generate_users(conn):
    """create users"""

    users = []

    roles = (
        ["client"] * 500
        + ["employee"] * 10
        + ["admin"]
    )

    for number, role in enumerate(roles, start=1):
        username = f"Test User {number}"
        phone = f"+38050{number:06d}"

        users.append((username, phone, role))

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO users (username, phone, role)
            VALUES (%s, %s, %s)
            """,
            users
        )

    print(f"Created {len(users)} users.")


def generate_clients(conn):
    """Creates test client records."""

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id
            FROM users
            WHERE role = 'client'
            ORDER BY phone;
        """)

        client_ids = cur.fetchall()

        clients = []

        for number, (user_id,) in enumerate(client_ids, start=1):
            email = f"client{number:03d}@example.com"

            telegram_id = (
                7000000000 + number
                if number <= 300
                else None
            )

            clients.append((user_id, email, telegram_id))

        cur.executemany(
            """
            INSERT INTO clients (user_id, email, telegram_id)
            VALUES (%s, %s, %s)
            """,
            clients
        )

    print(f"Created {len(clients)} clients.")



def generate_employees(conn):
    """Creates test employee records."""

    specializations = [
        "Cosmetologist",
        "Dermatologist",
        "Massage Therapist",
        "Hardware Cosmetologist",
        "Aesthetician",
        "Cosmetologist",
        "Massage Therapist",
        "Aesthetician",
        "Dermatologist",
        "Hardware Cosmetologist"
    ]

    employees = []

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id
            FROM users
            WHERE role = 'employee'
            ORDER BY phone;
        """)

        employee_ids = cur.fetchall()

        for number, (user_id,) in enumerate(employee_ids):
            employees.append((
                user_id,
                specializations[number],
                round(random.uniform(4.0, 5.0), 2),
                random.choice([18000, 20000, 22000, 25000]),
                random.choice([25, 30, 35]),
                random.choice([5, 10, 12])
            ))

        cur.executemany(
            """
            INSERT INTO employees (
                user_id,
                specialization,
                rating,
                base_rate,
                procedure_percent,
                sales_percent
            )
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            employees
        )

    print(f"Created {len(employees)} employees.")



def generate_procedures(conn):
    """Creates test procedures."""

    procedures = [
        # Facial Treatments
        ("Deep Facial Cleansing", "FAC-001", "Facial Treatments", 1200, 90),
        ("Hydrating Facial", "FAC-002", "Facial Treatments", 1000, 60),
        ("Anti-Aging Facial", "FAC-003", "Facial Treatments", 1600, 90),
        ("Sensitive Skin Treatment", "FAC-004", "Facial Treatments", 1100, 60),
        ("Acne Treatment", "FAC-005", "Facial Treatments", 1400, 75),
        ("Express Facial", "FAC-006", "Facial Treatments", 700, 30),

        # Peels
        ("Chemical Peel", "PEL-001", "Peels", 1800, 60),
        ("Enzyme Peel", "PEL-002", "Peels", 1000, 45),
        ("Mandelic Acid Peel", "PEL-003", "Peels", 1500, 45),
        ("Salicylic Acid Peel", "PEL-004", "Peels", 1600, 60),
        ("Lactic Acid Peel", "PEL-005", "Peels", 1400, 45),
        ("PRX-T33 Peel", "PEL-006", "Peels", 2500, 60),

        # Massage
        ("Classic Facial Massage", "MAS-001", "Massage", 800, 40),
        ("Lymphatic Facial Massage", "MAS-002", "Massage", 900, 45),
        ("Relaxing Body Massage", "MAS-003", "Massage", 1500, 60),
        ("Therapeutic Back Massage", "MAS-004", "Massage", 1200, 45),
        ("Anti-Cellulite Massage", "MAS-005", "Massage", 1700, 60),
        ("Hot Stone Massage", "MAS-006", "Massage", 2000, 75),

        # Hardware Cosmetology
        ("Ultrasound Facial Cleaning", "HWC-001", "Hardware Cosmetology", 1300, 60),
        ("Microcurrent Therapy", "HWC-002", "Hardware Cosmetology", 1500, 45),
        ("RF Lifting", "HWC-003", "Hardware Cosmetology", 2200, 60),
        ("Hydrofacial", "HWC-004", "Hardware Cosmetology", 1900, 60),
        ("LED Light Therapy", "HWC-005", "Hardware Cosmetology", 900, 30),
        ("Ultrasound Skin Lifting", "HWC-006", "Hardware Cosmetology", 1800, 45),

        # Skin Rejuvenation
        ("Collagen Therapy", "SKR-001", "Skin Rejuvenation", 2000, 60),
        ("Vitamin Facial Treatment", "SKR-002", "Skin Rejuvenation", 1300, 45),
        ("Skin Hydration Therapy", "SKR-003", "Skin Rejuvenation", 1600, 60),
        ("Brightening Treatment", "SKR-004", "Skin Rejuvenation", 1400, 45),
        ("Anti-Wrinkle Treatment", "SKR-005", "Skin Rejuvenation", 2300, 75),
        ("Skin Recovery Treatment", "SKR-006", "Skin Rejuvenation", 1700, 60),
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO procedures (
                name,
                service_code,
                category,
                base_price,
                duration_minutes
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            procedures
        )

    print(f"Created {len(procedures)} procedures.")


def generate_employee_procedures(conn):
    """Assigns procedures to employees based on their specializations."""

    specialization_categories = {
        "Aesthetician": [
            "Facial Treatments",
            "Skin Rejuvenation"
        ],
        "Cosmetologist": [
            "Facial Treatments",
            "Peels",
            "Skin Rejuvenation"
        ],
        "Dermatologist": [
            "Peels",
            "Skin Rejuvenation"
        ],
        "Hardware Cosmetologist": [
            "Hardware Cosmetology"
        ],
        "Massage Therapist": [
            "Massage"
        ]
    }

    assignments = []

    with conn.cursor() as cur:
        cur.execute("""
            SELECT user_id, specialization
            FROM employees;
        """)
        employees = cur.fetchall()

        cur.execute("""
            SELECT id, category
            FROM procedures
            WHERE is_active = TRUE;
        """)
        procedures = cur.fetchall()

        for employee_id, specialization in employees:
            categories = specialization_categories.get(specialization, [])

            for procedure_id, category in procedures:
                if category in categories:
                    assignments.append((employee_id, procedure_id))

        cur.executemany("""
            INSERT INTO employee_procedures (
                employee_id,
                procedure_id
            )
            VALUES (%s, %s);
        """, assignments)

    print(f"Created {len(assignments)} employee-procedure assignments.")



def generate_products(conn):
    """Creates test products with stock quantities and prices."""

    products = [
        # Cleansers
        ("Cleansing Gel", 35, 450),
        ("Micellar Water", 40, 380),
        ("Cleansing Foam", 30, 420),
        ("Makeup Remover", 25, 350),
        ("Gentle Cleansing Milk", 28, 390),
        ("Enzyme Powder Cleanser", 20, 520),
        ("Deep Cleansing Gel", 32, 480),
        ("Sensitive Skin Cleanser", 22, 460),
        ("Cleansing Oil", 26, 550),

        # Creams
        ("Hydrating Face Cream", 30, 650),
        ("Anti-Aging Cream", 20, 950),
        ("Night Repair Cream", 24, 850),
        ("Day Protection Cream", 28, 700),
        ("Sensitive Skin Cream", 25, 620),
        ("Eye Contour Cream", 18, 780),
        ("Nourishing Face Cream", 22, 720),
        ("Mattifying Face Cream", 20, 590),
        ("Barrier Repair Cream", 26, 820),

        # Serums
        ("Hyaluronic Acid Serum", 25, 750),
        ("Vitamin C Serum", 20, 900),
        ("Niacinamide Serum", 28, 680),
        ("Retinol Serum", 15, 1100),
        ("Peptide Serum", 18, 1200),
        ("Collagen Serum", 22, 850),
        ("Brightening Serum", 20, 790),
        ("Soothing Serum", 24, 700),
        ("Anti-Aging Serum", 16, 1250),

        # Masks
        ("Hydrating Face Mask", 30, 350),
        ("Purifying Clay Mask", 25, 400),
        ("Alginate Mask", 35, 320),
        ("Collagen Face Mask", 22, 480),
        ("Calming Face Mask", 28, 360),
        ("Brightening Mask", 20, 430),
        ("Detox Face Mask", 24, 390),
        ("Nourishing Face Mask", 26, 420),
        ("Anti-Aging Mask", 18, 550),

        # Skin Care Products
        ("SPF 50 Sunscreen", 40, 600),
        ("Exfoliating Toner", 22, 580),
        ("Facial Toner", 30, 400),
        ("Lip Care Balm", 35, 250),
        ("Eye Patches", 28, 450),
        ("Thermal Water Spray", 32, 300),
        ("Facial Mist", 25, 350),
        ("Skin Recovery Lotion", 20, 650),
        ("Body Care Lotion", 24, 500),
    ]

    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO products (
                product_name,
                quantity,
                price_per_item
            )
            VALUES (%s, %s, %s)
            """,
            products
        )

    print(f"Created {len(products)} products.")




def generate_orders(conn):
    """Generates 3000 historical orders for 2025."""

    # Load existing clients, procedures, products and employees
    with conn.cursor() as cur:
        cur.execute("""
            SELECT user_id
            FROM clients;
        """)
        client_ids = [row[0] for row in cur.fetchall()]

        cur.execute("""
            SELECT id, base_price
            FROM procedures
            WHERE is_active = TRUE;
        """)
        procedures = cur.fetchall()

        cur.execute("""
            SELECT id, product_name, price_per_item
            FROM products;
        """)
        products = cur.fetchall()

        cur.execute("""
            SELECT procedure_id, employee_id
            FROM employee_procedures;
        """)
        assignments = cur.fetchall()

    if not client_ids:
        raise ValueError("No clients found.")

    if not procedures:
        raise ValueError("No active procedures found.")

    if not products:
        raise ValueError("No products found.")

    # Map procedures to employees
    procedure_employees = {}

    for procedure_id, employee_id in assignments:
        procedure_employees.setdefault(
            procedure_id, []
        ).append(employee_id)

    available_procedures = [
        procedure
        for procedure in procedures
        if procedure[0] in procedure_employees
    ]

    if not available_procedures:
        raise ValueError("No assigned employees for procedures.")

    # Give some clients a higher probability of returning
    random.shuffle(client_ids)

    client_weights = [
        5 if index < 100
        else 2 if index < 250
        else 1
        for index in range(len(client_ids))
    ]

    # 70% procedures, 20% products, 10% mixed
    order_types = (
        ["procedure"] * 2100
        + ["product"] * 600
        + ["mixed"] * 300
    )
    random.shuffle(order_types)

    # Historical statuses: 90% completed, 10% cancelled
    statuses = (
        ["Completed"] * 2700
        + ["Cancelled"] * 300
    )
    random.shuffle(statuses)

    procedure_rows = []
    product_rows = []

    with conn.cursor() as cur:

        for order_type, status in zip(order_types, statuses):

            client_id = random.choices(
                client_ids,
                weights=client_weights,
                k=1
            )[0]

            has_procedures = order_type in (
                "procedure", "mixed"
            )

            has_products = order_type in (
                "product", "mixed"
            )

            appointment_date = None
            start_time = None

            selected_procedures = []
            selected_products_data = []

            total_price = Decimal("0")

            # Generate procedure
            if has_procedures:

                procedure_id, procedure_price = random.choice(
                    available_procedures
                )

                employee_id = random.choice(
                    procedure_employees[procedure_id]
                )

                selected_procedures.append((
                    procedure_id,
                    employee_id,
                    procedure_price
                ))

                total_price += Decimal(str(procedure_price))

                # Generate appointment date in 2025
                while True:
                    appointment_date = (
                        date(2025, 1, 1)
                        + timedelta(days=random.randint(0, 364))
                    )

                    # Clinic works Monday-Saturday
                    if appointment_date.weekday() != 6:
                        break

                # Start time from 09:00 to 16:00
                slot = random.randint(0, 14)

                start_time = time(
                    9 + slot // 2,
                    30 * (slot % 2)
                )

            # Generate products
            if has_products:

                products_count = random.randint(1, 3)

                selected_products = random.sample(
                    products,
                    k=min(products_count, len(products))
                )

                for product_id, product_name, product_price in selected_products:

                    quantity = random.randint(1, 3)

                    selected_products_data.append((
                        product_id,
                        product_name,
                        product_price,
                        quantity
                    ))

                    total_price += (
                        Decimal(str(product_price)) * quantity
                    )

            # Fulfillment method
            fulfillment_method = None
            delivery_address = None

            if has_products:

                fulfillment_method = random.choices(
                    ["pickup", "clinic_courier", "nova_poshta"],
                    weights=[55, 25, 20],
                    k=1
                )[0]

                if fulfillment_method != "pickup":
                    delivery_address = (
                        f"Test delivery address "
                        f"{random.randint(1, 999)}, Kyiv"
                    )

            # Payment method
            if fulfillment_method in (
                "clinic_courier", "nova_poshta"
            ):
                payment_method = random.choice([
                    "cash",
                    "card_on_delivery",
                    "online"
                ])
            else:
                payment_method = random.choice([
                    "cash",
                    "online"
                ])

            # Payment status
            payment_status = (
                "paid"
                if status == "Completed"
                else "cancelled"
            )

            # Insert order
            cur.execute(
                """
                INSERT INTO orders (
                    client_id,
                    status,
                    appointment_date,
                    start_time,
                    total_price,
                    payment_method,
                    payment_status,
                    fulfillment_method,
                    delivery_address
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    client_id,
                    status,
                    appointment_date,
                    start_time,
                    total_price,
                    payment_method,
                    payment_status,
                    fulfillment_method,
                    delivery_address
                )
            )

            order_id = cur.fetchone()[0]

            # Prepare procedure order lines
            for procedure_id, employee_id, price in selected_procedures:

                procedure_rows.append((
                    order_id,
                    procedure_id,
                    1,
                    price,
                    employee_id
                ))

            # Prepare product order lines
            for product_id, product_name, price, quantity in selected_products_data:

                product_rows.append((
                    order_id,
                    product_id,
                    product_name,
                    price,
                    quantity
                ))

        # Insert procedure lines
        if procedure_rows:
            cur.executemany(
                """
                INSERT INTO order_procedures (
                    order_id,
                    procedure_id,
                    quantity,
                    price_per_item,
                    employee_id
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                procedure_rows
            )

        # Insert product lines
        if product_rows:
            cur.executemany(
                """
                INSERT INTO order_products (
                    order_id,
                    product_id,
                    product_name,
                    product_price,
                    product_quantity
                )
                VALUES (%s, %s, %s, %s, %s);
                """,
                product_rows
            )

    print("Created 3000 orders.")
    print(f"Created {len(procedure_rows)} procedure lines.")
    print(f"Created {len(product_rows)} product lines.")








def main():
    """Connects to the database and generates test data."""

    with psycopg.connect(DATABASE_URL) as conn:

        with conn.cursor() as cur:
            cur.execute("SELECT version();")
            print(cur.fetchone()[0])

        # Generate users
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users;")
            users_count = cur.fetchone()[0]

        if users_count == 0:
            print("Generating users...")
            generate_users(conn)
        else:
            print(f"Users already exist: {users_count}. Skipping.")

        # Generate clients
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM clients;")
            clients_count = cur.fetchone()[0]

        if clients_count == 0:
            print("Generating clients...")
            generate_clients(conn)
        else:
            print(f"Clients already exist: {clients_count}. Skipping.")

        # Generate employees
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM employees;")
            employees_count = cur.fetchone()[0]

        if employees_count == 0:
            print("Generating employees...")
            generate_employees(conn)
        else:
            print(f"Employees already exist: {employees_count}. Skipping.")

        # Generate procedures
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM procedures;")
            procedures_count = cur.fetchone()[0]

        if procedures_count == 0:
            print("Generating procedures...")
            generate_procedures(conn)
        else:
            print(
                f"Procedures already exist: "
                f"{procedures_count}. Skipping."
            )

        # Generate employee-procedure assignments
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM employee_procedures;"
            )
            assignments_count = cur.fetchone()[0]

        if assignments_count == 0:
            print("Generating employee-procedure assignments...")
            generate_employee_procedures(conn)
        else:
            print(
                f"Employee-procedure assignments already exist: "
                f"{assignments_count}. Skipping."
            )

        # Generate products
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM products;")
            products_count = cur.fetchone()[0]

        if products_count == 0:
            print("Generating products...")
            generate_products(conn)
        else:
            print(
                f"Products already exist: "
                f"{products_count}. Skipping."
            )

        # Generate orders
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM orders;")
            orders_count = cur.fetchone()[0]

        if orders_count == 0:
            print("Generating orders...")
            generate_orders(conn)
        else:
            print(
                f"Orders already exist: "
                f"{orders_count}. Skipping."
            )

        # Verify generated data
        with conn.cursor() as cur:
            cur.execute("""
                SELECT
                    (SELECT COUNT(*) FROM users),
                    (SELECT COUNT(*) FROM clients),
                    (SELECT COUNT(*) FROM employees),
                    (SELECT COUNT(*) FROM procedures),
                    (SELECT COUNT(*) FROM employee_procedures),
                    (SELECT COUNT(*) FROM products),
                    (SELECT COUNT(*) FROM orders),
                    (SELECT COUNT(*) FROM order_procedures),
                    (SELECT COUNT(*) FROM order_products);
            """)

            result = cur.fetchone()

        print("\nDatabase records:")
        print(f"Users: {result[0]}")
        print(f"Clients: {result[1]}")
        print(f"Employees: {result[2]}")
        print(f"Procedures: {result[3]}")
        print(f"Employee-procedure assignments: {result[4]}")
        print(f"Products: {result[5]}")
        print(f"Orders: {result[6]}")
        print(f"Procedure order lines: {result[7]}")
        print(f"Product order lines: {result[8]}")

    print("\nData generation completed!")


if __name__ == "__main__":
    main()
