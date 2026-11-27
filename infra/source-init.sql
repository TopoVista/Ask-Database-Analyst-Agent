CREATE TABLE orders (order_id text PRIMARY KEY, amount_inr numeric(18,2) NOT NULL, status text NOT NULL, channel text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now());
INSERT INTO orders(order_id, amount_inr, status, channel) VALUES ('seed-1', 2100000, 'paid', 'direct'), ('seed-2', 300000, 'paid', 'marketplace');
