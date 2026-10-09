from flask import Flask, request, redirect, url_for, session, flash
from flask import render_template_string, send_file
import sqlite3
import os
import shutil
import functools
from datetime import datetime, date


# =========================================================
# PANDEY KIRANA STORE
# FRESH PROJECT
# STEP 1 - 46
# PART 1
# =========================================================

app = Flask(__name__)

app.secret_key = os.environ.get("SECRET_KEY", "pandey_kirana_store_2026")

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE = os.path.join(
    BASE_DIR,
    "database.db"
)


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db():

    db = sqlite3.connect(
        DATABASE,
        timeout=30,
        check_same_thread=False
    )

    db.row_factory = sqlite3.Row

    db.execute(
        "PRAGMA busy_timeout = 30000"
    )

    db.execute(
        "PRAGMA foreign_keys = ON"
    )

    return db


# =========================================================
# DATABASE HELPERS
# =========================================================

def get_columns(db, table):

    rows = db.execute(
        f"PRAGMA table_info({table})"
    ).fetchall()

    return [
        row["name"]
        for row in rows
    ]


def add_column(
    db,
    table,
    column,
    definition
):

    if column not in get_columns(
        db,
        table
    ):

        db.execute(
            f"""
            ALTER TABLE {table}
            ADD COLUMN {column} {definition}
            """
        )


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    db = get_db()

    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL,

            role TEXT DEFAULT 'staff'

        )
    """)

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS products (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            category TEXT DEFAULT '',

            quantity REAL DEFAULT 0,

            unit TEXT DEFAULT 'pcs',

            buying_price REAL DEFAULT 0,

            selling_price REAL DEFAULT 0,

            low_stock REAL DEFAULT 5

        )
    """)

    # -----------------------------------------------------
    # CUSTOMERS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS customers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            phone TEXT DEFAULT '',

            udhaar REAL DEFAULT 0

        )
    """)

    # -----------------------------------------------------
    # SUPPLIERS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS suppliers (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL,

            phone TEXT DEFAULT ''

        )
    """)

    # -----------------------------------------------------
    # BILLS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS bills (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            bill_number TEXT UNIQUE,

            customer_id INTEGER,

            customer_name TEXT DEFAULT '',

            customer_phone TEXT DEFAULT '',

            subtotal REAL DEFAULT 0,

            discount REAL DEFAULT 0,

            gst_percent REAL DEFAULT 0,

            gst_amount REAL DEFAULT 0,

            total REAL DEFAULT 0,

            profit REAL DEFAULT 0,

            payment_method TEXT DEFAULT 'Cash',

            created_at TEXT

        )
    """)

    # -----------------------------------------------------
    # BILL ITEMS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS bill_items (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            bill_id INTEGER,

            product_id INTEGER,

            product_name TEXT,

            quantity REAL DEFAULT 0,

            unit TEXT DEFAULT 'pcs',

            buying_price REAL DEFAULT 0,

            selling_price REAL DEFAULT 0,

            amount REAL DEFAULT 0,

            profit REAL DEFAULT 0

        )
    """)

    # -----------------------------------------------------
    # EXPENSES
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS expenses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            description TEXT NOT NULL,

            amount REAL DEFAULT 0,

            expense_date TEXT

        )
    """)

    # -----------------------------------------------------
    # PURCHASES
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS purchases (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            supplier_id INTEGER,

            product_id INTEGER,

            product_name TEXT DEFAULT '',

            quantity REAL DEFAULT 0,

            buying_price REAL DEFAULT 0,

            total_amount REAL DEFAULT 0,

            purchase_date TEXT

        )
    """)

    # -----------------------------------------------------
    # SETTINGS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS settings (

            id INTEGER PRIMARY KEY,

            shop_name TEXT DEFAULT
                'Pandey Kirana Store',

            address TEXT DEFAULT '',

            phone TEXT DEFAULT '',

            gst_number TEXT DEFAULT ''

        )
    """)

    # -----------------------------------------------------
    # CUSTOMER PAYMENTS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS payments (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            customer_id INTEGER,

            amount REAL DEFAULT 0,

            payment_method TEXT DEFAULT 'Cash',

            created_at TEXT

        )
    """)

    # -----------------------------------------------------
    # SUPPLIER PAYMENTS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS supplier_payments (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            supplier_id INTEGER,

            amount REAL DEFAULT 0,

            payment_method TEXT DEFAULT 'Cash',

            created_at TEXT

        )
    """)

    # -----------------------------------------------------
    # STOCK MOVEMENTS
    # -----------------------------------------------------

    db.execute("""
        CREATE TABLE IF NOT EXISTS stock_movements (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            product_id INTEGER,

            product_name TEXT DEFAULT '',

            movement_type TEXT DEFAULT
                'ADJUSTMENT',

            quantity REAL DEFAULT 0,

            reason TEXT DEFAULT '',

            created_at TEXT

        )
    """)

    # -----------------------------------------------------
    # DEFAULT ADMIN USER
    # -----------------------------------------------------

    existing_user = db.execute("""
        SELECT id
        FROM users
        WHERE username = ?
    """, ("admin",)).fetchone()

    if existing_user is None:

        db.execute("""
            INSERT INTO users
            (
                username,
                password,
                role
            )
            VALUES (?, ?, ?)
        """, (
            "admin",
            "1234",
            "admin"
        ))

    # -----------------------------------------------------
    # DEFAULT SHOP SETTINGS
    # -----------------------------------------------------

    setting = db.execute("""
        SELECT id
        FROM settings
        WHERE id = 1
    """).fetchone()

    if setting is None:

        db.execute("""
            INSERT INTO settings
            (
                id,
                shop_name,
                address,
                phone,
                gst_number
            )
            VALUES (?, ?, ?, ?, ?)
        """, (
            1,
            "Pandey Kirana Store",
            "",
            "",
            ""
        ))

    db.commit()

    db.close()


# Create database when application starts
init_db()


# =========================================================
# COMMON HELPER FUNCTIONS
# =========================================================

def money(value):

    try:
        return f"₹{float(value or 0):,.2f}"

    except (ValueError, TypeError):

        return "₹0.00"


def now_string():

    return datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )


def login_required(function):

    @functools.wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("logged_in"):

            return redirect(
                url_for("login")
            )

        return function(
            *args,
            **kwargs
        )

    return wrapper


def admin_required(function):

    @functools.wraps(function)
    def wrapper(*args, **kwargs):

        if not session.get("logged_in"):

            return redirect(
                url_for("login")
            )

        if session.get("role") != "admin":

            flash(
                "Admin access required.",
                "error"
            )

            return redirect(
                url_for("dashboard")
            )

        return function(
            *args,
            **kwargs
        )

    return wrapper


# =========================================================
# COMMON CSS
# =========================================================

STYLE = """

<style>

* {
    box-sizing: border-box;
}

body {

    margin: 0;

    font-family:
        Arial,
        Helvetica,
        sans-serif;

    background: #f4f6f8;

    color: #222;
}


/* HEADER */

.header {

    background: #1565c0;

    color: white;

    padding: 18px 25px;

    display: flex;

    justify-content:
        space-between;

    align-items: center;

    flex-wrap: wrap;

}

.header h2 {

    margin: 0;

}


/* NAVIGATION */

.nav {

    background: #0d47a1;

    padding: 10px;

    display: flex;

    flex-wrap: wrap;

    gap: 5px;

}

.nav a {

    color: white;

    text-decoration: none;

    padding: 9px 12px;

    border-radius: 5px;

}

.nav a:hover {

    background: #1976d2;

}


/* CONTAINER */

.container {

    max-width: 1450px;

    margin: auto;

    padding: 20px;

}


/* CARD */

.card {

    background: white;

    padding: 20px;

    margin-bottom: 20px;

    border-radius: 10px;

    box-shadow:
        0 2px 8px
        rgba(0, 0, 0, 0.08);

}


/* GRID */

.grid {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(190px, 1fr)
        );

    gap: 15px;

}


/* STAT CARD */

.stat {

    background: white;

    padding: 20px;

    border-radius: 10px;

    box-shadow:
        0 2px 8px
        rgba(0, 0, 0, 0.08);

}

.stat h3 {

    margin: 0;

    font-size: 16px;

}

.stat p {

    margin-top: 10px;

    margin-bottom: 0;

    font-size: 25px;

    font-weight: bold;

}


/* FORM */

.form-grid {

    display: grid;

    grid-template-columns:
        repeat(
            auto-fit,
            minmax(200px, 1fr)
        );

    gap: 12px;

}


input,
select,
textarea {

    width: 100%;

    padding: 10px;

    margin-top: 5px;

    margin-bottom: 12px;

    border: 1px solid #ccc;

    border-radius: 6px;

    font-size: 14px;

}


/* BUTTONS */

button,
.btn {

    display: inline-block;

    padding: 10px 15px;

    border: none;

    border-radius: 6px;

    background: #1565c0;

    color: white;

    text-decoration: none;

    cursor: pointer;

    font-size: 14px;

}

button:hover,
.btn:hover {

    opacity: 0.9;

}


.green {

    background: #2e7d32;

}

.red {

    background: #c62828;

}

.orange {

    background: #ef6c00;

}

.gray {

    background: #616161;

}

.purple {

    background: #6a1b9a;

}


/* ACTIONS */

.actions {

    display: flex;

    flex-wrap: wrap;

    gap: 7px;

}


/* TABLE */

table {

    width: 100%;

    border-collapse: collapse;

}

th,
td {

    padding: 10px;

    border-bottom:
        1px solid #ddd;

    text-align: left;

}

th {

    background: #e3f2fd;

}


/* ALERT */

.alert {

    padding: 12px;

    border-radius: 6px;

    margin-bottom: 15px;

}

.success {

    background: #d4edda;

    color: #155724;

}

.error {

    background: #f8d7da;

    color: #721c24;

}

.warning {

    background: #fff3cd;

    color: #856404;

}


/* BADGES */

.badge {

    display: inline-block;

    padding: 5px 8px;

    border-radius: 5px;

    font-size: 12px;

    font-weight: bold;

}

.badge-green {

    background: #d4edda;

    color: #155724;

}

.badge-red {

    background: #f8d7da;

    color: #721c24;

}

.badge-orange {

    background: #fff3cd;

    color: #856404;

}


/* LOGIN */

.login-box {

    max-width: 400px;

    margin: 80px auto;

}


/* PRINT */

@media print {

    .no-print {

        display: none !important;

    }

    body {

        background: white;

    }

    .card {

        box-shadow: none;

    }

}


/* MOBILE */

@media(max-width: 700px) {

    .container {

        padding: 10px;

    }

    table {

        font-size: 12px;

    }

    th,
    td {

        padding: 7px;

    }

    .header {

        padding: 15px;

    }

}

</style>

"""


# =========================================================
# PAGE TEMPLATE
# =========================================================

def render_page(
    title,
    content
):

    messages = ""

    for category, message in session.pop(
        "_flashes",
        []
    ):

        messages += f"""
        <div class="alert {category}">
            {message}
        </div>
        """


    if session.get("logged_in"):

        navigation = """

        <div class="nav no-print">

            <a href="/">
                🏠 Dashboard
            </a>

            <a href="/products">
                📦 Products
            </a>

            <a href="/billing">
                🧾 Billing
            </a>

            <a href="/bill_history">
                📋 Sales
            </a>

            <a href="/customers">
                👥 Customers
            </a>

            <a href="/suppliers">
                🚚 Suppliers
            </a>

            <a href="/purchases">
                🛒 Purchases
            </a>

            <a href="/expenses">
                💸 Expenses
            </a>

            <a href="/reports">
                📊 Reports
            </a>

            <a href="/logout">
                🚪 Logout
            </a>

        </div>

        """

    else:

        navigation = ""


    username = session.get(
        "username",
        ""
    )

    role = session.get(
        "role",
        ""
    )


    return render_template_string(
        """

<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width,
                 initial-scale=1.0"
    >

    <title>
        {{ title }} -
        Pandey Kirana Store
    </title>

    {{ style | safe }}

</head>


<body>


<div class="header">

    <h2>
        🛒 Pandey Kirana Store
    </h2>

    {% if username %}

        <span>

            {{ username }}
            ({{ role }})

        </span>

    {% endif %}

</div>


{{ navigation | safe }}


<div class="container">

    {{ messages | safe }}

    {{ content | safe }}

</div>


</body>

</html>

        """,

        title=title,

        style=STYLE,

        navigation=navigation,

        messages=messages,

        content=content,

        username=username,

        role=role
    )


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/login",
    methods=["GET", "POST"]
)
def login():

    if session.get("logged_in"):

        return redirect(
            url_for("dashboard")
        )


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )


        db = get_db()

        user = db.execute(
            """
            SELECT *
            FROM users
            WHERE username = ?
              AND password = ?
            """,
            (
                username,
                password
            )
        ).fetchone()

        db.close()


        if user:

            session["logged_in"] = True

            session["user_id"] = user["id"]

            session["username"] = user["username"]

            session["role"] = user["role"]

            return redirect(
                url_for("dashboard")
            )


        flash(
            "Wrong username or password.",
            "error"
        )


    return render_template_string(
        f"""

<!DOCTYPE html>

<html>

<head>

    <meta charset="UTF-8">

    <meta
        name="viewport"
        content="width=device-width,
                 initial-scale=1.0"
    >

    <title>
        Login -
        Pandey Kirana Store
    </title>

    {STYLE}

</head>


<body>


<div class="card login-box">

    <h2>
        🛒 Pandey Kirana Store
    </h2>

    <h3>
        Admin Login
    </h3>


    <form method="post">

        <label>
            Username
        </label>

        <input
            type="text"
            name="username"
            required
        >


        <label>
            Password
        </label>

        <input
            type="password"
            name="password"
            required
        >


        <button
            type="submit"
            class="green"
        >
            Login
        </button>

    </form>


    <hr>


    <p>

        <b>Default Login</b>

        <br><br>

        Username:
        <b>admin</b>

        <br>

        Password:
        <b>1234</b>

    </p>

</div>


</body>

</html>

        """
    )


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/")
@login_required
def dashboard():

    db = get_db()


    total_products = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM products
        """
    ).fetchone()["total"]


    total_customers = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM customers
        """
    ).fetchone()["total"]


    total_suppliers = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM suppliers
        """
    ).fetchone()["total"]


    total_bills = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM bills
        """
    ).fetchone()["total"]


    total_sales = db.execute(
        """
        SELECT COALESCE(
            SUM(total),
            0
        ) AS total
        FROM bills
        """
    ).fetchone()["total"]


    total_profit = db.execute(
        """
        SELECT COALESCE(
            SUM(profit),
            0
        ) AS total
        FROM bills
        """
    ).fetchone()["total"]


    total_expenses = db.execute(
        """
        SELECT COALESCE(
            SUM(amount),
            0
        ) AS total
        FROM expenses
        """
    ).fetchone()["total"]


    low_stock = db.execute(
        """
        SELECT COUNT(*) AS total
        FROM products
        WHERE quantity <= low_stock
        """
    ).fetchone()["total"]


    today_sales = db.execute(
        """
        SELECT COALESCE(
            SUM(total),
            0
        ) AS total
        FROM bills
        WHERE DATE(created_at)
              = DATE('now')
        """
    ).fetchone()["total"]


    today_profit = db.execute(
        """
        SELECT COALESCE(
            SUM(profit),
            0
        ) AS total
        FROM bills
        WHERE DATE(created_at)
              = DATE('now')
        """
    ).fetchone()["total"]


    db.close()


    net_amount = (
        float(total_sales)
        - float(total_expenses)
    )


    content = f"""

<h1>
    🏠 Dashboard
</h1>


<div class="grid">


    <div class="stat">

        <h3>
            📦 Total Products
        </h3>

        <p>
            {total_products}
        </p>

    </div>


    <div class="stat">

        <h3>
            👥 Customers
        </h3>

        <p>
            {total_customers}
        </p>

    </div>


    <div class="stat">

        <h3>
            🚚 Suppliers
        </h3>

        <p>
            {total_suppliers}
        </p>

    </div>


    <div class="stat">

        <h3>
            🧾 Total Bills
        </h3>

        <p>
            {total_bills}
        </p>

    </div>


    <div class="stat">

        <h3>
            💰 Total Sales
        </h3>

        <p>
            {money(total_sales)}
        </p>

    </div>


    <div class="stat">

        <h3>
            📈 Total Profit
        </h3>

        <p>
            {money(total_profit)}
        </p>

    </div>


    <div class="stat">

        <h3>
            💸 Expenses
        </h3>

        <p>
            {money(total_expenses)}
        </p>

    </div>


    <div class="stat">

        <h3>
            ⚠ Low Stock
        </h3>

        <p>
            {low_stock}
        </p>

    </div>


    <div class="stat">

        <h3>
            📅 Today's Sales
        </h3>

        <p>
            {money(today_sales)}
        </p>

    </div>


    <div class="stat">

        <h3>
            📊 Today's Profit
        </h3>

        <p>
            {money(today_profit)}
        </p>

    </div>


</div>


<div class="card">

    <h2>
        Quick Actions
    </h2>


    <div class="actions">

        <a
            class="btn green"
            href="/add_product"
        >
            ➕ Add Product
        </a>


        <a
            class="btn"
            href="/billing"
        >
            🧾 New Bill
        </a>


        <a
            class="btn orange"
            href="/customers"
        >
            👥 Customer
        </a>


        <a
            class="btn purple"
            href="/suppliers"
        >
            🚚 Supplier
        </a>


        <a
            class="btn"
            href="/reports"
        >
            📊 Reports
        </a>

    </div>

</div>


<div class="card">

    <h2>
        Store Summary
    </h2>

    <p>
        Total Sales:
        <b>{money(total_sales)}</b>
    </p>

    <p>
        Total Expenses:
        <b>{money(total_expenses)}</b>
    </p>

    <p>
        Sales - Expenses:
        <b>{money(net_amount)}</b>
    </p>

</div>

"""


    return render_page(
        "Dashboard",
        content
    )
    # =========================================================
# PART 2
# PRODUCT MANAGEMENT
# =========================================================


# =========================================================
# PRODUCTS LIST
# =========================================================

@app.route("/products")
@login_required
def products():

    search = request.args.get(
        "search",
        ""
    ).strip()


    db = get_db()


    if search:

        product_list = db.execute(
            """
            SELECT *
            FROM products

            WHERE name LIKE ?
               OR category LIKE ?

            ORDER BY name
            """,
            (
                "%" + search + "%",
                "%" + search + "%"
            )
        ).fetchall()

    else:

        product_list = db.execute(
            """
            SELECT *
            FROM products

            ORDER BY name
            """
        ).fetchall()


    db.close()


    rows = ""


    for product in product_list:


        quantity = float(
            product["quantity"] or 0
        )

        low_stock = float(
            product["low_stock"] or 0
        )


        if quantity <= 0:

            status = """
            <span class="badge badge-red">
                OUT OF STOCK
            </span>
            """

        elif quantity <= low_stock:

            status = """
            <span class="badge badge-orange">
                LOW STOCK
            </span>
            """

        else:

            status = """
            <span class="badge badge-green">
                AVAILABLE
            </span>
            """


        rows += f"""

        <tr>

            <td>
                {product["id"]}
            </td>


            <td>
                <b>
                    {product["name"]}
                </b>
            </td>


            <td>
                {product["category"] or "-"}
            </td>


            <td>
                {quantity:g}
                {product["unit"]}
            </td>


            <td>
                {money(product["buying_price"])}
            </td>


            <td>
                {money(product["selling_price"])}
            </td>


            <td>
                {status}
            </td>


            <td>

                <div class="actions">

                    <a
                        class="btn"
                        href="/edit_product/{product["id"]}"
                    >
                        ✏ Edit
                    </a>


                    <a
                        class="btn orange"
                        href="/stock/{product["id"]}"
                    >
                        📦 Stock
                    </a>


                    <a
                        class="btn red"
                        href="/delete_product/{product["id"]}"
                        onclick="return confirm('Delete this product?')"
                    >
                        🗑 Delete
                    </a>

                </div>

            </td>

        </tr>

        """


    content = f"""

    <h1>
        📦 Product Management
    </h1>


    <div class="card">

        <form method="get">

            <div class="form-grid">

                <div>

                    <label>
                        Search Product
                    </label>

                    <input
                        type="text"
                        name="search"
                        value="{search}"
                        placeholder="Product name or category"
                    >

                </div>

            </div>


            <button type="submit">
                🔍 Search
            </button>


            <a
                class="btn gray"
                href="/products"
            >
                Clear
            </a>


            <a
                class="btn green"
                href="/add_product"
            >
                ➕ Add Product
            </a>

        </form>

    </div>


    <div class="card">

        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        ID
                    </th>

                    <th>
                        Product
                    </th>

                    <th>
                        Category
                    </th>

                    <th>
                        Stock
                    </th>

                    <th>
                        Buying Price
                    </th>

                    <th>
                        Selling Price
                    </th>

                    <th>
                        Status
                    </th>

                    <th>
                        Actions
                    </th>

                </tr>

                {rows}

            </table>

        </div>

    </div>

    """


    return render_page(
        "Products",
        content
    )


# =========================================================
# ADD PRODUCT
# =========================================================

@app.route(
    "/add_product",
    methods=["GET", "POST"]
)
@login_required
def add_product():


    if request.method == "POST":


        name = request.form.get(
            "name",
            ""
        ).strip()


        category = request.form.get(
            "category",
            ""
        ).strip()


        unit = request.form.get(
            "unit",
            "pcs"
        ).strip()


        try:

            quantity = float(
                request.form.get(
                    "quantity",
                    0
                )
            )


            buying_price = float(
                request.form.get(
                    "buying_price",
                    0
                )
            )


            selling_price = float(
                request.form.get(
                    "selling_price",
                    0
                )
            )


            low_stock = float(
                request.form.get(
                    "low_stock",
                    5
                )
            )


        except ValueError:

            flash(
                "Please enter valid numbers.",
                "error"
            )

            return redirect(
                url_for("add_product")
            )


        if not name:

            flash(
                "Product name is required.",
                "error"
            )

            return redirect(
                url_for("add_product")
            )


        if quantity < 0:

            flash(
                "Quantity cannot be negative.",
                "error"
            )

            return redirect(
                url_for("add_product")
            )


        if buying_price < 0:

            flash(
                "Buying price cannot be negative.",
                "error"
            )

            return redirect(
                url_for("add_product")
            )


        if selling_price < 0:

            flash(
                "Selling price cannot be negative.",
                "error"
            )

            return redirect(
                url_for("add_product")
            )


        db = get_db()


        cursor = db.execute(
            """
            INSERT INTO products
            (
                name,
                category,
                quantity,
                unit,
                buying_price,
                selling_price,
                low_stock
            )

            VALUES
            (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                name,
                category,
                quantity,
                unit,
                buying_price,
                selling_price,
                low_stock
            )
        )


        product_id = cursor.lastrowid


        if quantity > 0:

            db.execute(
                """
                INSERT INTO stock_movements
                (
                    product_id,
                    product_name,
                    movement_type,
                    quantity,
                    reason,
                    created_at
                )

                VALUES
                (?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    name,
                    "OPENING STOCK",
                    quantity,
                    "Product created",
                    now_string()
                )
            )


        db.commit()

        db.close()


        flash(
            "Product added successfully.",
            "success"
        )


        return redirect(
            url_for("products")
        )


    content = """

    <h1>
        ➕ Add New Product
    </h1>


    <div class="card">

        <form method="post">


            <div class="form-grid">


                <div>

                    <label>
                        Product Name
                    </label>

                    <input
                        type="text"
                        name="name"
                        placeholder="Example: Rice"
                        required
                    >

                </div>


                <div>

                    <label>
                        Category
                    </label>

                    <input
                        type="text"
                        name="category"
                        placeholder="Example: Grocery"
                    >

                </div>


                <div>

                    <label>
                        Quantity
                    </label>

                    <input
                        type="number"
                        name="quantity"
                        step="0.01"
                        min="0"
                        value="0"
                        required
                    >

                </div>


                <div>

                    <label>
                        Unit
                    </label>

                    <select name="unit">

                        <option value="pcs">
                            Pieces
                        </option>

                        <option value="kg">
                            Kilogram
                        </option>

                        <option value="gram">
                            Gram
                        </option>

                        <option value="litre">
                            Litre
                        </option>

                        <option value="ml">
                            Millilitre
                        </option>

                        <option value="packet">
                            Packet
                        </option>

                        <option value="box">
                            Box
                        </option>

                        <option value="bottle">
                            Bottle
                        </option>

                    </select>

                </div>


                <div>

                    <label>
                        Buying Price
                    </label>

                    <input
                        type="number"
                        name="buying_price"
                        step="0.01"
                        min="0"
                        value="0"
                        required
                    >

                </div>


                <div>

                    <label>
                        Selling Price
                    </label>

                    <input
                        type="number"
                        name="selling_price"
                        step="0.01"
                        min="0"
                        value="0"
                        required
                    >

                </div>


                <div>

                    <label>
                        Low Stock Limit
                    </label>

                    <input
                        type="number"
                        name="low_stock"
                        step="0.01"
                        min="0"
                        value="5"
                        required
                    >

                </div>


            </div>


            <br>


            <button
                type="submit"
                class="green"
            >
                💾 Save Product
            </button>


            <a
                class="btn gray"
                href="/products"
            >
                Cancel
            </a>


        </form>

    </div>

    """


    return render_page(
        "Add Product",
        content
    )


# =========================================================
# EDIT PRODUCT
# =========================================================

@app.route(
    "/edit_product/<int:product_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_product(product_id):


    db = get_db()


    product = db.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()


    if product is None:

        db.close()

        flash(
            "Product not found.",
            "error"
        )

        return redirect(
            url_for("products")
        )


    if request.method == "POST":


        name = request.form.get(
            "name",
            ""
        ).strip()


        category = request.form.get(
            "category",
            ""
        ).strip()


        unit = request.form.get(
            "unit",
            "pcs"
        ).strip()


        try:

            quantity = float(
                request.form.get(
                    "quantity",
                    0
                )
            )


            buying_price = float(
                request.form.get(
                    "buying_price",
                    0
                )
            )


            selling_price = float(
                request.form.get(
                    "selling_price",
                    0
                )
            )


            low_stock = float(
                request.form.get(
                    "low_stock",
                    5
                )
            )


        except ValueError:

            db.close()

            flash(
                "Please enter valid numbers.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_product",
                    product_id=product_id
                )
            )


        if not name:

            db.close()

            flash(
                "Product name is required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_product",
                    product_id=product_id
                )
            )


        old_quantity = float(
            product["quantity"] or 0
        )


        db.execute(
            """
            UPDATE products

            SET
                name = ?,
                category = ?,
                quantity = ?,
                unit = ?,
                buying_price = ?,
                selling_price = ?,
                low_stock = ?

            WHERE id = ?
            """,
            (
                name,
                category,
                quantity,
                unit,
                buying_price,
                selling_price,
                low_stock,
                product_id
            )
        )


        if quantity != old_quantity:

            difference = (
                quantity
                - old_quantity
            )


            db.execute(
                """
                INSERT INTO stock_movements
                (
                    product_id,
                    product_name,
                    movement_type,
                    quantity,
                    reason,
                    created_at
                )

                VALUES
                (?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    name,
                    "ADJUSTMENT",
                    difference,
                    "Product edited",
                    now_string()
                )
            )


        db.commit()

        db.close()


        flash(
            "Product updated successfully.",
            "success"
        )


        return redirect(
            url_for("products")
        )


    db.close()


    selected_unit = product["unit"]


    units = [
        ("pcs", "Pieces"),
        ("kg", "Kilogram"),
        ("gram", "Gram"),
        ("litre", "Litre"),
        ("ml", "Millilitre"),
        ("packet", "Packet"),
        ("box", "Box"),
        ("bottle", "Bottle")
    ]


    unit_options = ""


    for value, label in units:

        selected = (
            "selected"
            if value == selected_unit
            else ""
        )


        unit_options += f"""
        <option
            value="{value}"
            {selected}
        >
            {label}
        </option>
        """


    content = f"""

    <h1>
        ✏ Edit Product
    </h1>


    <div class="card">

        <form method="post">


            <div class="form-grid">


                <div>

                    <label>
                        Product Name
                    </label>

                    <input
                        type="text"
                        name="name"
                        value="{product["name"]}"
                        required
                    >

                </div>


                <div>

                    <label>
                        Category
                    </label>

                    <input
                        type="text"
                        name="category"
                        value="{product["category"] or ""}"
                    >

                </div>


                <div>

                    <label>
                        Quantity
                    </label>

                    <input
                        type="number"
                        name="quantity"
                        step="0.01"
                        min="0"
                        value="{product["quantity"]}"
                        required
                    >

                </div>


                <div>

                    <label>
                        Unit
                    </label>

                    <select name="unit">

                        {unit_options}

                    </select>

                </div>


                <div>

                    <label>
                        Buying Price
                    </label>

                    <input
                        type="number"
                        name="buying_price"
                        step="0.01"
                        min="0"
                        value="{product["buying_price"]}"
                        required
                    >

                </div>


                <div>

                    <label>
                        Selling Price
                    </label>

                    <input
                        type="number"
                        name="selling_price"
                        step="0.01"
                        min="0"
                        value="{product["selling_price"]}"
                        required
                    >

                </div>


                <div>

                    <label>
                        Low Stock Limit
                    </label>

                    <input
                        type="number"
                        name="low_stock"
                        step="0.01"
                        min="0"
                        value="{product["low_stock"]}"
                        required
                    >

                </div>


            </div>


            <br>


            <button
                type="submit"
                class="green"
            >
                💾 Update Product
            </button>


            <a
                class="btn gray"
                href="/products"
            >
                Cancel
            </a>


        </form>

    </div>

    """


    return render_page(
        "Edit Product",
        content
    )


