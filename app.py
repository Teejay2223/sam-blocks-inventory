from flask import Flask, g, render_template, request, redirect, url_for, flash, session
import sqlite3
import os
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['DATABASE'] = os.path.join(app.root_path, 'database.db')
app.secret_key = 'dev'

# Database helpers
def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        db = get_db()
        schema_path = os.path.join(app.root_path, 'schema.sql')
        print(f"Schema path: {schema_path}")  # Debugging
        with open(schema_path, 'r') as f:
            db.executescript(f.read())

@app.cli.command('init-db')
def init_db_command():
    init_db()
    print("Database initialized.")


@app.cli.command('show-customers')
def show_customers():
    """Print all customers in the database."""
    with app.app_context():
        db = get_db()
        result = db.execute('SELECT * FROM customers').fetchall()
        for row in result:
            print(dict(row))

@app.before_request
def restrict_access():
    if 'user_id' in session and session.get('role') != 'Admin':
        restricted_routes = ['/materials/add', '/orders/<int:order_id>/delete']
        if request.path in restricted_routes:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))

# --- Routes ---
@app.route('/')
def index():
    if 'user_id' not in session:
        # Not logged in: show welcome page with login/register
        return render_template('welcome.html')
    elif session.get('role') == 'Admin':
        # Admin: show dashboard or admin homepage
        return redirect(url_for('dashboard'))
    else:
        # Customer: show customer homepage or orders
        return render_template('customer_home.html', user_name=session.get('user_name'))

@app.route('/orders/add', methods=['GET', 'POST'])
def add_order():
    db = get_db()
    if request.method == 'POST':
        customer_id = int(request.form['customer_id'])
        product_id = int(request.form['product_id'])
        qty = int(request.form['qty'])

        # Get product price
        product = db.execute(
            'SELECT price FROM products WHERE id = ?',
            (product_id,)
        ).fetchone()

        if not product:
            flash("Invalid product selected.", "danger")
            return redirect(url_for('add_order'))

        unit_price = product['price']
        total_amount = unit_price * qty

        # Insert order
        db.execute(
            'INSERT INTO orders (customer_id, item_type, qty) VALUES (?, ?, ?)',
            (customer_id, str(product_id), qty)
        )
        db.commit()

        # Get last order ID
        order_id = db.execute('SELECT last_insert_rowid() as id').fetchone()['id']

        # Insert payment record with calculated amount
        db.execute(
            'INSERT INTO payments (order_id, amount, status) VALUES (?, ?, ?)',
            (order_id, total_amount, 'Pending')
        )
        db.commit()

        flash(f'Order created! Payment of ₦{total_amount:.2f} is pending.', 'success')
        return redirect(url_for('list_orders'))

    customers = db.execute('SELECT * FROM customers').fetchall()
    products = db.execute('SELECT * FROM products').fetchall()
    return render_template('orders/add.html', customers=customers, products=products)


    # Fetch customers for the dropdown in the form
    customers = db.execute('SELECT id, name FROM customers').fetchall()
    return render_template('orders/add.html', customers=customers)

@app.route('/orders/<int:order_id>/complete', methods=['POST'])
def complete_order(order_id):
    db = get_db()
    amount_paid = float(request.form['amount_paid'])
    # Record sale
    db.execute(
        'INSERT INTO sales (order_id, amount) VALUES (?, ?)',
        (order_id, amount_paid)
    )
    # Update order status (add a 'status' column to the 'orders' table)
    db.execute('UPDATE orders SET status="Completed" WHERE id=?', (order_id,))
    db.commit()
    flash('Sale recorded!', 'success')
    return redirect(url_for('list_orders'))

@app.route('/orders/<int:order_id>/update-status', methods=['POST'])
def update_order_status(order_id):
    status = request.form['status']
    db = get_db()
    db.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    db.commit()
    flash('Order status updated successfully!', 'success')
    return redirect(url_for('list_orders'))

@app.route('/orders/<int:order_id>/pay', methods=['POST'])
def record_payment(order_id):
    amount = float(request.form['amount'])
    db = get_db()
    db.execute(
        'INSERT INTO payments (order_id, amount, status) VALUES (?, ?, "Paid")',
        (order_id, amount)
    )
    db.commit()
    flash('Payment recorded successfully!', 'success')
    return redirect(url_for('view_order', order_id=order_id))

@app.route('/materials')
def list_materials():
    db = get_db()
    materials = db.execute('SELECT * FROM raw_materials').fetchall()
    low_stock_count = db.execute(
        'SELECT COUNT(*) FROM raw_materials WHERE qty < reorder_level'
    ).fetchone()[0]
    return render_template('materials/list.html', materials=materials, low_stock_count=low_stock_count)


@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/calculator')
def calculator():
    return render_template('calculator.html')

