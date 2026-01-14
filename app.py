import os
from datetime import datetime
from urllib.parse import quote_plus

from flask import (
    Flask, render_template, redirect,
    url_for, request, session, flash
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename

# =========================
# ADMIN MOBILE NUMBER
# =========================
ADMIN_MOBILE = "7978692808"

# =========================
# APP CONFIG
# =========================
app = Flask(__name__)
app.config["SECRET_KEY"] = "change_this_secret_key"
import os

database_url = os.environ.get("DATABASE_URL")

if database_url:
    # Render / Production (PostgreSQL)
    app.config["SQLALCHEMY_DATABASE_URI"] = database_url.replace(
        "postgres://", "postgresql://"
    )
else:
    # Local development (SQLite)
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///hotel.db"


app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

UPLOAD_FOLDER = os.path.join("static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)

# =========================
# DATABASE MODELS
# =========================
class Dish(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    mrp = db.Column(db.Integer)
    category = db.Column(db.String(80), nullable=False)
    image_filename = db.Column(db.String(200))
    veg_type = db.Column(db.String(20))
    is_best_seller = db.Column(db.Boolean, default=False)
    is_new = db.Column(db.Boolean, default=False)


class Order(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), default="Pending")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total_amount = db.Column(db.Integer, nullable=False)
    items = db.relationship("OrderItem", backref="order", cascade="all, delete-orphan")


class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("order.id"))
    dish_id = db.Column(db.Integer, db.ForeignKey("dish.id"))
    quantity = db.Column(db.Integer)
    price = db.Column(db.Integer)
    dish = db.relationship("Dish")


class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login_at = db.Column(db.DateTime, default=datetime.utcnow)

# =========================
# HELPERS
# =========================
def get_cart():
    return session.setdefault("cart", {})

def save_cart(cart):
    session["cart"] = cart
    session.modified = True

def is_admin():
    return session.get("is_admin") is True

# =========================
# INIT DB
# =========================
def init_db():
    with app.app_context():
        db.create_all()

# =========================
# PUBLIC ROUTES
# =========================
@app.route("/")
def home():
    return render_template("index.html", menu_items=Dish.query.all())


@app.route("/menu")
def menu():
    f = request.args.get("filter", "All")
    q = Dish.query

    if f in ["Veg", "Non-veg"]:
        q = q.filter_by(veg_type=f)
    elif f != "All":
        q = q.filter_by(category=f)

    filters = ["All","Veg","Non-veg","Biryani","Snacks","Main Course","Dessert","Beverages"]

    return render_template(
        "menu.html",
        menu_items=q.all(),
        filters=filters,
        current_filter=f
    )

# =========================
# CART
# =========================
@app.route("/add_to_cart/<int:item_id>")
def add_to_cart(item_id):
    cart = get_cart()
    cart[str(item_id)] = cart.get(str(item_id), 0) + 1
    save_cart(cart)
    return redirect(url_for("cart_view"))


@app.route("/cart")
def cart_view():
    cart = get_cart()
    items, total = [], 0

    for k, q in cart.items():
        dish = Dish.query.get(int(k))
        if dish:
            subtotal = dish.price * q
            total += subtotal
            items.append({
                "id": dish.id,
                "name": dish.name,
                "price": dish.price,
                "quantity": q,
                "subtotal": subtotal
            })

    return render_template("cart.html", cart_items=items, total=total)


@app.route("/update_cart", methods=["POST"])
def update_cart():
    cart = {}
    for k, v in request.form.items():
        if k.startswith("qty_") and int(v) > 0:
            cart[k.split("_")[1]] = int(v)
    save_cart(cart)
    return redirect(url_for("cart_view"))

# =========================
# 🔐 SINGLE LOGIN (ADMIN + CUSTOMER)
# =========================
@app.route("/login", methods=["GET","POST"])
def customer_login():
    if request.method == "POST":
        phone = request.form.get("phone")

        if not phone or len(phone) != 10:
            return render_template("customer_login.html", error="Invalid phone number")

        customer = Customer.query.filter_by(phone=phone).first()
        if not customer:
            customer = Customer(phone=phone)
            db.session.add(customer)

        customer.last_login_at = datetime.utcnow()
        db.session.commit()

        session.clear()

        # ADMIN AUTO LOGIN
        if phone == ADMIN_MOBILE:
            session["is_admin"] = True
            session["admin_phone"] = phone
            flash("Welcome Admin", "success")
            return redirect(url_for("admin_dashboard"))

        # CUSTOMER LOGIN
        session["customer_phone"] = phone
        flash("Login successful", "success")
        return redirect(url_for("home"))

    return render_template("customer_login.html")

# =========================
# CHECKOUT (SAVE ORDER)
# =========================
@app.route("/checkout", methods=["GET","POST"])
def checkout():
    if not session.get("customer_phone"):
        flash("Please login first", "warning")
        return redirect(url_for("customer_login"))

    cart = get_cart()
    if not cart:
        return redirect(url_for("menu"))

    items, total = [], 0
    for k, q in cart.items():
        dish = Dish.query.get(int(k))
        if dish:
            subtotal = dish.price * q
            total += subtotal
            items.append({
                "id": dish.id,
                "name": dish.name,
                "price": dish.price,
                "quantity": q,
                "subtotal": subtotal
            })

    if request.method == "POST":
        name = request.form.get("name")
        phone = request.form.get("phone")
        address = request.form.get("address")

        order = Order(
            customer_name=name,
            phone=phone,
            address=address,
            payment_method="Cash on Delivery",
            total_amount=total,
            status="Pending"
        )
        db.session.add(order)
        db.session.commit()

        for item in items:
            db.session.add(OrderItem(
                order_id=order.id,
                dish_id=item["id"],
                quantity=item["quantity"],
                price=item["price"]
            ))

        db.session.commit()
        session.pop("cart", None)

        return redirect(url_for("order_success", order_id=order.id))

    return render_template("checkout.html", cart_items=items, total=total)

# =========================
# ORDER SUCCESS + WHATSAPP
# =========================
@app.route("/order_success")
def order_success():
    order_id = request.args.get("order_id", type=int)
    order = Order.query.get_or_404(order_id)

    items_text = ""
    for item in order.items:
        items_text += f"\n- {item.dish.name} × {item.quantity} = ₹{item.quantity * item.price}"

    message = f"""
🟢 New Order – Mission Shakti Cafe

👤 Name: {order.customer_name}
📞 Phone: {order.phone}
🏠 Address: {order.address}

🍽 Items:{items_text}

💰 Total: ₹{order.total_amount}
🚚 Delivery Time: 30 Minutes
💵 Payment: Cash on Delivery
"""

    whatsapp_url = "https://wa.me/917894332390?text=" + quote_plus(message)

    return render_template("order_success.html", order=order, whatsapp_url=whatsapp_url)

# =========================
# ADMIN DASHBOARD
# =========================
@app.route("/admin/dashboard")
def admin_dashboard():
    if not is_admin():
        return redirect(url_for("customer_login"))

    return render_template(
        "admin_dashboard.html",
        total_dishes=Dish.query.count(),
        total_orders=Order.query.count(),
        pending_orders=Order.query.filter_by(status="Pending").count(),
        total_customers=Customer.query.count(),
        latest_customers=Customer.query.order_by(Customer.created_at.desc()).limit(10)
    )


@app.route("/admin/logout")
def admin_logout():
    session.clear()
    return redirect(url_for("home"))

# =========================
# ADMIN ITEMS
# =========================
@app.route("/admin/items", methods=["GET","POST"])
def admin_items():
    if not is_admin():
        return redirect(url_for("customer_login"))

    if request.method == "POST":
        img = request.files.get("image")
        filename = None
        if img and img.filename:
            filename = secure_filename(img.filename)
            img.save(os.path.join(UPLOAD_FOLDER, filename))

        dish = Dish(
            name=request.form["name"],
            price=int(request.form["price"]),
            mrp=request.form.get("mrp", type=int),
            category=request.form["category"],
            veg_type=request.form.get("veg_type"),
            is_best_seller=bool(request.form.get("best_seller")),
            is_new=bool(request.form.get("is_new")),
            image_filename=filename
        )
        db.session.add(dish)
        db.session.commit()

    return render_template("admin_items.html", dishes=Dish.query.all())


@app.route("/admin/dishes/delete/<int:dish_id>", methods=["POST"])
def delete_dish(dish_id):
    if not is_admin():
        return redirect(url_for("customer_login"))

    dish = Dish.query.get_or_404(dish_id)
    db.session.delete(dish)
    db.session.commit()
    return redirect(url_for("admin_items"))

# =========================
# ADMIN ORDERS
# =========================
@app.route("/admin/orders")
def admin_orders():
    if not is_admin():
        return redirect(url_for("customer_login"))

    status = request.args.get("status", "All")
    q = Order.query
    if status != "All":
        q = q.filter_by(status=status)

    return render_template(
        "admin_orders.html",
        orders=q.order_by(Order.created_at.desc()).all(),
        status_filter=status
    )


@app.route("/admin/orders/update_status/<int:order_id>", methods=["POST"])
def update_order_status(order_id):
    if not is_admin():
        return redirect(url_for("customer_login"))

    order = Order.query.get_or_404(order_id)
    order.status = request.form.get("status", "Pending")
    db.session.commit()
    return redirect(url_for("admin_orders"))


# =========================
# CUSTOMER ORDER HISTORY
# =========================

@app.route("/my-orders")
def my_orders():
    if not session.get("customer_phone"):
        flash("Please login to view your orders", "warning")
        return redirect(url_for("customer_login"))

    orders = Order.query.filter_by(
        phone=session["customer_phone"]
    ).order_by(Order.created_at.desc()).all()

    return render_template("my_orders.html", orders=orders)


# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    init_db()
    app.run()
# this ensures db folder exists
try:
    with app.app_context():
        db.create_all()
except Exception as e:
 
    print("DB init error:", e)
