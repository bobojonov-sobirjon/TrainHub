from app.core.exceptions import AppError
from app.db.connection import execute, fetch, fetchrow
from app.schemas.stage import FaqIn, LegalIn, TicketIn


async def list_faq(q: str | None, audience: str | None, published_only: bool) -> list[dict]:
    args: list = []
    where = ["TRUE"]
    if published_only:
        where.append("is_published = TRUE")
    if audience:
        args.append(audience)
        where.append(f"(audience = ${len(args)} OR audience = 'all')")
    if q:
        args.append(f"%{q}%")
        where.append(f"(question ILIKE ${len(args)} OR answer ILIKE ${len(args)})")
    rows = await fetch(
        f"""
        SELECT id, slug, question, answer, audience, sort_order, is_published
        FROM faq_articles
        WHERE {" AND ".join(where)}
        ORDER BY sort_order, id
        """,
        *args,
    )
    return [dict(r) for r in rows]


async def get_faq(slug: str) -> dict:
    row = await fetchrow(
        "SELECT id, slug, question, answer, audience FROM faq_articles WHERE slug = $1 AND is_published = TRUE",
        slug,
    )
    if row is None:
        raise AppError("FAQ_NOT_FOUND", "Статья не найдена", http_status=404)
    return dict(row)


async def upsert_faq(payload: FaqIn, faq_id: int | None = None) -> dict:
    if faq_id:
        row = await fetchrow(
            """
            UPDATE faq_articles
            SET slug = $2, question = $3, answer = $4, audience = $5, sort_order = $6, is_published = $7
            WHERE id = $1
            RETURNING id, slug, question, answer, audience, sort_order, is_published
            """,
            faq_id,
            payload.slug,
            payload.question,
            payload.answer,
            payload.audience,
            payload.sort_order,
            payload.is_published,
        )
        if row is None:
            raise AppError("FAQ_NOT_FOUND", "Статья не найдена", http_status=404)
        return dict(row)
    row = await fetchrow(
        """
        INSERT INTO faq_articles (slug, question, answer, audience, sort_order, is_published)
        VALUES ($1,$2,$3,$4,$5,$6)
        RETURNING id, slug, question, answer, audience, sort_order, is_published
        """,
        payload.slug,
        payload.question,
        payload.answer,
        payload.audience,
        payload.sort_order,
        payload.is_published,
    )
    return dict(row)


async def publish_faq(faq_id: int, is_published: bool) -> dict:
    row = await fetchrow(
        "UPDATE faq_articles SET is_published = $2 WHERE id = $1 RETURNING id, slug, is_published",
        faq_id,
        is_published,
    )
    if row is None:
        raise AppError("FAQ_NOT_FOUND", "Статья не найдена", http_status=404)
    return dict(row)


async def get_legal(doc_type: str) -> dict:
    row = await fetchrow(
        "SELECT type, version, body_md, file_url, file_name, published_at FROM legal_documents WHERE type = $1",
        doc_type,
    )
    if row is None:
        raise AppError("LEGAL_NOT_FOUND", "Документ не найден", http_status=404)
    return dict(row)


async def update_legal(doc_type: str, payload: LegalIn) -> dict:
    row = await fetchrow(
        """
        UPDATE legal_documents
        SET body_md = $2, version = $3, file_url = NULL, file_name = NULL, published_at = NOW()
        WHERE type = $1
        RETURNING type, version, body_md, file_url, file_name, published_at
        """,
        doc_type,
        payload.body_md,
        payload.version,
    )
    if row is None:
        raise AppError("LEGAL_NOT_FOUND", "Документ не найден", http_status=404)
    return dict(row)


async def update_legal_file(doc_type: str, *, version: str, file_url: str, file_name: str) -> dict:
    row = await fetchrow(
        """
        UPDATE legal_documents
        SET file_url = $2, file_name = $3, version = $4, published_at = NOW()
        WHERE type = $1
        RETURNING type, version, body_md, file_url, file_name, published_at
        """,
        doc_type,
        file_url,
        file_name,
        version,
    )
    if row is None:
        raise AppError("LEGAL_NOT_FOUND", "Документ не найден", http_status=404)
    return dict(row)


async def create_ticket(user_id: int, payload: TicketIn) -> dict:
    row = await fetchrow(
        """
        INSERT INTO support_tickets (user_id, subject, message)
        VALUES ($1,$2,$3)
        RETURNING id, subject, message, status, created_at
        """,
        user_id,
        payload.subject,
        payload.message,
    )
    return dict(row)


async def my_tickets(user_id: int) -> list[dict]:
    rows = await fetch(
        "SELECT id, subject, message, status, created_at FROM support_tickets WHERE user_id = $1 ORDER BY created_at DESC",
        user_id,
    )
    return [dict(r) for r in rows]


async def admin_tickets() -> list[dict]:
    rows = await fetch(
        """
        SELECT t.id, t.subject, t.message, t.status, t.created_at, u.email, u.first_name
        FROM support_tickets t
        JOIN users u ON u.id = t.user_id
        ORDER BY t.created_at DESC
        """
    )
    return [dict(r) for r in rows]


async def get_faq_admin(faq_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT id, slug, question, answer, audience, sort_order, is_published
        FROM faq_articles WHERE id = $1
        """,
        faq_id,
    )
    if row is None:
        raise AppError("FAQ_NOT_FOUND", "Статья не найдена", http_status=404)
    return dict(row)


async def get_ticket_admin(ticket_id: int) -> dict:
    row = await fetchrow(
        """
        SELECT t.id, t.subject, t.message, t.status, t.created_at,
               u.id AS user_id, u.email, u.first_name, u.last_name, u.public_id
        FROM support_tickets t
        JOIN users u ON u.id = t.user_id
        WHERE t.id = $1
        """,
        ticket_id,
    )
    if row is None:
        raise AppError("TICKET_NOT_FOUND", "Обращение не найдено", http_status=404)
    return dict(row)


async def set_ticket_status(ticket_id: int, status: str) -> dict:
    row = await fetchrow(
        "UPDATE support_tickets SET status = $2 WHERE id = $1 RETURNING id, status",
        ticket_id,
        status,
    )
    if row is None:
        raise AppError("TICKET_NOT_FOUND", "Обращение не найдено", http_status=404)
    return dict(row)
