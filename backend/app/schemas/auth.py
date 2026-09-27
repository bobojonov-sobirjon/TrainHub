from datetime import date

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.core.constants import APP_ROLES


class RegisterRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "email": "ivan.petrov@example.com",
                    "phone": "+79991234567",
                    "password": "Secret123!",
                    "role": "client",
                    "gender": "male",
                    "birth_date": "1994-05-12",
                }
            ]
        }
    )

    first_name: str = Field(min_length=1, max_length=80, description="Имя пользователя", examples=["Иван"])
    last_name: str = Field(default="", max_length=80, description="Фамилия", examples=["Петров"])
    email: EmailStr | None = Field(default=None, description="Email. Нужен email или телефон", examples=["ivan.petrov@example.com"])
    phone: str | None = Field(default=None, max_length=20, description="Телефон в международном формате", examples=["+79991234567"])
    password: str = Field(min_length=8, max_length=72, description="Пароль, минимум 8 символов", examples=["Secret123!"])
    role: str = Field(description="Роль: client или trainer", examples=["client"])
    gender: str | None = Field(default=None, description="Пол: male, female, other", examples=["male"])
    birth_date: date | None = Field(default=None, description="Дата рождения YYYY-MM-DD", examples=["1994-05-12"])

    @model_validator(mode="after")
    def validate_register(self) -> "RegisterRequest":
        if self.role not in APP_ROLES:
            raise ValueError("Role must be client or trainer")
        if not self.email and not self.phone:
            raise ValueError("Email or phone is required")
        return self


class LoginRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [{"login": "admin@trainhub.local", "password": "Admin123!"}]
        }
    )

    login: str = Field(min_length=3, max_length=120, description="Email или телефон", examples=["admin@trainhub.local"])
    password: str = Field(min_length=1, max_length=72, description="Пароль", examples=["Admin123!"])


class RefreshRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"}]}
    )

    refresh_token: str = Field(description="Refresh JWT из ответа login/register", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"])


class LogoutRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"}]}
    )

    refresh_token: str = Field(description="Refresh JWT, который нужно отозвать", examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.refresh"])


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"old_password": "Secret123!", "new_password": "NewSecret123!"}]}
    )

    old_password: str = Field(min_length=1, max_length=72, description="Текущий пароль", examples=["Secret123!"])
    new_password: str = Field(min_length=8, max_length=72, description="Новый пароль, минимум 8 символов", examples=["NewSecret123!"])


class PasswordResetRequest(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"login": "ivan.petrov@example.com"}]})

    login: str = Field(min_length=3, max_length=120, description="Email или телефон аккаунта", examples=["ivan.petrov@example.com"])


class GoogleAuthIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6Imdvb2dsZS1pZCIsInR5cCI6IkpXVCJ9", "role": "client"}]}
    )

    id_token: str = Field(
        description="Firebase ID token после Google Sign-In в Firebase Auth, либо native Google ID token",
        examples=["eyJhbGciOiJSUzI1NiIsImtpZCI6ImZpcmViYXNlLWlkIn0"],
    )
    role: str = Field(default="client", description="Роль при первой регистрации: client или trainer", examples=["client"])


class AppleAuthIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "identity_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.apple",
                    "first_name": "Иван",
                    "last_name": "Петров",
                    "role": "client",
                }
            ]
        }
    )

    identity_token: str = Field(
        description="Firebase ID token после Apple Sign-In в Firebase Auth, либо native Apple identity token",
        examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.apple"],
    )
    first_name: str | None = Field(default=None, description="Имя, Apple отдаёт только при первом входе", examples=["Иван"])
    last_name: str | None = Field(default=None, description="Фамилия при первом входе", examples=["Петров"])
    role: str = Field(default="client", description="Роль при первой регистрации: client или trainer", examples=["client"])


class TelegramSendCodeIn(BaseModel):
    model_config = ConfigDict(json_schema_extra={"examples": [{"identifier": "+998901234567"}]})

    identifier: str = Field(
        min_length=3,
        max_length=64,
        description="Телефон (+998…) или Telegram username (john_doe / @john_doe)",
        examples=["+998901234567"],
    )


class TelegramVerifyIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"identifier": "+998901234567", "code": "482193", "role": "client"}]}
    )

    identifier: str = Field(
        min_length=3,
        max_length=64,
        description="Тот же телефон или username, что в send-code",
        examples=["+998901234567"],
    )
    code: str = Field(min_length=4, max_length=8, description="Код из лички Telegram-бота", examples=["482193"])
    role: str = Field(default="client", description="Роль при первой регистрации: client или trainer", examples=["client"])


class DeviceIn(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"platform": "ios", "token": "fcm-device-registration-token", "device_name": "iPhone 15", "app_version": "1.0.0"}]}
    )

    platform: str = Field(description="Платформа: ios, android, web", examples=["ios"])
    token: str = Field(
        min_length=8,
        max_length=4096,
        description="FCM registration token из Firebase Messaging",
        examples=["fcm-device-registration-token"],
    )
    device_name: str | None = Field(default=None, max_length=120, description="Название устройства", examples=["iPhone 15"])
    app_version: str | None = Field(default=None, max_length=40, description="Версия приложения", examples=["1.0.0"])


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"token": "reset-token-from-email", "new_password": "NewSecret123!"}]}
    )

    token: str = Field(description="Токен из письма/SMS сброса пароля", examples=["reset-token-from-email"])
    new_password: str = Field(min_length=8, max_length=72, description="Новый пароль", examples=["NewSecret123!"])