# =========================================================
# DELETE PRODUCT
# =========================================================

@app.route(
    "/delete_product/<int:product_id>"
)
@login_required
def delete_product(product_id):


    db = get_db()


    product = db.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()


    if product is None:

        db.close()

        flash(
            "Product not found.",
            "error"
        )

        return redirect(
            url_for("products")
        )


    bill_item = db.execute(
        """
        SELECT id
        FROM bill_items
        WHERE product_id = ?
        LIMIT 1
        """,
        (product_id,)
    ).fetchone()


    if bill_item:

        db.close()

        flash(
            "This product is already used in a bill. "
            "Edit its stock instead of deleting it.",
            "error"
        )

        return redirect(
            url_for("products")
        )


    db.execute(
        """
        DELETE FROM stock_movements
        WHERE product_id = ?
        """,
        (product_id,)
    )


    db.execute(
        """
        DELETE FROM products
        WHERE id = ?
        """,
        (product_id,)
    )


    db.commit()

    db.close()


    flash(
        "Product deleted successfully.",
        "success"
    )


    return redirect(
        url_for("products")
    )


# =========================================================
# STOCK MANAGEMENT
# =========================================================

@app.route(
    "/stock/<int:product_id>",
    methods=["GET", "POST"]
)
@login_required
def stock(product_id):


    db = get_db()


    product = db.execute(
        """
        SELECT *
        FROM products
        WHERE id = ?
        """,
        (product_id,)
    ).fetchone()


    if product is None:

        db.close()

        flash(
            "Product not found.",
            "error"
        )

        return redirect(
            url_for("products")
        )


    if request.method == "POST":


        try:

            new_quantity = float(
                request.form.get(
                    "quantity",
                    0
                )
            )

        except ValueError:

            db.close()

            flash(
                "Please enter a valid quantity.",
                "error"
            )

            return redirect(
                url_for(
                    "stock",
                    product_id=product_id
                )
            )


        if new_quantity < 0:

            db.close()

            flash(
                "Stock cannot be negative.",
                "error"
            )

            return redirect(
                url_for(
                    "stock",
                    product_id=product_id
                )
            )


        old_quantity = float(
            product["quantity"] or 0
        )


        difference = (
            new_quantity
            - old_quantity
        )


        reason = request.form.get(
            "reason",
            "Manual stock adjustment"
        ).strip()


        db.execute(
            """
            UPDATE products

            SET quantity = ?

            WHERE id = ?
            """,
            (
                new_quantity,
                product_id
            )
        )


        if difference != 0:

            db.execute(
                """
                INSERT INTO stock_movements
                (
                    product_id,
                    product_name,
                    movement_type,
                    quantity,
                    reason,
                    created_at
                )

                VALUES
                (?, ?, ?, ?, ?, ?)
                """,
                (
                    product_id,
                    product["name"],
                    "ADJUSTMENT",
                    difference,
                    reason,
                    now_string()
                )
            )


        db.commit()

        db.close()


        flash(
            "Stock updated successfully.",
            "success"
        )


        return redirect(
            url_for("products")
        )


    movements = db.execute(
        """
        SELECT *
        FROM stock_movements

        WHERE product_id = ?

        ORDER BY id DESC

        LIMIT 20
        """,
        (product_id,)
    ).fetchall()


    db.close()


    movement_rows = ""


    for movement in movements:

        quantity_value = float(
            movement["quantity"] or 0
        )


        if quantity_value > 0:

            quantity_display = (
                f"+{quantity_value:g}"
            )

        else:

            quantity_display = (
                f"{quantity_value:g}"
            )


        movement_rows += f"""

        <tr>

            <td>
                {movement["movement_type"]}
            </td>

            <td>
                {quantity_display}
                {product["unit"]}
            </td>

            <td>
                {movement["reason"]}
            </td>

            <td>
                {movement["created_at"]}
            </td>

        </tr>

        """


    content = f"""

    <h1>
        📦 Stock Management
    </h1>


    <div class="card">

        <h2>
            {product["name"]}
        </h2>


        <p>
            Current Stock:
            <b>
                {float(product["quantity"] or 0):g}
                {product["unit"]}
            </b>
        </p>


        <form method="post">


            <label>
                New Stock Quantity
            </label>

            <input
                type="number"
                name="quantity"
                step="0.01"
                min="0"
                value="{product["quantity"]}"
                required
            >


            <label>
                Reason
            </label>

            <input
                type="text"
                name="reason"
                value="Manual stock adjustment"
            >


            <button
                type="submit"
                class="green"
            >
                💾 Update Stock
            </button>


            <a
                class="btn gray"
                href="/products"
            >
                Back
            </a>


        </form>

    </div>


    <div class="card">

        <h2>
            Recent Stock History
        </h2>


        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        Type
                    </th>

                    <th>
                        Quantity
                    </th>

                    <th>
                        Reason
                    </th>

                    <th>
                        Date
                    </th>

                </tr>

                {movement_rows}

            </table>

        </div>

    </div>

    """


    return render_page(
        "Stock Management",
        content
    )
    # =========================================================
# PART 3
# CUSTOMER MANAGEMENT + UDHAAR
# =========================================================


# =========================================================
# CUSTOMERS LIST
# =========================================================

@app.route("/customers")
@login_required
def customers():

    search = request.args.get(
        "search",
        ""
    ).strip()


    db = get_db()


    if search:

        customer_list = db.execute(
            """
            SELECT *
            FROM customers

            WHERE name LIKE ?
               OR phone LIKE ?

            ORDER BY name
            """,
            (
                "%" + search + "%",
                "%" + search + "%"
            )
        ).fetchall()

    else:

        customer_list = db.execute(
            """
            SELECT *
            FROM customers
            ORDER BY name
            """
        ).fetchall()


    rows = ""

    total_udhaar = 0


    for customer in customer_list:

        udhaar = float(
            customer["udhaar"] or 0
        )

        total_udhaar += udhaar


        if udhaar > 0:

            status = """
            <span class="badge badge-red">
                UDHAAR
            </span>
            """

        else:

            status = """
            <span class="badge badge-green">
                CLEAR
            </span>
            """


        rows += f"""

        <tr>

            <td>
                {customer["id"]}
            </td>

            <td>
                <b>
                    {customer["name"]}
                </b>
            </td>

            <td>
                {customer["phone"] or "-"}
            </td>

            <td>
                <b>
                    {money(udhaar)}
                </b>
            </td>

            <td>
                {status}
            </td>

            <td>

                <div class="actions">

                    <a
                        class="btn"
                        href="/edit_customer/{customer["id"]}"
                    >
                        ✏ Edit
                    </a>


                    <a
                        class="btn green"
                        href="/customer_payment/{customer["id"]}"
                    >
                        💵 Payment
                    </a>


                    <a
                        class="btn purple"
                        href="/customer_history/{customer["id"]}"
                    >
                        📋 History
                    </a>


                    <a
                        class="btn red"
                        href="/delete_customer/{customer["id"]}"
                        onclick="return confirm('Delete this customer?')"
                    >
                        🗑 Delete
                    </a>

                </div>

            </td>

        </tr>

        """


    db.close()


    content = f"""

    <h1>
        👥 Customer Management
    </h1>


    <div class="grid">


        <div class="stat">

            <h3>
                Total Customers
            </h3>

            <p>
                {len(customer_list)}
            </p>

        </div>


        <div class="stat">

            <h3>
                Total Udhaar
            </h3>

            <p>
                {money(total_udhaar)}
            </p>

        </div>


    </div>


    <br>


    <div class="card">

        <form method="get">

            <label>
                Search Customer
            </label>

            <input
                type="text"
                name="search"
                value="{search}"
                placeholder="Name or phone"
            >


            <button type="submit">
                🔍 Search
            </button>


            <a
                class="btn gray"
                href="/customers"
            >
                Clear
            </a>


            <a
                class="btn green"
                href="/add_customer"
            >
                ➕ Add Customer
            </a>

        </form>

    </div>


    <div class="card">

        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        ID
                    </th>

                    <th>
                        Name
                    </th>

                    <th>
                        Phone
                    </th>

                    <th>
                        Udhaar
                    </th>

                    <th>
                        Status
                    </th>

                    <th>
                        Actions
                    </th>

                </tr>

                {rows}

            </table>

        </div>

    </div>

    """


    return render_page(
        "Customers",
        content
    )


# =========================================================
# ADD CUSTOMER
# =========================================================

@app.route(
    "/add_customer",
    methods=["GET", "POST"]
)
@login_required
def add_customer():


    if request.method == "POST":


        name = request.form.get(
            "name",
            ""
        ).strip()


        phone = request.form.get(
            "phone",
            ""
        ).strip()


        if not name:

            flash(
                "Customer name is required.",
                "error"
            )

            return redirect(
                url_for("add_customer")
            )


        db = get_db()


        db.execute(
            """
            INSERT INTO customers
            (
                name,
                phone,
                udhaar
            )

            VALUES (?, ?, ?)
            """,
            (
                name,
                phone,
                0
            )
        )


        db.commit()

        db.close()


        flash(
            "Customer added successfully.",
            "success"
        )


        return redirect(
            url_for("customers")
        )


    content = """

    <h1>
        ➕ Add Customer
    </h1>


    <div class="card">

        <form method="post">


            <label>
                Customer Name
            </label>

            <input
                type="text"
                name="name"
                placeholder="Customer name"
                required
            >


            <label>
                Phone Number
            </label>

            <input
                type="text"
                name="phone"
                placeholder="Phone number"
            >


            <br>


            <button
                type="submit"
                class="green"
            >
                💾 Save Customer
            </button>


            <a
                class="btn gray"
                href="/customers"
            >
                Cancel
            </a>


        </form>

    </div>

    """


    return render_page(
        "Add Customer",
        content
    )


# =========================================================
# EDIT CUSTOMER
# =========================================================

