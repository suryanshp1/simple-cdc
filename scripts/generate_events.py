#!/usr/bin/env python3
"""
SimpleCDC Test Event Generator
===============================
Generates random INSERT, UPDATE, DELETE operations on the users and orders
tables to test the CDC pipeline.

Usage:
    python scripts/generate_events.py                 # 20 events, 1/sec
    python scripts/generate_events.py --count 50      # 50 events
    python scripts/generate_events.py --rate 0.2       # 5 events/sec
    python scripts/generate_events.py --burst 10       # 10 events instantly
"""

import argparse
import random
import sys
import time

try:
    import psycopg
except ImportError:
    print("ERROR: psycopg not installed. Run: pip install 'psycopg[binary]'")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Test data pools
# ---------------------------------------------------------------------------
FIRST_NAMES = [
    "Liam", "Olivia", "Noah", "Emma", "Oliver", "Ava", "James", "Sophia",
    "Benjamin", "Isabella", "Lucas", "Mia", "Henry", "Charlotte", "Alexander",
]
LAST_NAMES = [
    "Garcia", "Martinez", "Robinson", "Clark", "Rodriguez", "Lewis", "Lee",
    "Walker", "Hall", "Allen", "Young", "King", "Wright", "Scott", "Torres",
]
ROLES = ["user", "admin", "editor", "viewer"]
PRODUCTS = [
    "PostgreSQL Handbook", "Docker Mastery Course", "Kubernetes Sticker Pack",
    "CDC Platform License", "Monitoring Dashboard", "API Gateway Pro",
    "Redis Cache Module", "GraphQL Toolkit", "CI/CD Pipeline Kit",
    "Cloud Migration Guide",
]
ORDER_STATUSES = ["pending", "processing", "shipped", "completed", "cancelled"]


def random_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def random_email(name: str) -> str:
    slug = name.lower().replace(" ", ".") + str(random.randint(1, 9999))
    return f"{slug}@example.com"


# ---------------------------------------------------------------------------
# Event generators
# ---------------------------------------------------------------------------
def insert_user(cur):
    name = random_name()
    email = random_email(name)
    role = random.choice(ROLES)
    cur.execute(
        "INSERT INTO users (name, email, role) VALUES (%s, %s, %s) RETURNING id",
        (name, email, role),
    )
    uid = cur.fetchone()[0]
    print(f"  INSERT users  id={uid}  name={name}  role={role}")


def update_user(cur):
    cur.execute("SELECT id FROM users ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if not row:
        return insert_user(cur)
    uid = row[0]
    new_role = random.choice(ROLES)
    cur.execute("UPDATE users SET role = %s, updated_at = NOW() WHERE id = %s", (new_role, uid))
    print(f"  UPDATE users  id={uid}  role→{new_role}")


def delete_user(cur):
    cur.execute("SELECT id FROM users WHERE id > 5 ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if not row:
        return insert_user(cur)
    uid = row[0]
    # Remove related orders first
    cur.execute("DELETE FROM orders WHERE user_id = %s", (uid,))
    cur.execute("DELETE FROM users WHERE id = %s", (uid,))
    print(f"  DELETE users  id={uid}")


def insert_order(cur):
    cur.execute("SELECT id FROM users ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if not row:
        insert_user(cur)
        cur.execute("SELECT id FROM users ORDER BY RANDOM() LIMIT 1")
        row = cur.fetchone()
    uid = row[0]
    product = random.choice(PRODUCTS)
    qty = random.randint(1, 10)
    price = round(random.uniform(9.99, 299.99), 2)
    cur.execute(
        "INSERT INTO orders (user_id, product, quantity, price, status) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING id",
        (uid, product, qty, price, "pending"),
    )
    oid = cur.fetchone()[0]
    print(f"  INSERT orders id={oid}  product={product}  price=${price}")


def update_order(cur):
    cur.execute("SELECT id FROM orders ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if not row:
        return insert_order(cur)
    oid = row[0]
    new_status = random.choice(ORDER_STATUSES)
    cur.execute(
        "UPDATE orders SET status = %s, updated_at = NOW() WHERE id = %s",
        (new_status, oid),
    )
    print(f"  UPDATE orders id={oid}  status→{new_status}")


def delete_order(cur):
    cur.execute("SELECT id FROM orders WHERE id > 5 ORDER BY RANDOM() LIMIT 1")
    row = cur.fetchone()
    if not row:
        return insert_order(cur)
    oid = row[0]
    cur.execute("DELETE FROM orders WHERE id = %s", (oid,))
    print(f"  DELETE orders id={oid}")


# Weighted operations: more inserts/updates than deletes
OPERATIONS = [
    insert_user, insert_user, insert_user,
    update_user, update_user,
    delete_user,
    insert_order, insert_order, insert_order,
    update_order, update_order,
    delete_order,
]


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="SimpleCDC test event generator")
    parser.add_argument("--host", default="localhost", help="PostgreSQL host (default: localhost)")
    parser.add_argument("--port", type=int, default=5432, help="PostgreSQL port (default: 5432)")
    parser.add_argument("--user", default="admin", help="DB user (default: admin)")
    parser.add_argument("--password", default="admin", help="DB password (default: admin)")
    parser.add_argument("--dbname", default="app", help="DB name (default: app)")
    parser.add_argument("--count", type=int, default=20, help="Number of events to generate (default: 20)")
    parser.add_argument("--rate", type=float, default=1.0, help="Seconds between events (default: 1.0)")
    parser.add_argument("--burst", type=int, default=0, help="Generate N events instantly, ignore --rate")
    args = parser.parse_args()

    dsn = f"postgresql://{args.user}:{args.password}@{args.host}:{args.port}/{args.dbname}"
    print(f"🔌 Connecting to {args.host}:{args.port}/{args.dbname}")

    try:
        conn = psycopg.connect(dsn, autocommit=True)
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)

    print(f"✅ Connected. Generating {args.count} events...\n")
    cur = conn.cursor()

    for i in range(1, args.count + 1):
        op = random.choice(OPERATIONS)
        print(f"[{i}/{args.count}]", end="")
        try:
            op(cur)
        except Exception as e:
            print(f"  ⚠️  Error: {e}")

        if args.burst == 0 and i < args.count:
            time.sleep(args.rate)

    print(f"\n🎉 Done! Generated {args.count} events.")
    conn.close()


if __name__ == "__main__":
    main()
