from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_app_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.stage import CheckoutIn, PaymentMethodIn, SubscriptionPatchIn, WebhookMockIn
from app.services import billing as bill

router = APIRouter()


@router.get("/plans", tags=["Shared - Billing"], summary="Тарифы")
async def plans(audience: str | None = None) -> SuccessResponse[list]:
    return SuccessResponse(data=await bill.list_plans(audience))


@router.get("/me/subscription", tags=["Shared - Billing"], summary="Текущая подписка")
async def status(
    user: Annotated[UserPublic, Depends(get_app_user)],
    audience: str | None = None,
) -> SuccessResponse[dict | None]:
    return SuccessResponse(data=await bill.current_subscription(user.id, audience))


@router.post(
    "/me/subscription/checkout",
    tags=["Shared - Billing"],
    summary="Оформить подписку (mock)",
    description="Создаёт mock-оплату по `plan_id` из списка тарифов.",
)
async def checkout(payload: CheckoutIn, user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.checkout_mock(user.id, payload.plan_id))


@router.post(
    "/me/subscription/cancel",
    tags=["Shared - Billing"],
    summary="Отменить автопродление",
    description="Тело запроса не требуется. Подписка действует до конца оплаченного периода.",
)
async def cancel(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.cancel_subscription(user.id))


@router.post(
    "/me/subscription/resume",
    tags=["Shared - Billing"],
    summary="Возобновить автопродление",
    description="Тело запроса не требуется.",
)
async def resume(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.resume_subscription(user.id))


@router.patch(
    "/me/subscription",
    tags=["Shared - Billing"],
    summary="Изменить тариф или автопродление",
    description="`plan_id` — новый тариф (mock checkout). `auto_renew` — вкл/выкл автопродление.",
)
async def patch_subscription(
    payload: SubscriptionPatchIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.patch_subscription(user.id, payload.plan_id, payload.auto_renew))


@router.get("/payments", tags=["Shared - Billing"], summary="История платежей")
async def history(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await bill.payments(user.id))


@router.get("/payments/{payment_id}", tags=["Shared - Billing"], summary="Чек платежа")
async def payment_receipt(
    payment_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.payment_receipt(user.id, payment_id))


@router.post(
    "/payments/{payment_id}/retry",
    tags=["Shared - Billing"],
    summary="Повторить ошибочный платёж",
    description="Только для статуса `failed`. Создаёт новую mock-оплату по тому же тарифу.",
)
async def retry_payment(
    payment_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.retry_payment(user.id, payment_id))


@router.get("/me/payment-methods", tags=["Shared - Billing"], summary="Сохранённые карты")
async def payment_methods(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await bill.list_payment_methods(user.id))


@router.post(
    "/me/payment-methods",
    tags=["Shared - Billing"],
    summary="Добавить карту (mock)",
    description="Сохраняет бренд и последние 4 цифры. Реальный эквайринг не подключён.",
)
async def add_payment_method(
    payload: PaymentMethodIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(
        data=await bill.add_payment_method(user.id, payload.brand, payload.last4, payload.is_default)
    )


@router.delete(
    "/me/payment-methods/{method_id}",
    tags=["Shared - Billing"],
    summary="Удалить карту",
    description="Тело запроса не требуется.",
)
async def delete_payment_method(
    method_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await bill.delete_payment_method(user.id, method_id)
    return SuccessResponse(data={"ok": True})


@router.post(
    "/webhooks/payments/mock",
    tags=["Shared - Billing"],
    summary="Тестовый webhook оплаты",
    description="Тестовое подтверждение платежа. `event_id` должен быть уникальным.",
)
async def webhook(payload: WebhookMockIn) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.webhook_mock(payload.event_id, payload.user_id, payload.plan_id))