@app.route(
    "/edit_customer/<int:customer_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_customer(customer_id):


    db = get_db()


    customer = db.execute(
        """
        SELECT *
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    ).fetchone()


    if customer is None:

        db.close()

        flash(
            "Customer not found.",
            "error"
        )

        return redirect(
            url_for("customers")
        )


    if request.method == "POST":


        name = request.form.get(
            "name",
            ""
        ).strip()


        phone = request.form.get(
            "phone",
            ""
        ).strip()


        if not name:

            db.close()

            flash(
                "Customer name is required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_customer",
                    customer_id=customer_id
                )
            )


        db.execute(
            """
            UPDATE customers

            SET
                name = ?,
                phone = ?

            WHERE id = ?
            """,
            (
                name,
                phone,
                customer_id
            )
        )


        db.commit()

        db.close()


        flash(
            "Customer updated successfully.",
            "success"
        )


        return redirect(
            url_for("customers")
        )


    db.close()


    content = f"""

    <h1>
        ✏ Edit Customer
    </h1>


    <div class="card">

        <form method="post">


            <label>
                Customer Name
            </label>

            <input
                type="text"
                name="name"
                value="{customer["name"]}"
                required
            >


            <label>
                Phone Number
            </label>

            <input
                type="text"
                name="phone"
                value="{customer["phone"] or ""}"
            >


            <p>

                Current Udhaar:

                <b>
                    {money(customer["udhaar"])}
                </b>

            </p>


            <button
                type="submit"
                class="green"
            >
                💾 Update Customer
            </button>


            <a
                class="btn gray"
                href="/customers"
            >
                Cancel
            </a>


        </form>

    </div>

    """


    return render_page(
        "Edit Customer",
        content
    )


# =========================================================
# DELETE CUSTOMER
# =========================================================

@app.route(
    "/delete_customer/<int:customer_id>"
)
@login_required
def delete_customer(customer_id):


    db = get_db()


    customer = db.execute(
        """
        SELECT *
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    ).fetchone()


    if customer is None:

        db.close()

        flash(
            "Customer not found.",
            "error"
        )

        return redirect(
            url_for("customers")
        )


    bill = db.execute(
        """
        SELECT id
        FROM bills
        WHERE customer_id = ?
        LIMIT 1
        """,
        (customer_id,)
    ).fetchone()


    if bill:

        db.close()

        flash(
            "This customer has billing history and cannot be deleted.",
            "error"
        )

        return redirect(
            url_for("customers")
        )


    payment = db.execute(
        """
        SELECT id
        FROM payments
        WHERE customer_id = ?
        LIMIT 1
        """,
        (customer_id,)
    ).fetchone()


    if payment:

        db.close()

        flash(
            "This customer has payment history and cannot be deleted.",
            "error"
        )

        return redirect(
            url_for("customers")
        )


    db.execute(
        """
        DELETE FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    )


    db.commit()

    db.close()


    flash(
        "Customer deleted successfully.",
        "success"
    )


    return redirect(
        url_for("customers")
    )


# =========================================================
# CUSTOMER PAYMENT
# =========================================================

@app.route(
    "/customer_payment/<int:customer_id>",
    methods=["GET", "POST"]
)
@login_required
def customer_payment(customer_id):


    db = get_db()


    customer = db.execute(
        """
        SELECT *
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    ).fetchone()


    if customer is None:

        db.close()

        flash(
            "Customer not found.",
            "error"
        )

        return redirect(
            url_for("customers")
        )


    if request.method == "POST":


        try:

            amount = float(
                request.form.get(
                    "amount",
                    0
                )
            )

        except ValueError:

            db.close()

            flash(
                "Enter a valid payment amount.",
                "error"
            )

            return redirect(
                url_for(
                    "customer_payment",
                    customer_id=customer_id
                )
            )


        payment_method = request.form.get(
            "payment_method",
            "Cash"
        ).strip()


        if amount <= 0:

            db.close()

            flash(
                "Payment amount must be greater than zero.",
                "error"
            )

            return redirect(
                url_for(
                    "customer_payment",
                    customer_id=customer_id
                )
            )


        current_udhaar = float(
            customer["udhaar"] or 0
        )


        if amount > current_udhaar:

            db.close()

            flash(
                "Payment cannot be greater than current udhaar.",
                "error"
            )

            return redirect(
                url_for(
                    "customer_payment",
                    customer_id=customer_id
                )
            )


        new_udhaar = (
            current_udhaar
            - amount
        )


        db.execute(
            """
            UPDATE customers

            SET udhaar = ?

            WHERE id = ?
            """,
            (
                new_udhaar,
                customer_id
            )
        )


        db.execute(
            """
            INSERT INTO payments
            (
                customer_id,
                amount,
                payment_method,
                created_at
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                customer_id,
                amount,
                payment_method,
                now_string()
            )
        )


        db.commit()

        db.close()


        flash(
            "Customer payment recorded successfully.",
            "success"
        )


        return redirect(
            url_for(
                "customer_history",
                customer_id=customer_id
            )
        )


    current_udhaar = float(
        customer["udhaar"] or 0
    )


    db.close()


    content = f"""

    <h1>
        💵 Customer Payment
    </h1>


    <div class="card">


        <h2>
            {customer["name"]}
        </h2>


        <p>
            Phone:
            <b>
                {customer["phone"] or "-"}
            </b>
        </p>


        <p>
            Current Udhaar:
            <b>
                {money(current_udhaar)}
            </b>
        </p>


        <hr>


        <form method="post">


            <label>
                Payment Amount
            </label>

            <input
                type="number"
                name="amount"
                step="0.01"
                min="0.01"
                max="{current_udhaar}"
                required
            >


            <label>
                Payment Method
            </label>

            <select name="payment_method">

                <option value="Cash">
                    Cash
                </option>

                <option value="UPI">
                    UPI
                </option>

                <option value="Card">
                    Card
                </option>

                <option value="Bank">
                    Bank Transfer
                </option>

            </select>


            <button
                type="submit"
                class="green"
            >
                💾 Save Payment
            </button>


            <a
                class="btn gray"
                href="/customers"
            >
                Cancel
            </a>


        </form>

    </div>

    """


    return render_page(
        "Customer Payment",
        content
    )


# =========================================================
# CUSTOMER HISTORY
# =========================================================

@app.route(
    "/customer_history/<int:customer_id>"
)
@login_required
def customer_history(customer_id):


    db = get_db()


    customer = db.execute(
        """
        SELECT *
        FROM customers
        WHERE id = ?
        """,
        (customer_id,)
    ).fetchone()


    if customer is None:

        db.close()

        flash(
            "Customer not found.",
            "error"
        )

        return redirect(
            url_for("customers")
        )


    bills = db.execute(
        """
        SELECT *
        FROM bills

        WHERE customer_id = ?

        ORDER BY id DESC
        """,
        (customer_id,)
    ).fetchall()


    payments = db.execute(
        """
        SELECT *
        FROM payments

        WHERE customer_id = ?

        ORDER BY id DESC
        """,
        (customer_id,)
    ).fetchall()


    db.close()


    bill_rows = ""


    for bill in bills:

        bill_rows += f"""

        <tr>

            <td>
                {bill["bill_number"] or bill["id"]}
            </td>

            <td>
                {bill["created_at"]}
            </td>

            <td>
                {money(bill["total"])}
            </td>

            <td>
                {bill["payment_method"]}
            </td>

            <td>

                <a
                    class="btn"
                    href="/invoice/{bill["id"]}"
                >
                    🧾 Invoice
                </a>

            </td>

        </tr>

        """


    payment_rows = ""


    for payment in payments:

        payment_rows += f"""

        <tr>

            <td>
                {payment["created_at"]}
            </td>

            <td>
                {money(payment["amount"])}
            </td>

            <td>
                {payment["payment_method"]}
            </td>

        </tr>

        """


    content = f"""

    <h1>
        📋 Customer History
    </h1>


    <div class="card">

        <h2>
            {customer["name"]}
        </h2>


        <p>
            Phone:
            <b>
                {customer["phone"] or "-"}
            </b>
        </p>


        <p>
            Current Udhaar:
            <b>
                {money(customer["udhaar"])}
            </b>
        </p>


        <a
            class="btn green"
            href="/customer_payment/{customer_id}"
        >
            💵 Receive Payment
        </a>


        <a
            class="btn gray"
            href="/customers"
        >
            Back
        </a>

    </div>


    <div class="card">

        <h2>
            🧾 Bills
        </h2>


        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        Bill No.
                    </th>

                    <th>
                        Date
                    </th>

                    <th>
                        Amount
                    </th>

                    <th>
                        Payment
                    </th>

                    <th>
                        Action
                    </th>

                </tr>

                {bill_rows}

            </table>

        </div>

    </div>


    <div class="card">

        <h2>
            💵 Payments
        </h2>


        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        Date
                    </th>

                    <th>
                        Amount
                    </th>

                    <th>
                        Method
                    </th>

                </tr>

                {payment_rows}

            </table>

        </div>

    </div>

    """


    return render_page(
        "Customer History",
        content
    )
    # =========================================================
# PART 4
# SUPPLIER MANAGEMENT + PURCHASES
# =========================================================


# =========================================================
# SUPPLIERS LIST
# =========================================================

@app.route("/suppliers")
@login_required
def suppliers():

    search = request.args.get(
        "search",
        ""
    ).strip()


    db = get_db()


    if search:

        supplier_list = db.execute(
            """
            SELECT *
            FROM suppliers

            WHERE name LIKE ?
               OR phone LIKE ?

            ORDER BY name
            """,
            (
                "%" + search + "%",
                "%" + search + "%"
            )
        ).fetchall()

    else:

        supplier_list = db.execute(
            """
            SELECT *
            FROM suppliers
            ORDER BY name
            """
        ).fetchall()


    total_purchase = db.execute(
        """
        SELECT COALESCE(
            SUM(total_amount),
            0
        ) AS total

        FROM purchases
        """
    ).fetchone()["total"]


    total_paid = db.execute(
        """
        SELECT COALESCE(
            SUM(amount),
            0
        ) AS total

        FROM supplier_payments
        """
    ).fetchone()["total"]


    rows = ""


    for supplier in supplier_list:


        purchase_total = db.execute(
            """
            SELECT COALESCE(
                SUM(total_amount),
                0
            ) AS total

            FROM purchases

            WHERE supplier_id = ?
            """,
            (supplier["id"],)
        ).fetchone()["total"]


        paid_total = db.execute(
            """
            SELECT COALESCE(
                SUM(amount),
                0
            ) AS total

            FROM supplier_payments

            WHERE supplier_id = ?
            """,
            (supplier["id"],)
        ).fetchone()["total"]


        balance = (
            float(purchase_total or 0)
            - float(paid_total or 0)
        )


        if balance > 0:

            status = """
            <span class="badge badge-red">
                PAYMENT DUE
            </span>
            """

        else:

            status = """
            <span class="badge badge-green">
                CLEAR
            </span>
            """


        rows += f"""

        <tr>

            <td>
                {supplier["id"]}
            </td>


            <td>
                <b>
                    {supplier["name"]}
                </b>
            </td>


            <td>
                {supplier["phone"] or "-"}
            </td>


            <td>
                {money(purchase_total)}
            </td>


            <td>
                {money(paid_total)}
            </td>


            <td>
                <b>
                    {money(balance)}
                </b>
            </td>


            <td>
                {status}
            </td>


            <td>

                <div class="actions">

                    <a
                        class="btn"
                        href="/edit_supplier/{supplier["id"]}"
                    >
                        ✏ Edit
                    </a>


                    <a
                        class="btn green"
                        href="/supplier_payment/{supplier["id"]}"
                    >
                        💵 Payment
                    </a>


                    <a
                        class="btn purple"
                        href="/supplier_history/{supplier["id"]}"
                    >
                        📋 History
                    </a>


                    <a
                        class="btn red"
                        href="/delete_supplier/{supplier["id"]}"
                        onclick="return confirm('Delete this supplier?')"
                    >
                        🗑 Delete
                    </a>

                </div>

            </td>

        </tr>

        """


    db.close()


    outstanding = (
        float(total_purchase or 0)
        - float(total_paid or 0)
    )


    content = f"""

    <h1>
        🚚 Supplier Management
    </h1>


    <div class="grid">


        <div class="stat">

            <h3>
                Total Suppliers
            </h3>

            <p>
                {len(supplier_list)}
            </p>

        </div>


        <div class="stat">

            <h3>
                Total Purchases
            </h3>

            <p>
                {money(total_purchase)}
            </p>

        </div>


        <div class="stat">

            <h3>
                Supplier Payments
            </h3>

            <p>
                {money(total_paid)}
            </p>

        </div>


        <div class="stat">

            <h3>
                Outstanding
            </h3>

            <p>
                {money(outstanding)}
            </p>

        </div>


    </div>


    <br>


    <div class="card">

        <form method="get">

            <label>
                Search Supplier
            </label>

            <input
                type="text"
                name="search"
                value="{search}"
                placeholder="Supplier name or phone"
            >


            <button type="submit">
                🔍 Search
            </button>


            <a
                class="btn gray"
                href="/suppliers"
            >
                Clear
            </a>


            <a
                class="btn green"
                href="/add_supplier"
            >
                ➕ Add Supplier
            </a>


            <a
                class="btn orange"
                href="/add_purchase"
            >
                🛒 Add Purchase
            </a>

        </form>

    </div>


    <div class="card">

        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        ID
                    </th>

                    <th>
                        Supplier
                    </th>

                    <th>
                        Phone
                    </th>

                    <th>
                        Purchases
                    </th>

                    <th>
                        Paid
                    </th>

                    <th>
                        Balance
                    </th>

                    <th>
                        Status
                    </th>

                    <th>
                        Actions
                    </th>

                </tr>

                {rows}

            </table>

        </div>

    </div>

    """


    return render_page(
        "Suppliers",
        content
    )


# =========================================================
# ADD SUPPLIER
# =========================================================

@app.route(
    "/add_supplier",
    methods=["GET", "POST"]
)
@login_required
def add_supplier():


    if request.method == "POST":


        name = request.form.get(
            "name",
            ""
        ).strip()


        phone = request.form.get(
            "phone",
            ""
        ).strip()


        if not name:

            flash(
                "Supplier name is required.",
                "error"
            )

            return redirect(
                url_for("add_supplier")
            )


        db = get_db()


        db.execute(
            """
            INSERT INTO suppliers
            (
                name,
                phone
            )

            VALUES (?, ?)
            """,
            (
                name,
                phone
            )
        )


        db.commit()

        db.close()


        flash(
            "Supplier added successfully.",
            "success"
        )


        return redirect(
            url_for("suppliers")
        )


    content = """

    <h1>
        ➕ Add Supplier
    </h1>


    <div class="card">

        <form method="post">


            <label>
                Supplier Name
            </label>

            <input
                type="text"
                name="name"
                placeholder="Supplier name"
                required
            >


            <label>
                Phone Number
            </label>

            <input
                type="text"
                name="phone"
                placeholder="Phone number"
            >


            <br>


            <button
                type="submit"
                class="green"
            >
                💾 Save Supplier
            </button>


            <a
                class="btn gray"
                href="/suppliers"
            >
                Cancel
            </a>


        </form>

    </div>

    """


    return render_page(
        "Add Supplier",
        content
    )


# =========================================================
# EDIT SUPPLIER
# =========================================================

@app.route(
    "/edit_supplier/<int:supplier_id>",
    methods=["GET", "POST"]
)
@login_required
def edit_supplier(supplier_id):


    db = get_db()


    supplier = db.execute(
        """
        SELECT *
        FROM suppliers
        WHERE id = ?
        """,
        (supplier_id,)
    ).fetchone()


    if supplier is None:

        db.close()

        flash(
            "Supplier not found.",
            "error"
        )

        return redirect(
            url_for("suppliers")
        )


    if request.method == "POST":


        name = request.form.get(
            "name",
            ""
        ).strip()


        phone = request.form.get(
            "phone",
            ""
        ).strip()


        if not name:

            db.close()

            flash(
                "Supplier name is required.",
                "error"
            )

            return redirect(
                url_for(
                    "edit_supplier",
                    supplier_id=supplier_id
                )
            )


        db.execute(
            """
            UPDATE suppliers

            SET
                name = ?,
                phone = ?

            WHERE id = ?
            """,
            (
                name,
                phone,
                supplier_id
            )
        )


        db.commit()

        db.close()


        flash(
            "Supplier updated successfully.",
            "success"
        )


        return redirect(
            url_for("suppliers")
        )


    db.close()


    content = f"""

    <h1>
        ✏ Edit Supplier
    </h1>


    <div class="card">

        <form method="post">


            <label>
                Supplier Name
            </label>

            <input
                type="text"
                name="name"
                value="{supplier["name"]}"
                required
            >


            <label>
                Phone Number
            </label>

            <input
                type="text"
                name="phone"
                value="{supplier["phone"] or ""}"
            >


            <button
                type="submit"
                class="green"
            >
                💾 Update Supplier
            </button>


            <a
                class="btn gray"
                href="/suppliers"
            >
                Cancel
            </a>


        </form>

    </div>

    """


    return render_page(
        "Edit Supplier",
        content
    )


# =========================================================
# DELETE SUPPLIER
# =========================================================

@app.route(
    "/delete_supplier/<int:supplier_id>"
)
@login_required
def delete_supplier(supplier_id):


    db = get_db()


    supplier = db.execute(
        """
        SELECT *
        FROM suppliers
        WHERE id = ?
        """,
        (supplier_id,)
    ).fetchone()


    if supplier is None:

        db.close()

        flash(
            "Supplier not found.",
            "error"
        )

        return redirect(
            url_for("suppliers")
        )


    purchase = db.execute(
        """
        SELECT id
        FROM purchases
        WHERE supplier_id = ?
        LIMIT 1
        """,
        (supplier_id,)
    ).fetchone()


    if purchase:

        db.close()

        flash(
            "This supplier has purchase history and cannot be deleted.",
            "error"
        )

        return redirect(
            url_for("suppliers")
        )


    payment = db.execute(
        """
        SELECT id
        FROM supplier_payments
        WHERE supplier_id = ?
        LIMIT 1
        """,
        (supplier_id,)
    ).fetchone()


    if payment:

        db.close()

        flash(
            "This supplier has payment history and cannot be deleted.",
            "error"
        )

        return redirect(
            url_for("suppliers")
        )


    db.execute(
        """
        DELETE FROM suppliers
        WHERE id = ?
        """,
        (supplier_id,)
    )


    db.commit()

    db.close()


    flash(
        "Supplier deleted successfully.",
        "success"
    )


    return redirect(
        url_for("suppliers")
    )


# =========================================================
# ADD PURCHASE
# =========================================================

@app.route(
    "/add_purchase",
    methods=["GET", "POST"]
)
@login_required
def add_purchase():


    db = get_db()


    suppliers_list = db.execute(
        """
        SELECT *
        FROM suppliers
        ORDER BY name
        """
    ).fetchall()


    products_list = db.execute(
        """
        SELECT *
        FROM products
        ORDER BY name
        """
    ).fetchall()


    if request.method == "POST":


        try:

            supplier_id = int(
                request.form.get(
                    "supplier_id"
                )
            )

            product_id = int(
                request.form.get(
                    "product_id"
                )
            )

            quantity = float(
                request.form.get(
                    "quantity",
                    0
                )
            )

            buying_price = float(
                request.form.get(
                    "buying_price",
                    0
                )
            )

        except (
            ValueError,
            TypeError
        ):

            db.close()

            flash(
                "Please enter valid purchase details.",
                "error"
            )

            return redirect(
                url_for("add_purchase")
            )


        if quantity <= 0:

            db.close()

            flash(
                "Quantity must be greater than zero.",
                "error"
            )

            return redirect(
                url_for("add_purchase")
            )


        if buying_price < 0:

            db.close()

            flash(
                "Buying price cannot be negative.",
                "error"
            )

            return redirect(
                url_for("add_purchase")
            )


        supplier = db.execute(
            """
            SELECT *
            FROM suppliers
            WHERE id = ?
            """,
            (supplier_id,)
        ).fetchone()


        product = db.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()


        if supplier is None:

            db.close()

            flash(
                "Supplier not found.",
                "error"
            )

            return redirect(
                url_for("add_purchase")
            )


        if product is None:

            db.close()

            flash(
                "Product not found.",
                "error"
            )

            return redirect(
                url_for("add_purchase")
            )


        total_amount = (
            quantity
            * buying_price
        )


        old_quantity = float(
            product["quantity"] or 0
        )


        new_quantity = (
            old_quantity
            + quantity
        )


        db.execute(
            """
            INSERT INTO purchases
            (
                supplier_id,
                product_id,
                product_name,
                quantity,
                buying_price,
                total_amount,
                purchase_date
            )

            VALUES
            (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                supplier_id,
                product_id,
                product["name"],
                quantity,
                buying_price,
                total_amount,
                now_string()
            )
        )


        db.execute(
            """
            UPDATE products

            SET
                quantity = ?,
                buying_price = ?

            WHERE id = ?
            """,
            (
                new_quantity,
                buying_price,
                product_id
            )
        )


        db.execute(
            """
            INSERT INTO stock_movements
            (
                product_id,
                product_name,
                movement_type,
                quantity,
                reason,
                created_at
            )

            VALUES
            (?, ?, ?, ?, ?, ?)
            """,
            (
                product_id,
                product["name"],
                "PURCHASE",
                quantity,
                "Purchase from "
                + supplier["name"],
                now_string()
            )
        )


        db.commit()

        db.close()


        flash(
            "Purchase added and stock updated successfully.",
            "success"
        )


        return redirect(
            url_for("purchases")
        )


    supplier_options = ""


    for supplier in suppliers_list:

        supplier_options += f"""

        <option value="{supplier["id"]}">
            {supplier["name"]}
        </option>

        """


    product_options = ""


    for product in products_list:

        product_options += f"""

        <option value="{product["id"]}">
            {product["name"]}
        </option>

        """


    db.close()


    content = f"""

    <h1>
        🛒 Add Purchase
    </h1>


    <div class="card">


        <form method="post">


            <label>
                Supplier
            </label>

            <select
                name="supplier_id"
                required
            >

                <option value="">
                    Select Supplier
                </option>

                {supplier_options}

            </select>


            <label>
                Product
            </label>

            <select
                name="product_id"
                required
            >

                <option value="">
                    Select Product
                </option>

                {product_options}

            </select>


            <label>
                Quantity
            </label>

            <input
                type="number"
                name="quantity"
                step="0.01"
                min="0.01"
                required
            >


            <label>
                Buying Price Per Unit
            </label>

            <input
                type="number"
                name="buying_price"
                step="0.01"
                min="0"
                required
            >


            <br>


            <button
                type="submit"
                class="green"
            >
                💾 Save Purchase
            </button>


            <a
                class="btn gray"
                href="/purchases"
            >
                Cancel
            </a>


        </form>


        <br>


        <p>
            <b>Note:</b>
            Saving a purchase automatically increases
            the product stock.
        </p>


    </div>

    """


    return render_page(
        "Add Purchase",
        content
    )


# =========================================================
# PURCHASE HISTORY
# =========================================================

@app.route("/purchases")
@login_required
def purchases():

    search = request.args.get(
        "search",
        ""
    ).strip()


    db = get_db()


    if search:

        purchase_list = db.execute(
            """
            SELECT
                purchases.*,
                suppliers.name AS supplier_name

            FROM purchases

            LEFT JOIN suppliers
                ON suppliers.id =
                   purchases.supplier_id

            WHERE purchases.product_name LIKE ?
               OR suppliers.name LIKE ?

            ORDER BY purchases.id DESC
            """,
            (
                "%" + search + "%",
                "%" + search + "%"
            )
        ).fetchall()

    else:

        purchase_list = db.execute(
            """
            SELECT
                purchases.*,
                suppliers.name AS supplier_name

            FROM purchases

            LEFT JOIN suppliers
                ON suppliers.id =
                   purchases.supplier_id

            ORDER BY purchases.id DESC
            """
        ).fetchall()


    total = db.execute(
        """
        SELECT COALESCE(
            SUM(total_amount),
            0
        ) AS total

        FROM purchases
        """
    ).fetchone()["total"]


    rows = ""


    for purchase in purchase_list:

        rows += f"""

        <tr>

            <td>
                {purchase["id"]}
            </td>

            <td>
                {purchase["purchase_date"]}
            </td>

            <td>
                {purchase["supplier_name"] or "-"}
            </td>

            <td>
                {purchase["product_name"]}
            </td>

            <td>
                {float(purchase["quantity"] or 0):g}
            </td>

            <td>
                {money(purchase["buying_price"])}
            </td>

            <td>
                <b>
                    {money(purchase["total_amount"])}
                </b>
            </td>

        </tr>

        """


    db.close()


    content = f"""

    <h1>
        🛒 Purchase Management
    </h1>


    <div class="grid">


        <div class="stat">

            <h3>
                Total Purchase Records
            </h3>

            <p>
                {len(purchase_list)}
            </p>

        </div>


        <div class="stat">

            <h3>
                Total Purchase Amount
            </h3>

            <p>
                {money(total)}
            </p>

        </div>


    </div>


    <br>


    <div class="card">

        <form method="get">

            <label>
                Search
            </label>

            <input
                type="text"
                name="search"
                value="{search}"
                placeholder="Supplier or product"
            >


            <button type="submit">
                🔍 Search
            </button>


            <a
                class="btn gray"
                href="/purchases"
            >
                Clear
            </a>


            <a
                class="btn green"
                href="/add_purchase"
            >
                ➕ Add Purchase
            </a>

        </form>

    </div>


    <div class="card">

        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        ID
                    </th>

                    <th>
                        Date
                    </th>

                    <th>
                        Supplier
                    </th>

                    <th>
                        Product
                    </th>

                    <th>
                        Quantity
                    </th>

                    <th>
                        Buying Price
                    </th>

                    <th>
                        Total
                    </th>

                </tr>

                {rows}

            </table>

        </div>

    </div>

    """


    return render_page(
        "Purchases",
        content
    )


# =========================================================
# SUPPLIER PAYMENT
# =========================================================

@app.route(
    "/supplier_payment/<int:supplier_id>",
    methods=["GET", "POST"]
)
@login_required
def supplier_payment(supplier_id):


    db = get_db()


    supplier = db.execute(
        """
        SELECT *
        FROM suppliers
        WHERE id = ?
        """,
        (supplier_id,)
    ).fetchone()


    if supplier is None:

        db.close()

        flash(
            "Supplier not found.",
            "error"
        )

        return redirect(
            url_for("suppliers")
        )


    purchase_total = db.execute(
        """
        SELECT COALESCE(
            SUM(total_amount),
            0
        ) AS total

        FROM purchases

        WHERE supplier_id = ?
        """,
        (supplier_id,)
    ).fetchone()["total"]


    paid_total = db.execute(
        """
        SELECT COALESCE(
            SUM(amount),
            0
        ) AS total

        FROM supplier_payments

        WHERE supplier_id = ?
        """,
        (supplier_id,)
    ).fetchone()["total"]


    balance = (
        float(purchase_total or 0)
        - float(paid_total or 0)
    )


    if request.method == "POST":


        try:

            amount = float(
                request.form.get(
                    "amount",
                    0
                )
            )

        except ValueError:

            db.close()

            flash(
                "Enter a valid payment amount.",
                "error"
            )

            return redirect(
                url_for(
                    "supplier_payment",
                    supplier_id=supplier_id
                )
            )


        payment_method = request.form.get(
            "payment_method",
            "Cash"
        ).strip()


        if amount <= 0:

            db.close()

            flash(
                "Payment amount must be greater than zero.",
                "error"
            )

            return redirect(
                url_for(
                    "supplier_payment",
                    supplier_id=supplier_id
                )
            )


        if amount > balance:

            db.close()

            flash(
                "Payment cannot be greater than outstanding balance.",
                "error"
            )

            return redirect(
                url_for(
                    "supplier_payment",
                    supplier_id=supplier_id
                )
            )


        db.execute(
            """
            INSERT INTO supplier_payments
            (
                supplier_id,
                amount,
                payment_method,
                created_at
            )

            VALUES (?, ?, ?, ?)
            """,
            (
                supplier_id,
                amount,
                payment_method,
                now_string()
            )
        )


        db.commit()

        db.close()


        flash(
            "Supplier payment recorded successfully.",
            "success"
        )


        return redirect(
            url_for(
                "supplier_history",
                supplier_id=supplier_id
            )
        )


    db.close()


    content = f"""

    <h1>
        💵 Supplier Payment
    </h1>


    <div class="card">


        <h2>
            {supplier["name"]}
        </h2>


        <p>
            Phone:
            <b>
                {supplier["phone"] or "-"}
            </b>
        </p>


        <p>
            Total Purchases:
            <b>
                {money(purchase_total)}
            </b>
        </p>


        <p>
            Already Paid:
            <b>
                {money(paid_total)}
            </b>
        </p>


        <p>
            Outstanding Balance:
            <b>
                {money(balance)}
            </b>
        </p>


        <hr>


        <form method="post">


            <label>
                Payment Amount
            </label>

            <input
                type="number"
                name="amount"
                step="0.01"
                min="0.01"
                max="{balance}"
                required
            >


            <label>
                Payment Method
            </label>

            <select name="payment_method">

                <option value="Cash">
                    Cash
                </option>

                <option value="UPI">
                    UPI
                </option>

                <option value="Card">
                    Card
                </option>

                <option value="Bank">
                    Bank Transfer
                </option>

            </select>


            <button
                type="submit"
                class="green"
            >
                💾 Save Payment
            </button>


            <a
                class="btn gray"
                href="/suppliers"
            >
                Cancel
            </a>


        </form>

    </div>

    """


    return render_page(
        "Supplier Payment",
        content
    )


# =========================================================
# SUPPLIER HISTORY
# =========================================================

@app.route(
    "/supplier_history/<int:supplier_id>"
)
@login_required
def supplier_history(supplier_id):


    db = get_db()


    supplier = db.execute(
        """
        SELECT *
        FROM suppliers
        WHERE id = ?
        """,
        (supplier_id,)
    ).fetchone()


    if supplier is None:

        db.close()

        flash(
            "Supplier not found.",
            "error"
        )

        return redirect(
            url_for("suppliers")
        )


    purchases_list = db.execute(
        """
        SELECT *
        FROM purchases

        WHERE supplier_id = ?

        ORDER BY id DESC
        """,
        (supplier_id,)
    ).fetchall()


    payments_list = db.execute(
        """
        SELECT *
        FROM supplier_payments

        WHERE supplier_id = ?

        ORDER BY id DESC
        """,
        (supplier_id,)
    ).fetchall()


    purchase_total = sum(
        float(row["total_amount"] or 0)
        for row in purchases_list
    )


    payment_total = sum(
        float(row["amount"] or 0)
        for row in payments_list
    )


    balance = (
        purchase_total
        - payment_total
    )


    db.close()


    purchase_rows = ""


    for purchase in purchases_list:

        purchase_rows += f"""

        <tr>

            <td>
                {purchase["purchase_date"]}
            </td>

            <td>
                {purchase["product_name"]}
            </td>

            <td>
                {float(purchase["quantity"] or 0):g}
            </td>

            <td>
                {money(purchase["buying_price"])}
            </td>

            <td>
                {money(purchase["total_amount"])}
            </td>

        </tr>

        """


    payment_rows = ""


    for payment in payments_list:

        payment_rows += f"""

        <tr>

            <td>
                {payment["created_at"]}
            </td>

            <td>
                {money(payment["amount"])}
            </td>

            <td>
                {payment["payment_method"]}
            </td>

        </tr>

        """


    content = f"""

    <h1>
        📋 Supplier History
    </h1>


    <div class="card">


        <h2>
            {supplier["name"]}
        </h2>


        <p>
            Phone:
            <b>
                {supplier["phone"] or "-"}
            </b>
        </p>


        <div class="grid">


            <div class="stat">

                <h3>
                    Purchases
                </h3>

                <p>
                    {money(purchase_total)}
                </p>

            </div>


            <div class="stat">

                <h3>
                    Paid
                </h3>

                <p>
                    {money(payment_total)}
                </p>

            </div>


            <div class="stat">

                <h3>
                    Balance
                </h3>

                <p>
                    {money(balance)}
                </p>

            </div>


        </div>


        <br>


        <a
            class="btn green"
            href="/supplier_payment/{supplier_id}"
        >
            💵 Make Payment
        </a>


        <a
            class="btn gray"
            href="/suppliers"
        >
            Back
        </a>

    </div>


    <div class="card">

        <h2>
            🛒 Purchase History
        </h2>


        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        Date
                    </th>

                    <th>
                        Product
                    </th>

                    <th>
                        Quantity
                    </th>

                    <th>
                        Buying Price
                    </th>

                    <th>
                        Total
                    </th>

                </tr>

                {purchase_rows}

            </table>

        </div>

    </div>


    <div class="card">

        <h2>
            💵 Payment History
        </h2>


        <div style="overflow-x:auto;">

            <table>

                <tr>

                    <th>
                        Date
                    </th>

                    <th>
                        Amount
                    </th>

                    <th>
                        Method
                    </th>

                </tr>

                {payment_rows}

            </table>

        </div>

    </div>

    """


    return render_page(
        "Supplier History",
        content
    )
    # =========================================================
# PART 5
# BILLING SYSTEM
# =========================================================


# =========================================================
# BILLING PAGE
# =========================================================

@app.route(
    "/billing",
    methods=["GET", "POST"]
)
@login_required
def billing():

    db = get_db()

    try:



        products_list = db.execute(
            """
            SELECT *
            FROM products
            WHERE quantity > 0
            ORDER BY name
            """
        ).fetchall()


        customers_list = db.execute(
            """
            SELECT *
            FROM customers
            ORDER BY name
            """
        ).fetchall()


        if request.method == "POST":

            try:

                product_ids = request.form.getlist(
                    "product_id"
                )

                quantities = request.form.getlist(
                    "quantity"
                )

                discount = float(
                    request.form.get(
                        "discount",
                        0
                    )
                )

                gst_percent = float(
                    request.form.get(
                        "gst_percent",
                        0
                    )
                )

            except ValueError:

                db.close()

                flash(
                    "Please enter valid billing values.",
                    "error"
                )

                return redirect(
                    url_for("billing")
                )


            customer_id_raw = request.form.get(
                "customer_id",
                ""
            ).strip()


            customer_id = None


            if customer_id_raw:

                try:

                    customer_id = int(
                        customer_id_raw
                    )

                except ValueError:

                    db.close()

                    flash(
                        "Invalid customer.",
                        "error"
                    )

                    return redirect(
                        url_for("billing")
                    )


            payment_method = request.form.get(
                "payment_method",
                "Cash"
            ).strip()


            customer_name = request.form.get(
                "customer_name",
                ""
            ).strip()


            customer_phone = request.form.get(
                "customer_phone",
                ""
            ).strip()


            if customer_id:

                customer = db.execute(
                    """
                    SELECT *
                    FROM customers
                    WHERE id = ?
                    """,
                    (customer_id,)
                ).fetchone()


                if customer:

                    customer_name = customer["name"]

                    customer_phone = (
                        customer["phone"] or ""
                    )


            if discount < 0:

                db.close()

                flash(
                    "Discount cannot be negative.",
                    "error"
                )

                return redirect(
                    url_for("billing")
                )


            if gst_percent < 0:

                db.close()

                flash(
                    "GST cannot be negative.",
                    "error"
                )

                return redirect(
                    url_for("billing")
                )


            # -------------------------------------------------
            # PREPARE BILL ITEMS
            # -------------------------------------------------

            bill_items = []

            subtotal = 0

            total_profit = 0


            if len(product_ids) == 0:

                db.close()

                flash(
                    "Please add at least one product.",
                    "error"
                )

                return redirect(
                    url_for("billing")
                )


            for index in range(
                len(product_ids)
            ):


                try:

                    product_id = int(
                        product_ids[index]
                    )

                    quantity = float(
                        quantities[index]
                    )

                except (
                    ValueError,
                    TypeError,
                    IndexError
                ):

                    continue


                if quantity <= 0:

                    continue


                product = db.execute(
                    """
                    SELECT *
                    FROM products
                    WHERE id = ?
                    """,
                    (product_id,)
                ).fetchone()


                if product is None:

                    db.close()

                    flash(
                        "One of the selected products was not found.",
                        "error"
                    )

                    return redirect(
                        url_for("billing")
                    )


                available_stock = float(
                    product["quantity"] or 0
                )


                if quantity > available_stock:

                    db.close()

                    flash(
                        f'Not enough stock for "{product["name"]}". '
                        f'Available: {available_stock:g}',
                        "error"
                    )

                    return redirect(
                        url_for("billing")
                    )


                selling_price = float(
                    product["selling_price"] or 0
                )


                buying_price = float(
                    product["buying_price"] or 0
                )


                amount = (
                    quantity
                    * selling_price
                )


                item_profit = (
                    quantity
                    * (
                        selling_price
                        - buying_price
                    )
                )


                subtotal += amount

                total_profit += item_profit


                bill_items.append({

                    "product_id":
                        product_id,

                    "product_name":
                        product["name"],

                    "quantity":
                        quantity,

                    "unit":
                        product["unit"],

                    "buying_price":
                        buying_price,

                    "selling_price":
                        selling_price,

                    "amount":
                        amount,

                    "profit":
                        item_profit

                })


            if not bill_items:

                db.close()

                flash(
                    "Please enter a valid quantity for at least one product.",
                    "error"
                )

                return redirect(
                    url_for("billing")
                )


            # -------------------------------------------------
            # CALCULATE TOTAL
            # -------------------------------------------------

            taxable_amount = (
                subtotal
                - discount
            )


            if taxable_amount < 0:

                taxable_amount = 0


            gst_amount = (
                taxable_amount
                * gst_percent
                / 100
            )


            total = (
                taxable_amount
                + gst_amount
            )


            # Discount reduces profit.
            total_profit -= discount


            # -------------------------------------------------
            # PAYMENT / UDHAR
            # -------------------------------------------------

            if payment_method.lower() == "udhaar":

                if customer_id is None:

                    db.close()

                    flash(
                        "Select a customer for Udhaar billing.",
                        "error"
                    )

                    return redirect(
                        url_for("billing")
                    )


            # -------------------------------------------------
            # CREATE BILL NUMBER
            # -------------------------------------------------

            last_bill = db.execute(
                """
                SELECT id
                FROM bills
                ORDER BY id DESC
                LIMIT 1
                """
            ).fetchone()


            if last_bill:

                next_number = (
                    int(last_bill["id"])
                    + 1
                )

            else:

                next_number = 1


            bill_number = (
                "PKS-"
                + str(next_number).zfill(5)
            )


            # -------------------------------------------------
            # INSERT BILL
            # -------------------------------------------------

            cursor = db.execute(
                """
                INSERT INTO bills
                (
                    bill_number,
                    customer_id,
                    customer_name,
                    customer_phone,
                    subtotal,
                    discount,
                    gst_percent,
                    gst_amount,
                    total,
                    profit,
                    payment_method,
                    created_at
                )

                VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bill_number,
                    customer_id,
                    customer_name,
                    customer_phone,
                    subtotal,
                    discount,
                    gst_percent,
                    gst_amount,
                    total,
                    total_profit,
                    payment_method,
                    now_string()
                )
            )


            bill_id = cursor.lastrowid


            # -------------------------------------------------
            # INSERT ITEMS + UPDATE STOCK
            # -------------------------------------------------

            for item in bill_items:


                db.execute(
                    """
                    INSERT INTO bill_items
                    (
                        bill_id,
                        product_id,
                        product_name,
                        quantity,
                        unit,
                        buying_price,
                        selling_price,
                        amount,
                        profit
                    )

                    VALUES
                    (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        bill_id,
                        item["product_id"],
                        item["product_name"],
                        item["quantity"],
                        item["unit"],
                        item["buying_price"],
                        item["selling_price"],
                        item["amount"],
                        item["profit"]
                    )
                )


                db.execute(
                    """
                    UPDATE products

                    SET quantity =
                        quantity - ?

                    WHERE id = ?
                    """,
                    (
                        item["quantity"],
                        item["product_id"]
                    )
                )


                db.execute(
                    """
                    INSERT INTO stock_movements
                    (
                        product_id,
                        product_name,
                        movement_type,
                        quantity,
                        reason,
                        created_at
                    )

                    VALUES
                    (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item["product_id"],
                        item["product_name"],
                        "SALE",
                        -item["quantity"],
                        "Bill " + bill_number,
                        now_string()
                    )
                )


            # -------------------------------------------------
            # ADD UDHAR TO CUSTOMER
            # -------------------------------------------------

            if payment_method.lower() == "udhaar":

                db.execute(
                    """
                    UPDATE customers

                    SET udhaar =
                        udhaar + ?

                    WHERE id = ?
                    """,
                    (
                        total,
                        customer_id
                    )
                )


            db.commit()

            db.close()


            flash(
                "Bill created successfully.",
                "success"
            )


            return redirect(
                url_for(
                    "invoice",
                    bill_id=bill_id
                )
            )


        # =====================================================
        # PRODUCT OPTIONS
        # =====================================================

        product_options = ""


        for product in products_list:

            product_options += f"""

            <option
                value="{product["id"]}"
            >
                {product["name"]}
                |
                Stock:
                {float(product["quantity"] or 0):g}
                {product["unit"]}
                |
                {money(product["selling_price"])}
            </option>

            """


        # =====================================================
        # CUSTOMER OPTIONS
        # =====================================================

        customer_options = """

        <option value="">
            Walk-in Customer
        </option>

        """


        for customer in customers_list:

            customer_options += f"""

            <option
                value="{customer["id"]}"
            >
                {customer["name"]}
                -
                {customer["phone"] or "No phone"}
            </option>

            """


        db.close()


        content = f"""

        <h1>
            🧾 New Bill
        </h1>


        <div class="card">

            <form
                method="post"
                id="billingForm"
            >


                <h2>
                    Customer Details
                </h2>


                <label>
                    Customer
                </label>

                <select
                    name="customer_id"
                    id="customer_id"
                >

                    {customer_options}

                </select>


                <div class="form-grid">


                    <div>

                        <label>
                            Customer Name
                        </label>

                        <input
                            type="text"
                            name="customer_name"
                            placeholder="Walk-in customer"
                        >

                    </div>


                    <div>

                        <label>
                            Customer Phone
                        </label>

                        <input
                            type="text"
                            name="customer_phone"
                            placeholder="Phone number"
                        >

                    </div>


                </div>


                <hr>


                <h2>
                    Bill Items
                </h2>


                <div id="items">


                    <div
                        class="card bill-row"
                        style="border:1px solid #ddd;"
                    >


                        <div class="form-grid">


                            <div>

                                <label>
                                    Product
                                </label>

                                <select
                                    name="product_id"
                                    required
                                >

                                    <option value="">
                                        Select Product
                                    </option>

                                    {product_options}

                                </select>

                            </div>


                            <div>

                                <label>
                                    Quantity
                                </label>

                                <input
                                    type="number"
                                    name="quantity"
                                    step="0.01"
                                    min="0.01"
                                    value="1"
                                    required
                                >

                            </div>


                        </div>


                        <button
                            type="button"
                            class="red"
                            onclick="removeRow(this)"
                        >
                            🗑 Remove
                        </button>


                    </div>


                </div>


                <button
                    type="button"
                    class="orange"
                    onclick="addRow()"
                >
                    ➕ Add Another Product
                </button>


                <br>
                <br>


                <div class="form-grid">


                    <div>

                        <label>
                            Discount
                        </label>

                        <input
                            type="number"
                            name="discount"
                            step="0.01"
                            min="0"
                            value="0"
                        >

                    </div>


                    <div>

                        <label>
                            GST %
                        </label>

                        <input
                            type="number"
                            name="gst_percent"
                            step="0.01"
                            min="0"
                            value="0"
                        >

                    </div>


                    <div>

                        <label>
                            Payment Method
                        </label>

                        <select
                            name="payment_method"
                            required
                        >

                            <option value="Cash">
                                Cash
                            </option>

                            <option value="UPI">
                                UPI
                            </option>

                            <option value="Card">
                                Card
                            </option>

                            <option value="Bank">
                                Bank Transfer
                            </option>

                            <option value="Udhaar">
                                Udhaar
                            </option>

                        </select>

                    </div>


                </div>


                <br>


                <button
                    type="submit"
                    class="green"
                >
                    🧾 Create Bill
                </button>


                <a
                    class="btn gray"
                    href="/"
                >
                    Cancel
                </a>


            </form>

        </div>


        <script>

        function addRow() {{

            const container =
                document.getElementById("items");

            const firstRow =
                container.querySelector(".bill-row");

            const newRow =
                firstRow.cloneNode(true);

            newRow
                .querySelector("select")
                .selectedIndex = 0;

            newRow
                .querySelector("input")
                .value = 1;

            container.appendChild(newRow);

        }}


        function removeRow(button) {{

            const container =
                document.getElementById("items");

            const rows =
                container.querySelectorAll(".bill-row");

            if (rows.length <= 1) {{

                alert(
                    "At least one product is required."
                );

                return;

            }}

            button
                .closest(".bill-row")
                .remove();

        }}

        </script>

        """


        return render_page(
            "Billing",
            content
        )

    except sqlite3.OperationalError as e:

        db.rollback()

        flash(
            "Database is busy. Please try again in a moment.",
            "error"
        )

        return redirect(
            url_for("billing")
        )

    finally:

        db.close()




# =========================================================
# BILL HISTORY / SALES
# =========================================================

@app.route("/bill_history")
@login_required
def bill_history():

    search = request.args.get(
        "search",
        ""
    ).strip()


    db = get_db()

    try:



        if search:

            bill_list = db.execute(
                """
                SELECT *
                FROM bills

                WHERE bill_number LIKE ?
                   OR customer_name LIKE ?
                   OR customer_phone LIKE ?

                ORDER BY id DESC
                """,
                (
                    "%" + search + "%",
                    "%" + search + "%",
                    "%" + search + "%"
                )
            ).fetchall()

        else:

            bill_list = db.execute(
                """
                SELECT *
                FROM bills
                ORDER BY id DESC
                """
            ).fetchall()


        total_sales = sum(
            float(bill["total"] or 0)
            for bill in bill_list
        )


        total_profit = sum(
            float(bill["profit"] or 0)
            for bill in bill_list
        )


        rows = ""


        for bill in bill_list:

            rows += f"""

            <tr>

                <td>
                    {bill["bill_number"] or bill["id"]}
                </td>

                <td>
                    {bill["created_at"]}
                </td>

                <td>
                    {bill["customer_name"] or "Walk-in"}
                </td>

                <td>
                    {bill["payment_method"]}
                </td>

                <td>
                    {money(bill["total"])}
                </td>

                <td>
                    {money(bill["profit"])}
                </td>

                <td>

                    <div class="actions">

                        <a
                            class="btn"
                            href="/invoice/{bill["id"]}"
                        >
                            🧾 View
                        </a>


                        <a
                            class="btn red"
                            href="/delete_bill/{bill["id"]}"
                            onclick="return confirm('Delete this bill? Stock will be restored.')"
                        >
                            🗑 Delete
                        </a>

                    </div>

                </td>

            </tr>

            """


        db.close()


        content = f"""

        <h1>
            📋 Sales / Bill History
        </h1>


        <div class="grid">


            <div class="stat">

                <h3>
                    Bills Found
                </h3>

                <p>
                    {len(bill_list)}
                </p>

            </div>


            <div class="stat">

                <h3>
                    Sales
                </h3>

                <p>
                    {money(total_sales)}
                </p>

            </div>


            <div class="stat">

                <h3>
                    Profit
                </h3>

                <p>
                    {money(total_profit)}
                </p>

            </div>


        </div>


        <br>


        <div class="card">

            <form method="get">

                <label>
                    Search Bills
                </label>

                <input
                    type="text"
                    name="search"
                    value="{search}"
                    placeholder="Bill number, customer name or phone"
                >


                <button type="submit">
                    🔍 Search
                </button>


                <a
                    class="btn gray"
                    href="/bill_history"
                >
                    Clear
                </a>


                <a
                    class="btn green"
                    href="/billing"
                >
                    ➕ New Bill
                </a>

            </form>

        </div>


        <div class="card">

            <div style="overflow-x:auto;">

                <table>

                    <tr>

                        <th>
                            Bill No.
                        </th>

                        <th>
                            Date
                        </th>

                        <th>
                            Customer
                        </th>

                        <th>
                            Payment
                        </th>

                        <th>
                            Total
                        </th>

                        <th>
                            Profit
                        </th>

                        <th>
                            Actions
                        </th>

                    </tr>

                    {rows}

                </table>

            </div>

        </div>

        """


        return render_page(
            "Bill History",
            content
        )

    except sqlite3.OperationalError as e:

        db.rollback()

        flash(
            "Database is busy. Please try again in a moment.",
            "error"
        )

        return redirect(
            url_for("bill_history")
        )

    finally:

        db.close()




# =========================================================
# INVOICE
# =========================================================

@app.route(
    "/invoice/<int:bill_id>"
)
@login_required
def invoice(bill_id):

    db = get_db()

    try:



        bill = db.execute(
            """
            SELECT *
            FROM bills
            WHERE id = ?
            """,
            (bill_id,)
        ).fetchone()


        if bill is None:

            db.close()

            flash(
                "Bill not found.",
                "error"
            )

            return redirect(
                url_for("bill_history")
            )


        items = db.execute(
            """
            SELECT *
            FROM bill_items

            WHERE bill_id = ?

            ORDER BY id
            """,
            (bill_id,)
        ).fetchall()


        setting = db.execute(
            """
            SELECT *
            FROM settings
            WHERE id = 1
            """
        ).fetchone()


        db.close()


        item_rows = ""


        item_number = 1


        for item in items:

            item_rows += f"""

            <tr>

                <td>
                    {item_number}
                </td>

                <td>
                    {item["product_name"]}
                </td>

                <td>
                    {float(item["quantity"] or 0):g}
                    {item["unit"]}
                </td>

                <td>
                    {money(item["selling_price"])}
                </td>

                <td>
                    {money(item["amount"])}
                </td>

            </tr>

            """


            item_number += 1


        shop_name = (
            setting["shop_name"]
            if setting
            else "Pandey Kirana Store"
        )


        address = (
            setting["address"]
            if setting
            else ""
        )


        shop_phone = (
            setting["phone"]
            if setting
            else ""
        )


        gst_number = (
            setting["gst_number"]
            if setting
            else ""
        )


        content = f"""

        <div class="card invoice">


            <div class="no-print actions">

                <a
                    class="btn gray"
                    href="/bill_history"
                >
                    ← Back
                </a>


                <button
                    onclick="window.print()"
                >
                    🖨 Print
                </button>

            </div>


            <br>


            <div style="text-align:center;">

                <h1>
                    {shop_name}
                </h1>


                <p>
                    {address}
                </p>


                <p>
                    Phone:
                    {shop_phone}
                </p>


                <p>
                    GST:
                    {gst_number or "N/A"}
                </p>

            </div>


            <hr>


            <div class="form-grid">


                <div>

                    <b>
                        Bill No:
                    </b>

                    {bill["bill_number"]}

                    <br><br>

                    <b>
                        Date:
                    </b>

                    {bill["created_at"]}

                </div>


                <div>

                    <b>
                        Customer:
                    </b>

                    {bill["customer_name"] or "Walk-in Customer"}

                    <br><br>

                    <b>
                        Phone:
                    </b>

                    {bill["customer_phone"] or "-"}

                </div>


            </div>


            <br>


            <table>

                <tr>

                    <th>
                        #
                    </th>

                    <th>
                        Product
                    </th>

                    <th>
                        Quantity
                    </th>

                    <th>
                        Price
                    </th>

                    <th>
                        Amount
                    </th>

                </tr>

                {item_rows}

            </table>


            <br>


            <div style="max-width:400px;margin-left:auto;">


                <p>
                    Subtotal:
                    <b>
                        {money(bill["subtotal"])}
                    </b>
                </p>


                <p>
                    Discount:
                    <b>
                        {money(bill["discount"])}
                    </b>
                </p>


                <p>
                    GST ({bill["gst_percent"]}%):
                    <b>
                        {money(bill["gst_amount"])}
                    </b>
                </p>


                <hr>


                <h2>
                    Total:
                    {money(bill["total"])}
                </h2>


                <p>
                    Payment:
                    <b>
                        {bill["payment_method"]}
                    </b>
                </p>


            </div>


            <hr>


            <p style="text-align:center;">

                Thank you for shopping with us!

            </p>


        </div>

        """


        return render_page(
            "Invoice",
            content
        )
    except sqlite3.OperationalError as e:

        db.rollback()

        flash(
            "Database is busy. Please try again in a moment.",
            "error"
        )

        return redirect(
            url_for("bill_history")
        )

    finally:

        db.close()



# =========================================================
# DELETE BILL
# =========================================================

@app.route(
    "/delete_bill/<int:bill_id>"
)
@login_required
def delete_bill(bill_id):


    db = get_db()


    bill = db.execute(
        """
        SELECT *
        FROM bills
        WHERE id = ?
        """,
        (bill_id,)
    ).fetchone()


    if bill is None:

        db.close()

        flash(
            "Bill not found.",
            "error"
        )

        return redirect(
            url_for("bill_history")
        )


    items = db.execute(
        """
        SELECT *
        FROM bill_items

        WHERE bill_id = ?
        """,
        (bill_id,)
    ).fetchall()


    # -----------------------------------------------------
    # RESTORE STOCK
    # -----------------------------------------------------

    for item in items:

        db.execute(
            """
            UPDATE products

            SET quantity =
                quantity + ?

            WHERE id = ?
            """,
            (
                item["quantity"],
                item["product_id"]
            )
        )


        db.execute(
            """
            INSERT INTO stock_movements
            (
                product_id,
                product_name,
                movement_type,
                quantity,
                reason,
                created_at
            )

            VALUES
            (?, ?, ?, ?, ?, ?)
            """,
            (
                item["product_id"],
                item["product_name"],
                "SALE REVERSAL",
                item["quantity"],
                "Deleted bill "
                + str(
                    bill["bill_number"]
                    or bill_id
                ),
                now_string()
            )
        )


    # -----------------------------------------------------
    # REMOVE UDHAR
    # -----------------------------------------------------

    if (
        bill["payment_method"]
        and
        bill["payment_method"].lower()
        == "udhaar"
        and
        bill["customer_id"]
    ):

        db.execute(
            """
            UPDATE customers

            SET udhaar =
                CASE
                    WHEN udhaar >= ?
                    THEN udhaar - ?
                    ELSE 0
                END

            WHERE id = ?
            """,
            (
                bill["total"],
                bill["total"],
                bill["customer_id"]
            )
        )


    # -----------------------------------------------------
    # DELETE ITEMS + BILL
    # -----------------------------------------------------

    db.execute(
        """
        DELETE FROM bill_items
        WHERE bill_id = ?
        """,
        (bill_id,)
    )


    db.execute(
        """
        DELETE FROM bills
        WHERE id = ?
        """,
        (bill_id,)
    )


    db.commit()

    db.close()


    flash(
        "Bill deleted and stock restored successfully.",
        "success"
    )


    return redirect(
        url_for("bill_history")
    )
    # ============================================================
# STEP 31-36 : EXPENSES + REPORTS
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# STEP 31 : EXPENSE MANAGEMENT
# ------------------------------------------------------------

@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    db = get_db()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        amount_text = request.form.get("amount", "").strip()
        category = request.form.get("category", "Other").strip()
        note = request.form.get("note", "").strip()

        if not title or not amount_text:
            flash("Expense title and amount are required.", "error")
            db.close()
            return redirect(url_for("expenses"))

        try:
            amount = float(amount_text)
        except ValueError:
            flash("Please enter a valid amount.", "error")
            db.close()
            return redirect(url_for("expenses"))

        if amount <= 0:
            flash("Amount must be greater than 0.", "error")
            db.close()
            return redirect(url_for("expenses"))

        db.execute("""
            INSERT INTO expenses
            (title, amount, category, note, expense_date)
            VALUES (?, ?, ?, ?, ?)
        """, (
            title,
            amount,
            category,
            note,
            datetime.now().strftime("%Y-%m-%d")
        ))

        db.commit()
        db.close()

        flash("Expense added successfully.", "success")
        return redirect(url_for("expenses"))

    rows = db.execute("""
        SELECT *
        FROM expenses
        ORDER BY id DESC
    """).fetchall()

    total_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """).fetchone()[0]

    today_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE expense_date = ?
    """, (
        datetime.now().strftime("%Y-%m-%d"),
    )).fetchone()[0]

    db.close()

    body = """
    <div class="page-header">
        <div>
            <h1>💸 Expenses</h1>
            <p class="muted">Manage shop expenses and daily spending.</p>
        </div>
    </div>

    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-title">Total Expenses</div>
            <div class="stat-value">{{ money(total_expenses) }}</div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Today's Expenses</div>
            <div class="stat-value">{{ money(today_expenses) }}</div>
        </div>
    </div>

    <div class="card">
        <h2>Add Expense</h2>

        <form method="POST" class="form-grid">

            <div>
                <label>Expense Title</label>
                <input
                    type="text"
                    name="title"
                    placeholder="e.g. Electricity Bill"
                    required
                >
            </div>

            <div>
                <label>Amount</label>
                <input
                    type="number"
                    name="amount"
                    step="0.01"
                    min="0.01"
                    placeholder="Enter amount"
                    required
                >
            </div>

            <div>
                <label>Category</label>
                <select name="category">
                    <option>Rent</option>
                    <option>Electricity</option>
                    <option>Transport</option>
                    <option>Salary</option>
                    <option>Maintenance</option>
                    <option>Packaging</option>
                    <option>Other</option>
                </select>
            </div>

            <div>
                <label>Note</label>
                <input
                    type="text"
                    name="note"
                    placeholder="Optional note"
                >
            </div>

            <div class="full">
                <button class="btn btn-primary" type="submit">
                    ➕ Add Expense
                </button>
            </div>

        </form>
    </div>

    <div class="card">
        <h2>Expense History</h2>

        {% if rows %}
        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>#</th>
                        <th>Date</th>
                        <th>Title</th>
                        <th>Category</th>
                        <th>Note</th>
                        <th>Amount</th>
                        <th>Action</th>
                    </tr>
                </thead>

                <tbody>
                {% for row in rows %}
                    <tr>
                        <td>{{ row["id"] }}</td>
                        <td>{{ row["expense_date"] }}</td>
                        <td>{{ row["title"] }}</td>
                        <td>{{ row["category"] }}</td>
                        <td>{{ row["note"] or "-" }}</td>
                        <td><strong>{{ money(row["amount"]) }}</strong></td>

                        <td>
                            <a
                                class="btn btn-danger btn-sm"
                                href="{{ url_for('delete_expense', expense_id=row['id']) }}"
                                onclick="return confirm('Delete this expense?')"
                            >
                                Delete
                            </a>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>

        {% else %}
            <div class="empty">
                No expenses found.
            </div>
        {% endif %}
    </div>
    """

    return render_page(
        "Expenses",
        body,
        rows=rows,
        total_expenses=total_expenses,
        today_expenses=today_expenses
    )


# ------------------------------------------------------------
# STEP 32 : DELETE EXPENSE
# ------------------------------------------------------------

@app.route("/delete_expense/<int:expense_id>")
@login_required
def delete_expense(expense_id):
    db = get_db()

    expense = db.execute("""
        SELECT *
        FROM expenses
        WHERE id = ?
    """, (expense_id,)).fetchone()

    if not expense:
        db.close()
        flash("Expense not found.", "error")
        return redirect(url_for("expenses"))

    db.execute("""
        DELETE FROM expenses
        WHERE id = ?
    """, (expense_id,))

    db.commit()
    db.close()

    flash("Expense deleted successfully.", "success")
    return redirect(url_for("expenses"))


# ------------------------------------------------------------
# STEP 33 : REPORTS
# ------------------------------------------------------------

@app.route("/reports")
@login_required
def reports():
    db = get_db()

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    # Today's sales
    today_sales = db.execute("""
        SELECT
            COALESCE(SUM(total), 0)
        FROM bills
        WHERE DATE(bill_date) = ?
    """, (today,)).fetchone()[0]

    # Monthly sales
    monthly_sales = db.execute("""
        SELECT
            COALESCE(SUM(total), 0)
        FROM bills
        WHERE strftime('%Y-%m', bill_date) = ?
    """, (month,)).fetchone()[0]

    # Today's bills
    today_bills = db.execute("""
        SELECT COUNT(*)
        FROM bills
        WHERE DATE(bill_date) = ?
    """, (today,)).fetchone()[0]

    # Monthly bills
    monthly_bills = db.execute("""
        SELECT COUNT(*)
        FROM bills
        WHERE strftime('%Y-%m', bill_date) = ?
    """, (month,)).fetchone()[0]

    # Today's expenses
    today_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE expense_date = ?
    """, (today,)).fetchone()[0]

    # Monthly expenses
    monthly_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE substr(expense_date, 1, 7) = ?
    """, (month,)).fetchone()[0]

    # Profit before expenses
    today_profit_before_expense = db.execute("""
        SELECT COALESCE(SUM(
            (bi.quantity * bi.price)
            - (bi.quantity * p.purchase_price)
        ), 0)
        FROM bill_items bi
        JOIN bills b ON b.id = bi.bill_id
        JOIN products p ON p.id = bi.product_id
        WHERE DATE(b.bill_date) = ?
    """, (today,)).fetchone()[0]

    monthly_profit_before_expense = db.execute("""
        SELECT COALESCE(SUM(
            (bi.quantity * bi.price)
            - (bi.quantity * p.purchase_price)
        ), 0)
        FROM bill_items bi
        JOIN bills b ON b.id = bi.bill_id
        JOIN products p ON p.id = bi.product_id
        WHERE strftime('%Y-%m', b.bill_date) = ?
    """, (month,)).fetchone()[0]

    today_net_profit = today_profit_before_expense - today_expenses
    monthly_net_profit = (
        monthly_profit_before_expense - monthly_expenses
    )

    # Top selling products
    top_products = db.execute("""
        SELECT
            p.name,
            SUM(bi.quantity) AS quantity_sold,
            SUM(bi.quantity * bi.price) AS sales_amount
        FROM bill_items bi
        JOIN products p ON p.id = bi.product_id
        JOIN bills b ON b.id = bi.bill_id
        WHERE strftime('%Y-%m', b.bill_date) = ?
        GROUP BY bi.product_id
        ORDER BY quantity_sold DESC
        LIMIT 10
    """, (month,)).fetchall()

    # Payment method summary
    payment_summary = db.execute("""
        SELECT
            payment_method,
            COUNT(*) AS bill_count,
            COALESCE(SUM(total), 0) AS amount
        FROM bills
        WHERE strftime('%Y-%m', bill_date) = ?
        GROUP BY payment_method
        ORDER BY amount DESC
    """, (month,)).fetchall()

    # Low stock products
    low_stock = db.execute("""
        SELECT *
        FROM products
        WHERE stock <= min_stock
        ORDER BY stock ASC
    """).fetchall()

    # Recent expenses
    recent_expenses = db.execute("""
        SELECT *
        FROM expenses
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

    db.close()

    body = """
    <div class="page-header">
        <div>
            <h1>📊 Reports</h1>
            <p class="muted">
                Business performance report for {{ month }}.
            </p>
        </div>
    </div>

    <div class="stats-grid">

        <div class="stat-card">
            <div class="stat-title">Today's Sales</div>
            <div class="stat-value">
                {{ money(today_sales) }}
            </div>
            <div class="stat-small">
                {{ today_bills }} bills
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Monthly Sales</div>
            <div class="stat-value">
                {{ money(monthly_sales) }}
            </div>
            <div class="stat-small">
                {{ monthly_bills }} bills
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Monthly Expenses</div>
            <div class="stat-value">
                {{ money(monthly_expenses) }}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Monthly Net Profit</div>
            <div class="stat-value">
                {{ money(monthly_net_profit) }}
            </div>
        </div>

    </div>


    <div class="grid-2">

        <div class="card">
            <h2>📅 Today's Report</h2>

            <div class="report-row">
                <span>Sales</span>
                <strong>{{ money(today_sales) }}</strong>
            </div>

            <div class="report-row">
                <span>Gross Profit</span>
                <strong>
                    {{ money(today_profit_before_expense) }}
                </strong>
            </div>

            <div class="report-row">
                <span>Expenses</span>
                <strong>{{ money(today_expenses) }}</strong>
            </div>

            <div class="report-row total-row">
                <span>Net Profit</span>
                <strong>{{ money(today_net_profit) }}</strong>
            </div>
        </div>


        <div class="card">
            <h2>📆 Monthly Report</h2>

            <div class="report-row">
                <span>Sales</span>
                <strong>{{ money(monthly_sales) }}</strong>
            </div>

            <div class="report-row">
                <span>Gross Profit</span>
                <strong>
                    {{ money(monthly_profit_before_expense) }}
                </strong>
            </div>

            <div class="report-row">
                <span>Expenses</span>
                <strong>{{ money(monthly_expenses) }}</strong>
            </div>

            <div class="report-row total-row">
                <span>Net Profit</span>
                <strong>{{ money(monthly_net_profit) }}</strong>
            </div>
        </div>

    </div>


    <div class="card">
        <h2>🏆 Top Selling Products</h2>

        {% if top_products %}

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Product</th>
                        <th>Quantity Sold</th>
                        <th>Sales Amount</th>
                    </tr>
                </thead>

                <tbody>
                {% for row in top_products %}
                    <tr>
                        <td>{{ loop.index }}</td>
                        <td>{{ row["name"] }}</td>
                        <td>{{ row["quantity_sold"] }}</td>
                        <td>
                            {{ money(row["sales_amount"]) }}
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>

        {% else %}
            <div class="empty">
                No sales data available for this month.
            </div>
        {% endif %}
    </div>


    <div class="card">
        <h2>💳 Payment Method Summary</h2>

        {% if payment_summary %}

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Payment Method</th>
                        <th>Bills</th>
                        <th>Amount</th>
                    </tr>
                </thead>

                <tbody>
                {% for row in payment_summary %}
                    <tr>
                        <td>{{ row["payment_method"] }}</td>
                        <td>{{ row["bill_count"] }}</td>
                        <td>
                            <strong>
                                {{ money(row["amount"]) }}
                            </strong>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>

        {% else %}
            <div class="empty">
                No payment data available.
            </div>
        {% endif %}
    </div>


    <div class="card">
        <h2>⚠️ Low Stock Products</h2>

        {% if low_stock %}

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Current Stock</th>
                        <th>Minimum Stock</th>
                        <th>Status</th>
                    </tr>
                </thead>

                <tbody>
                {% for row in low_stock %}
                    <tr>
                        <td>{{ row["name"] }}</td>
                        <td>{{ row["stock"] }}</td>
                        <td>{{ row["min_stock"] }}</td>
                        <td>
                            <span class="badge badge-danger">
                                Low Stock
                            </span>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>

        {% else %}
            <div class="empty">
                ✅ All products have sufficient stock.
            </div>
        {% endif %}
    </div>


    <div class="card">
        <h2>💸 Recent Expenses</h2>

        {% if recent_expenses %}

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Title</th>
                        <th>Category</th>
                        <th>Amount</th>
                    </tr>
                </thead>

                <tbody>
                {% for row in recent_expenses %}
                    <tr>
                        <td>{{ row["expense_date"] }}</td>
                        <td>{{ row["title"] }}</td>
                        <td>{{ row["category"] }}</td>
                        <td>
                            <strong>
                                {{ money(row["amount"]) }}
                            </strong>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>

        {% else %}
            <div class="empty">
                No expenses found.
            </div>
        {% endif %}
    </div>
    """

    return render_page(
        "Reports",
        body,
        month=month,
        today_sales=today_sales,
        monthly_sales=monthly_sales,
        today_bills=today_bills,
        monthly_bills=monthly_bills,
        today_expenses=today_expenses,
        monthly_expenses=monthly_expenses,
        today_profit_before_expense=today_profit_before_expense,
        monthly_profit_before_expense=monthly_profit_before_expense,
        today_net_profit=today_net_profit,
        monthly_net_profit=monthly_net_profit,
        top_products=top_products,
        payment_summary=payment_summary,
        low_stock=low_stock,
        recent_expenses=recent_expenses
    )


