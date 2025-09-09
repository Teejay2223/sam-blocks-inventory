-- Raw Materials Table
CREATE TABLE IF NOT EXISTS raw_materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    qty REAL NOT NULL,
    reorder_level REAL NOT NULL
);

-- Finished Blocks Table
CREATE TABLE IF NOT EXISTS finished_blocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    block_type TEXT NOT NULL,
    qty INTEGER NOT NULL,
    date_produced TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Customers Table
CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    phone TEXT NOT NULL,
    password TEXT NOT NULL,
    role TEXT DEFAULT 'Customer'
);

PRAGMA table_info(customers);

-- Orders Table
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    qty INTEGER NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customers (id)
);

-- Order Items Table
CREATE TABLE IF NOT EXISTS order_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    item_id INTEGER NOT NULL,
    qty INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (order_id) REFERENCES orders(id)
);

-- Sales Table
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sale_date DATE NOT NULL,
    amount REAL NOT NULL
);

-- Payments Table
CREATE TABLE IF NOT EXISTS payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL,
    amount REAL NOT NULL,
    date_paid TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Pending',
    FOREIGN KEY (order_id) REFERENCES orders (id)
);

-- Products Table
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    size TEXT NOT NULL,
    price REAL NOT NULL
);

INSERT INTO products (name, description, size, price) VALUES
('Standard Block', 'A durable block suitable for general construction.', '400x200x200 mm', 50.00),
('Hollow Block', 'A lightweight block for partition walls.', '400x200x150 mm', 45.00),
('Custom Block', 'Custom-sized blocks for special projects.', 'Variable', 60.00);

