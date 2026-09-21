from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_app_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.stage import CheckoutIn, WebhookMockIn
from app.services import billing as bill

router = APIRouter()


@router.get("/plans", tags=["App - Billing"], summary="Тарифы")
async def plans(audience: str | None = None) -> SuccessResponse[list]:
    return SuccessResponse(data=await bill.list_plans(audience))


@router.get("/me/subscription", tags=["App - Billing"], summary="Текущая подписка")
async def status(
    user: Annotated[UserPublic, Depends(get_app_user)],
    audience: str | None = None,
) -> SuccessResponse[dict | None]:
    return SuccessResponse(data=await bill.current_subscription(user.id, audience))


@router.post(
    "/me/subscription/checkout",
    tags=["App - Billing"],
    summary="Оформить подписку (mock)",
    description="Создаёт mock-оплату по `plan_id` из списка тарифов.",
)
async def checkout(payload: CheckoutIn, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.checkout_mock(user.id, payload.plan_id))


@router.post(
    "/me/subscription/cancel",
    tags=["App - Billing"],
    summary="Отменить автопродление",
    description="Тело запроса не требуется. Подписка действует до конца оплаченного периода.",
)
async def cancel(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.cancel_subscription(user.id))


@router.post(
    "/me/subscription/resume",
    tags=["App - Billing"],
    summary="Возобновить автопродление",
    description="Тело запроса не требуется.",
)
async def resume(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.resume_subscription(user.id))


@router.get("/payments", tags=["App - Billing"], summary="История платежей")
async def history(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await bill.payments(user.id))


@router.post(
    "/webhooks/payments/mock",
    tags=["App - Billing"],
    summary="Тестовый webhook оплаты",
    description="Тестовое подтверждение платежа. `event_id` должен быть уникальным.",
)
async def webhook(payload: WebhookMockIn) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.webhook_mock(payload.event_id, payload.user_id, payload.plan_id))