# ------------------------------------------------------------
# STEP 34 : STOCK REPORT
# ------------------------------------------------------------

@app.route("/stock_report")
@login_required
def stock_report():
    db = get_db()

    products = db.execute("""
        SELECT
            p.*,
            COALESCE(
                (
                    SELECT SUM(bi.quantity)
                    FROM bill_items bi
                    WHERE bi.product_id = p.id
                ), 0
            ) AS sold_quantity
        FROM products p
        ORDER BY p.name ASC
    """).fetchall()

    total_stock_value = db.execute("""
        SELECT COALESCE(
            SUM(stock * purchase_price), 0
        )
        FROM products
    """).fetchone()[0]

    total_selling_value = db.execute("""
        SELECT COALESCE(
            SUM(stock * selling_price), 0
        )
        FROM products
    """).fetchone()[0]

    db.close()

    body = """
    <div class="page-header">
        <div>
            <h1>📦 Stock Report</h1>
            <p class="muted">
                Complete inventory and stock valuation.
            </p>
        </div>
    </div>

    <div class="stats-grid">

        <div class="stat-card">
            <div class="stat-title">Purchase Value</div>
            <div class="stat-value">
                {{ money(total_stock_value) }}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Selling Value</div>
            <div class="stat-value">
                {{ money(total_selling_value) }}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Potential Margin</div>
            <div class="stat-value">
                {{ money(total_selling_value - total_stock_value) }}
            </div>
        </div>

    </div>

    <div class="card">
        <h2>Inventory</h2>

        {% if products %}

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Product</th>
                        <th>Category</th>
                        <th>Stock</th>
                        <th>Min Stock</th>
                        <th>Purchase Price</th>
                        <th>Selling Price</th>
                        <th>Stock Value</th>
                        <th>Sold</th>
                        <th>Status</th>
                    </tr>
                </thead>

                <tbody>
                {% for row in products %}
                    <tr>
                        <td>{{ row["name"] }}</td>
                        <td>{{ row["category"] or "-" }}</td>
                        <td>{{ row["stock"] }}</td>
                        <td>{{ row["min_stock"] }}</td>

                        <td>
                            {{ money(row["purchase_price"]) }}
                        </td>

                        <td>
                            {{ money(row["selling_price"]) }}
                        </td>

                        <td>
                            {{ money(
                                row["stock"] * row["purchase_price"]
                            ) }}
                        </td>

                        <td>{{ row["sold_quantity"] }}</td>

                        <td>
                            {% if row["stock"] <= 0 %}
                                <span class="badge badge-danger">
                                    Out of Stock
                                </span>
                            {% elif row["stock"] <= row["min_stock"] %}
                                <span class="badge badge-warning">
                                    Low Stock
                                </span>
                            {% else %}
                                <span class="badge badge-success">
                                    Available
                                </span>
                            {% endif %}
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>

        {% else %}
            <div class="empty">
                No products found.
            </div>
        {% endif %}
    </div>
    """

    return render_page(
        "Stock Report",
        body,
        products=products,
        total_stock_value=total_stock_value,
        total_selling_value=total_selling_value
    )


# ------------------------------------------------------------
# STEP 35 : DAILY SALES REPORT
# ------------------------------------------------------------

