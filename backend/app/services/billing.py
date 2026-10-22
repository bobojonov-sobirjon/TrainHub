import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from app.core.config import settings
from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.db.transactions import transaction
from app.services import robokassa

logger = logging.getLogger(__name__)


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


async def _plan(plan_id: int) -> dict:
    plan = await fetchrow("SELECT * FROM subscription_plans WHERE id = $1 AND is_active = TRUE", plan_id)
    if plan is None:
        raise AppError("PLAN_NOT_FOUND", "Тариф не найден", http_status=404)
    return dict(plan)


def _period_label(period: str) -> str:
    return "1 год" if period == "year" else "1 месяц"


async def checkout(user_id: int, plan_id: int) -> dict:
    if robokassa.configured():
        return await checkout_robokassa(user_id, plan_id)
    return await checkout_mock(user_id, plan_id)


async def checkout_mock(user_id: int, plan_id: int) -> dict:
    plan = await _plan(plan_id)
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
            INSERT INTO payments (user_id, subscription_id, amount, currency, status, provider_event_id, paid_at, provider, plan_id)
            VALUES ($1,$2,$3,$4,'paid',$5,$6,'mock',$7)
            RETURNING id
            """,
            user_id,
            sub["id"],
            plan["price_amount"],
            plan["currency"],
            event_id,
            now,
            plan_id,
        )
    return {
        "subscription_id": sub["id"],
        "payment_id": pay["id"],
        "inv_id": pay["id"],
        "payment_url": None,
        "provider": "mock",
        "status": "active",
        "is_test": True,
        "amount": robokassa.format_outsum(plan["price_amount"]),
        "currency": plan["currency"],
        "plan_id": plan_id,
        "ends_at": ends,
    }


async def checkout_robokassa(user_id: int, plan_id: int) -> dict:
    plan = await _plan(plan_id)
    user = await fetchrow("SELECT email FROM users WHERE id = $1", user_id)
    out_sum = robokassa.format_outsum(plan["price_amount"])
    async with transaction() as conn:
        pay = await conn.fetchrow(
            """
            INSERT INTO payments (user_id, subscription_id, amount, currency, status, provider, plan_id)
            VALUES ($1, NULL, $2, $3, 'pending', 'robokassa', $4)
            RETURNING id
            """,
            user_id,
            plan["price_amount"],
            plan["currency"],
            plan_id,
        )
    inv_id = int(pay["id"])
    url = robokassa.payment_url(
        out_sum=out_sum,
        inv_id=inv_id,
        description=f"TrainHub PRO, {_period_label(plan['period'])}",
        email=(user["email"] if user else None),
    )
    logger.info("robokassa checkout payment_id=%s is_test=%s", inv_id, settings.robokassa_is_test)
    return {
        "subscription_id": None,
        "payment_id": inv_id,
        "inv_id": inv_id,
        "payment_url": url,
        "provider": "robokassa",
        "status": "pending",
        "is_test": settings.robokassa_is_test,
        "amount": out_sum,
        "currency": plan["currency"],
        "plan_id": plan_id,
        "ends_at": None,
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
        SELECT id, amount, currency, status, paid_at, created_at, provider_event_id, provider, plan_id
        FROM payments WHERE user_id = $1
        ORDER BY created_at DESC
        """,
        user_id,
    )
    return [dict(r) for r in rows]


async def mark_payment_failed(payment_id: int) -> None:
    await execute(
        "UPDATE payments SET status = 'failed' WHERE id = $1 AND status = 'pending'",
        payment_id,
    )


async def _activate_paid(conn, payment: dict, plan: dict, event_id: str) -> None:
    now = datetime.now(UTC)
    delta = _period_delta(plan["period"])
    current = await conn.fetchrow(
        """
        SELECT id, status, ends_at FROM subscriptions
        WHERE user_id = $1 AND audience = $2
        ORDER BY created_at DESC
        LIMIT 1
        """,
        payment["user_id"],
        plan["audience"],
    )
    if current and current["status"] == "active" and current["ends_at"] and current["ends_at"] > now:
        ends = current["ends_at"] + delta
        await conn.execute(
            """
            UPDATE subscriptions
            SET plan_id = $1, status = 'active', ends_at = $2, auto_renew = TRUE, cancel_at_period_end = FALSE
            WHERE id = $3
            """,
            plan["id"],
            ends,
            current["id"],
        )
        sub_id = current["id"]
    else:
        ends = now + delta
        row = await conn.fetchrow(
            """
            INSERT INTO subscriptions (user_id, plan_id, audience, status, starts_at, ends_at, auto_renew)
            VALUES ($1,$2,$3,'active',$4,$5, TRUE)
            RETURNING id
            """,
            payment["user_id"],
            plan["id"],
            plan["audience"],
            now,
            ends,
        )
        sub_id = row["id"]
    await conn.execute(
        """
        UPDATE payments
        SET status = 'paid',
            paid_at = $1,
            subscription_id = $2,
            provider_event_id = $3,
            provider = 'robokassa'
        WHERE id = $4
        """,
        now,
        sub_id,
        event_id,
        payment["id"],
    )


