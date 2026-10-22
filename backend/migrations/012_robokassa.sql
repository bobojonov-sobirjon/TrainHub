ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS plan_id BIGINT REFERENCES subscription_plans (id);

ALTER TABLE payments
    ADD COLUMN IF NOT EXISTS provider TEXT NOT NULL DEFAULT 'mock';

UPDATE payments p
SET plan_id = s.plan_id
FROM subscriptions s
WHERE p.subscription_id = s.id
  AND p.plan_id IS NULL;

CREATE INDEX IF NOT EXISTS idx_payments_plan ON payments (plan_id);

UPDATE subscription_plans
SET price_amount = 999, discount_pct = 0
WHERE period = 'month';

UPDATE subscription_plans
SET price_amount = 8990, discount_pct = 25
WHERE period = 'year';
