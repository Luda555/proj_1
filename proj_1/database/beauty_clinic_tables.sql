
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(), 
    username VARCHAR(100) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    role VARCHAR(20) NOT NULL CHECK (role IN ('client', 'employee', 'admin'))
);

CREATE TABLE clients (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    email VARCHAR(255), CHECK (
    email IS NULL OR
    email ~ '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
),
    telegram_id BIGINT UNIQUE
);

CREATE TABLE employees (
    user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    specialization VARCHAR(100) NOT NULL,
    rating NUMERIC(3,2) NOT NULL DEFAULT 0,
    base_rate NUMERIC(10, 2) DEFAULT 20000 NOT NULL CHECK (base_rate >= 0),
    procedure_percent NUMERIC(5, 2) DEFAULT 30 NOT NULL CHECK (procedure_percent BETWEEN 0 AND 100),
    sales_percent NUMERIC(5, 2) DEFAULT 10 NOT NULL CHECK (sales_percent BETWEEN 0 AND 100)
);


CREATE TABLE products (
    id SERIAL PRIMARY KEY, 
    product_name VARCHAR(200) NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity >= 0),
    reserved_quantity INTEGER NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0 AND reserved_quantity <= quantity),
    price_per_item NUMERIC(10, 2) NOT NULL CHECK (price_per_item >= 0)
);

CREATE TABLE procedures (
    id SERIAL PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    service_code VARCHAR(200) NOT NULL UNIQUE,
    category VARCHAR(200) NOT NULL,
    base_price NUMERIC(10, 2) NOT NULL
        CHECK (base_price > 0),
    duration_minutes INTEGER NOT NULL
        CHECK (duration_minutes > 0),
    description TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    client_id UUID NOT NULL REFERENCES clients(user_id),

    status VARCHAR(20) NOT NULL CHECK (
        status IN ('Scheduled', 'In Progress', 'Completed', 'Cancelled')
    ),

    appointment_date DATE,
    start_time TIME,

    total_price NUMERIC(10, 2) NOT NULL CHECK (total_price >= 0),

    payment_method VARCHAR(50) CHECK (
        payment_method IN ('cash', 'card_on_delivery', 'online')
    ),

    payment_status VARCHAR(50) NOT NULL DEFAULT 'pending' CHECK (
        payment_status IN ('pending', 'paid', 'cancelled')
    ),

    fulfillment_method VARCHAR(50) CHECK (
        fulfillment_method IN ('pickup', 'clinic_courier', 'nova_poshta')
    ),

    delivery_address TEXT,

    CHECK (
        (
            fulfillment_method IN ('nova_poshta', 'clinic_courier')
            AND delivery_address IS NOT NULL
            AND TRIM(delivery_address) <> ''
        )
        OR
        (
            fulfillment_method = 'pickup'
            AND delivery_address IS NULL
        )
        OR fulfillment_method IS NULL
    ),

    CHECK (
        (appointment_date IS NULL AND start_time IS NULL)
        OR
        (appointment_date IS NOT NULL AND start_time IS NOT NULL)
    )
);

CREATE TABLE order_products (
    id SERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id INT NOT NULL REFERENCES products(id), 
    product_name VARCHAR(200) NOT NULL,
    product_price NUMERIC(10, 2) NOT NULL CHECK (product_price >= 0),
    product_quantity INTEGER NOT NULL CHECK (product_quantity > 0)
);

CREATE TABLE order_procedures (
    id SERIAL PRIMARY KEY,
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    procedure_id INT NOT NULL REFERENCES procedures(id),
    quantity INT NOT NULL CHECK (quantity > 0),
    price_per_item NUMERIC(10, 2) NOT NULL CHECK (price_per_item >= 0),
    employee_id UUID REFERENCES employees(user_id) NOT NULL
);

CREATE TABLE employee_procedures (
    employee_id UUID NOT NULL REFERENCES employees(user_id) ON DELETE CASCADE,
    procedure_id INT NOT NULL REFERENCES procedures(id),
    PRIMARY KEY(employee_id, procedure_id)
);    

CREATE TABLE employee_rating (
    id SERIAL PRIMARY KEY,
    employee_id UUID NOT NULL REFERENCES employees(user_id) ON DELETE CASCADE,
    client_id UUID NOT NULL REFERENCES clients(user_id) ON DELETE CASCADE,
    score INT  NOT NULL CHECK (score BETWEEN 1 AND 5)
);    

-- 1. Search for a client's orders
CREATE INDEX IF NOT EXISTS idx_orders_client_id
ON orders(client_id);

-- 2. Search for products in an order
CREATE INDEX IF NOT EXISTS idx_order_products_order_id
ON order_products(order_id);

-- 3. Search for sales of a specific product
CREATE INDEX IF NOT EXISTS idx_order_products_product_id
ON order_products(product_id);

-- 4. Search for procedures in an order
CREATE INDEX IF NOT EXISTS idx_order_procedures_order_id
ON order_procedures(order_id);

-- 5. Search for orders containing a specific procedure
CREATE INDEX IF NOT EXISTS idx_order_procedures_procedure_id
ON order_procedures(procedure_id);

-- 6. Search for procedures performed by an employee
CREATE INDEX IF NOT EXISTS idx_order_procedures_employee_id
ON order_procedures(employee_id);

-- 7. Search for employees qualified to perform a procedure
CREATE INDEX IF NOT EXISTS idx_employee_procedures_procedure_id
ON employee_procedures(procedure_id);

-- 8. Search for ratings submitted by a client
CREATE INDEX IF NOT EXISTS idx_employee_rating_client_id
ON employee_rating(client_id);

-- 9. Search for ratings received by an employee
CREATE INDEX IF NOT EXISTS idx_employee_rating_employee_id
ON employee_rating(employee_id);



