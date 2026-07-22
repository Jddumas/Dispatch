"""Generate realistic seed data for the Dispatch AI project."""

import random
from datetime import datetime, timedelta
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent
OUT_FILE = DATA_DIR / "seed_data.sql"

FIRST_NAMES = [
    "Emma", "Liam", "Olivia", "Noah", "Ava", "Ethan", "Sophia", "Mason",
    "Isabella", "William", "Mia", "James", "Charlotte", "Benjamin", "Amelia",
    "Lucas", "Harper", "Henry", "Evelyn", "Alexander", "Abigail", "Michael",
    "Ella", "Daniel", "Scarlett", "Matthew", "Grace", "Jackson", "Chloe",
    "Sebastian", "Lily", "Aiden", "Aria", "David", "Zoey", "Joseph", "Riley",
    "Samuel", "Nora", "Carter", "Hazel", "Owen", "Aubrey", "Wyatt", "Ellie",
    "John", "Stella", "Jack", "Nova", "Luke", "Penelope",
]

LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez",
    "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin",
    "Lee", "Perez", "Thompson", "White", "Harris", "Sanchez", "Clark",
    "Ramirez", "Lewis", "Robinson", "Walker", "Young", "Allen", "King",
    "Wright", "Scott", "Torres", "Nguyen", "Hill", "Flores", "Green",
    "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell", "Mitchell",
    "Carter", "Roberts",
]

PRODUCTS = [
    "Wireless Mouse", "Mechanical Keyboard", "USB-C Hub", "Webcam 1080p",
    "Noise-Canceling Headphones", "Standing Desk", "Ergonomic Chair",
    "27-inch Monitor", "Laptop Stand", "Smartphone Case", "Bluetooth Speaker",
    "Portable Charger", "Smart Watch", "Fitness Tracker", "Tablet Sleeve",
    "External SSD 1TB", "Mesh Wi-Fi Router", "Smart Bulb Kit",
    "Streaming Microphone", "Webcam Ring Light", "Gaming Headset",
    "USB Microphone", "4K Monitor", "Docking Station", "Wireless Charger",
    "Travel Backpack", "Laptop Sleeve", "Desktop PC", "Graphics Tablet",
    "VR Headset",
]

ORDER_STATUSES = ["pending", "shipped", "delivered", "cancelled", "returned"]
TICKET_SUBJECTS = [
    "Order not delivered",
    "Wrong item received",
    "Request refund",
    "Product defective",
    "Missing accessory",
    "Account access issue",
    "Shipping delay",
    "Return status question",
    "Payment issue",
    "Warranty claim",
    "Product compatibility question",
    "Discount not applied",
]
TICKET_DESCRIPTIONS = [
    "I ordered last week and it still has not arrived.",
    "The box contained a different model than what I ordered.",
    "I would like to return this item and get my money back.",
    "The device stopped working after two days.",
    "The charger was missing from the package.",
    "I cannot log in to my account.",
    "My order was supposed to arrive yesterday.",
    "I returned an item but have not received a refund.",
    "My credit card was charged twice.",
    "I need to claim the warranty for this product.",
    "Will this work with my current setup?",
    "The promo code did not work at checkout.",
]
TICKET_STATUSES = ["open", "resolved", "pending"]


def random_timestamp(start: datetime, end: datetime) -> str:
    delta = end - start
    random_seconds = random.randint(0, int(delta.total_seconds()))
    return (start + timedelta(seconds=random_seconds)).strftime("%Y-%m-%d %H:%M:%S")


def generate_seed_data(num_rows: int = 50) -> str:
    start = datetime.now() - timedelta(days=365)
    end = datetime.now()

    lines = [
        "-- Dispatch AI seed data",
        "-- Generated automatically; do not hand-edit.",
        "",
        "DROP TABLE IF EXISTS support_tickets;",
        "DROP TABLE IF EXISTS orders;",
        "DROP TABLE IF EXISTS customers;",
        "",
        "CREATE TABLE customers (",
        "    id SERIAL PRIMARY KEY,",
        "    name VARCHAR(100) NOT NULL,",
        "    email VARCHAR(100) NOT NULL UNIQUE,",
        "    created_at TIMESTAMP DEFAULT NOW()",
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
        "INSERT INTO customers (name, email, created_at) VALUES",
    ]

    customers = []
    for i in range(num_rows):
        first = FIRST_NAMES[i % len(FIRST_NAMES)]
        last = LAST_NAMES[i % len(LAST_NAMES)]
        name = f"{first} {last}"
        email = f"{first.lower()}.{last.lower()}{i}@example.com"
        created_at = random_timestamp(start, end)
        customers.append(f"    ('{name}', '{email}', '{created_at}')")
    lines.append(",\n".join(customers) + ";")

    lines.extend(["", "INSERT INTO orders (customer_id, product_name, status, total, created_at) VALUES"])
    orders = []
    for i in range(num_rows):
        customer_id = random.randint(1, num_rows)
        product = random.choice(PRODUCTS)
        status = random.choice(ORDER_STATUSES)
        total = round(random.uniform(19.99, 999.99), 2)
        created_at = random_timestamp(start, end)
        orders.append(f"    ({customer_id}, '{product}', '{status}', {total}, '{created_at}')")
    lines.append(",\n".join(orders) + ";")

    lines.extend(["", "INSERT INTO support_tickets (customer_id, order_id, subject, description, status, created_at) VALUES"])
    tickets = []
    for i in range(num_rows):
        customer_id = random.randint(1, num_rows)
        order_id = random.randint(1, num_rows)
        subject = random.choice(TICKET_SUBJECTS)
        description = random.choice(TICKET_DESCRIPTIONS)
        status = random.choice(TICKET_STATUSES)
        created_at = random_timestamp(start, end)
        tickets.append(
            f"    ({customer_id}, {order_id}, '{subject}', '{description}', '{status}', '{created_at}')"
        )
    lines.append(",\n".join(tickets) + ";")

    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    sql = generate_seed_data(50)
    OUT_FILE.write_text(sql, encoding="utf-8")
    print(f"Wrote {OUT_FILE}")
