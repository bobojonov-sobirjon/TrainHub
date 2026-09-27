from datetime import UTC, datetime, timedelta
from uuid import uuid4

from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction


def _period_delta(period: str) -> timedelta:
    return timedelta(days=365) if period == "year" else timedelta(days=30)


async def list_plans(audience: str | None) -> list[dict]:
    if audience:
        rows = await fetch(
            "SELECT id, audience, code, period, price_amount, currency, discount_pct FROM subscription_plans WHERE is_active = TRUE AND audience = $1 ORDER BY period",
            audience,
        )
    else:
        rows = await fetch(
            "SELECT id, audience, code, period, price_amount, currency, discount_pct FROM subscription_plans WHERE is_active = TRUE ORDER BY audience, period"
        )
    return [dict(r) for r in rows]


async def current_subscription(user_id: int, audience: str | None) -> dict | None:
    if audience:
        row = await fetchrow(
            """
            SELECT s.*, p.code, p.period, p.price_amount, p.currency
            FROM subscriptions s
            JOIN subscription_plans p ON p.id = s.plan_id
            WHERE s.user_id = $1 AND s.audience = $2
            ORDER BY s.created_at DESC LIMIT 1
            """,
            user_id,
            audience,
        )
    else:
        row = await fetchrow(
            """
            SELECT s.*, p.code, p.period, p.price_amount, p.currency
            FROM subscriptions s
            JOIN subscription_plans p ON p.id = s.plan_id
            WHERE s.user_id = $1
            ORDER BY s.created_at DESC LIMIT 1
            """,
            user_id,
        )
    return dict(row) if row else None


async def checkout_mock(user_id: int, plan_id: int) -> dict:
    plan = await fetchrow("SELECT * FROM subscription_plans WHERE id = $1 AND is_active = TRUE", plan_id)
    if plan is None:
        raise AppError("PLAN_NOT_FOUND", "Тариф не найден", http_status=404)
    now = datetime.now(UTC)
    ends = now + _period_delta(plan["period"])
    event_id = f"mock_{uuid4().hex}"
    async with transaction() as conn:
        sub = await conn.fetchrow(
            """
            INSERT INTO subscriptions (user_id, plan_id, audience, status, starts_at, ends_at, auto_renew)
            VALUES ($1,$2,$3,'active',$4,$5, TRUE)
            RETURNING id
            """,
            user_id,
            plan_id,
            plan["audience"],
            now,
            ends,
        )
        pay = await conn.fetchrow(
            """
            INSERT INTO payments (user_id, subscription_id, amount, currency, status, provider_event_id, paid_at)
            VALUES ($1,$2,$3,$4,'paid',$5,$6)
            RETURNING id
            """,
            user_id,
            sub["id"],
            plan["price_amount"],
            plan["currency"],
            event_id,
            now,
        )
    return {
        "subscription_id": sub["id"],
        "payment_id": pay["id"],
        "provider": "mock",
        "status": "active",
        "ends_at": ends,
    }


async def cancel_subscription(user_id: int) -> dict:
    sub = await current_subscription(user_id, None)
    if sub is None or sub["status"] != "active":
        raise AppError("NO_ACTIVE_SUBSCRIPTION", "Нет активной подписки", http_status=404)
    await execute(
        """
        UPDATE subscriptions
        SET cancel_at_period_end = TRUE, auto_renew = FALSE, status = 'cancelled'
        WHERE id = $1 AND user_id = $2
        """,
        sub["id"],
        user_id,
    )
    return await current_subscription(user_id, sub["audience"]) or {}


async def resume_subscription(user_id: int) -> dict:
    sub = await current_subscription(user_id, None)
    if sub is None:
        raise AppError("NO_SUBSCRIPTION", "Подписка не найдена", http_status=404)
    await execute(
        """
        UPDATE subscriptions
        SET cancel_at_period_end = FALSE, auto_renew = TRUE, status = 'active'
        WHERE id = $1 AND user_id = $2 AND ends_at > NOW()
        """,
        sub["id"],
        user_id,
    )
    return await current_subscription(user_id, sub["audience"]) or {}


