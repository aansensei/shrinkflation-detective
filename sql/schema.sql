CREATE TABLE IF NOT EXISTS products (
    id         SERIAL PRIMARY KEY,
    kroger_id  VARCHAR(50) UNIQUE NOT NULL,
    name       TEXT NOT NULL,
    brand      TEXT,
    category   TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS snapshots (
    id                SERIAL PRIMARY KEY,
    product_id        INT REFERENCES products(id),
    snapshot_date     DATE NOT NULL,
    price             NUMERIC(8,2),
    weight_raw        TEXT,
    weight_normalized NUMERIC(10,4),
    weight_unit       VARCHAR(10),
    price_per_unit    NUMERIC(10,4),
    created_at        TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_snapshots_product_date
    ON snapshots(product_id, snapshot_date);
