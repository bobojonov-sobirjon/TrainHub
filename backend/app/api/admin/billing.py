from typing import Annotated

from fastapi import APIRouter, Depends

from app.deps.auth import get_admin_user
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.pagination import Page, page_args
from app.services import billing as bill

router = APIRouter()


@router.get("/plans", tags=["Admin - Billing"], summary="Тарифы")
async def plans(_user: Annotated[UserPublic, Depends(get_admin_user)], audience: str | None = None) -> SuccessResponse[list]:
    return SuccessResponse(data=await bill.list_plans(audience))


@router.get("/payments", tags=["Admin - Billing"], summary="Все платежи")
async def payments(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await bill.admin_payments(page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/payments/{payment_id}", tags=["Admin - Billing"], summary="Карточка платежа")
async def payment_detail(
    payment_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.admin_payment(payment_id))


@router.get("/subscriptions", tags=["Admin - Billing"], summary="Все подписки")
async def subscriptions(
    _user: Annotated[UserPublic, Depends(get_admin_user)],
    page: int = 1,
    page_size: int = 20,
) -> SuccessResponse[Page[dict]]:
    page, page_size, offset = page_args(page, page_size)
    items, total = await bill.admin_subscriptions(page_size, offset)
    return SuccessResponse(data=Page(items=items, total=total, page=page, page_size=page_size))


@router.get("/subscriptions/{subscription_id}", tags=["Admin - Billing"], summary="Карточка подписки")
async def subscription_detail(
    subscription_id: int, _user: Annotated[UserPublic, Depends(get_admin_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await bill.admin_subscription(subscription_id))
