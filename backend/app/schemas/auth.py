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


class PasswordResetConfirmRequest(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={"examples": [{"token": "reset-token-from-email", "new_password": "NewSecret123!"}]}
    )

    token: str = Field(description="Токен из письма/SMS сброса пароля", examples=["reset-token-from-email"])
    new_password: str = Field(min_length=8, max_length=72, description="Новый пароль", examples=["NewSecret123!"])
