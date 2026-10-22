import logging

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from app.services import billing as bill

logger = logging.getLogger(__name__)

router = APIRouter()


def _page(title: str, heading: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{title}</title>
  <style>
    body {{ margin:0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
           background:#0f1419; color:#f4f6f8; min-height:100vh; display:flex; align-items:center; justify-content:center; }}
    .card {{ max-width:420px; margin:24px; padding:28px 24px; background:#1a222c; border-radius:16px;
             box-shadow:0 12px 40px rgba(0,0,0,.35); }}
    h1 {{ font-size:22px; margin:0 0 12px; }}
    p {{ margin:0; line-height:1.5; color:#c5ced8; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>{heading}</h1>
    <p>{body}</p>
  </div>
</body>
</html>"""


async def _params(request: Request) -> dict[str, str]:
    data = {key: str(value) for key, value in request.query_params.items()}
    if request.method == "POST":
        form = await request.form()
        data.update({key: str(value) for key, value in form.items()})
    return data


@router.api_route("/pay/success", methods=["GET", "POST"], include_in_schema=False)
async def pay_success(request: Request) -> HTMLResponse:
    params = await _params(request)
    inv_raw = params.get("InvId") or params.get("inv_id") or ""
    extra = f" Номер платежа: {inv_raw}." if inv_raw else ""
    return HTMLResponse(
        _page(
            "TrainHub — оплата",
            "Платёж отправлен",
            "Банк ещё подтверждает оплату. Подписка PRO откроется автоматически после уведомления от Robokassa. "
            f"Можно вернуться в приложение.{extra}",
        )
    )


@router.api_route("/pay/fail", methods=["GET", "POST"], include_in_schema=False)
async def pay_fail(request: Request) -> HTMLResponse:
    params = await _params(request)
    inv_raw = params.get("InvId") or params.get("inv_id") or ""
    if inv_raw.isdigit():
        try:
            await bill.mark_payment_failed(int(inv_raw))
        except Exception:
            logger.exception("pay fail mark pending")
    extra = f" Номер платежа: {inv_raw}." if inv_raw else ""
    return HTMLResponse(
        _page(
            "TrainHub — оплата не прошла",
            "Оплата не завершена",
            f"Средства не списаны или платёж отменён. Откройте приложение и повторите оплату.{extra}",
        )
    )
