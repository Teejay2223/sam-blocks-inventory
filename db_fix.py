from app import get_db, app

with app.app_context():
    db = get_db()

    # 1. Try adding role column (ignore if it already exists)
    try:
        db.execute('ALTER TABLE customers ADD COLUMN role TEXT DEFAULT "Customer"')
        print("Role column added.")
    except Exception as e:
        print("Role column probably already exists:", e)

    # 2. Promote your account
    db.execute(
        'UPDATE customers SET role="Admin" WHERE email=?',
        ("tijjanishuaibmatopkm@gmail.com",)
    )
    db.commit()

    # 3. Show result
    result = db.execute(
        'SELECT id, name, email, role FROM customers WHERE email=?',
        ("tijjanishuaibmatopkm@gmail.com",)
    ).fetchone()
    print(dict(result))
