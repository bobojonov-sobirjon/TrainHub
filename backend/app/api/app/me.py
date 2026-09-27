from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.deps.auth import get_app_user
from app.schemas.auth import DeviceIn
from app.schemas.common import SuccessResponse, UserPublic
from app.schemas.stage import ProfilePatchIn
from app.services import devices as device_svc
from app.services import users as user_svc

router = APIRouter()


@router.get(
    "/me",
    response_model=SuccessResponse[UserPublic],
    tags=["Shared - Profile"],
    summary="Текущий пользователь приложения",
)
async def me(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[UserPublic]:
    return SuccessResponse(data=await user_svc.get_me(user.id))


@router.patch(
    "/me",
    response_model=SuccessResponse[UserPublic],
    tags=["Shared - Profile"],
    summary="Обновить личные данные",
    description="Имя, фамилия, пол, дата рождения, рост и целевой вес. Телефон и email не меняются.",
)
async def patch_me(
    payload: ProfilePatchIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[UserPublic]:
    return SuccessResponse(data=await user_svc.patch_me(user.id, payload))


@router.post(
    "/me/avatar",
    response_model=SuccessResponse[UserPublic],
    tags=["Shared - Profile"],
    summary="Загрузить аватар",
    description="multipart/form-data, поле `file`. JPEG/PNG/WebP.",
)
async def upload_avatar(
    user: Annotated[UserPublic, Depends(get_app_user)],
    file: UploadFile = File(..., description="Изображение профиля"),
) -> SuccessResponse[UserPublic]:
    data = await file.read()
    return SuccessResponse(data=await user_svc.set_avatar(user.id, data, file.filename or "avatar.jpg"))


@router.get(
    "/me/devices",
    tags=["Shared - Profile"],
    summary="Устройства для push",
)
async def list_devices(user: Annotated[UserPublic, Depends(get_app_user)]) -> SuccessResponse[list]:
    return SuccessResponse(data=await device_svc.list_devices(user.id))


@router.post(
    "/me/devices",
    tags=["Shared - Profile"],
    summary="Сохранить push-токен устройства",
    description="Регистрирует FCM token устройства. Один токен — одно устройство. Повторный вызов обновляет `last_seen_at`.",
)
async def upsert_device(
    payload: DeviceIn, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    return SuccessResponse(data=await device_svc.upsert_device(user.id, payload))


@router.delete(
    "/me/devices/{device_id}",
    tags=["Shared - Profile"],
    summary="Удалить устройство",
    description="Тело запроса не требуется. Снимает push-токен с аккаунта.",
)
async def delete_device(
    device_id: int, user: Annotated[UserPublic, Depends(get_app_user)]
) -> SuccessResponse[dict]:
    await device_svc.delete_device(user.id, device_id)
    return SuccessResponse(data={"ok": True})
