-- SimpleCDC: Database initialization script
-- Creates sample tables, CDC events table, publication, and seed data.

-- ============================================================
-- 1. CDC Events table (stores captured change events)
-- ============================================================
CREATE TABLE IF NOT EXISTS cdc_events (
    id UUID PRIMARY KEY,
    table_name TEXT NOT NULL,
    operation TEXT NOT NULL CHECK (operation IN ('INSERT', 'UPDATE', 'DELETE')),
    payload JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_cdc_events_table_name ON cdc_events (table_name);
CREATE INDEX idx_cdc_events_operation ON cdc_events (operation);
CREATE INDEX idx_cdc_events_created_at ON cdc_events (created_at DESC);

-- ============================================================
-- 2. Sample application tables
-- ============================================================
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    role VARCHAR(50) DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Set REPLICA IDENTITY FULL so UPDATE/DELETE events include all columns
ALTER TABLE users REPLICA IDENTITY FULL;

CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    product VARCHAR(200) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price NUMERIC(10, 2) NOT NULL,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

ALTER TABLE orders REPLICA IDENTITY FULL;

-- ============================================================
-- 3. Logical replication publication
--    Publishes only application tables, NOT cdc_events
-- ============================================================
CREATE PUBLICATION simplecdc_pub FOR TABLE users, orders;

-- ============================================================
-- 4. Seed data
-- ============================================================
INSERT INTO users (name, email, role) VALUES
    ('Alice Johnson', 'alice@example.com', 'admin'),
    ('Bob Smith', 'bob@example.com', 'user'),
    ('Charlie Brown', 'charlie@example.com', 'user'),
    ('Diana Prince', 'diana@example.com', 'editor'),
    ('Eve Wilson', 'eve@example.com', 'user');

INSERT INTO orders (user_id, product, quantity, price, status) VALUES
    (1, 'PostgreSQL Handbook', 2, 49.99, 'completed'),
    (2, 'Docker Mastery Course', 1, 29.99, 'pending'),
    (3, 'Kubernetes Sticker Pack', 5, 9.99, 'shipped'),
    (1, 'CDC Platform License', 1, 199.00, 'completed'),
    (4, 'Monitoring Dashboard', 1, 79.50, 'pending');