async def payments(user_id: int) -> list[dict]:
    rows = await fetch(
        """
        SELECT id, amount, currency, status, paid_at, created_at, provider_event_id
        FROM payments WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user_id,
    )
    return [dict(r) for r in rows]


async def webhook_mock(event_id: str, user_id: int, plan_id: int) -> dict:
    existing = await fetchrow("SELECT id FROM payments WHERE provider_event_id = $1", event_id)
    if existing:
        return {"ok": True, "duplicate": True, "payment_id": existing["id"]}
    result = await checkout_mock(user_id, plan_id)
    await execute(
        "UPDATE payments SET provider_event_id = $1 WHERE id = $2",
        event_id,
        result["payment_id"],
    )
    result["duplicate"] = False
    return result


async def admin_payments(page_size: int, offset: int) -> tuple[list[dict], int]:
    total = await fetchrow("SELECT COUNT(*) AS total FROM payments")
    rows = await fetch(
        """
        SELECT p.id, p.amount, p.currency, p.status, p.paid_at, p.created_at,
               u.email, u.first_name, u.last_name
        FROM payments p
        JOIN users u ON u.id = p.user_id
        ORDER BY p.created_at DESC
        LIMIT $1 OFFSET $2
        """,
        page_size,
        offset,
    )
    return [dict(r) for r in rows], int(total["total"])


async def admin_subscriptions(page_size: int, offset: int) -> tuple[list[dict], int]:
    total = await fetchrow("SELECT COUNT(*) AS total FROM subscriptions")
    rows = await fetch(
        """
        SELECT s.id, s.audience, s.status, s.starts_at, s.ends_at, s.auto_renew,
               u.email, u.first_name, pl.code
        FROM subscriptions s
        JOIN users u ON u.id = s.user_id
        JOIN subscription_plans pl ON pl.id = s.plan_id
        ORDER BY s.created_at DESC
        LIMIT $1 OFFSET $2
        """,
        page_size,
        offset,
    )
    return [dict(r) for r in rows], int(total["total"])


async def admin_payment(payment_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT p.id, p.user_id, p.subscription_id, p.amount, p.currency, p.status,
               p.provider_event_id, p.paid_at, p.created_at,
               u.email, u.first_name, u.last_name, u.public_id
        FROM payments p
        JOIN users u ON u.id = p.user_id
        WHERE p.id = $1
        """,
        payment_id,
    )
    if row is None:
        raise AppError("PAYMENT_NOT_FOUND", "Платёж не найден", http_status=404)
    return dict(row)


async def admin_subscription(subscription_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT s.id, s.user_id, s.audience, s.status, s.starts_at, s.ends_at,
               s.auto_renew, s.cancel_at_period_end, s.created_at,
               u.email, u.first_name, u.last_name, u.public_id, pl.code, pl.price_amount, pl.currency
        FROM subscriptions s
        JOIN users u ON u.id = s.user_id
        JOIN subscription_plans pl ON pl.id = s.plan_id
        WHERE s.id = $1
        """,
        subscription_id,
    )
    if row is None:
        raise AppError("NO_SUBSCRIPTION", "Подписка не найдена", http_status=404)
    return dict(row)


async def payment_receipt(user_id: int, payment_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT p.id, p.amount, p.currency, p.status, p.paid_at, p.created_at,
               p.subscription_id, pl.code AS plan_code, pl.period
        FROM payments p
        LEFT JOIN subscriptions s ON s.id = p.subscription_id
        LEFT JOIN subscription_plans pl ON pl.id = s.plan_id
        WHERE p.id = $1 AND p.user_id = $2
        """,
        payment_id,
        user_id,
    )
    if row is None:
        raise AppError("PAYMENT_NOT_FOUND", "Платёж не найден", http_status=404)
    return dict(row)


async def retry_payment(user_id: int, payment_id: int) -> dict:
    pay = await fetchrow(
        "SELECT id, subscription_id, status FROM payments WHERE id = $1 AND user_id = $2",
        payment_id,
        user_id,
    )
    if pay is None:
        raise AppError("PAYMENT_NOT_FOUND", "Платёж не найден", http_status=404)
    if pay["status"] != "failed":
        raise AppError("VALIDATION_ERROR", "Повторить можно только ошибочный платёж", http_status=422)
    sub = await fetchrow("SELECT plan_id FROM subscriptions WHERE id = $1 AND user_id = $2", pay["subscription_id"], user_id)
    if sub is None:
        raise AppError("NO_SUBSCRIPTION", "Подписка не найдена", http_status=404)
    return await checkout_mock(user_id, sub["plan_id"])


async def patch_subscription(user_id: int, plan_id: int | None, auto_renew: bool | None) -> dict:
    if plan_id is not None:
        return await checkout_mock(user_id, plan_id)
    sub = await current_subscription(user_id, None)
    if sub is None:
        raise AppError("NO_SUBSCRIPTION", "Подписка не найдена", http_status=404)
    if auto_renew is True:
        return await resume_subscription(user_id)
    if auto_renew is False:
        return await cancel_subscription(user_id)
    return sub


async def list_payment_methods(user_id: int) -> list[dict]:
    rows = await fetch(
        "SELECT id, brand, last4, is_default, created_at FROM payment_methods WHERE user_id = $1 ORDER BY is_default DESC, id DESC",
        user_id,
    )
    return [dict(r) for r in rows]


async def add_payment_method(user_id: int, brand: str, last4: str, is_default: bool) -> dict:
    if is_default:
        await execute("UPDATE payment_methods SET is_default = FALSE WHERE user_id = $1", user_id)
    row = await fetchrow(
        """
        INSERT INTO payment_methods (user_id, brand, last4, is_default)
        VALUES ($1, $2, $3, $4)
        RETURNING id, brand, last4, is_default, created_at
        """,
        user_id,
        brand,
        last4,
        is_default,
    )
    return dict(row)


async def delete_payment_method(user_id: int, method_id: int) -> None:
    row = await fetchrow(
        "DELETE FROM payment_methods WHERE id = $1 AND user_id = $2 RETURNING id",
        method_id,
        user_id,
    )
    if row is None:
        raise AppError("NOT_FOUND", "Способ оплаты не найден", http_status=404)