@app.route("/daily_sales")
@login_required
def daily_sales():
    db = get_db()

    rows = db.execute("""
        SELECT
            DATE(bill_date) AS sale_date,
            COUNT(*) AS bill_count,
            COALESCE(SUM(subtotal), 0) AS subtotal,
            COALESCE(SUM(discount), 0) AS discount,
            COALESCE(SUM(gst_amount), 0) AS gst,
            COALESCE(SUM(total), 0) AS total
        FROM bills
        GROUP BY DATE(bill_date)
        ORDER BY sale_date DESC
        LIMIT 60
    """).fetchall()

    db.close()

    body = """
    <div class="page-header">
        <div>
            <h1>📅 Daily Sales</h1>
            <p class="muted">
                Day-wise sales summary.
            </p>
        </div>
    </div>

    <div class="card">
        {% if rows %}

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Date</th>
                        <th>Bills</th>
                        <th>Subtotal</th>
                        <th>Discount</th>
                        <th>GST</th>
                        <th>Total Sales</th>
                    </tr>
                </thead>

                <tbody>
                {% for row in rows %}
                    <tr>
                        <td>{{ row["sale_date"] }}</td>
                        <td>{{ row["bill_count"] }}</td>
                        <td>{{ money(row["subtotal"]) }}</td>
                        <td>{{ money(row["discount"]) }}</td>
                        <td>{{ money(row["gst"]) }}</td>

                        <td>
                            <strong>
                                {{ money(row["total"]) }}
                            </strong>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>

        {% else %}
            <div class="empty">
                No sales data found.
            </div>
        {% endif %}
    </div>
    """

    return render_page(
        "Daily Sales",
        body,
        rows=rows
    )


# ------------------------------------------------------------
# STEP 36 : MONTHLY SALES REPORT
# ------------------------------------------------------------

@app.route("/monthly_sales")
@login_required
def monthly_sales():
    db = get_db()

    rows = db.execute("""
        SELECT
            strftime('%Y-%m', bill_date) AS sale_month,
            COUNT(*) AS bill_count,
            COALESCE(SUM(subtotal), 0) AS subtotal,
            COALESCE(SUM(discount), 0) AS discount,
            COALESCE(SUM(gst_amount), 0) AS gst,
            COALESCE(SUM(total), 0) AS total
        FROM bills
        GROUP BY strftime('%Y-%m', bill_date)
        ORDER BY sale_month DESC
        LIMIT 24
    """).fetchall()

    db.close()

    body = """
    <div class="page-header">
        <div>
            <h1>📆 Monthly Sales</h1>
            <p class="muted">
                Month-wise sales summary.
            </p>
        </div>
    </div>

    <div class="card">
        {% if rows %}

        <div class="table-wrap">
            <table>
                <thead>
                    <tr>
                        <th>Month</th>
                        <th>Bills</th>
                        <th>Subtotal</th>
                        <th>Discount</th>
                        <th>GST</th>
                        <th>Total Sales</th>
                    </tr>
                </thead>

                <tbody>
                {% for row in rows %}
                    <tr>
                        <td>{{ row["sale_month"] }}</td>
                        <td>{{ row["bill_count"] }}</td>
                        <td>{{ money(row["subtotal"]) }}</td>
                        <td>{{ money(row["discount"]) }}</td>
                        <td>{{ money(row["gst"]) }}</td>

                        <td>
                            <strong>
                                {{ money(row["total"]) }}
                            </strong>
                        </td>
                    </tr>
                {% endfor %}
                </tbody>
            </table>
        </div>

        {% else %}
            <div class="empty">
                No monthly sales data found.
            </div>
        {% endif %}
    </div>
    """

    return render_page(
        "Monthly Sales",
        body,
        rows=rows
    )
    # ============================================================
# STEP 37-39 : BUSINESS SUMMARY + SALES DASHBOARD
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# STEP 37 : BUSINESS SUMMARY
# ------------------------------------------------------------

@app.route("/business_summary")
@login_required
def business_summary():
    db = get_db()

    today = datetime.now().strftime("%Y-%m-%d")
    month = datetime.now().strftime("%Y-%m")

    # --------------------------------------------------------
    # BASIC BUSINESS NUMBERS
    # --------------------------------------------------------

    total_products = db.execute("""
        SELECT COUNT(*)
        FROM products
    """).fetchone()[0]

    total_customers = db.execute("""
        SELECT COUNT(*)
        FROM customers
    """).fetchone()[0]

    total_suppliers = db.execute("""
        SELECT COUNT(*)
        FROM suppliers
    """).fetchone()[0]

    total_bills = db.execute("""
        SELECT COUNT(*)
        FROM bills
    """).fetchone()[0]

    total_sales = db.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM bills
    """).fetchone()[0]

    total_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
    """).fetchone()[0]

    # --------------------------------------------------------
    # TODAY
    # --------------------------------------------------------

    today_sales = db.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM bills
        WHERE DATE(bill_date) = ?
    """, (today,)).fetchone()[0]

    today_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE expense_date = ?
    """, (today,)).fetchone()[0]

    today_bills = db.execute("""
        SELECT COUNT(*)
        FROM bills
        WHERE DATE(bill_date) = ?
    """, (today,)).fetchone()[0]

    # --------------------------------------------------------
    # CURRENT MONTH
    # --------------------------------------------------------

    monthly_sales = db.execute("""
        SELECT COALESCE(SUM(total), 0)
        FROM bills
        WHERE strftime('%Y-%m', bill_date) = ?
    """, (month,)).fetchone()[0]

    monthly_expenses = db.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM expenses
        WHERE substr(expense_date, 1, 7) = ?
    """, (month,)).fetchone()[0]

    monthly_bills = db.execute("""
        SELECT COUNT(*)
        FROM bills
        WHERE strftime('%Y-%m', bill_date) = ?
    """, (month,)).fetchone()[0]

    # --------------------------------------------------------
    # CUSTOMER UDHAAR
    # --------------------------------------------------------

    total_udhaar = db.execute("""
        SELECT COALESCE(SUM(balance), 0)
        FROM customers
    """).fetchone()[0]

    # --------------------------------------------------------
    # SUPPLIER BALANCE
    # --------------------------------------------------------

    total_supplier_due = db.execute("""
        SELECT COALESCE(SUM(balance), 0)
        FROM suppliers
    """).fetchone()[0]

    # --------------------------------------------------------
    # STOCK VALUES
    # --------------------------------------------------------

    stock_purchase_value = db.execute("""
        SELECT COALESCE(
            SUM(stock * purchase_price), 0
        )
        FROM products
    """).fetchone()[0]

    stock_selling_value = db.execute("""
        SELECT COALESCE(
            SUM(stock * selling_price), 0
        )
        FROM products
    """).fetchone()[0]

    potential_stock_profit = (
        stock_selling_value - stock_purchase_value
    )

    # --------------------------------------------------------
    # LOW STOCK
    # --------------------------------------------------------

    low_stock_count = db.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE stock <= min_stock
    """).fetchone()[0]

    out_of_stock_count = db.execute("""
        SELECT COUNT(*)
        FROM products
        WHERE stock <= 0
    """).fetchone()[0]

    # --------------------------------------------------------
    # PAYMENT METHODS
    # --------------------------------------------------------

    payment_summary = db.execute("""
        SELECT
            payment_method,
            COUNT(*) AS bill_count,
            COALESCE(SUM(total), 0) AS amount
        FROM bills
        GROUP BY payment_method
        ORDER BY amount DESC
    """).fetchall()

    # --------------------------------------------------------
    # TOP PRODUCTS
    # --------------------------------------------------------

    top_products = db.execute("""
        SELECT
            p.name,
            SUM(bi.quantity) AS quantity_sold,
            COALESCE(
                SUM(bi.quantity * bi.price), 0
            ) AS sales_amount
        FROM bill_items bi
        JOIN products p
            ON p.id = bi.product_id
        GROUP BY bi.product_id
        ORDER BY quantity_sold DESC
        LIMIT 10
    """).fetchall()

    # --------------------------------------------------------
    # RECENT BILLS
    # --------------------------------------------------------

    recent_bills = db.execute("""
        SELECT
            id,
            bill_no,
            customer_name,
            total,
            payment_method,
            bill_date
        FROM bills
        ORDER BY id DESC
        LIMIT 10
    """).fetchall()

    db.close()

    # --------------------------------------------------------
    # PROFIT ESTIMATE
    # --------------------------------------------------------

    estimated_profit = total_sales - total_expenses
    monthly_net = monthly_sales - monthly_expenses
    today_net = today_sales - today_expenses

    body = """
    <div class="page-header">
        <div>
            <h1>🏪 Business Summary</h1>
            <p class="muted">
                Complete overview of Pandey Kirana Store.
            </p>
        </div>
    </div>


    <!-- BASIC BUSINESS CARDS -->

    <div class="stats-grid">

        <div class="stat-card">
            <div class="stat-title">Total Products</div>
            <div class="stat-value">
                {{ total_products }}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Customers</div>
            <div class="stat-value">
                {{ total_customers }}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Suppliers</div>
            <div class="stat-value">
                {{ total_suppliers }}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Total Bills</div>
            <div class="stat-value">
                {{ total_bills }}
            </div>
        </div>

    </div>


    <!-- SALES -->

    <div class="stats-grid">

        <div class="stat-card">
            <div class="stat-title">Total Sales</div>
            <div class="stat-value">
                {{ money(total_sales) }}
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Today's Sales</div>
            <div class="stat-value">
                {{ money(today_sales) }}
            </div>
            <div class="stat-small">
                {{ today_bills }} bills
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Monthly Sales</div>
            <div class="stat-value">
                {{ money(monthly_sales) }}
            </div>
            <div class="stat-small">
                {{ monthly_bills }} bills
            </div>
        </div>

        <div class="stat-card">
            <div class="stat-title">Total Expenses</div>
            <div class="stat-value">
                {{ money(total_expenses) }}
            </div>
        </div>

    </div>


    <!-- PROFIT -->

    <div class="grid-2">

        <div class="card">
            <h2>💰 Profit Overview</h2>

            <div class="report-row">
                <span>Total Sales</span>
                <strong>
                    {{ money(total_sales) }}
                </strong>
            </div>

            <div class="report-row">
                <span>Total Expenses</span>
                <strong>
                    {{ money(total_expenses) }}
                </strong>
            </div>

            <div class="report-row total-row">
                <span>Estimated Net</span>
                <strong>
                    {{ money(estimated_profit) }}
                </strong>
            </div>
        </div>


        <div class="card">
            <h2>📅 Current Month</h2>

            <div class="report-row">
                <span>Monthly Sales</span>
                <strong>
                    {{ money(monthly_sales) }}
                </strong>
            </div>

            <div class="report-row">
                <span>Monthly Expenses</span>
                <strong>
                    {{ money(monthly_expenses) }}
                </strong>
            </div>

            <div class="report-row total-row">
                <span>Monthly Net</span>
                <strong>
                    {{ money(monthly_net) }}
                </strong>
            </div>
        </div>

    </div>


    <!-- TODAY -->

    <div class="card">
        <h2>📌 Today's Summary</h2>

        <div class="report-row">
            <span>Today's Sales</span>
            <strong>
                {{ money(today_sales) }}
            </strong>
        </div>

        <div class="report-row">
            <span>Today's Expenses</span>
            <strong>
                {{ money(today_expenses) }}
            </strong>
        </div>

        <div class="report-row total-row">
            <span>Today's Net</span>
            <strong>
                {{ money(today_net) }}
            </strong>
        </div>
    </div>


    <!-- STOCK -->

    <div class="grid-2">

        <div class="card">
            <h2>📦 Stock Value</h2>

            <div class="report-row">
                <span>Purchase Value</span>
                <strong>
                    {{ money(stock_purchase_value) }}
                </strong>
            </div>

            <div class="report-row">
                <span>Selling Value</span>
                <strong>
                    {{ money(stock_selling_value) }}
                </strong>
            </div>

            <div class="report-row total-row">
                <span>Potential Stock Profit</span>
                <strong>
                    {{ money(potential_stock_profit) }}
                </strong>
            </div>
        </div>


        <div class="card">
            <h2>⚠️ Stock Alerts</h2>

            <div class="report-row">
                <span>Low Stock Items</span>
                <strong>
                    {{ low_stock_count }}
                </strong>
            </div>

            <div class="report-row">
                <span>Out of Stock</span>
                <strong>
                    {{ out_of_stock_count }}
                </strong>
            </div>
        </div>

    </div>


    <!-- CUSTOMER / SUPPLIER BALANCE -->

    <div class="grid-2">

        <div class="card">
            <h2>👥 Customer Udhaar</h2>

            <div class="big-number">
                {{ money(total_udhaar) }}
            </div>

            <a
                class="btn btn-primary"
                href="{{ url_for('customers') }}"
            >
                View Customers
            </a>
        </div>


        <div class="card">
            <h2>🚚 Supplier Due</h2>

            <div class="big-number">
                {{ money(total_supplier_due) }}
            </div>

            <a
                class="btn btn-primary"
                href="{{ url_for('suppliers') }}"
            >
                View Suppliers
            </a>
        </div>

    </div>


    <!-- PAYMENT SUMMARY -->

    <div class="card">
        <h2>💳 Payment Summary</h2>

        {% if payment_summary %}

        <div class="table-wrap">
            <table>

                <thead>
                    <tr>
                        <th>Payment Method</th>
                        <th>Bills</th>
                        <th>Amount</th>
                    </tr>
                </thead>

                <tbody>

                {% for row in payment_summary %}

                    <tr>
                        <td>
                            {{ row["payment_method"] }}
                        </td>

                        <td>
                            {{ row["bill_count"] }}
                        </td>

                        <td>
                            <strong>
                                {{ money(row["amount"]) }}
                            </strong>
                        </td>
                    </tr>

                {% endfor %}

                </tbody>
            </table>
        </div>

        {% else %}

            <div class="empty">
                No payment data available.
            </div>

        {% endif %}
    </div>


    <!-- TOP PRODUCTS -->

    <div class="card">
        <h2>🏆 Top Selling Products</h2>

        {% if top_products %}

        <div class="table-wrap">
            <table>

                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Product</th>
                        <th>Quantity Sold</th>
                        <th>Sales Amount</th>
                    </tr>
                </thead>

                <tbody>

                {% for row in top_products %}

                    <tr>
                        <td>
                            {{ loop.index }}
                        </td>

                        <td>
                            {{ row["name"] }}
                        </td>

                        <td>
                            {{ row["quantity_sold"] }}
                        </td>

                        <td>
                            {{ money(row["sales_amount"]) }}
                        </td>
                    </tr>

                {% endfor %}

                </tbody>
            </table>
        </div>

        {% else %}

            <div class="empty">
                No product sales available.
            </div>

        {% endif %}
    </div>


    <!-- RECENT BILLS -->

    <div class="card">
        <h2>🧾 Recent Bills</h2>

        {% if recent_bills %}

        <div class="table-wrap">
            <table>

                <thead>
                    <tr>
                        <th>Bill No.</th>
                        <th>Customer</th>
                        <th>Amount</th>
                        <th>Payment</th>
                        <th>Date</th>
                        <th>Action</th>
                    </tr>
                </thead>

                <tbody>

                {% for row in recent_bills %}

                    <tr>

                        <td>
                            {{ row["bill_no"] }}
                        </td>

                        <td>
                            {{ row["customer_name"] }}
                        </td>

                        <td>
                            <strong>
                                {{ money(row["total"]) }}
                            </strong>
                        </td>

                        <td>
                            {{ row["payment_method"] }}
                        </td>

                        <td>
                            {{ row["bill_date"] }}
                        </td>

                        <td>
                            <a
                                class="btn btn-sm btn-primary"
                                href="{{ url_for(
                                    'invoice',
                                    bill_id=row['id']
                                ) }}"
                            >
                                View
                            </a>
                        </td>

                    </tr>

                {% endfor %}

                </tbody>
            </table>
        </div>

        {% else %}

            <div class="empty">
                No bills available.
            </div>

        {% endif %}
    </div>
    """

    return render_page(
        "Business Summary",
        body,

        total_products=total_products,
        total_customers=total_customers,
        total_suppliers=total_suppliers,
        total_bills=total_bills,

        total_sales=total_sales,
        today_sales=today_sales,
        monthly_sales=monthly_sales,

        total_expenses=total_expenses,
        today_expenses=today_expenses,
        monthly_expenses=monthly_expenses,

        today_bills=today_bills,
        monthly_bills=monthly_bills,

        total_udhaar=total_udhaar,
        total_supplier_due=total_supplier_due,

        stock_purchase_value=stock_purchase_value,
        stock_selling_value=stock_selling_value,
        potential_stock_profit=potential_stock_profit,

        low_stock_count=low_stock_count,
        out_of_stock_count=out_of_stock_count,

        estimated_profit=estimated_profit,
        monthly_net=monthly_net,
        today_net=today_net,

        payment_summary=payment_summary,
        top_products=top_products,
        recent_bills=recent_bills
    )


# ------------------------------------------------------------
# STEP 38 : SALES DASHBOARD
# ------------------------------------------------------------

@app.route("/sales_dashboard")
@login_required
def sales_dashboard():
    db = get_db()

    # Last 7 days sales
    daily_sales = db.execute("""
        SELECT
            DATE(bill_date) AS sale_date,
            COALESCE(SUM(total), 0) AS total
        FROM bills
        WHERE DATE(bill_date) >= DATE('now', '-6 day')
        GROUP BY DATE(bill_date)
        ORDER BY sale_date ASC
    """).fetchall()

    # Last 7 days expenses
    daily_expenses = db.execute("""
        SELECT
            expense_date,
            COALESCE(SUM(amount), 0) AS total
        FROM expenses
        WHERE expense_date >= DATE('now', '-6 day')
        GROUP BY expense_date
        ORDER BY expense_date ASC
    """).fetchall()

    # Monthly sales
    monthly_data = db.execute("""
        SELECT
            strftime('%Y-%m', bill_date) AS sale_month,
            COALESCE(SUM(total), 0) AS total
        FROM bills
        GROUP BY strftime('%Y-%m', bill_date)
        ORDER BY sale_month ASC
        LIMIT 12
    """).fetchall()

    # Category-wise sales
    category_sales = db.execute("""
        SELECT
            COALESCE(p.category, 'Other') AS category,
            COALESCE(
                SUM(bi.quantity * bi.price), 0
            ) AS total
        FROM bill_items bi
        JOIN products p
            ON p.id = bi.product_id
        GROUP BY p.category
        ORDER BY total DESC
    """).fetchall()

    db.close()

    # --------------------------------------------------------
    # Convert database rows into JavaScript-safe values
    # --------------------------------------------------------

    daily_labels = [
        row["sale_date"]
        for row in daily_sales
    ]

    daily_values = [
        float(row["total"])
        for row in daily_sales
    ]

    expense_labels = [
        row["expense_date"]
        for row in daily_expenses
    ]

    expense_values = [
        float(row["total"])
        for row in daily_expenses
    ]

    month_labels = [
        row["sale_month"]
        for row in monthly_data
    ]

    month_values = [
        float(row["total"])
        for row in monthly_data
    ]

    category_labels = [
        row["category"]
        for row in category_sales
    ]

    category_values = [
        float(row["total"])
        for row in category_sales
    ]

    body = """
    <div class="page-header">
        <div>
            <h1>📈 Sales Dashboard</h1>
            <p class="muted">
                Visual sales and business performance dashboard.
            </p>
        </div>
    </div>


    <div class="grid-2">

        <div class="card">
            <h2>📅 Last 7 Days Sales</h2>

            <div class="chart-box">
                <canvas id="dailySalesChart"></canvas>
            </div>
        </div>


        <div class="card">
            <h2>💸 Last 7 Days Expenses</h2>

            <div class="chart-box">
                <canvas id="expenseChart"></canvas>
            </div>
        </div>

    </div>


    <div class="card">
        <h2>📊 Monthly Sales</h2>

        <div class="chart-box large">
            <canvas id="monthlySalesChart"></canvas>
        </div>
    </div>


    <div class="card">
        <h2>🛒 Category-wise Sales</h2>

        <div class="chart-box">
            <canvas id="categoryChart"></canvas>
        </div>
    </div>


    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>

    <script>

        const dailyLabels = {{ daily_labels | tojson }};
        const dailyValues = {{ daily_values | tojson }};

        const expenseLabels = {{ expense_labels | tojson }};
        const expenseValues = {{ expense_values | tojson }};

        const monthLabels = {{ month_labels | tojson }};
        const monthValues = {{ month_values | tojson }};

        const categoryLabels = {{ category_labels | tojson }};
        const categoryValues = {{ category_values | tojson }};


        // ----------------------------------------------------
        // DAILY SALES CHART
        // ----------------------------------------------------

        new Chart(
            document.getElementById("dailySalesChart"),
            {
                type: "line",

                data: {
                    labels: dailyLabels,

                    datasets: [
                        {
                            label: "Sales",

                            data: dailyValues,

                            tension: 0.3,

                            fill: false
                        }
                    ]
                },

                options: {
                    responsive: true,

                    maintainAspectRatio: false,

                    plugins: {
                        legend: {
                            display: true
                        }
                    }
                }
            }
        );


        // ----------------------------------------------------
        // EXPENSE CHART
        // ----------------------------------------------------

        new Chart(
            document.getElementById("expenseChart"),
            {
                type: "bar",

                data: {
                    labels: expenseLabels,

                    datasets: [
                        {
                            label: "Expenses",

                            data: expenseValues
                        }
                    ]
                },

                options: {
                    responsive: true,

                    maintainAspectRatio: false
                }
            }
        );


        // ----------------------------------------------------
        // MONTHLY SALES
        // ----------------------------------------------------

        new Chart(
            document.getElementById("monthlySalesChart"),
            {
                type: "bar",

                data: {
                    labels: monthLabels,

                    datasets: [
                        {
                            label: "Monthly Sales",

                            data: monthValues
                        }
                    ]
                },

                options: {
                    responsive: true,

                    maintainAspectRatio: false,

                    scales: {
                        y: {
                            beginAtZero: true
                        }
                    }
                }
            }
        );


        // ----------------------------------------------------
        // CATEGORY SALES
        // ----------------------------------------------------

        new Chart(
            document.getElementById("categoryChart"),
            {
                type: "doughnut",

                data: {
                    labels: categoryLabels,

                    datasets: [
                        {
                            label: "Category Sales",

                            data: categoryValues
                        }
                    ]
                },

                options: {
                    responsive: true,

                    maintainAspectRatio: false
                }
            }
        );

    </script>
    """

    return render_page(
        "Sales Dashboard",
        body,

        daily_labels=daily_labels,
        daily_values=daily_values,

        expense_labels=expense_labels,
        expense_values=expense_values,

        month_labels=month_labels,
        month_values=month_values,

        category_labels=category_labels,
        category_values=category_values
    )


# ------------------------------------------------------------
# STEP 39 : QUICK REPORT MENU
# ------------------------------------------------------------

@app.route("/report_menu")
@login_required
def report_menu():

    body = """
    <div class="page-header">
        <div>
            <h1>📊 Reports Center</h1>
            <p class="muted">
                Open any report from the options below.
            </p>
        </div>
    </div>


    <div class="quick-grid">

        <a
            class="quick-card"
            href="{{ url_for('reports') }}"
        >
            <div class="quick-icon">📊</div>
            <h3>All Reports</h3>
            <p>Complete business reports.</p>
        </a>


        <a
            class="quick-card"
            href="{{ url_for('business_summary') }}"
        >
            <div class="quick-icon">🏪</div>
            <h3>Business Summary</h3>
            <p>Complete shop overview.</p>
        </a>


        <a
            class="quick-card"
            href="{{ url_for('sales_dashboard') }}"
        >
            <div class="quick-icon">📈</div>
            <h3>Sales Dashboard</h3>
            <p>Visual sales charts.</p>
        </a>


        <a
            class="quick-card"
            href="{{ url_for('daily_sales') }}"
        >
            <div class="quick-icon">📅</div>
            <h3>Daily Sales</h3>
            <p>Day-wise sales report.</p>
        </a>


        <a
            class="quick-card"
            href="{{ url_for('monthly_sales') }}"
        >
            <div class="quick-icon">📆</div>
            <h3>Monthly Sales</h3>
            <p>Month-wise sales report.</p>
        </a>


        <a
            class="quick-card"
            href="{{ url_for('stock_report') }}"
        >
            <div class="quick-icon">📦</div>
            <h3>Stock Report</h3>
            <p>Inventory and stock value.</p>
        </a>

    </div>
    """

    return render_page(
        "Reports Center",
        body
    )
    # ============================================================
# STEP 40-43 : SETTINGS + USER MANAGEMENT
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# STEP 40 : SHOP SETTINGS
# ------------------------------------------------------------

@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    db = get_db()

    if request.method == "POST":

        shop_name = request.form.get("shop_name", "").strip()
        owner_name = request.form.get("owner_name", "").strip()
        phone = request.form.get("phone", "").strip()
        address = request.form.get("address", "").strip()
        gst_number = request.form.get("gst_number", "").strip()
        invoice_note = request.form.get("invoice_note", "").strip()

        if not shop_name:
            flash("Shop name is required.", "error")
            db.close()
            return redirect(url_for("settings"))

        values = {
            "shop_name": shop_name,
            "owner_name": owner_name,
            "phone": phone,
            "address": address,
            "gst_number": gst_number,
            "invoice_note": invoice_note
        }

        for key, value in values.items():

            existing = db.execute("""
                SELECT id
                FROM settings
                WHERE key = ?
            """, (key,)).fetchone()

            if existing:

                db.execute("""
                    UPDATE settings
                    SET value = ?
                    WHERE key = ?
                """, (value, key))

            else:

                db.execute("""
                    INSERT INTO settings
                    (key, value)
                    VALUES (?, ?)
                """, (key, value))

        db.commit()
        db.close()

        flash("Shop settings updated successfully.", "success")

        return redirect(url_for("settings"))

    rows = db.execute("""
        SELECT key, value
        FROM settings
    """).fetchall()

    db.close()

    settings_data = {}

    for row in rows:
        settings_data[row["key"]] = row["value"]

    body = """
    <div class="page-header">

        <div>
            <h1>⚙️ Shop Settings</h1>

            <p class="muted">
                Manage your shop information.
            </p>
        </div>

    </div>


    <div class="card">

        <h2>🏪 Shop Information</h2>

        <form method="POST">

            <div class="form-grid">

                <div>

                    <label>Shop Name</label>

                    <input
                        type="text"
                        name="shop_name"
                        value="{{ settings_data.get('shop_name', 'Pandey Kirana Store') }}"
                        required
                    >

                </div>


                <div>

                    <label>Owner Name</label>

                    <input
                        type="text"
                        name="owner_name"
                        value="{{ settings_data.get('owner_name', '') }}"
                        placeholder="Owner name"
                    >

                </div>


                <div>

                    <label>Phone Number</label>

                    <input
                        type="text"
                        name="phone"
                        value="{{ settings_data.get('phone', '') }}"
                        placeholder="Shop phone number"
                    >

                </div>


                <div>

                    <label>GST Number</label>

                    <input
                        type="text"
                        name="gst_number"
                        value="{{ settings_data.get('gst_number', '') }}"
                        placeholder="GSTIN"
                    >

                </div>


                <div class="full">

                    <label>Shop Address</label>

                    <textarea
                        name="address"
                        rows="3"
                        placeholder="Enter complete shop address"
                    >{{ settings_data.get('address', '') }}</textarea>

                </div>


                <div class="full">

                    <label>Invoice Note</label>

                    <textarea
                        name="invoice_note"
                        rows="3"
                        placeholder="Thank you for shopping with us!"
                    >{{ settings_data.get('invoice_note', '') }}</textarea>

                </div>


                <div class="full">

                    <button
                        type="submit"
                        class="btn btn-primary"
                    >
                        💾 Save Settings
                    </button>

                </div>

            </div>

        </form>

    </div>


    <div class="card">

        <h2>ℹ️ Current Shop Details</h2>

        <div class="info-list">

            <div>
                <strong>Shop:</strong>
                {{ settings_data.get('shop_name', '-') }}
            </div>

            <div>
                <strong>Owner:</strong>
                {{ settings_data.get('owner_name', '-') or '-' }}
            </div>

            <div>
                <strong>Phone:</strong>
                {{ settings_data.get('phone', '-') or '-' }}
            </div>

            <div>
                <strong>GST:</strong>
                {{ settings_data.get('gst_number', '-') or '-' }}
            </div>

            <div>
                <strong>Address:</strong>
                {{ settings_data.get('address', '-') or '-' }}
            </div>

        </div>

    </div>
    """

    return render_page(
        "Settings",
        body,
        settings_data=settings_data
    )