@app.route('/materials/add', methods=['GET', 'POST'])
def add_material():
    if request.method == 'POST':
        name = request.form['name']
        qty = float(request.form['qty'])
        reorder_level = float(request.form['reorder_level'])
        db = get_db()
        db.execute(
            'INSERT INTO raw_materials (name, qty, reorder_level) VALUES (?, ?, ?)',
            (name, qty, reorder_level)
        )
        db.commit()
        flash('Material added successfully!', 'success')
        return redirect(url_for('list_materials'))
    return render_template('materials/add.html')

@app.route('/materials/<int:material_id>/edit', methods=['GET', 'POST'])
def edit_material(material_id):
    db = get_db()
    material = db.execute('SELECT * FROM raw_materials WHERE id = ?', (material_id,)).fetchone()
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        size = request.form['size']
        price = request.form['price']
        db.execute('UPDATE raw_materials SET name=?, description=?, size=?, price=? WHERE id=?',
                   (name, description, size, price, material_id))
        db.commit()
        flash('Material updated successfully!', 'success')
        return redirect(url_for('list_materials'))
    return render_template('materials/edit.html', material=material)

# Order Management
@app.route('/orders')
def list_orders():
    db = get_db()
    orders = db.execute('''
        SELECT orders.id, customers.name AS customer_name, orders.item_type, orders.qty
        FROM orders        JOIN customers ON orders.customer_id = customers.id
    ''').fetchall()
    return render_template('orders/list.html', orders=orders)

@app.route('/orders/<int:order_id>')
def view_order(order_id):
    db = get_db()
    # Fetch the order details
    order = db.execute('''
        SELECT orders.id, customers.name AS customer_name, orders.item_type, orders.qty
        FROM orders
        JOIN customers ON orders.customer_id = customers.id
        WHERE orders.id = ?
    ''', (order_id,)).fetchone()

    if not order:
        flash('Order not found!', 'danger')
        return redirect(url_for('list_orders'))

    return render_template('orders/view.html', order=order)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        new_password = request.form['new_password']
        hashed_password = generate_password_hash(new_password)

        db = get_db()
        user = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()

        if user:
            db.execute('UPDATE customers SET password = ? WHERE email = ?', (hashed_password, email))
            db.commit()
            flash('Password reset successful. You can now log in with your new password.', 'success')
            return redirect(url_for('login'))
        else:
            flash('Email not found. Please check and try again.', 'danger')

    return render_template('forgot_password.html')

@app.route('/orders/<int:order_id>/delete', methods=['POST'])
def delete_order(order_id):
    db = get_db()
    db.execute('DELETE FROM orders WHERE id = ?', (order_id,))
    db.commit()
    flash('Order deleted successfully!', 'success')
    return redirect(url_for('list_orders'))

@app.route('/inspect-orders')
def inspect_orders():
    db = get_db()
    schema = db.execute("PRAGMA table_info(orders);").fetchall()
    return {'schema': [dict(column) for column in schema]}

# Customer Management
@app.route('/customers')
def list_customers():
    # Example customer data
    db = get_db()
    customers = db.execute('SELECT * FROM customers').fetchall()
    return render_template('customer/list.html', customers=customers)

@app.route('/customers/add', methods=['GET', 'POST'])
def add_customer():
    if request.method == 'POST':
        name = request.form['name']
        phone = request.form['phone']
        address = request.form['address']

        # Save the customer to the database
        db = get_db()
        db.execute('INSERT INTO customers (name, phone, address) VALUES (?, ?, ?)', (name, phone, address))
        db.commit()

        # Flash success message
        flash('Customer added successfully!', 'success')
        return redirect(url_for('list_customers'))

    return render_template('customer/add.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = request.form['password']
        hashed_password = generate_password_hash(password)

        db = get_db()

        # Check if email already exists
        existing_user = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()
        if existing_user:
            flash('Email already registered. Please use a different email or log in.', 'danger')
            return redirect(url_for('register'))

        # Insert new user
        db.execute(
            'INSERT INTO customers (name, email, phone, password) VALUES (?, ?, ?, ?)',
            (name, email, phone, hashed_password)
        )
        db.commit()

        flash('Registration successful! You can now log in.', 'success')
        return redirect(url_for('login'))

    # For GET request → show the form
    return render_template('register.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        
        db = get_db()
        user = db.execute('SELECT * FROM customers WHERE email = ?', (email,)).fetchone()

        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_name'] = user['name']
            # Set role: you may need to add a user column to your customers table
            session['role'] = user['role'] if user['role']  else 'Customer'
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid login credentials. Please try again.', 'danger')
    return render_template('login.html')

@app.route('/sales')
def sales_report():
    # Demo data for presentation
    months = ["January", "February", "March", "April", "May", "June"]
    total_sales = [1200, 1900, 3000, 2500, 2800, 3200]

    return render_template('sales.html', months=months, total_sales=total_sales)


@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role') != 'Admin':
        flash('Access denied: Admins only.', 'danger')
        return redirect(url_for('login'))
    db = get_db()
    # Example query for monthly production
    production_data = db.execute('''
        SELECT strftime('%m', date_produced) AS month, SUM(qty) AS total_qty
        FROM finished_blocks
        GROUP BY month
        ORDER BY month
    ''').fetchall()

    months = [row['month'] for row in production_data]
    quantities = [row['total_qty'] for row in production_data]

    return render_template('dashboard.html',
                           user_name=session.get('user_name'),
                           months=months,
                           quantities=quantities)

@app.route('/logout', methods=['GET', 'POST'])
def logout():
    if request.method == 'POST':
        session.clear()  # Clear the session
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))  # Redirect to the homepage
    return render_template('logout.html')