async def webhook_robokassa(params: dict[str, str]) -> str:
    out_sum = (params.get("OutSum") or params.get("out_sum") or "").strip()
    inv_raw = (params.get("InvId") or params.get("inv_id") or "").strip()
    signature = (params.get("SignatureValue") or params.get("crc") or "").strip()
    if not out_sum or not inv_raw.isdigit() or not signature:
        return "bad request"
    inv_id = int(inv_raw)
    if not robokassa.configured() or not robokassa.verify_result(out_sum, inv_id, signature, params):
        logger.warning("robokassa bad sign inv_id=%s", inv_id)
        return "bad sign"
    try:
        paid_sum = robokassa.parse_outsum(out_sum)
    except ValueError:
        return "bad sum"

    async with transaction() as conn:
        pay = await conn.fetchrow("SELECT * FROM payments WHERE id = $1 FOR UPDATE", inv_id)
        if pay is None:
            return "not found"
        if pay["status"] == "paid":
            return f"OK{inv_id}"
        expected = Decimal(str(pay["amount"])).quantize(Decimal("0.01"))
        if abs(paid_sum - expected) > Decimal("0.01"):
            logger.warning("robokassa bad sum inv_id=%s got=%s expected=%s", inv_id, paid_sum, expected)
            return "bad sum"
        plan_id = pay["plan_id"]
        if plan_id is None and pay["subscription_id"]:
            sub = await conn.fetchrow("SELECT plan_id FROM subscriptions WHERE id = $1", pay["subscription_id"])
            plan_id = sub["plan_id"] if sub else None
        if plan_id is None:
            return "no plan"
        plan = await conn.fetchrow("SELECT * FROM subscription_plans WHERE id = $1", plan_id)
        if plan is None:
            return "no plan"
        await _activate_paid(conn, dict(pay), dict(plan), f"robokassa:{inv_id}")
    logger.info("robokassa paid inv_id=%s", inv_id)
    return f"OK{inv_id}"


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
               p.provider, p.plan_id,
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
               p.provider_event_id, p.paid_at, p.created_at, p.provider, p.plan_id,
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
               p.subscription_id, p.provider, p.plan_id,
               COALESCE(pl.code, pl2.code) AS plan_code,
               COALESCE(pl.period, pl2.period) AS period
        FROM payments p
        LEFT JOIN subscriptions s ON s.id = p.subscription_id
        LEFT JOIN subscription_plans pl ON pl.id = s.plan_id
        LEFT JOIN subscription_plans pl2 ON pl2.id = p.plan_id
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
        "SELECT id, subscription_id, status, plan_id FROM payments WHERE id = $1 AND user_id = $2",
        payment_id,
        user_id,
    )
    if pay is None:
        raise AppError("PAYMENT_NOT_FOUND", "Платёж не найден", http_status=404)
    if pay["status"] not in {"failed", "pending"}:
        raise AppError("VALIDATION_ERROR", "Повторить можно только незавершённый платёж", http_status=422)
    plan_id = pay["plan_id"]
    if plan_id is None and pay["subscription_id"]:
        sub = await fetchrow(
            "SELECT plan_id FROM subscriptions WHERE id = $1 AND user_id = $2",
            pay["subscription_id"],
            user_id,
        )
        plan_id = sub["plan_id"] if sub else None
    if plan_id is None:
        raise AppError("NO_SUBSCRIPTION", "Тариф платежа не найден", http_status=404)
    if pay["status"] == "pending":
        await mark_payment_failed(payment_id)
    return await checkout(user_id, plan_id)


async def patch_subscription(user_id: int, plan_id: int | None, auto_renew: bool | None) -> dict:
    if plan_id is not None:
        return await checkout(user_id, plan_id)
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