# ------------------------------------------------------------
# STEP 41 : USER MANAGEMENT
# ------------------------------------------------------------

@app.route("/users")
@admin_required
def users():

    db = get_db()

    users_list = db.execute("""
        SELECT
            id,
            username,
            role,
            created_at
        FROM users
        ORDER BY id ASC
    """).fetchall()

    db.close()

    body = """
    <div class="page-header">

        <div>
            <h1>👤 User Management</h1>

            <p class="muted">
                Manage users who can access the store system.
            </p>
        </div>

        <div>

            <a
                href="{{ url_for('add_user') }}"
                class="btn btn-primary"
            >
                ➕ Add User
            </a>

        </div>

    </div>


    <div class="card">

        {% if users_list %}

        <div class="table-wrap">

            <table>

                <thead>

                    <tr>
                        <th>ID</th>
                        <th>Username</th>
                        <th>Role</th>
                        <th>Created</th>
                        <th>Action</th>
                    </tr>

                </thead>


                <tbody>

                {% for user in users_list %}

                    <tr>

                        <td>
                            {{ user["id"] }}
                        </td>

                        <td>
                            <strong>
                                {{ user["username"] }}
                            </strong>
                        </td>

                        <td>

                            {% if user["role"] == "admin" %}

                                <span class="badge badge-success">
                                    Admin
                                </span>

                            {% else %}

                                <span class="badge">
                                    Staff
                                </span>

                            {% endif %}

                        </td>

                        <td>
                            {{ user["created_at"] }}
                        </td>

                        <td>

                            {% if user["username"] != session.get("username") %}

                                <a
                                    class="btn btn-danger btn-sm"
                                    href="{{ url_for(
                                        'delete_user',
                                        user_id=user['id']
                                    ) }}"
                                    onclick="return confirm(
                                        'Delete this user?'
                                    )"
                                >
                                    Delete
                                </a>

                            {% else %}

                                <span class="muted">
                                    Current user
                                </span>

                            {% endif %}

                        </td>

                    </tr>

                {% endfor %}

                </tbody>

            </table>

        </div>

        {% else %}

            <div class="empty">
                No users found.
            </div>

        {% endif %}

    </div>
    """

    return render_page(
        "User Management",
        body,
        users_list=users_list
    )


# ------------------------------------------------------------
# STEP 42 : ADD USER
# ------------------------------------------------------------

@app.route("/add_user", methods=["GET", "POST"])
@admin_required
def add_user():

    if request.method == "POST":

        username = request.form.get(
            "username", ""
        ).strip()

        password = request.form.get(
            "password", ""
        ).strip()

        role = request.form.get(
            "role", "staff"
        ).strip()

        if not username or not password:

            flash(
                "Username and password are required.",
                "error"
            )

            return redirect(
                url_for("add_user")
            )

        if role not in ["admin", "staff"]:

            role = "staff"

        db = get_db()

        existing = db.execute("""
            SELECT id
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if existing:

            db.close()

            flash(
                "Username already exists.",
                "error"
            )

            return redirect(
                url_for("add_user")
            )

        db.execute("""
            INSERT INTO users
            (username, password, role, created_at)
            VALUES (?, ?, ?, ?)
        """, (
            username,
            password,
            role,
            now_string()
        ))

        db.commit()
        db.close()

        flash(
            "User created successfully.",
            "success"
        )

        return redirect(
            url_for("users")
        )


    body = """
    <div class="page-header">

        <div>

            <h1>➕ Add User</h1>

            <p class="muted">
                Create a new store-system user.
            </p>

        </div>

    </div>


    <div class="card">

        <form method="POST">

            <div class="form-grid">

                <div>

                    <label>Username</label>

                    <input
                        type="text"
                        name="username"
                        placeholder="Enter username"
                        required
                    >

                </div>


                <div>

                    <label>Password</label>

                    <input
                        type="password"
                        name="password"
                        placeholder="Enter password"
                        required
                    >

                </div>


                <div>

                    <label>Role</label>

                    <select name="role">

                        <option value="staff">
                            Staff
                        </option>

                        <option value="admin">
                            Admin
                        </option>

                    </select>

                </div>


                <div class="full">

                    <button
                        type="submit"
                        class="btn btn-primary"
                    >
                        👤 Create User
                    </button>

                    <a
                        href="{{ url_for('users') }}"
                        class="btn btn-secondary"
                    >
                        Cancel
                    </a>

                </div>

            </div>

        </form>

    </div>
    """

    return render_page(
        "Add User",
        body
    )


# ------------------------------------------------------------
# STEP 43 : DELETE USER
# ------------------------------------------------------------

@app.route("/delete_user/<int:user_id>")
@admin_required
def delete_user(user_id):

    db = get_db()

    user = db.execute("""
        SELECT *
        FROM users
        WHERE id = ?
    """, (user_id,)).fetchone()

    if not user:

        db.close()

        flash(
            "User not found.",
            "error"
        )

        return redirect(
            url_for("users")
        )


    # Current logged-in user cannot delete itself

    if user["username"] == session.get("username"):

        db.close()

        flash(
            "You cannot delete your current account.",
            "error"
        )

        return redirect(
            url_for("users")
        )


    # Do not allow deleting the last admin

    if user["role"] == "admin":

        admin_count = db.execute("""
            SELECT COUNT(*)
            FROM users
            WHERE role = 'admin'
        """).fetchone()[0]

        if admin_count <= 1:

            db.close()

            flash(
                "At least one admin account must remain.",
                "error"
            )

            return redirect(
                url_for("users")
            )


    db.execute("""
        DELETE FROM users
        WHERE id = ?
    """, (user_id,))

    db.commit()
    db.close()

    flash(
        "User deleted successfully.",
        "success"
    )

    return redirect(
        url_for("users")
    )


# ------------------------------------------------------------
# STEP 44 : CHANGE PASSWORD
# ------------------------------------------------------------

@app.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():

    if request.method == "POST":

        current_password = request.form.get(
            "current_password", ""
        ).strip()

        new_password = request.form.get(
            "new_password", ""
        ).strip()

        confirm_password = request.form.get(
            "confirm_password", ""
        ).strip()


        if not current_password:

            flash(
                "Enter your current password.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )


        if not new_password:

            flash(
                "Enter a new password.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )


        if len(new_password) < 4:

            flash(
                "New password must contain at least 4 characters.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )


        if new_password != confirm_password:

            flash(
                "New passwords do not match.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )


        db = get_db()

        user = db.execute("""
            SELECT *
            FROM users
            WHERE id = ?
        """, (
            session.get("user_id"),
        )).fetchone()


        if not user:

            db.close()

            session.clear()

            return redirect(
                url_for("login")
            )


        if user["password"] != current_password:

            db.close()

            flash(
                "Current password is incorrect.",
                "error"
            )

            return redirect(
                url_for("change_password")
            )


        db.execute("""
            UPDATE users
            SET password = ?
            WHERE id = ?
        """, (
            new_password,
            user["id"]
        ))

        db.commit()
        db.close()


        flash(
            "Password changed successfully.",
            "success"
        )

        return redirect(
            url_for("index")
        )


    body = """
    <div class="page-header">

        <div>

            <h1>🔐 Change Password</h1>

            <p class="muted">
                Change the password of your current account.
            </p>

        </div>

    </div>


    <div class="card">

        <form method="POST">

            <div class="form-grid">

                <div class="full">

                    <label>
                        Current Password
                    </label>

                    <input
                        type="password"
                        name="current_password"
                        placeholder="Enter current password"
                        required
                    >

                </div>


                <div>

                    <label>
                        New Password
                    </label>

                    <input
                        type="password"
                        name="new_password"
                        placeholder="Enter new password"
                        required
                    >

                </div>


                <div>

                    <label>
                        Confirm New Password
                    </label>

                    <input
                        type="password"
                        name="confirm_password"
                        placeholder="Confirm new password"
                        required
                    >

                </div>


                <div class="full">

                    <button
                        type="submit"
                        class="btn btn-primary"
                    >
                        🔐 Change Password
                    </button>

                </div>

            </div>

        </form>

    </div>
    """

    return render_page(
        "Change Password",
        body
    )
    # ============================================================
# STEP 45-48 : BACKUP + RESTORE + STOCK HISTORY
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# STEP 45 : STOCK MOVEMENT HISTORY
# ------------------------------------------------------------

@app.route("/stock_history")
@login_required
def stock_history():

    db = get_db()

    movements = db.execute("""
        SELECT
            sm.*,
            p.name AS product_name
        FROM stock_movements sm
        LEFT JOIN products p
            ON p.id = sm.product_id
        ORDER BY sm.id DESC
        LIMIT 500
    """).fetchall()

    db.close()

    body = """
    <div class="page-header">

        <div>

            <h1>📦 Stock History</h1>

            <p class="muted">
                Complete record of stock changes.
            </p>

        </div>

    </div>


    <div class="card">

        {% if movements %}

        <div class="table-wrap">

            <table>

                <thead>

                    <tr>
                        <th>Date</th>
                        <th>Product</th>
                        <th>Type</th>
                        <th>Quantity</th>
                        <th>Before</th>
                        <th>After</th>
                        <th>Note</th>
                    </tr>

                </thead>


                <tbody>

                {% for row in movements %}

                    <tr>

                        <td>
                            {{ row["created_at"] }}
                        </td>

                        <td>
                            {{ row["product_name"] or "Deleted Product" }}
                        </td>

                        <td>

                            {% if row["movement_type"] == "PURCHASE" %}

                                <span class="badge badge-success">
                                    Purchase
                                </span>

                            {% elif row["movement_type"] == "SALE" %}

                                <span class="badge badge-warning">
                                    Sale
                                </span>

                            {% elif row["movement_type"] == "ADJUSTMENT" %}

                                <span class="badge">
                                    Adjustment
                                </span>

                            {% else %}

                                <span class="badge">
                                    {{ row["movement_type"] }}
                                </span>

                            {% endif %}

                        </td>


                        <td>
                            {{ row["quantity"] }}
                        </td>


                        <td>
                            {{ row["stock_before"] }}
                        </td>


                        <td>
                            {{ row["stock_after"] }}
                        </td>


                        <td>
                            {{ row["note"] or "-" }}
                        </td>

                    </tr>

                {% endfor %}

                </tbody>

            </table>

        </div>

        {% else %}

            <div class="empty">
                No stock movement history found.
            </div>

        {% endif %}

    </div>
    """

    return render_page(
        "Stock History",
        body,
        movements=movements
    )


# ------------------------------------------------------------
# STEP 46 : DATABASE BACKUP
# ------------------------------------------------------------

@app.route("/backup")
@admin_required
def backup_database():

    if not os.path.exists(DATABASE):

        flash(
            "Database file was not found.",
            "error"
        )

        return redirect(url_for("index"))


    backup_folder = os.path.join(
        os.path.dirname(DATABASE),
        "backups"
    )

    os.makedirs(
        backup_folder,
        exist_ok=True
    )


    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    backup_name = (
        "pandey_kirana_backup_"
        + timestamp
        + ".db"
    )

    backup_path = os.path.join(
        backup_folder,
        backup_name
    )


    # Make a copy of the database

    shutil.copy2(
        DATABASE,
        backup_path
    )


    flash(
        "Database backup created successfully.",
        "success"
    )


    return send_file(
        backup_path,
        as_attachment=True,
        download_name=backup_name
    )


# ------------------------------------------------------------
# STEP 47 : BACKUP LIST
# ------------------------------------------------------------

@app.route("/backup_list")
@admin_required
def backup_list():

    backup_folder = os.path.join(
        os.path.dirname(DATABASE),
        "backups"
    )

    os.makedirs(
        backup_folder,
        exist_ok=True
    )


    backup_files = []

    for filename in os.listdir(backup_folder):

        if filename.lower().endswith(".db"):

            full_path = os.path.join(
                backup_folder,
                filename
            )

            backup_files.append({
                "name": filename,
                "size": os.path.getsize(full_path),
                "created": datetime.fromtimestamp(
                    os.path.getmtime(full_path)
                ).strftime("%Y-%m-%d %H:%M:%S")
            })


    backup_files.sort(
        key=lambda x: x["created"],
        reverse=True
    )


    body = """
    <div class="page-header">

        <div>

            <h1>💾 Database Backups</h1>

            <p class="muted">
                Manage local database backup files.
            </p>

        </div>

        <div>

            <a
                href="{{ url_for('backup_database') }}"
                class="btn btn-primary"
            >
                💾 Create Backup
            </a>

        </div>

    </div>


    <div class="card">

        {% if backup_files %}

        <div class="table-wrap">

            <table>

                <thead>

                    <tr>
                        <th>Backup File</th>
                        <th>Created</th>
                        <th>Size</th>
                        <th>Action</th>
                    </tr>

                </thead>


                <tbody>

                {% for backup in backup_files %}

                    <tr>

                        <td>
                            {{ backup["name"] }}
                        </td>

                        <td>
                            {{ backup["created"] }}
                        </td>

                        <td>
                            {{ "%.2f"|format(
                                backup["size"] / 1024
                            ) }} KB
                        </td>

                        <td>

                            <a
                                class="btn btn-primary btn-sm"
                                href="{{ url_for(
                                    'download_backup',
                                    filename=backup['name']
                                ) }}"
                            >
                                Download
                            </a>


                            <a
                                class="btn btn-danger btn-sm"
                                href="{{ url_for(
                                    'delete_backup',
                                    filename=backup['name']
                                ) }}"
                                onclick="return confirm(
                                    'Delete this backup?'
                                )"
                            >
                                Delete
                            </a>

                        </td>

                    </tr>

                {% endfor %}

                </tbody>

            </table>

        </div>

        {% else %}

            <div class="empty">
                No backup files found.
            </div>

        {% endif %}

    </div>


    <div class="card">

        <h2>⚠️ Backup Information</h2>

        <p>
            Keep backup files in a safe location.
        </p>

        <p>
            A backup contains the store database,
            including products, customers, suppliers,
            bills and other saved information.
        </p>

    </div>
    """

    return render_page(
        "Database Backups",
        body,
        backup_files=backup_files
    )


# ------------------------------------------------------------
# STEP 48 : DOWNLOAD BACKUP
# ------------------------------------------------------------

@app.route("/download_backup/<path:filename>")
@admin_required
def download_backup(filename):

    # Security check:
    # only allow files from the backup folder

    if os.path.basename(filename) != filename:

        flash(
            "Invalid backup filename.",
            "error"
        )

        return redirect(
            url_for("backup_list")
        )


    backup_folder = os.path.join(
        os.path.dirname(DATABASE),
        "backups"
    )

    file_path = os.path.join(
        backup_folder,
        filename
    )


    if not os.path.exists(file_path):

        flash(
            "Backup file not found.",
            "error"
        )

        return redirect(
            url_for("backup_list")
        )


    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename
    )


# ------------------------------------------------------------
# STEP 49 : DELETE BACKUP
# ------------------------------------------------------------

@app.route("/delete_backup/<path:filename>")
@admin_required
def delete_backup(filename):

    if os.path.basename(filename) != filename:

        flash(
            "Invalid backup filename.",
            "error"
        )

        return redirect(
            url_for("backup_list")
        )


    backup_folder = os.path.join(
        os.path.dirname(DATABASE),
        "backups"
    )

    file_path = os.path.join(
        backup_folder,
        filename
    )


    if not os.path.exists(file_path):

        flash(
            "Backup file not found.",
            "error"
        )

        return redirect(
            url_for("backup_list")
        )


    try:

        os.remove(file_path)

        flash(
            "Backup deleted successfully.",
            "success"
        )

    except Exception as e:

        flash(
            "Could not delete backup: " + str(e),
            "error"
        )


    return redirect(
        url_for("backup_list")
    )


# ------------------------------------------------------------
# STEP 50 : DATABASE INFORMATION
# ------------------------------------------------------------

@app.route("/database_info")
@admin_required
def database_info():

    db = get_db()

    tables = db.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
        ORDER BY name
    """).fetchall()


    table_info = []

    for table in tables:

        table_name = table["name"]

        count = db.execute(
            "SELECT COUNT(*) FROM " + table_name
        ).fetchone()[0]

        table_info.append({
            "name": table_name,
            "count": count
        })


    db.close()


    database_size = 0

    if os.path.exists(DATABASE):

        database_size = os.path.getsize(
            DATABASE
        )


    body = """
    <div class="page-header">

        <div>

            <h1>🗄️ Database Information</h1>

            <p class="muted">
                Information about the store database.
            </p>

        </div>

    </div>


    <div class="stats-grid">

        <div class="stat-card">

            <div class="stat-title">
                Database Size
            </div>

            <div class="stat-value">
                {{ "%.2f"|format(
                    database_size / 1024
                ) }} KB
            </div>

        </div>


        <div class="stat-card">

            <div class="stat-title">
                Tables
            </div>

            <div class="stat-value">
                {{ table_info|length }}
            </div>

        </div>

    </div>


    <div class="card">

        <h2>📋 Database Tables</h2>

        <div class="table-wrap">

            <table>

                <thead>

                    <tr>
                        <th>Table</th>
                        <th>Records</th>
                    </tr>

                </thead>


                <tbody>

                {% for table in table_info %}

                    <tr>

                        <td>
                            {{ table["name"] }}
                        </td>

                        <td>
                            {{ table["count"] }}
                        </td>

                    </tr>

                {% endfor %}

                </tbody>

            </table>

        </div>

    </div>
    """

    return render_page(
        "Database Information",
        body,
        database_size=database_size,
        table_info=table_info
    )
    # ============================================================
# PART 10 — RESTORE, DATABASE TOOLS, ERROR HANDLING & RUN
# PANDEY KIRANA STORE
# ============================================================

from werkzeug.utils import secure_filename


# ------------------------------------------------------------
# DATABASE VALIDATION
# ------------------------------------------------------------

def validate_database_file(db_file):
    """
    Check whether a SQLite database is valid
    and contains the important tables of this project.
    """

    connection = None

    try:
        connection = sqlite3.connect(db_file)

        # SQLite integrity check
        result = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()

        if not result or result[0] != "ok":
            return False, "Database integrity check failed."

        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table'"
            ).fetchall()
        }

        required_tables = {
            "users",
            "products",
            "customers",
            "suppliers",
            "bills",
            "bill_items",
            "expenses",
            "purchases",
            "settings",
            "payments",
            "supplier_payments",
            "stock_movements"
        }

        missing_tables = required_tables - tables

        if missing_tables:
            return False, (
                "Required tables are missing: "
                + ", ".join(sorted(missing_tables))
            )

        return True, "Database is valid."

    except Exception as e:
        return False, str(e)

    finally:
        if connection:
            connection.close()


# ------------------------------------------------------------
# RESTORE DATABASE
# ------------------------------------------------------------

@app.route("/restore", methods=["GET", "POST"])
@admin_required
def restore_database():

    if request.method == "POST":

        uploaded_file = request.files.get("database_file")

        if not uploaded_file:
            flash("Please select a database file.", "danger")
            return redirect(url_for("restore_database"))

        if not uploaded_file.filename:
            flash("No file selected.", "danger")
            return redirect(url_for("restore_database"))

        filename = secure_filename(uploaded_file.filename)

        if not filename.lower().endswith(".db"):
            flash("Only .db files are allowed.", "danger")
            return redirect(url_for("restore_database"))

        restore_folder = "restore_temp"

        os.makedirs(restore_folder, exist_ok=True)

        temp_file = os.path.join(
            restore_folder,
            "restore_database_temp.db"
        )

        try:

            uploaded_file.save(temp_file)

            valid, message = validate_database_file(temp_file)

            if not valid:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

                flash(
                    "Restore cancelled: " + message,
                    "danger"
                )

                return redirect(url_for("restore_database"))

            # Make a safety backup of current database
            os.makedirs("backups", exist_ok=True)

            safety_name = (
                "before_restore_"
                + datetime.now().strftime("%Y%m%d_%H%M%S")
                + ".db"
            )

            safety_backup = os.path.join(
                "backups",
                safety_name
            )

            if os.path.exists(DATABASE):
                shutil.copy2(
                    DATABASE,
                    safety_backup
                )

            # Replace current database
            shutil.copy2(
                temp_file,
                DATABASE
            )

            if os.path.exists(temp_file):
                os.remove(temp_file)

            flash(
                "Database restored successfully.",
                "success"
            )

            return redirect(url_for("index"))

        except Exception as e:

            if os.path.exists(temp_file):
                try:
                    os.remove(temp_file)
                except:
                    pass

            flash(
                "Restore failed: " + str(e),
                "danger"
            )

            return redirect(url_for("restore_database"))

    # GET request

    backup_files = []

    os.makedirs("backups", exist_ok=True)

    for filename in os.listdir("backups"):

        full_path = os.path.join(
            "backups",
            filename
        )

        if (
            os.path.isfile(full_path)
            and filename.lower().endswith(".db")
        ):
            backup_files.append({
                "filename": filename,
                "size": round(
                    os.path.getsize(full_path) / 1024,
                    2
                ),
                "created": datetime.fromtimestamp(
                    os.path.getmtime(full_path)
                ).strftime("%d-%m-%Y %H:%M:%S")
            })

    backup_files.sort(
        key=lambda x: x["filename"],
        reverse=True
    )

    html = """

    <div class="card">

        <h2>♻️ Restore Database</h2>

        <div class="alert alert-warning">
            <b>Important:</b>
            Restoring a database will replace the current database.
            A safety backup of the current database will be created
            automatically before restore.
        </div>

        <form method="POST"
              enctype="multipart/form-data">

            <label>Select Database Backup (.db)</label>

            <input type="file"
                   name="database_file"
                   accept=".db"
                   required>

            <button class="btn btn-primary"
                    type="submit"
                    onclick="return confirm(
                    'Are you sure you want to restore this database?'
                    );">
                ♻️ Restore Database
            </button>

        </form>

    </div>


    <div class="card">

        <h2>Available Backups</h2>

        {% if backup_files %}

        <table>

            <tr>
                <th>File</th>
                <th>Size</th>
                <th>Created</th>
                <th>Action</th>
            </tr>

            {% for backup in backup_files %}

            <tr>

                <td>
                    {{ backup.filename }}
                </td>

                <td>
                    {{ backup.size }} KB
                </td>

                <td>
                    {{ backup.created }}
                </td>

                <td>

                    <a class="btn btn-primary"
                       href="{{ url_for(
                       'download_backup',
                       filename=backup.filename
                       ) }}">
                       Download
                    </a>

                    <a class="btn btn-danger"
                       href="{{ url_for(
                       'restore_existing_backup',
                       filename=backup.filename
                       ) }}"
                       onclick="return confirm(
                       'Restore this backup?'
                       );">
                       Restore
                    </a>

                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No backup files available.</p>

        {% endif %}

    </div>

    """

    return render_page(
        "Restore Database",
        render_template_string(
            html,
            backup_files=backup_files
        )
    )


# ------------------------------------------------------------
# RESTORE AN EXISTING BACKUP
# ------------------------------------------------------------

@app.route("/restore_existing_backup/<path:filename>")
@admin_required
def restore_existing_backup(filename):

    filename = os.path.basename(filename)

    if not filename.lower().endswith(".db"):
        flash(
            "Invalid backup file.",
            "danger"
        )
        return redirect(url_for("restore_database"))

    backup_path = os.path.join(
        "backups",
        filename
    )

    if not os.path.exists(backup_path):
        flash(
            "Backup file not found.",
            "danger"
        )
        return redirect(url_for("restore_database"))

    try:

        valid, message = validate_database_file(
            backup_path
        )

        if not valid:
            flash(
                "Restore cancelled: " + message,
                "danger"
            )
            return redirect(url_for("restore_database"))

        # Create safety backup first
        os.makedirs("backups", exist_ok=True)

        safety_name = (
            "before_restore_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".db"
        )

        safety_path = os.path.join(
            "backups",
            safety_name
        )

        if os.path.exists(DATABASE):
            shutil.copy2(
                DATABASE,
                safety_path
            )

        # Restore selected backup
        shutil.copy2(
            backup_path,
            DATABASE
        )

        flash(
            "Selected backup restored successfully.",
            "success"
        )

        return redirect(url_for("index"))

    except Exception as e:

        flash(
            "Restore failed: " + str(e),
            "danger"
        )

        return redirect(url_for("restore_database"))


# ------------------------------------------------------------
# DOWNLOAD CURRENT DATABASE
# ------------------------------------------------------------

@app.route("/download_database")
@admin_required
def download_database():

    if not os.path.exists(DATABASE):

        flash(
            "Database file not found.",
            "danger"
        )

        return redirect(url_for("index"))

    return send_file(
        DATABASE,
        as_attachment=True,
        download_name="pandey_kirana_store_database.db"
    )


# ------------------------------------------------------------
# SYSTEM STATUS
# ------------------------------------------------------------

@app.route("/system_status")
@admin_required
def system_status():

    database_exists = os.path.exists(DATABASE)

    database_size = 0

    if database_exists:
        database_size = round(
            os.path.getsize(DATABASE) / 1024,
            2
        )

    backup_count = 0

    if os.path.exists("backups"):

        backup_count = len([
            f for f in os.listdir("backups")
            if f.lower().endswith(".db")
            and os.path.isfile(
                os.path.join("backups", f)
            )
        ])

    table_counts = {}

    if database_exists:

        db = get_db()

        try:

            tables = db.execute(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            ).fetchall()

            for table in tables:

                table_name = table["name"]

                try:

                    count = db.execute(
                        f'SELECT COUNT(*) FROM "{table_name}"'
                    ).fetchone()[0]

                    table_counts[table_name] = count

                except:
                    table_counts[table_name] = "N/A"

        finally:
            db.close()

    html = """

    <div class="card">

        <h2>🖥️ System Status</h2>

        <table>

            <tr>
                <th>Item</th>
                <th>Status</th>
            </tr>

            <tr>
                <td>Application</td>
                <td>🟢 Running</td>
            </tr>

            <tr>
                <td>Database</td>
                <td>
                    {% if database_exists %}
                        🟢 Available
                    {% else %}
                        🔴 Missing
                    {% endif %}
                </td>
            </tr>

            <tr>
                <td>Database Size</td>
                <td>{{ database_size }} KB</td>
            </tr>

            <tr>
                <td>Total Backups</td>
                <td>{{ backup_count }}</td>
            </tr>

        </table>

    </div>


    <div class="card">

        <h2>📊 Database Tables</h2>

        <table>

            <tr>
                <th>Table</th>
                <th>Records</th>
            </tr>

            {% for table, count in table_counts.items() %}

            <tr>
                <td>{{ table }}</td>
                <td>{{ count }}</td>
            </tr>

            {% endfor %}

        </table>

    </div>


    <div class="card">

        <h2>Database Tools</h2>

        <a class="btn btn-primary"
           href="{{ url_for('backup_database') }}">
           💾 Create Backup
        </a>

        <a class="btn btn-primary"
           href="{{ url_for('restore_database') }}">
           ♻️ Restore
        </a>

        <a class="btn btn-primary"
           href="{{ url_for('download_database') }}">
           ⬇️ Download Database
        </a>

    </div>

    """

    return render_page(
        "System Status",
        render_template_string(
            html,
            database_exists=database_exists,
            database_size=database_size,
            backup_count=backup_count,
            table_counts=table_counts
        )
    )