@app.route('/logout_confirm', methods=['POST'])
def logout_confirm():
    # Perform logout logic here
    session.clear()  # Example: Clear the session
    return redirect(url_for('login'))  # Redirect to login page

@app.route('/record-production', methods=['GET', 'POST'])
def record_production():
    conn = get_db()
    warning = None

    if request.method == 'POST':
        block_type = request.form['block_type']
        qty = int(request.form['qty'])
        date_produced = request.form['date_produced']

        # Save production record
        conn.execute(
            'INSERT INTO finished_blocks (block_type, qty, date_produced) VALUES (?, ?, ?)',
            (block_type, qty, date_produced)
        )
        conn.commit()
        flash('Production recorded successfully!', 'success')
        return redirect(url_for('record_production'))

    # Fetch recent productions
    productions = conn.execute('SELECT * FROM finished_blocks ORDER BY date_produced DESC LIMIT 10').fetchall()

    # Fetch production summary
    summary = conn.execute('''
        SELECT block_type, SUM(qty) AS total_qty
        FROM finished_blocks
        GROUP BY block_type
    ''').fetchall()

    return render_template('record_production.html', productions=productions, summary=summary, warning=warning)

@app.route('/search', methods=['GET'])
def search():
    query = request.args.get('q')
    db = get_db()
    results = db.execute('SELECT * FROM customers WHERE name LIKE ?', ('%' + query + '%',)).fetchall()
    return render_template('search_results.html', results=results)

@app.route('/products')
def list_products():
    db = get_db()
    products = db.execute('SELECT * FROM products').fetchall()
    return render_template('products.html', products=products)

@app.route('/sales')
def sales():
    db = get_db()
    sales_data = db.execute('''
        SELECT strftime('%m', sale_date) AS month, SUM(amount) AS total_sales
        FROM sales
        GROUP BY month
        ORDER BY month
    ''').fetchall()

    months = [row['month'] for row in sales_data]
    total_sales = [row['total_sales'] for row in sales_data]

    return render_template('sales.html', months=months, total_sales=total_sales)

@app.route('/sales/add', methods=['GET', 'POST'])
def add_sales():
    if request.method == 'POST':
        sale_date = request.form['sale_date']
        amount = float(request.form['amount'])

        # Insert the sales record into the database
        db = get_db()
        db.execute('INSERT INTO sales (sale_date, amount) VALUES (?, ?)', (sale_date, amount))
        db.commit()

        flash('Sales record added successfully!', 'success')
        return redirect(url_for('sales'))  # Redirect to the sales chart page

    return render_template('sales/add.html')

@app.route('/sales/list')
def list_sales():
    db = get_db()
    sales = db.execute('SELECT * FROM sales ORDER BY sale_date DESC').fetchall()
    return render_template('sales_list.html', sales=sales)

@app.route('/customer_home')
def customer_home():
    if 'user_id' not in session or session.get('role') != 'Customer':
        return redirect(url_for('login'))
    return render_template('customer_home.html', user_name=session.get('user_name'))
#promote someone to admin
@app.route('/make-admin')
def make_admin():
    db = get_db()
    admin_email = "tijjanishuaibmatopkm@gmail.com"  # your real email

    # Promote the user with this email to admin
    db.execute("UPDATE customers SET role=? WHERE email=?", ('Admin', admin_email))
    db.commit()

    result = db.execute('SELECT * FROM customers WHERE email=?', (admin_email,)).fetchone()
    print(dict(result) if result else "No user found with that email")

    return f"User {admin_email} promoted to Admin!"



from app import get_db, app

with app.app_context():
    db = get_db()
    result = db.execute('SELECT * FROM customers').fetchall()
    print(result)

# Run the app
if __name__ == '__main__':
    with app.app_context():
        # Example: Initialize the database or run some queries
        db = get_db()
        print("Database connection established.")
    app.run(debug=True)