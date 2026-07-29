"""Generate richer seed data for the Dispatch AI demo database."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

OUTPUT = Path(__file__).with_name("seed_data.sql")

FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason", "Isabella",
    "William", "Mia", "James", "Charlotte", "Benjamin", "Amelia", "Lucas", "Harper",
    "Henry", "Evelyn", "Alexander", "Abigail", "Michael", "Ella", "Daniel", "Scarlett",
    "Matthew", "Grace", "Jackson", "Chloe", "Sebastian", "Lily", "Aiden", "Aria", "David",
    "Zoey", "Joseph", "Riley", "Samuel", "Nora", "Carter", "Hazel", "Owen", "Aubrey",
    "Wyatt", "Ellie", "John", "Stella", "Jack", "Nova", "Luke",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis",
    "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores",
    "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

PRODUCT_CATALOG = [
    ("USB-C Hub", "Accessories", 59.99),
    ("Webcam Ring Light", "Photography", 34.99),
    ("Smart Bulb Kit", "Smart Home", 89.99),
    ("Streaming Microphone", "Audio", 129.99),
    ("27-inch Monitor", "Electronics", 299.99),
    ("Desktop PC", "Electronics", 899.99),
    ("Laptop Sleeve", "Accessories", 24.99),
    ("USB Microphone", "Audio", 79.99),
    ("4K Monitor", "Electronics", 449.99),
    ("Wireless Charger", "Accessories", 39.99),
    ("Smart Watch", "Wearables", 199.99),
    ("Graphics Tablet", "Electronics", 349.99),
    ("Docking Station", "Accessories", 149.99),
    ("Fitness Tracker", "Wearables", 129.99),
    ("Mesh Wi-Fi Router", "Smart Home", 159.99),
    ("Noise-Canceling Headphones", "Audio", 249.99),
    ("Ergonomic Chair", "Office", 499.99),
    ("Standing Desk", "Office", 599.99),
    ("Portable Charger", "Accessories", 49.99),
    ("VR Headset", "Gaming", 399.99),
    ("Travel Backpack", "Accessories", 89.99),
    ("Mechanical Keyboard", "Gaming", 119.99),
    ("Tablet Sleeve", "Accessories", 29.99),
    ("Webcam 1080p", "Photography", 69.99),
    ("External SSD 1TB", "Electronics", 109.99),
    ("Laptop Stand", "Office", 45.99),
    ("Gaming Mouse", "Gaming", 59.99),
    ("Bluetooth Speaker", "Audio", 99.99),
    ("Smart Thermostat", "Smart Home", 179.99),
    ("Action Camera", "Photography", 249.99),
]

ORDER_STATUSES = ["pending", "shipped", "delivered", "returned", "cancelled"]
ORDER_WEIGHTS = [20, 20, 40, 10, 10]

PAYMENT_METHODS = ["credit_card", "paypal", "apple_pay", "bank_transfer"]
SHIPPING_CARRIERS = ["FedEx", "UPS", "USPS", "DHL"]
REFUND_REASONS = ["Defective", "Wrong item", "Changed mind", "Not as described"]
TICKET_SUBJECTS = [
    "Product defective", "Shipping delay", "Missing accessory", "Payment issue",
    "Return status question", "Wrong item received", "Warranty claim",
    "Product compatibility question", "Account access issue", "Request refund",
    "Order not delivered", "Discount not applied",
]
TICKET_DESCRIPTIONS = [
    "I would like to return this item and get my money back.",
    "I ordered last week and it still has not arrived.",
    "I returned an item but have not received a refund.",
    "Will this work with my current setup?",
    "The device stopped working after two days.",
    "My credit card was charged twice.",
    "I need to claim the warranty for this product.",
    "My order was supposed to arrive yesterday.",
    "The box contained a different model than what I ordered.",
    "I cannot log in to my account.",
    "The promo code did not work at checkout.",
    "The charger was missing from the package.",
]
ACCOUNT_NOTES = [
    "VIP customer, prioritize handling.",
    "Called support on 2026-01-10 about shipping.",
    "Requested email preference update.",
    "Has had two previous returns.",
    "Eligible for loyalty program tier 2.",
    "Prefers contact via email.",
    "Account created from referral program.",
]
LOYALTY_TIERS = ["bronze", "silver", "gold", "platinum"]
REGIONS = ["North", "South", "East", "West", "Central"]
ACCOUNT_STATUSES = ["active", "inactive"]
PREFERRED_CONTACT = ["email", "email", "phone", "chat", "sms"]
SIGNUP_SOURCES = ["organic", "referral", "paid_ad", "partner", "event"]


def _sql_str(value: str) -> str:
    return value.replace("'", "''")


def _random_date(days_back: int = 365) -> datetime:
    now = datetime.now(tz=timezone.utc)
    delta = timedelta(seconds=random.randint(0, days_back * 24 * 3600))
    return now - delta


def _date_str(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def generate_customers(count: int) -> list[dict]:
    customers = []
    for i in range(count):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[i % len(LAST_NAMES)]
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        created = _random_date(400)
        customers.append({
            "id": i + 1,
            "name": name,
            "email": email,
            "created_at": created,
            "loyalty_tier": random.choices(LOYALTY_TIERS, weights=[30, 35, 25, 10])[0],
            "region": REGIONS[i % len(REGIONS)],
            "account_status": random.choices(ACCOUNT_STATUSES, weights=[80, 20])[0],
            "preferred_contact": random.choices(PREFERRED_CONTACT, weights=[50, 20, 15, 10, 5])[0],
            "signup_source": random.choices(SIGNUP_SOURCES, weights=[40, 20, 20, 10, 10])[0],
        })
    return customers


def generate_products() -> list[dict]:
    products = []
    for idx, (name, category, price) in enumerate(PRODUCT_CATALOG, start=1):
        products.append({
            "id": idx,
            "name": name,
            "category": category,
            "price": round(price, 2),
            "stock_quantity": random.randint(10, 500),
        })
    return products


def generate_orders(customers: list[dict], products: list[dict]) -> tuple[list[dict], list[dict]]:
    orders = []
    order_items = []
    order_id = 0
    for customer in customers:
        num_orders = random.choices([1, 2, 3, 4], weights=[30, 40, 20, 10])[0]
        for _ in range(num_orders):
            order_id += 1
            status = random.choices(ORDER_STATUSES, weights=ORDER_WEIGHTS)[0]
            created = _random_date(365)
            num_items = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
            chosen_products = random.sample(products, k=num_items)
            total = 0.0
            for prod in chosen_products:
                qty = random.randint(1, 3)
                unit_price = prod["price"]
                line_total = round(qty * unit_price, 2)
                total += line_total
                order_items.append({
                    "order_id": order_id,
                    "product_id": prod["id"],
                    "quantity": qty,
                    "unit_price": unit_price,
                    "line_total": line_total,
                })
            total = round(total, 2)
            first_product = chosen_products[0]["name"]
            orders.append({
                "id": order_id,
                "customer_id": customer["id"],
                "product_name": first_product,
                "status": status,
                "total": total,
                "created_at": created,
            })
    return orders, order_items


def generate_payments(orders: list[dict]) -> list[dict]:
    payments = []
    for order in orders:
        if order["status"] == "cancelled":
            status = "cancelled"
        elif order["status"] == "returned":
            status = "refunded"
        elif order["status"] == "pending":
            status = random.choice(["pending", "completed"])
        else:
            status = "completed"
        method = random.choice(PAYMENT_METHODS)
        created = order["created_at"] + timedelta(hours=random.randint(0, 24))
        payments.append({
            "id": len(payments) + 1,
            "order_id": order["id"],
            "amount": order["total"],
            "method": method,
            "status": status,
            "created_at": created,
        })
    return payments


def generate_shipping(orders: list[dict]) -> list[dict]:
    shipping = []
    for order in orders:
        if order["status"] in ("shipped", "delivered", "returned"):
            carrier = random.choice(SHIPPING_CARRIERS)
            tracking = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789", k=12))
            shipped_at = order["created_at"] + timedelta(days=random.randint(1, 3))
            delivered_at = None
            if order["status"] in ("delivered", "returned"):
                delivered_at = shipped_at + timedelta(days=random.randint(1, 5))
            shipping.append({
                "id": len(shipping) + 1,
                "order_id": order["id"],
                "carrier": carrier,
                "tracking_number": tracking,
                "status": "delivered" if delivered_at else "shipped",
                "shipped_at": shipped_at,
                "delivered_at": delivered_at,
            })
    return shipping


def generate_refunds(orders: list[dict]) -> list[dict]:
    refunds = []
    for order in orders:
        if order["status"] == "returned":
            amount = round(order["total"] * random.uniform(0.8, 1.0), 2)
            created = order["created_at"] + timedelta(days=random.randint(7, 21))
            refunds.append({
                "id": len(refunds) + 1,
                "order_id": order["id"],
                "amount": amount,
                "reason": random.choice(REFUND_REASONS),
                "status": random.choice(["pending", "completed"]),
                "created_at": created,
            })
    return refunds


def generate_support_tickets(customers: list[dict], orders: list[dict]) -> list[dict]:
    tickets = []
    for i in range(80):
        customer = random.choice(customers)
        customer_orders = [o for o in orders if o["customer_id"] == customer["id"]]
        order = random.choice(customer_orders) if customer_orders else None
        subject = random.choice(TICKET_SUBJECTS)
        description = random.choice(TICKET_DESCRIPTIONS)
        status = random.choices(["open", "pending", "resolved"], weights=[35, 35, 30])[0]
        created = _random_date(200)
        tickets.append({
            "id": i + 1,
            "customer_id": customer["id"],
            "order_id": order["id"] if order else None,
            "subject": subject,
            "description": description,
            "status": status,
            "created_at": created,
        })
    return tickets


def generate_account_notes(customers: list[dict]) -> list[dict]:
    notes = []
    for customer in customers:
        if random.random() < 0.4:
            continue
        count = random.randint(1, 3)
        for _ in range(count):
            notes.append({
                "id": len(notes) + 1,
                "customer_id": customer["id"],
                "note": random.choice(ACCOUNT_NOTES),
                "created_at": _random_date(300),
            })
    return notes


def build_sql(
    customers: list[dict],
    products: list[dict],
    orders: list[dict],
    order_items: list[dict],
    payments: list[dict],
    shipping: list[dict],
    refunds: list[dict],
    tickets: list[dict],
    notes: list[dict],
) -> str:
    lines = [
        "-- Dispatch AI seed data",
        "-- Generated automatically by data/generate_seed_data.py; do not hand-edit.",
        "",
        "DROP TABLE IF EXISTS account_notes;",
        "DROP TABLE IF EXISTS support_tickets;",
        "DROP TABLE IF EXISTS refunds;",
        "DROP TABLE IF EXISTS shipping;",
        "DROP TABLE IF EXISTS payments;",
        "DROP TABLE IF EXISTS order_items;",
        "DROP TABLE IF EXISTS orders;",
        "DROP TABLE IF EXISTS products;",
        "DROP TABLE IF EXISTS customers;",
        "",
        "CREATE TABLE customers (",
        "    id SERIAL PRIMARY KEY,",
        "    name VARCHAR(100) NOT NULL,",
        "    email VARCHAR(100) NOT NULL UNIQUE,",
        "    created_at TIMESTAMP DEFAULT NOW(),",
        "    loyalty_tier VARCHAR(50),",
        "    region VARCHAR(50),",
        "    account_status VARCHAR(50),",
        "    preferred_contact VARCHAR(50),",
        "    signup_source VARCHAR(50)",
        ");",
        "",
        "CREATE TABLE products (",
        "    id SERIAL PRIMARY KEY,",
        "    name VARCHAR(200) NOT NULL,",
        "    category VARCHAR(100) NOT NULL,",
        "    price DECIMAL(10,2) NOT NULL,",
        "    stock_quantity INTEGER NOT NULL",
        ");",
        "",
        "CREATE TABLE orders (",
        "    id SERIAL PRIMARY KEY,",
        "    customer_id INTEGER REFERENCES customers(id),",
        "    product_name VARCHAR(200) NOT NULL,",
        "    status VARCHAR(50) NOT NULL,",
        "    total DECIMAL(10,2) NOT NULL,",
        "    created_at TIMESTAMP DEFAULT NOW()",
        ");",
        "",
        "CREATE TABLE order_items (",
        "    id SERIAL PRIMARY KEY,",
        "    order_id INTEGER REFERENCES orders(id),",
        "    product_id INTEGER REFERENCES products(id),",
        "    quantity INTEGER NOT NULL,",
        "    unit_price DECIMAL(10,2) NOT NULL,",
        "    line_total DECIMAL(10,2) NOT NULL",
        ");",
        "",
        "CREATE TABLE payments (",
        "    id SERIAL PRIMARY KEY,",
        "    order_id INTEGER REFERENCES orders(id),",
        "    amount DECIMAL(10,2) NOT NULL,",
        "    method VARCHAR(50) NOT NULL,",
        "    status VARCHAR(50) NOT NULL,",
        "    created_at TIMESTAMP DEFAULT NOW()",
        ");",
        "",
        "CREATE TABLE shipping (",
        "    id SERIAL PRIMARY KEY,",
        "    order_id INTEGER REFERENCES orders(id),",
        "    carrier VARCHAR(100) NOT NULL,",
        "    tracking_number VARCHAR(100) NOT NULL,",
        "    status VARCHAR(50) NOT NULL,",
        "    shipped_at TIMESTAMP,",
        "    delivered_at TIMESTAMP",
        ");",
        "",
        "CREATE TABLE refunds (",
        "    id SERIAL PRIMARY KEY,",
        "    order_id INTEGER REFERENCES orders(id),",
        "    amount DECIMAL(10,2) NOT NULL,",
        "    reason VARCHAR(200),",
        "    status VARCHAR(50) NOT NULL,",
        "    created_at TIMESTAMP DEFAULT NOW()",
        ");",
        "",
        "CREATE TABLE support_tickets (",
        "    id SERIAL PRIMARY KEY,",
        "    customer_id INTEGER REFERENCES customers(id),",
        "    order_id INTEGER REFERENCES orders(id),",
        "    subject VARCHAR(200) NOT NULL,",
        "    description TEXT,",
        "    status VARCHAR(50) NOT NULL,",
        "    created_at TIMESTAMP DEFAULT NOW()",
        ");",
        "",
        "CREATE TABLE account_notes (",
        "    id SERIAL PRIMARY KEY,",
        "    customer_id INTEGER REFERENCES customers(id),",
        "    note TEXT NOT NULL,",
        "    created_at TIMESTAMP DEFAULT NOW()",
        ");",
        "",
    ]

    rows = ",\n    ".join(
        f"('{_sql_str(c['name'])}', '{_sql_str(c['email'])}', '{_date_str(c['created_at'])}', "
        f"'{_sql_str(c['loyalty_tier'])}', '{_sql_str(c['region'])}', "
        f"'{_sql_str(c['account_status'])}', '{_sql_str(c['preferred_contact'])}', "
        f"'{_sql_str(c['signup_source'])}')"
        for c in customers
    )
    lines.append(f"INSERT INTO customers (name, email, created_at, loyalty_tier, region, account_status, preferred_contact, signup_source) VALUES\n    {rows};")
    lines.append("")

    rows = ",\n    ".join(
        f"('{_sql_str(p['name'])}', '{_sql_str(p['category'])}', {p['price']}, {p['stock_quantity']})"
        for p in products
    )
    lines.append(f"INSERT INTO products (name, category, price, stock_quantity) VALUES\n    {rows};")
    lines.append("")

    rows = ",\n    ".join(
        f"({o['customer_id']}, '{_sql_str(o['product_name'])}', '{_sql_str(o['status'])}', {o['total']}, '{_date_str(o['created_at'])}')"
        for o in orders
    )
    lines.append(f"INSERT INTO orders (customer_id, product_name, status, total, created_at) VALUES\n    {rows};")
    lines.append("")

    rows = ",\n    ".join(
        f"({oi['order_id']}, {oi['product_id']}, {oi['quantity']}, {oi['unit_price']}, {oi['line_total']})"
        for oi in order_items
    )
    lines.append(f"INSERT INTO order_items (order_id, product_id, quantity, unit_price, line_total) VALUES\n    {rows};")
    lines.append("")

    rows = ",\n    ".join(
        f"({p['order_id']}, {p['amount']}, '{_sql_str(p['method'])}', '{_sql_str(p['status'])}', '{_date_str(p['created_at'])}')"
        for p in payments
    )
    lines.append(f"INSERT INTO payments (order_id, amount, method, status, created_at) VALUES\n    {rows};")
    lines.append("")

    rows = ",\n    ".join(
        (
            f"({s['order_id']}, '{_sql_str(s['carrier'])}', '{_sql_str(s['tracking_number'])}', "
            f"'{_sql_str(s['status'])}', '{_date_str(s['shipped_at'])}', "
            f"{'NULL' if s['delivered_at'] is None else repr(_date_str(s['delivered_at']))})"
        )
        for s in shipping
    )
    lines.append(f"INSERT INTO shipping (order_id, carrier, tracking_number, status, shipped_at, delivered_at) VALUES\n    {rows};")
    lines.append("")

    rows = ",\n    ".join(
        f"({r['order_id']}, {r['amount']}, '{_sql_str(r['reason'])}', '{_sql_str(r['status'])}', '{_date_str(r['created_at'])}')"
        for r in refunds
    )
    lines.append(f"INSERT INTO refunds (order_id, amount, reason, status, created_at) VALUES\n    {rows};")
    lines.append("")

    rows = ",\n    ".join(
        (
            f"({t['customer_id']}, {t['order_id'] if t['order_id'] else 'NULL'}, "
            f"'{_sql_str(t['subject'])}', '{_sql_str(t['description'])}', '{_sql_str(t['status'])}', '{_date_str(t['created_at'])}')"
        )
        for t in tickets
    )
    lines.append(f"INSERT INTO support_tickets (customer_id, order_id, subject, description, status, created_at) VALUES\n    {rows};")
    lines.append("")

    rows = ",\n    ".join(
        f"({n['customer_id']}, '{_sql_str(n['note'])}', '{_date_str(n['created_at'])}')"
        for n in notes
    )
    lines.append(f"INSERT INTO account_notes (customer_id, note, created_at) VALUES\n    {rows};")
    lines.append("")

    return "\n".join(lines)


def _add_demo_personas(
    customers: list[dict],
    products: list[dict],
    orders: list[dict],
    order_items: list[dict],
    payments: list[dict],
    shipping: list[dict],
    refunds: list[dict],
    tickets: list[dict],
    notes: list[dict],
) -> None:
    """Inject three hand-crafted demo personas with rich, story-telling histories.

    IDs are assigned sequentially from the current max so SERIAL ids in PostgreSQL
    match the dict ids used for cross-table references.
    """
    now = datetime.now(tz=timezone.utc)

    # Single counters — increment each time, no gaps.
    counters = {
        "oid": max(o["id"] for o in orders) + 1,
        "pid": max(p["id"] for p in payments) + 1,
        "sid": max(s["id"] for s in shipping) + 1,
        "rid": max(r["id"] for r in refunds) + 1,
        "tid": max(t["id"] for t in tickets) + 1,
        "nid": max(n["id"] for n in notes) + 1,
    }

    def _next(key: str) -> int:
        val = counters[key]
        counters[key] += 1
        return val

    def _order(customer_id: int, prod: dict, total: float, days_ago: int, status: str) -> int:
        oid = _next("oid")
        created = now - timedelta(days=days_ago)
        orders.append({"id": oid, "customer_id": customer_id, "product_name": prod["name"],
                       "status": status, "total": total, "created_at": created})
        order_items.append({"order_id": oid, "product_id": prod["id"], "quantity": 1,
                            "unit_price": total, "line_total": total})
        pay_st = "refunded" if status == "returned" else "completed"
        payments.append({"id": _next("pid"), "order_id": oid, "amount": total,
                         "method": "credit_card", "status": pay_st,
                         "created_at": created + timedelta(hours=1)})
        if status in ("shipped", "delivered", "returned"):
            shipped_at = created + timedelta(days=2)
            del_at = (shipped_at + timedelta(days=3)) if status in ("delivered", "returned") else None
            shipping.append({"id": _next("sid"), "order_id": oid, "carrier": "FedEx",
                             "tracking_number": f"DEMO{oid:06d}",
                             "status": "shipped" if status == "shipped" else "delivered",
                             "shipped_at": shipped_at, "delivered_at": del_at})
        if status == "returned":
            refunds.append({"id": _next("rid"), "order_id": oid, "amount": total,
                            "reason": "Not as described", "status": "completed",
                            "created_at": created + timedelta(days=12)})
        return oid

    def _ticket(customer_id: int, order_id: int, subject: str, desc: str, days_ago: int) -> None:
        tickets.append({"id": _next("tid"), "customer_id": customer_id, "order_id": order_id,
                        "subject": subject, "description": desc, "status": "open",
                        "created_at": now - timedelta(days=days_ago)})

    def _note(customer_id: int, note: str, days_ago: int = 0) -> None:
        notes.append({"id": _next("nid"), "customer_id": customer_id, "note": note,
                      "created_at": now - timedelta(days=days_ago)})

    # ── Persona 1: Sarah Chen — Platinum VIP, high spender, open warranty issue
    customers.append({
        "id": 51, "name": "Sarah Chen", "email": "sarah.chen@example.com",
        "created_at": now - timedelta(days=730), "loyalty_tier": "platinum",
        "region": "West", "account_status": "active",
        "preferred_contact": "email", "signup_source": "referral",
    })
    _order(51, products[15], 499.99, 400, "delivered")   # Noise-Canceling Headphones
    _order(51, products[6],  899.99, 200, "delivered")   # Desktop PC
    sarah_oid = _order(51, products[4], 449.99, 14, "delivered")   # 4K Monitor (recent)
    _ticket(51, sarah_oid, "4K Monitor has dead pixels",
            "I received my 4K Monitor two weeks ago and noticed three dead pixels in the center. I would like a replacement.", 10)
    _note(51, "VIP customer — platinum tier, $1,849.97 lifetime spend. Escalate any issues to senior support.", 1)

    # ── Persona 2: Marcus Johnson — Gold tier, chronic issues, churn risk ──────
    customers.append({
        "id": 52, "name": "Marcus Johnson", "email": "marcus.johnson@example.com",
        "created_at": now - timedelta(days=300), "loyalty_tier": "gold",
        "region": "East", "account_status": "active",
        "preferred_contact": "phone", "signup_source": "paid_ad",
    })
    m_oid1 = _order(52, products[21], 119.99, 250, "delivered")  # Mechanical Keyboard
    m_oid2 = _order(52, products[19], 399.99, 120, "delivered")  # VR Headset
    m_oid3 = _order(52, products[0],   59.99,  30, "returned")   # USB-C Hub
    _ticket(52, m_oid1, "Mechanical keyboard keys sticking",
            "Two keys on my keyboard have started sticking after 3 months of normal use.", 60)
    _ticket(52, m_oid2, "VR Headset display flickering",
            "The left eye display flickers intermittently. Very distracting during use.", 25)
    _ticket(52, m_oid3, "Refund not received after 2 weeks",
            "I returned the USB-C Hub over two weeks ago and still have not seen the refund on my account.", 15)
    _note(52, "At-risk customer — 3 open tickets, 1 refund, multiple product complaints. Consider proactive outreach.", 5)

    # ── Persona 3: Emily Torres — New bronze customer, first order in transit ──
    customers.append({
        "id": 53, "name": "Emily Torres", "email": "emily.torres@example.com",
        "created_at": now - timedelta(days=12), "loyalty_tier": "bronze",
        "region": "South", "account_status": "active",
        "preferred_contact": "chat", "signup_source": "organic",
    })
    e_oid = _order(53, products[27], 99.99, 10, "shipped")  # Bluetooth Speaker
    _ticket(53, e_oid, "Where is my order?",
            "I ordered a Bluetooth Speaker 10 days ago and tracking shows it has been in transit for 7 days. When will it arrive?", 2)


def main() -> None:
    customers = generate_customers(50)
    products = generate_products()
    orders, order_items = generate_orders(customers, products)
    payments = generate_payments(orders)
    shipping = generate_shipping(orders)
    refunds = generate_refunds(orders)
    tickets = generate_support_tickets(customers, orders)
    notes = generate_account_notes(customers)

    _add_demo_personas(customers, products, orders, order_items, payments, shipping, refunds, tickets, notes)

    sql = build_sql(customers, products, orders, order_items, payments, shipping, refunds, tickets, notes)
    OUTPUT.write_text(sql, encoding="utf-8")
    print(f"Generated {OUTPUT} with {len(customers)} customers, {len(products)} products, {len(orders)} orders.")


if __name__ == "__main__":
    main()