# ------------------------------------------------------------
# 404 ERROR PAGE
# ------------------------------------------------------------

@app.errorhandler(404)
def page_not_found(error):

    html = """

    <div class="card"
         style="text-align:center;">

        <h1>404</h1>

        <h2>Page Not Found</h2>

        <p>
            The page you are looking for does not exist.
        </p>

        <br>

        <a class="btn btn-primary"
           href="{{ url_for('index') }}">
           🏠 Go to Dashboard
        </a>

    </div>

    """

    return render_page(
        "Page Not Found",
        render_template_string(html)
    ), 404


# ------------------------------------------------------------
# 500 ERROR PAGE
# ------------------------------------------------------------

@app.errorhandler(500)
def internal_server_error(error):

    html = """

    <div class="card"
         style="text-align:center;">

        <h1>500</h1>

        <h2>Something went wrong</h2>

        <p>
            An unexpected server error occurred.
        </p>

        <br>

        <a class="btn btn-primary"
           href="{{ url_for('index') }}">
           🏠 Go to Dashboard
        </a>

    </div>

    """

    return render_page(
        "Server Error",
        render_template_string(html)
    ), 500


# ------------------------------------------------------------
# FINAL DATABASE INITIALIZATION
# ------------------------------------------------------------

try:

    init_db()

except Exception as e:

    print("Database initialization error:", e)


# PART 11 — QUICK SEARCH + STORE INFORMATION + UTILITIES
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# GLOBAL SEARCH
# ------------------------------------------------------------

@app.route("/search")
@login_required
def global_search():

    query = request.args.get("q", "").strip()

    products = []
    customers = []
    suppliers = []
    bills = []

    if query:

        db = get_db()

        try:

            search_text = "%" + query + "%"

            # Products
            products = db.execute(
                """
                SELECT *
                FROM products
                WHERE name LIKE ?
                   OR category LIKE ?
                   OR barcode LIKE ?
                ORDER BY name
                LIMIT 30
                """,
                (
                    search_text,
                    search_text,
                    search_text
                )
            ).fetchall()

            # Customers
            customers = db.execute(
                """
                SELECT *
                FROM customers
                WHERE name LIKE ?
                   OR phone LIKE ?
                ORDER BY name
                LIMIT 30
                """,
                (
                    search_text,
                    search_text
                )
            ).fetchall()

            # Suppliers
            suppliers = db.execute(
                """
                SELECT *
                FROM suppliers
                WHERE name LIKE ?
                   OR phone LIKE ?
                ORDER BY name
                LIMIT 30
                """,
                (
                    search_text,
                    search_text
                )
            ).fetchall()

            # Bills
            bills = db.execute(
                """
                SELECT *
                FROM bills
                WHERE bill_no LIKE ?
                   OR customer_name LIKE ?
                ORDER BY id DESC
                LIMIT 30
                """,
                (
                    search_text,
                    search_text
                )
            ).fetchall()

        finally:
            db.close()

    html = """

    <div class="card">

        <h2>🔎 Search Store</h2>

        <form method="GET"
              action="{{ url_for('global_search') }}">

            <input
                type="text"
                name="q"
                value="{{ query }}"
                placeholder="Search product, customer, supplier or bill..."
                autofocus
            >

            <button class="btn btn-primary"
                    type="submit">
                🔎 Search
            </button>

        </form>

    </div>


    {% if query %}

    <div class="card">

        <h2>📦 Products</h2>

        {% if products %}

        <table>

            <tr>
                <th>Name</th>
                <th>Category</th>
                <th>Price</th>
                <th>Stock</th>
            </tr>

            {% for product in products %}

            <tr>

                <td>{{ product["name"] }}</td>

                <td>
                    {{ product["category"] or "-" }}
                </td>

                <td>
                    ₹{{ money(product["selling_price"]) }}
                </td>

                <td>
                    {{ product["stock"] }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No products found.</p>

        {% endif %}

    </div>


    <div class="card">

        <h2>👥 Customers</h2>

        {% if customers %}

        <table>

            <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Udhaar</th>
            </tr>

            {% for customer in customers %}

            <tr>

                <td>{{ customer["name"] }}</td>

                <td>
                    {{ customer["phone"] or "-" }}
                </td>

                <td>
                    ₹{{ money(customer["balance"]) }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No customers found.</p>

        {% endif %}

    </div>


    <div class="card">

        <h2>🚚 Suppliers</h2>

        {% if suppliers %}

        <table>

            <tr>
                <th>Name</th>
                <th>Phone</th>
                <th>Due</th>
            </tr>

            {% for supplier in suppliers %}

            <tr>

                <td>{{ supplier["name"] }}</td>

                <td>
                    {{ supplier["phone"] or "-" }}
                </td>

                <td>
                    ₹{{ money(supplier["balance"]) }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No suppliers found.</p>

        {% endif %}

    </div>


    <div class="card">

        <h2>🧾 Bills</h2>

        {% if bills %}

        <table>

            <tr>
                <th>Bill No.</th>
                <th>Customer</th>
                <th>Total</th>
                <th>Date</th>
            </tr>

            {% for bill in bills %}

            <tr>

                <td>
                    {{ bill["bill_no"] }}
                </td>

                <td>
                    {{ bill["customer_name"] or "Walk-in Customer" }}
                </td>

                <td>
                    ₹{{ money(bill["grand_total"]) }}
                </td>

                <td>
                    {{ bill["created_at"] }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No bills found.</p>

        {% endif %}

    </div>

    {% endif %}

    """

    return render_page(
        "Search",
        render_template_string(
            html,
            query=query,
            products=products,
            customers=customers,
            suppliers=suppliers,
            bills=bills,
            money=money
        )
    )


# ------------------------------------------------------------
# STORE INFORMATION
# ------------------------------------------------------------

@app.route("/store_info")
@login_required
def store_info():

    db = get_db()

    try:

        settings_rows = db.execute(
            "SELECT key, value FROM settings"
        ).fetchall()

        settings_data = {
            row["key"]: row["value"]
            for row in settings_rows
        }

    finally:
        db.close()

    html = """

    <div class="card">

        <h2>🏪 Store Information</h2>

        <table>

            <tr>
                <th>Store Name</th>
                <td>
                    {{ settings_data.get(
                    "shop_name",
                    "Pandey Kirana Store"
                    ) }}
                </td>
            </tr>

            <tr>
                <th>Owner</th>
                <td>
                    {{ settings_data.get(
                    "owner_name",
                    "-"
                    ) }}
                </td>
            </tr>

            <tr>
                <th>Phone</th>
                <td>
                    {{ settings_data.get(
                    "phone",
                    "-"
                    ) }}
                </td>
            </tr>

            <tr>
                <th>Address</th>
                <td>
                    {{ settings_data.get(
                    "address",
                    "-"
                    ) }}
                </td>
            </tr>

            <tr>
                <th>GST Number</th>
                <td>
                    {{ settings_data.get(
                    "gst_number",
                    "-"
                    ) }}
                </td>
            </tr>

            <tr>
                <th>Invoice Note</th>
                <td>
                    {{ settings_data.get(
                    "invoice_note",
                    "-"
                    ) }}
                </td>
            </tr>

        </table>

    </div>


    <div class="card">

        <h2>⚡ Quick Actions</h2>

        <a class="btn btn-primary"
           href="{{ url_for('billing') }}">
           🧾 New Bill
        </a>

        <a class="btn btn-primary"
           href="{{ url_for('add_product') }}">
           ➕ Add Product
        </a>

        <a class="btn btn-primary"
           href="{{ url_for('add_customer') }}">
           👤 Add Customer
        </a>

        <a class="btn btn-primary"
           href="{{ url_for('add_supplier') }}">
           🚚 Add Supplier
        </a>

    </div>

    """

    return render_page(
        "Store Information",
        render_template_string(
            html,
            settings_data=settings_data
        )
    )


# ------------------------------------------------------------
# QUICK BACKUP BUTTON
# ------------------------------------------------------------

@app.route("/quick_backup")
@admin_required
def quick_backup():

    try:

        os.makedirs("backups", exist_ok=True)

        filename = (
            "quick_backup_"
            + datetime.now().strftime(
                "%Y%m%d_%H%M%S"
            )
            + ".db"
        )

        backup_path = os.path.join(
            "backups",
            filename
        )

        if not os.path.exists(DATABASE):

            init_db()

        shutil.copy2(
            DATABASE,
            backup_path
        )

        flash(
            "Quick backup created successfully.",
            "success"
        )

    except Exception as e:

        flash(
            "Backup failed: " + str(e),
            "danger"
        )

    return redirect(url_for("index"))


# ------------------------------------------------------------
# STOCK ALERT PAGE
# ------------------------------------------------------------

@app.route("/stock_alerts")
@login_required
def stock_alerts():

    db = get_db()

    try:

        low_stock = db.execute(
            """
            SELECT *
            FROM products
            WHERE stock > 0
              AND stock <= min_stock
            ORDER BY stock ASC, name
            """
        ).fetchall()

        out_of_stock = db.execute(
            """
            SELECT *
            FROM products
            WHERE stock <= 0
            ORDER BY name
            """
        ).fetchall()

    finally:
        db.close()

    html = """

    <div class="card">

        <h2>⚠️ Low Stock</h2>

        {% if low_stock %}

        <table>

            <tr>
                <th>Product</th>
                <th>Stock</th>
                <th>Minimum Stock</th>
                <th>Status</th>
            </tr>

            {% for product in low_stock %}

            <tr>

                <td>{{ product["name"] }}</td>

                <td>{{ product["stock"] }}</td>

                <td>{{ product["min_stock"] }}</td>

                <td>
                    ⚠️ Low Stock
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>✅ No low-stock products.</p>

        {% endif %}

    </div>


    <div class="card">

        <h2>🔴 Out of Stock</h2>

        {% if out_of_stock %}

        <table>

            <tr>
                <th>Product</th>
                <th>Category</th>
                <th>Stock</th>
            </tr>

            {% for product in out_of_stock %}

            <tr>

                <td>{{ product["name"] }}</td>

                <td>
                    {{ product["category"] or "-" }}
                </td>

                <td>
                    {{ product["stock"] }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>✅ No out-of-stock products.</p>

        {% endif %}

    </div>

    """

    return render_page(
        "Stock Alerts",
        render_template_string(
            html,
            low_stock=low_stock,
            out_of_stock=out_of_stock
        )
    )


# ------------------------------------------------------------
# USER PROFILE
# ------------------------------------------------------------

@app.route("/profile")
@login_required
def profile():

    username = session.get("username")

    db = get_db()

    try:

        user = db.execute(
            """
            SELECT id, username, role, created_at
            FROM users
            WHERE username = ?
            """,
            (username,)
        ).fetchone()

    finally:
        db.close()

    html = """

    <div class="card">

        <h2>👤 My Profile</h2>

        {% if user %}

        <table>

            <tr>
                <th>Username</th>
                <td>{{ user["username"] }}</td>
            </tr>

            <tr>
                <th>Role</th>
                <td>{{ user["role"] }}</td>
            </tr>

            <tr>
                <th>Account Created</th>
                <td>{{ user["created_at"] }}</td>
            </tr>

        </table>

        <br>

        <a class="btn btn-primary"
           href="{{ url_for('change_password') }}">
           🔑 Change Password
        </a>

        {% else %}

        <p>User information not found.</p>

        {% endif %}

    </div>

    """

    return render_page(
        "My Profile",
        render_template_string(
            html,
            user=user
        )
    )


# ============================================================
# END OF PART 11
# ============================================================
# ============================================================
# PART 12 — BARCODE / SKU UTILITIES
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# PRODUCT BARCODE SEARCH
# ------------------------------------------------------------

@app.route("/barcode_search")
@login_required
def barcode_search():

    barcode = request.args.get("barcode", "").strip()

    product = None

    if barcode:

        db = get_db()

        try:

            product = db.execute(
                """
                SELECT *
                FROM products
                WHERE barcode = ?
                LIMIT 1
                """,
                (barcode,)
            ).fetchone()

        finally:
            db.close()

    html = """

    <div class="card">

        <h2>📦 Barcode / SKU Search</h2>

        <form method="GET"
              action="{{ url_for('barcode_search') }}">

            <label>Enter Barcode / SKU</label>

            <input
                type="text"
                name="barcode"
                value="{{ barcode }}"
                placeholder="Enter product barcode..."
                autofocus
                required
            >

            <button class="btn btn-primary"
                    type="submit">
                🔎 Find Product
            </button>

        </form>

    </div>


    {% if barcode %}

        {% if product %}

        <div class="card">

            <h2>✅ Product Found</h2>

            <table>

                <tr>
                    <th>Product Name</th>
                    <td>{{ product["name"] }}</td>
                </tr>

                <tr>
                    <th>Category</th>
                    <td>
                        {{ product["category"] or "-" }}
                    </td>
                </tr>

                <tr>
                    <th>Barcode / SKU</th>
                    <td>
                        {{ product["barcode"] or "-" }}
                    </td>
                </tr>

                <tr>
                    <th>Selling Price</th>
                    <td>
                        ₹{{ money(product["selling_price"]) }}
                    </td>
                </tr>

                <tr>
                    <th>Available Stock</th>
                    <td>
                        {{ product["stock"] }}
                    </td>
                </tr>

            </table>

            <br>

            <a class="btn btn-primary"
               href="{{ url_for(
               'edit_product',
               product_id=product['id']
               ) }}">
               ✏️ Edit Product
            </a>

            <a class="btn btn-primary"
               href="{{ url_for('billing') }}">
               🧾 Go to Billing
            </a>

        </div>

        {% else %}

        <div class="card">

            <h2>❌ Product Not Found</h2>

            <p>
                No product was found with barcode/SKU:
                <b>{{ barcode }}</b>
            </p>

            <a class="btn btn-primary"
               href="{{ url_for('add_product') }}">
               ➕ Add New Product
            </a>

        </div>

        {% endif %}

    {% endif %}

    """

    return render_page(
        "Barcode Search",
        render_template_string(
            html,
            barcode=barcode,
            product=product,
            money=money
        )
    )


# ------------------------------------------------------------
# PRODUCT API-LIKE JSON SEARCH
# ------------------------------------------------------------

@app.route("/product_by_barcode")
@login_required
def product_by_barcode():

    barcode = request.args.get(
        "barcode",
        ""
    ).strip()

    if not barcode:

        return {
            "success": False,
            "message": "Barcode is required."
        }, 400

    db = get_db()

    try:

        product = db.execute(
            """
            SELECT
                id,
                name,
                category,
                barcode,
                purchase_price,
                selling_price,
                stock,
                min_stock
            FROM products
            WHERE barcode = ?
            LIMIT 1
            """,
            (barcode,)
        ).fetchone()

    finally:
        db.close()

    if not product:

        return {
            "success": False,
            "message": "Product not found."
        }, 404

    return {
        "success": True,
        "product": {
            "id": product["id"],
            "name": product["name"],
            "category": product["category"],
            "barcode": product["barcode"],
            "purchase_price": product["purchase_price"],
            "selling_price": product["selling_price"],
            "stock": product["stock"],
            "min_stock": product["min_stock"]
        }
    }


# ------------------------------------------------------------
# BARCODE PRODUCT LIST
# ------------------------------------------------------------

@app.route("/barcode_products")
@login_required
def barcode_products():

    db = get_db()

    try:

        products = db.execute(
            """
            SELECT
                id,
                name,
                category,
                barcode,
                selling_price,
                stock
            FROM products
            ORDER BY name
            """
        ).fetchall()

    finally:
        db.close()

    html = """

    <div class="card">

        <h2>🏷️ Product Barcode List</h2>

        <p>
            Products having a barcode/SKU are shown below.
        </p>

        <table>

            <tr>
                <th>#</th>
                <th>Product</th>
                <th>Category</th>
                <th>Barcode / SKU</th>
                <th>Price</th>
                <th>Stock</th>
            </tr>

            {% for product in products %}

            <tr>

                <td>
                    {{ loop.index }}
                </td>

                <td>
                    {{ product["name"] }}
                </td>

                <td>
                    {{ product["category"] or "-" }}
                </td>

                <td>
                    {% if product["barcode"] %}
                        {{ product["barcode"] }}
                    {% else %}
                        <span style="color:#777;">
                            No Barcode
                        </span>
                    {% endif %}
                </td>

                <td>
                    ₹{{ money(product["selling_price"]) }}
                </td>

                <td>
                    {{ product["stock"] }}
                </td>

            </tr>

            {% endfor %}

        </table>

    </div>

    """

    return render_page(
        "Barcode Products",
        render_template_string(
            html,
            products=products,
            money=money
        )
    )


# ------------------------------------------------------------
# BARCODE LABEL PREVIEW
# ------------------------------------------------------------

@app.route("/barcode_label/<int:product_id>")
@login_required
def barcode_label(product_id):

    db = get_db()

    try:

        product = db.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (product_id,)
        ).fetchone()

    finally:
        db.close()

    if not product:

        flash(
            "Product not found.",
            "danger"
        )

        return redirect(url_for("products"))

    html = """

    <div class="card"
         style="max-width:500px;
                margin:20px auto;
                text-align:center;">

        <h2>
            🏷️ Product Label
        </h2>

        <hr>

        <h3>
            {{ product["name"] }}
        </h3>

        {% if product["category"] %}

        <p>
            {{ product["category"] }}
        </p>

        {% endif %}

        <h2>
            ₹{{ money(product["selling_price"]) }}
        </h2>

        {% if product["barcode"] %}

        <div style="
            border:2px dashed #555;
            padding:20px;
            margin-top:20px;
            font-family:monospace;
            font-size:24px;
            letter-spacing:3px;
        ">

            {{ product["barcode"] }}

        </div>

        {% else %}

        <p>
            No barcode/SKU assigned.
        </p>

        {% endif %}

        <br>

        <button class="btn btn-primary"
                onclick="window.print();">
            🖨️ Print Label
        </button>

    </div>


    <style>

        @media print {

            body * {
                visibility: hidden;
            }

            .card,
            .card * {
                visibility: visible;
            }

            .card {
                position: absolute;
                left: 0;
                top: 0;
                width: 100%;
            }

            button {
                display: none;
            }

        }

    </style>

    """

    return render_page(
        "Product Label",
        render_template_string(
            html,
            product=product,
            money=money
        )
    )


# ------------------------------------------------------------
# END OF PART 12
# ------------------------------------------------------------
# ============================================================
# PART 13 — CUSTOMER & SUPPLIER STATEMENTS
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# CUSTOMER ACCOUNT STATEMENT
# ------------------------------------------------------------

@app.route("/customer_statement/<int:customer_id>")
@login_required
def customer_statement(customer_id):

    db = get_db()

    try:

        customer = db.execute(
            """
            SELECT *
            FROM customers
            WHERE id = ?
            """,
            (customer_id,)
        ).fetchone()

        if not customer:

            flash(
                "Customer not found.",
                "danger"
            )

            return redirect(url_for("customers"))

        # Customer bills
        bills = db.execute(
            """
            SELECT *
            FROM bills
            WHERE customer_id = ?
            ORDER BY id DESC
            """,
            (customer_id,)
        ).fetchall()

        # Customer payments
        payments = db.execute(
            """
            SELECT *
            FROM payments
            WHERE customer_id = ?
            ORDER BY id DESC
            """,
            (customer_id,)
        ).fetchall()

        total_billed = db.execute(
            """
            SELECT COALESCE(
                SUM(grand_total), 0
            )
            FROM bills
            WHERE customer_id = ?
            """,
            (customer_id,)
        ).fetchone()[0]

        total_paid = db.execute(
            """
            SELECT COALESCE(
                SUM(amount), 0
            )
            FROM payments
            WHERE customer_id = ?
            """,
            (customer_id,)
        ).fetchone()[0]

    finally:
        db.close()

    balance = float(total_billed or 0) - float(
        total_paid or 0
    )

    html = """

    <div class="card">

        <h2>👤 Customer Statement</h2>

        <table>

            <tr>
                <th>Customer Name</th>
                <td>{{ customer["name"] }}</td>
            </tr>

            <tr>
                <th>Phone</th>
                <td>
                    {{ customer["phone"] or "-" }}
                </td>
            </tr>

            <tr>
                <th>Address</th>
                <td>
                    {{ customer["address"] or "-" }}
                </td>
            </tr>

            <tr>
                <th>Total Billed</th>
                <td>
                    ₹{{ money(total_billed) }}
                </td>
            </tr>

            <tr>
                <th>Total Paid</th>
                <td>
                    ₹{{ money(total_paid) }}
                </td>
            </tr>

            <tr>
                <th>Current Balance</th>
                <td>
                    <b>
                        ₹{{ money(balance) }}
                    </b>
                </td>
            </tr>

        </table>

    </div>


    <div class="card">

        <h2>🧾 Customer Bills</h2>

        {% if bills %}

        <table>

            <tr>
                <th>Bill No.</th>
                <th>Date</th>
                <th>Payment</th>
                <th>Total</th>
                <th>Action</th>
            </tr>

            {% for bill in bills %}

            <tr>

                <td>
                    {{ bill["bill_no"] }}
                </td>

                <td>
                    {{ bill["created_at"] }}
                </td>

                <td>
                    {{ bill["payment_method"] }}
                </td>

                <td>
                    ₹{{ money(bill["grand_total"]) }}
                </td>

                <td>

                    <a class="btn btn-primary"
                       href="{{ url_for(
                       'invoice',
                       bill_id=bill['id']
                       ) }}">
                       View
                    </a>

                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No bills found.</p>

        {% endif %}

    </div>


    <div class="card">

        <h2>💰 Payments Received</h2>

        {% if payments %}

        <table>

            <tr>
                <th>Date</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Note</th>
            </tr>

            {% for payment in payments %}

            <tr>

                <td>
                    {{ payment["payment_date"] }}
                </td>

                <td>
                    ₹{{ money(payment["amount"]) }}
                </td>

                <td>
                    {{ payment["payment_method"] or "-" }}
                </td>

                <td>
                    {{ payment["note"] or "-" }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No payment records found.</p>

        {% endif %}

    </div>


    <div class="card">

        <a class="btn btn-primary"
           href="{{ url_for(
           'customer_payment',
           customer_id=customer['id']
           ) }}">
           💰 Add Payment
        </a>

        <button class="btn btn-primary"
                onclick="window.print();">
            🖨️ Print Statement
        </button>

    </div>


    <style>

        @media print {

            body * {
                visibility: hidden;
            }

            .card,
            .card * {
                visibility: visible;
            }

            .card {
                position: relative;
                width: 100%;
            }

            button,
            a {
                display: none !important;
            }

        }

    </style>

    """

    return render_page(
        "Customer Statement",
        render_template_string(
            html,
            customer=customer,
            bills=bills,
            payments=payments,
            total_billed=total_billed,
            total_paid=total_paid,
            balance=balance,
            money=money
        )
    )


# ------------------------------------------------------------
# SUPPLIER ACCOUNT STATEMENT
# ------------------------------------------------------------

@app.route("/supplier_statement/<int:supplier_id>")
@login_required
def supplier_statement(supplier_id):

    db = get_db()

    try:

        supplier = db.execute(
            """
            SELECT *
            FROM suppliers
            WHERE id = ?
            """,
            (supplier_id,)
        ).fetchone()

        if not supplier:

            flash(
                "Supplier not found.",
                "danger"
            )

            return redirect(url_for("suppliers"))

        purchases = db.execute(
            """
            SELECT *
            FROM purchases
            WHERE supplier_id = ?
            ORDER BY id DESC
            """,
            (supplier_id,)
        ).fetchall()

        payments = db.execute(
            """
            SELECT *
            FROM supplier_payments
            WHERE supplier_id = ?
            ORDER BY id DESC
            """,
            (supplier_id,)
        ).fetchall()

        total_purchase = db.execute(
            """
            SELECT COALESCE(
                SUM(total_amount), 0
            )
            FROM purchases
            WHERE supplier_id = ?
            """,
            (supplier_id,)
        ).fetchone()[0]

        total_paid = db.execute(
            """
            SELECT COALESCE(
                SUM(amount), 0
            )
            FROM supplier_payments
            WHERE supplier_id = ?
            """,
            (supplier_id,)
        ).fetchone()[0]

    finally:
        db.close()

    balance = float(
        total_purchase or 0
    ) - float(
        total_paid or 0
    )

    html = """

    <div class="card">

        <h2>🚚 Supplier Statement</h2>

        <table>

            <tr>
                <th>Supplier Name</th>
                <td>{{ supplier["name"] }}</td>
            </tr>

            <tr>
                <th>Phone</th>
                <td>
                    {{ supplier["phone"] or "-" }}
                </td>
            </tr>

            <tr>
                <th>Address</th>
                <td>
                    {{ supplier["address"] or "-" }}
                </td>
            </tr>

            <tr>
                <th>Total Purchase</th>
                <td>
                    ₹{{ money(total_purchase) }}
                </td>
            </tr>

            <tr>
                <th>Total Paid</th>
                <td>
                    ₹{{ money(total_paid) }}
                </td>
            </tr>

            <tr>
                <th>Current Due</th>
                <td>
                    <b>
                        ₹{{ money(balance) }}
                    </b>
                </td>
            </tr>

        </table>

    </div>


    <div class="card">

        <h2>📦 Purchase History</h2>

        {% if purchases %}

        <table>

            <tr>
                <th>Date</th>
                <th>Invoice No.</th>
                <th>Total</th>
                <th>Paid</th>
            </tr>

            {% for purchase in purchases %}

            <tr>

                <td>
                    {{ purchase["purchase_date"] }}
                </td>

                <td>
                    {{ purchase["invoice_no"] or "-" }}
                </td>

                <td>
                    ₹{{ money(
                    purchase["total_amount"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    purchase["paid_amount"]
                    ) }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No purchase records found.</p>

        {% endif %}

    </div>


    <div class="card">

        <h2>💰 Supplier Payments</h2>

        {% if payments %}

        <table>

            <tr>
                <th>Date</th>
                <th>Amount</th>
                <th>Method</th>
                <th>Note</th>
            </tr>

            {% for payment in payments %}

            <tr>

                <td>
                    {{ payment["payment_date"] }}
                </td>

                <td>
                    ₹{{ money(payment["amount"]) }}
                </td>

                <td>
                    {{ payment["payment_method"] or "-" }}
                </td>

                <td>
                    {{ payment["note"] or "-" }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No payment records found.</p>

        {% endif %}

    </div>


    <div class="card">

        <a class="btn btn-primary"
           href="{{ url_for(
           'supplier_payment',
           supplier_id=supplier['id']
           ) }}">
           💰 Add Payment
        </a>

        <button class="btn btn-primary"
                onclick="window.print();">
            🖨️ Print Statement
        </button>

    </div>


    <style>

        @media print {

            body * {
                visibility: hidden;
            }

            .card,
            .card * {
                visibility: visible;
            }

            .card {
                position: relative;
                width: 100%;
            }

            button,
            a {
                display: none !important;
            }

        }

    </style>

    """

    return render_page(
        "Supplier Statement",
        render_template_string(
            html,
            supplier=supplier,
            purchases=purchases,
            payments=payments,
            total_purchase=total_purchase,
            total_paid=total_paid,
            balance=balance,
            money=money
        )
    )


# ------------------------------------------------------------
# END OF PART 13
# ============================================================
# ============================================================
# PART 14 — DAILY CASH & PAYMENT SUMMARY
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# DAILY PAYMENT SUMMARY
# ------------------------------------------------------------

@app.route("/payment_summary")
@login_required
def payment_summary():

    selected_date = request.args.get(
        "date",
        date.today().strftime("%Y-%m-%d")
    )

    db = get_db()

    try:

        # Total sales for selected date
        total_sales = db.execute(
            """
            SELECT COALESCE(
                SUM(grand_total), 0
            )
            FROM bills
            WHERE DATE(created_at) = ?
            """,
            (selected_date,)
        ).fetchone()[0]

        # Payment method wise sales
        payment_rows = db.execute(
            """
            SELECT
                payment_method,
                COUNT(*) AS bill_count,
                COALESCE(
                    SUM(grand_total), 0
                ) AS total
            FROM bills
            WHERE DATE(created_at) = ?
            GROUP BY payment_method
            ORDER BY total DESC
            """,
            (selected_date,)
        ).fetchall()

        # Expenses
        total_expenses = db.execute(
            """
            SELECT COALESCE(
                SUM(amount), 0
            )
            FROM expenses
            WHERE expense_date = ?
            """,
            (selected_date,)
        ).fetchone()[0]

        # Customer payments received
        customer_payments = db.execute(
            """
            SELECT COALESCE(
                SUM(amount), 0
            )
            FROM payments
            WHERE DATE(payment_date) = ?
            """,
            (selected_date,)
        ).fetchone()[0]

        # Supplier payments made
        supplier_payments = db.execute(
            """
            SELECT COALESCE(
                SUM(amount), 0
            )
            FROM supplier_payments
            WHERE DATE(payment_date) = ?
            """,
            (selected_date,)
        ).fetchone()[0]

        # Number of bills
        bill_count = db.execute(
            """
            SELECT COUNT(*)
            FROM bills
            WHERE DATE(created_at) = ?
            """,
            (selected_date,)
        ).fetchone()[0]

    finally:
        db.close()

    net_cash = (
        float(total_sales or 0)
        + float(customer_payments or 0)
        - float(supplier_payments or 0)
        - float(total_expenses or 0)
    )

    html = """

    <div class="card">

        <h2>💰 Daily Payment Summary</h2>

        <form method="GET">

            <label>Select Date</label>

            <input
                type="date"
                name="date"
                value="{{ selected_date }}"
                required
            >

            <button
                class="btn btn-primary"
                type="submit">
                🔍 View
            </button>

        </form>

    </div>


    <div class="dashboard-grid">

        <div class="stat-card">
            <h3>🧾 Bills</h3>
            <h2>{{ bill_count }}</h2>
        </div>

        <div class="stat-card">
            <h3>💵 Sales</h3>
            <h2>₹{{ money(total_sales) }}</h2>
        </div>

        <div class="stat-card">
            <h3>💳 Customer Payments</h3>
            <h2>₹{{ money(customer_payments) }}</h2>
        </div>

        <div class="stat-card">
            <h3>🚚 Supplier Payments</h3>
            <h2>₹{{ money(supplier_payments) }}</h2>
        </div>

        <div class="stat-card">
            <h3>💸 Expenses</h3>
            <h2>₹{{ money(total_expenses) }}</h2>
        </div>

        <div class="stat-card">
            <h3>💰 Net Cash</h3>
            <h2>₹{{ money(net_cash) }}</h2>
        </div>

    </div>


    <div class="card">

        <h2>💳 Payment Method Summary</h2>

        {% if payment_rows %}

        <table>

            <tr>
                <th>Payment Method</th>
                <th>Bills</th>
                <th>Total Sales</th>
            </tr>

            {% for row in payment_rows %}

            <tr>

                <td>
                    {{ row["payment_method"] or "Unknown" }}
                </td>

                <td>
                    {{ row["bill_count"] }}
                </td>

                <td>
                    ₹{{ money(row["total"]) }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>
            No sales found for this date.
        </p>

        {% endif %}

    </div>


    <div class="card">

        <button
            class="btn btn-primary"
            onclick="window.print();">
            🖨️ Print Summary
        </button>

    </div>


    <style>

        .dashboard-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px
                rgba(0,0,0,0.08);
        }

        .stat-card h2 {
            margin-bottom: 0;
        }

        @media print {

            body * {
                visibility: hidden;
            }

            .card,
            .card *,
            .dashboard-grid,
            .dashboard-grid * {
                visibility: visible;
            }

            .card,
            .dashboard-grid {
                position: relative;
                width: 100%;
            }

            button {
                display: none !important;
            }

        }

    </style>

    """

    return render_page(
        "Payment Summary",
        render_template_string(
            html,
            selected_date=selected_date,
            total_sales=total_sales,
            payment_rows=payment_rows,
            total_expenses=total_expenses,
            customer_payments=customer_payments,
            supplier_payments=supplier_payments,
            bill_count=bill_count,
            net_cash=net_cash,
            money=money
        )
    )


# ------------------------------------------------------------
# CASH REGISTER
# ------------------------------------------------------------

@app.route("/cash_register")
@login_required
def cash_register():

    selected_date = request.args.get(
        "date",
        date.today().strftime("%Y-%m-%d")
    )

    db = get_db()

    try:

        cash_sales = db.execute(
            """
            SELECT COALESCE(
                SUM(grand_total), 0
            )
            FROM bills
            WHERE DATE(created_at) = ?
              AND payment_method = 'Cash'
            """,
            (selected_date,)
        ).fetchone()[0]

        cash_customer_payments = db.execute(
            """
            SELECT COALESCE(
                SUM(amount), 0
            )
            FROM payments
            WHERE DATE(payment_date) = ?
              AND (
                    payment_method = 'Cash'
                    OR payment_method IS NULL
                  )
            """,
            (selected_date,)
        ).fetchone()[0]

        cash_supplier_payments = db.execute(
            """
            SELECT COALESCE(
                SUM(amount), 0
            )
            FROM supplier_payments
            WHERE DATE(payment_date) = ?
              AND (
                    payment_method = 'Cash'
                    OR payment_method IS NULL
                  )
            """,
            (selected_date,)
        ).fetchone()[0]

        cash_expenses = db.execute(
            """
            SELECT COALESCE(
                SUM(amount), 0
            )
            FROM expenses
            WHERE expense_date = ?
              AND (
                    payment_method = 'Cash'
                    OR payment_method IS NULL
                  )
            """,
            (selected_date,)
        ).fetchone()[0]

    finally:
        db.close()

    cash_in = (
        float(cash_sales or 0)
        + float(cash_customer_payments or 0)
    )

    cash_out = (
        float(cash_supplier_payments or 0)
        + float(cash_expenses or 0)
    )

    closing_cash = cash_in - cash_out

    html = """

    <div class="card">

        <h2>💵 Cash Register</h2>

        <form method="GET">

            <label>Select Date</label>

            <input
                type="date"
                name="date"
                value="{{ selected_date }}"
                required
            >

            <button
                class="btn btn-primary"
                type="submit">
                🔍 View
            </button>

        </form>

    </div>


    <div class="card">

        <h2>📥 Cash In</h2>

        <table>

            <tr>
                <th>Cash Sales</th>
                <td>
                    ₹{{ money(cash_sales) }}
                </td>
            </tr>

            <tr>
                <th>Customer Payments</th>
                <td>
                    ₹{{ money(cash_customer_payments) }}
                </td>
            </tr>

            <tr>
                <th>Total Cash In</th>
                <td>
                    <b>
                        ₹{{ money(cash_in) }}
                    </b>
                </td>
            </tr>

        </table>

    </div>


    <div class="card">

        <h2>📤 Cash Out</h2>

        <table>

            <tr>
                <th>Supplier Payments</th>
                <td>
                    ₹{{ money(cash_supplier_payments) }}
                </td>
            </tr>

            <tr>
                <th>Expenses</th>
                <td>
                    ₹{{ money(cash_expenses) }}
                </td>
            </tr>

            <tr>
                <th>Total Cash Out</th>
                <td>
                    <b>
                        ₹{{ money(cash_out) }}
                    </b>
                </td>
            </tr>

        </table>

    </div>


    <div class="card">

        <h2>💰 Closing Cash</h2>

        <h1>
            ₹{{ money(closing_cash) }}
        </h1>

        <button
            class="btn btn-primary"
            onclick="window.print();">
            🖨️ Print
        </button>

    </div>

    """

    return render_page(
        "Cash Register",
        render_template_string(
            html,
            selected_date=selected_date,
            cash_sales=cash_sales,
            cash_customer_payments=cash_customer_payments,
            cash_supplier_payments=cash_supplier_payments,
            cash_expenses=cash_expenses,
            cash_in=cash_in,
            cash_out=cash_out,
            closing_cash=closing_cash,
            money=money
        )
    )


# ------------------------------------------------------------
# END OF PART 14
# ============================================================
# ============================================================
# PART 15 — PURCHASE & STOCK ANALYSIS
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# PURCHASE REPORT
# ------------------------------------------------------------

@app.route("/purchase_report")
@login_required
def purchase_report():

    selected_month = request.args.get(
        "month",
        date.today().strftime("%Y-%m")
    )

    db = get_db()

    try:

        purchases = db.execute(
            """
            SELECT
                purchases.*,
                suppliers.name AS supplier_name
            FROM purchases
            LEFT JOIN suppliers
                ON purchases.supplier_id = suppliers.id
            WHERE strftime(
                '%Y-%m',
                purchases.purchase_date
            ) = ?
            ORDER BY purchases.id DESC
            """,
            (selected_month,)
        ).fetchall()

        total_purchase = db.execute(
            """
            SELECT COALESCE(
                SUM(total_amount), 0
            )
            FROM purchases
            WHERE strftime(
                '%Y-%m',
                purchase_date
            ) = ?
            """,
            (selected_month,)
        ).fetchone()[0]

        total_paid = db.execute(
            """
            SELECT COALESCE(
                SUM(paid_amount), 0
            )
            FROM purchases
            WHERE strftime(
                '%Y-%m',
                purchase_date
            ) = ?
            """,
            (selected_month,)
        ).fetchone()[0]

        purchase_count = db.execute(
            """
            SELECT COUNT(*)
            FROM purchases
            WHERE strftime(
                '%Y-%m',
                purchase_date
            ) = ?
            """,
            (selected_month,)
        ).fetchone()[0]

    finally:
        db.close()

    total_due = (
        float(total_purchase or 0)
        - float(total_paid or 0)
    )

    html = """

    <div class="card">

        <h2>📦 Purchase Report</h2>

        <form method="GET">

            <label>Select Month</label>

            <input
                type="month"
                name="month"
                value="{{ selected_month }}"
                required
            >

            <button
                class="btn btn-primary"
                type="submit">
                🔍 View Report
            </button>

        </form>

    </div>


    <div class="dashboard-grid">

        <div class="stat-card">
            <h3>📦 Purchases</h3>
            <h2>{{ purchase_count }}</h2>
        </div>

        <div class="stat-card">
            <h3>💰 Total Purchase</h3>
            <h2>
                ₹{{ money(total_purchase) }}
            </h2>
        </div>

        <div class="stat-card">
            <h3>💵 Paid</h3>
            <h2>
                ₹{{ money(total_paid) }}
            </h2>
        </div>

        <div class="stat-card">
            <h3>⚠️ Due</h3>
            <h2>
                ₹{{ money(total_due) }}
            </h2>
        </div>

    </div>


    <div class="card">

        <h2>Purchase Details</h2>

        {% if purchases %}

        <table>

            <tr>
                <th>Date</th>
                <th>Supplier</th>
                <th>Invoice</th>
                <th>Total</th>
                <th>Paid</th>
                <th>Due</th>
            </tr>

            {% for purchase in purchases %}

            <tr>

                <td>
                    {{ purchase["purchase_date"] }}
                </td>

                <td>
                    {{ purchase["supplier_name"] or "-" }}
                </td>

                <td>
                    {{ purchase["invoice_no"] or "-" }}
                </td>

                <td>
                    ₹{{ money(
                    purchase["total_amount"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    purchase["paid_amount"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    (purchase["total_amount"] or 0)
                    -
                    (purchase["paid_amount"] or 0)
                    ) }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>
            No purchases found for this month.
        </p>

        {% endif %}

    </div>


    <div class="card">

        <button
            class="btn btn-primary"
            onclick="window.print();">
            🖨️ Print Report
        </button>

    </div>


    <style>

        .dashboard-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow:
                0 2px 8px rgba(0,0,0,0.08);
        }

        @media print {

            body * {
                visibility: hidden;
            }

            .card,
            .card *,
            .dashboard-grid,
            .dashboard-grid * {
                visibility: visible;
            }

            .card,
            .dashboard-grid {
                position: relative;
                width: 100%;
            }

            button {
                display: none !important;
            }

        }

    </style>

    """

    return render_page(
        "Purchase Report",
        render_template_string(
            html,
            selected_month=selected_month,
            purchases=purchases,
            total_purchase=total_purchase,
            total_paid=total_paid,
            total_due=total_due,
            purchase_count=purchase_count,
            money=money
        )
    )


# ------------------------------------------------------------
# STOCK VALUATION
# ------------------------------------------------------------

@app.route("/stock_valuation")
@login_required
def stock_valuation():

    db = get_db()

    try:

        products = db.execute(
            """
            SELECT *
            FROM products
            ORDER BY name
            """
        ).fetchall()

    finally:
        db.close()

    total_purchase_value = 0
    total_selling_value = 0
    total_potential_profit = 0

    product_data = []

    for product in products:

        stock = float(
            product["stock"] or 0
        )

        purchase_price = float(
            product["purchase_price"] or 0
        )

        selling_price = float(
            product["selling_price"] or 0
        )

        purchase_value = (
            stock * purchase_price
        )

        selling_value = (
            stock * selling_price
        )

        potential_profit = (
            selling_value - purchase_value
        )

        total_purchase_value += purchase_value
        total_selling_value += selling_value
        total_potential_profit += potential_profit

        product_data.append({
            "name": product["name"],
            "category": product["category"],
            "stock": stock,
            "purchase_price": purchase_price,
            "selling_price": selling_price,
            "purchase_value": purchase_value,
            "selling_value": selling_value,
            "potential_profit": potential_profit
        })

    html = """

    <div class="dashboard-grid">

        <div class="stat-card">

            <h3>📦 Stock Purchase Value</h3>

            <h2>
                ₹{{ money(total_purchase_value) }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>💰 Stock Selling Value</h3>

            <h2>
                ₹{{ money(total_selling_value) }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>📈 Potential Profit</h3>

            <h2>
                ₹{{ money(total_potential_profit) }}
            </h2>

        </div>

    </div>


    <div class="card">

        <h2>📊 Stock Valuation</h2>

        <table>

            <tr>
                <th>Product</th>
                <th>Stock</th>
                <th>Purchase Price</th>
                <th>Selling Price</th>
                <th>Purchase Value</th>
                <th>Selling Value</th>
                <th>Potential Profit</th>
            </tr>

            {% for item in product_data %}

            <tr>

                <td>
                    {{ item["name"] }}
                </td>

                <td>
                    {{ item["stock"] }}
                </td>

                <td>
                    ₹{{ money(
                    item["purchase_price"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    item["selling_price"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    item["purchase_value"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    item["selling_value"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    item["potential_profit"]
                    ) }}
                </td>

            </tr>

            {% endfor %}

        </table>

    </div>


    <div class="card">

        <button
            class="btn btn-primary"
            onclick="window.print();">
            🖨️ Print Valuation
        </button>

    </div>


    <style>

        .dashboard-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow:
                0 2px 8px rgba(0,0,0,0.08);
        }

        @media print {

            body * {
                visibility: hidden;
            }

            .card,
            .card *,
            .dashboard-grid,
            .dashboard-grid * {
                visibility: visible;
            }

            .card,
            .dashboard-grid {
                position: relative;
                width: 100%;
            }

            button {
                display: none !important;
            }

        }

    </style>

    """

    return render_page(
        "Stock Valuation",
        render_template_string(
            html,
            products=products,
            product_data=product_data,
            total_purchase_value=total_purchase_value,
            total_selling_value=total_selling_value,
            total_potential_profit=total_potential_profit,
            money=money
        )
    )


# ------------------------------------------------------------
# CATEGORY-WISE STOCK
# ------------------------------------------------------------

@app.route("/category_stock")
@login_required
def category_stock():

    db = get_db()

    try:

        categories = db.execute(
            """
            SELECT
                COALESCE(category, 'Other')
                AS category,
                COUNT(*) AS product_count,
                COALESCE(
                    SUM(stock), 0
                ) AS total_stock,
                COALESCE(
                    SUM(
                        stock * purchase_price
                    ), 0
                ) AS purchase_value,
                COALESCE(
                    SUM(
                        stock * selling_price
                    ), 0
                ) AS selling_value
            FROM products
            GROUP BY COALESCE(
                category,
                'Other'
            )
            ORDER BY selling_value DESC
            """
        ).fetchall()

    finally:
        db.close()

    html = """

    <div class="card">

        <h2>📊 Category-wise Stock</h2>

        {% if categories %}

        <table>

            <tr>
                <th>Category</th>
                <th>Products</th>
                <th>Total Stock</th>
                <th>Purchase Value</th>
                <th>Selling Value</th>
                <th>Potential Profit</th>
            </tr>

            {% for category in categories %}

            <tr>

                <td>
                    {{ category["category"] }}
                </td>

                <td>
                    {{ category["product_count"] }}
                </td>

                <td>
                    {{ category["total_stock"] }}
                </td>

                <td>
                    ₹{{ money(
                    category["purchase_value"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    category["selling_value"]
                    ) }}
                </td>

                <td>
                    ₹{{ money(
                    (category["selling_value"] or 0)
                    -
                    (category["purchase_value"] or 0)
                    ) }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>
            No category data available.
        </p>

        {% endif %}

    </div>

    """

    return render_page(
        "Category Stock",
        render_template_string(
            html,
            categories=categories,
            money=money
        )
    )


# ------------------------------------------------------------
# END OF PART 15
# ============================================================
# ============================================================
# PART 16 — SALES & PROFIT ANALYSIS
# PANDEY KIRANA STORE
# ============================================================


# ------------------------------------------------------------
# PRODUCT-WISE SALES REPORT
# ------------------------------------------------------------

@app.route("/product_sales_report")
@login_required
def product_sales_report():

    selected_month = request.args.get(
        "month",
        date.today().strftime("%Y-%m")
    )

    db = get_db()

    try:

        products = db.execute(
            """
            SELECT
                p.id,
                p.name,
                p.category,

                COALESCE(
                    SUM(
                        CASE
                            WHEN DATE(b.created_at) IS NOT NULL
                            THEN bi.quantity
                            ELSE 0
                        END
                    ),
                    0
                ) AS sold_quantity,

                COALESCE(
                    SUM(
                        bi.quantity * bi.price
                    ),
                    0
                ) AS sales_value,

                COALESCE(
                    SUM(
                        bi.quantity * p.purchase_price
                    ),
                    0
                ) AS cost_value

            FROM products p

            LEFT JOIN bill_items bi
                ON p.id = bi.product_id

            LEFT JOIN bills b
                ON bi.bill_id = b.id
                AND strftime(
                    '%Y-%m',
                    b.created_at
                ) = ?

            GROUP BY
                p.id,
                p.name,
                p.category

            ORDER BY sales_value DESC
            """,
            (selected_month,)
        ).fetchall()

    finally:
        db.close()

    product_data = []

    total_quantity = 0
    total_sales = 0
    total_cost = 0
    total_profit = 0

    for product in products:

        quantity = float(
            product["sold_quantity"] or 0
        )

        sales = float(
            product["sales_value"] or 0
        )

        cost = float(
            product["cost_value"] or 0
        )

        profit = sales - cost

        total_quantity += quantity
        total_sales += sales
        total_cost += cost
        total_profit += profit

        product_data.append({
            "name": product["name"],
            "category": product["category"],
            "quantity": quantity,
            "sales": sales,
            "cost": cost,
            "profit": profit
        })

    html = """

    <div class="card">

        <h2>📊 Product-wise Sales Report</h2>

        <form method="GET">

            <label>Select Month</label>

            <input
                type="month"
                name="month"
                value="{{ selected_month }}"
                required
            >

            <button
                class="btn btn-primary"
                type="submit">
                🔍 View
            </button>

        </form>

    </div>


    <div class="dashboard-grid">

        <div class="stat-card">

            <h3>📦 Units Sold</h3>

            <h2>
                {{ total_quantity }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>💰 Sales</h3>

            <h2>
                ₹{{ money(total_sales) }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>💵 Cost</h3>

            <h2>
                ₹{{ money(total_cost) }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>📈 Profit</h3>

            <h2>
                ₹{{ money(total_profit) }}
            </h2>

        </div>

    </div>


    <div class="card">

        <h2>Product Details</h2>

        {% if product_data %}

        <table>

            <tr>
                <th>Product</th>
                <th>Category</th>
                <th>Qty Sold</th>
                <th>Sales</th>
                <th>Cost</th>
                <th>Profit</th>
            </tr>

            {% for item in product_data %}

            <tr>

                <td>
                    {{ item["name"] }}
                </td>

                <td>
                    {{ item["category"] or "-" }}
                </td>

                <td>
                    {{ item["quantity"] }}
                </td>

                <td>
                    ₹{{ money(item["sales"]) }}
                </td>

                <td>
                    ₹{{ money(item["cost"]) }}
                </td>

                <td>
                    ₹{{ money(item["profit"]) }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>No product sales found.</p>

        {% endif %}

    </div>


    <div class="card">

        <button
            class="btn btn-primary"
            onclick="window.print();">
            🖨️ Print Report
        </button>

    </div>


    <style>

        .dashboard-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow:
                0 2px 8px rgba(0,0,0,0.08);
        }

        @media print {

            body * {
                visibility: hidden;
            }

            .card,
            .card *,
            .dashboard-grid,
            .dashboard-grid * {
                visibility: visible;
            }

            .card,
            .dashboard-grid {
                position: relative;
                width: 100%;
            }

            button {
                display: none !important;
            }

        }

    </style>

    """

    return render_page(
        "Product Sales Report",
        render_template_string(
            html,
            selected_month=selected_month,
            product_data=product_data,
            total_quantity=total_quantity,
            total_sales=total_sales,
            total_cost=total_cost,
            total_profit=total_profit,
            money=money
        )
    )


# ------------------------------------------------------------
# DAILY PROFIT REPORT
# ------------------------------------------------------------

@app.route("/profit_report")
@login_required
def profit_report():

    selected_date = request.args.get(
        "date",
        date.today().strftime("%Y-%m-%d")
    )

    db = get_db()

    try:

        sales = db.execute(
            """
            SELECT
                COALESCE(SUM(grand_total), 0)
            FROM bills
            WHERE DATE(created_at) = ?
            """,
            (selected_date,)
        ).fetchone()[0]

        cost = db.execute(
            """
            SELECT
                COALESCE(
                    SUM(
                        bi.quantity *
                        p.purchase_price
                    ),
                    0
                )
            FROM bill_items bi

            INNER JOIN bills b
                ON bi.bill_id = b.id

            INNER JOIN products p
                ON bi.product_id = p.id

            WHERE DATE(b.created_at) = ?
            """,
            (selected_date,)
        ).fetchone()[0]

        expenses = db.execute(
            """
            SELECT
                COALESCE(SUM(amount), 0)
            FROM expenses
            WHERE expense_date = ?
            """,
            (selected_date,)
        ).fetchone()[0]

        discount = db.execute(
            """
            SELECT
                COALESCE(SUM(discount), 0)
            FROM bills
            WHERE DATE(created_at) = ?
            """,
            (selected_date,)
        ).fetchone()[0]

    finally:
        db.close()

    gross_profit = (
        float(sales or 0)
        - float(cost or 0)
    )

    net_profit = (
        gross_profit
        - float(expenses or 0)
    )

    html = """

    <div class="card">

        <h2>📈 Profit Report</h2>

        <form method="GET">

            <label>Select Date</label>

            <input
                type="date"
                name="date"
                value="{{ selected_date }}"
                required
            >

            <button
                class="btn btn-primary"
                type="submit">
                🔍 View
            </button>

        </form>

    </div>


    <div class="dashboard-grid">

        <div class="stat-card">

            <h3>💰 Sales</h3>

            <h2>
                ₹{{ money(sales) }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>📦 Product Cost</h3>

            <h2>
                ₹{{ money(cost) }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>📈 Gross Profit</h3>

            <h2>
                ₹{{ money(gross_profit) }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>💸 Expenses</h3>

            <h2>
                ₹{{ money(expenses) }}
            </h2>

        </div>


        <div class="stat-card">

            <h3>✅ Net Profit</h3>

            <h2>
                ₹{{ money(net_profit) }}
            </h2>

        </div>

    </div>


    <div class="card">

        <h2>Profit Calculation</h2>

        <table>

            <tr>
                <th>Total Sales</th>
                <td>
                    ₹{{ money(sales) }}
                </td>
            </tr>

            <tr>
                <th>Product Cost</th>
                <td>
                    ₹{{ money(cost) }}
                </td>
            </tr>

            <tr>
                <th>Gross Profit</th>
                <td>
                    ₹{{ money(gross_profit) }}
                </td>
            </tr>

            <tr>
                <th>Expenses</th>
                <td>
                    ₹{{ money(expenses) }}
                </td>
            </tr>

            <tr>
                <th>Net Profit</th>
                <td>
                    <b>
                        ₹{{ money(net_profit) }}
                    </b>
                </td>
            </tr>

        </table>

        <br>

        <button
            class="btn btn-primary"
            onclick="window.print();">
            🖨️ Print Report
        </button>

    </div>


    <style>

        .dashboard-grid {
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }

        .stat-card {
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow:
                0 2px 8px rgba(0,0,0,0.08);
        }

        @media print {

            body * {
                visibility: hidden;
            }

            .card,
            .card *,
            .dashboard-grid,
            .dashboard-grid * {
                visibility: visible;
            }

            .card,
            .dashboard-grid {
                position: relative;
                width: 100%;
            }

            button {
                display: none !important;
            }

        }

    </style>

    """

    return render_page(
        "Profit Report",
        render_template_string(
            html,
            selected_date=selected_date,
            sales=sales,
            cost=cost,
            expenses=expenses,
            discount=discount,
            gross_profit=gross_profit,
            net_profit=net_profit,
            money=money
        )
    )


# ------------------------------------------------------------
# TOP SELLING PRODUCTS
# ------------------------------------------------------------

@app.route("/top_products")
@login_required
def top_products():

    db = get_db()

    try:

        products = db.execute(
            """
            SELECT
                p.name,
                p.category,
                COALESCE(
                    SUM(bi.quantity),
                    0
                ) AS quantity_sold,

                COALESCE(
                    SUM(
                        bi.quantity * bi.price
                    ),
                    0
                ) AS sales_value

            FROM bill_items bi

            INNER JOIN products p
                ON bi.product_id = p.id

            GROUP BY
                p.id,
                p.name,
                p.category

            ORDER BY quantity_sold DESC

            LIMIT 20
            """
        ).fetchall()

    finally:
        db.close()

    html = """

    <div class="card">

        <h2>🏆 Top Selling Products</h2>

        {% if products %}

        <table>

            <tr>
                <th>Rank</th>
                <th>Product</th>
                <th>Category</th>
                <th>Quantity Sold</th>
                <th>Sales Value</th>
            </tr>

            {% for product in products %}

            <tr>

                <td>
                    {{ loop.index }}
                </td>

                <td>
                    {{ product["name"] }}
                </td>

                <td>
                    {{ product["category"] or "-" }}
                </td>

                <td>
                    {{ product["quantity_sold"] }}
                </td>

                <td>
                    ₹{{ money(
                    product["sales_value"]
                    ) }}
                </td>

            </tr>

            {% endfor %}

        </table>

        {% else %}

        <p>
            No sales data available.
        </p>

        {% endif %}

    </div>

    """

    return render_page(
        "Top Products",
        render_template_string(
            html,
            products=products,
            money=money
        )
    )


# ------------------------------------------------------------
# END OF PART 16
# ============================================================


# ------------------------------------------------------------
# RUN APPLICATION
# ------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=port,
        debug=False
    )
