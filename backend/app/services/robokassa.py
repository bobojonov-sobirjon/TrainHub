import hashlib
import hmac
from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from app.core.config import settings

PAYMENT_URL = "https://auth.robokassa.ru/Merchant/Index.aspx"


def format_outsum(amount: Decimal | str | float | int) -> str:
    value = Decimal(str(amount)).quantize(Decimal("0.01"))
    return f"{value:.2f}"


def parse_outsum(raw: str) -> Decimal:
    text = (raw or "").strip().replace(",", ".")
    try:
        return Decimal(text).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("invalid OutSum") from exc


def configured() -> bool:
    login = (settings.robokassa_merchant_login or "").strip()
    password1, password2 = current_passwords()
    return bool(login and password1 and password2)


def current_passwords() -> tuple[str, str]:
    if settings.robokassa_is_test:
        password1 = settings.robokassa_test_password1 or settings.robokassa_password1
        password2 = settings.robokassa_test_password2 or settings.robokassa_password2
    else:
        password1 = settings.robokassa_password1
        password2 = settings.robokassa_password2
    return password1.strip(), password2.strip()


def _hash(payload: str) -> str:
    alg = (settings.robokassa_hash_alg or "md5").strip().lower()
    if alg not in hashlib.algorithms_available:
        alg = "md5"
    return hashlib.new(alg, payload.encode("utf-8")).hexdigest()


def _shp_suffix(extra: dict[str, str] | None) -> str:
    if not extra:
        return ""
    parts = [f"{key}={extra[key]}" for key in sorted(extra) if key.lower().startswith("shp_")]
    return (":" + ":".join(parts)) if parts else ""


def sign_payment(out_sum: str, inv_id: int, extra: dict[str, str] | None = None) -> str:
    password1, _ = current_passwords()
    login = settings.robokassa_merchant_login.strip()
    return _hash(f"{login}:{out_sum}:{inv_id}{_shp_suffix(extra)}:{password1}")


def sign_result(out_sum: str, inv_id: int, extra: dict[str, str] | None = None) -> str:
    _, password2 = current_passwords()
    return _hash(f"{out_sum}:{inv_id}{_shp_suffix(extra)}:{password2}")


def sign_success(out_sum: str, inv_id: int, extra: dict[str, str] | None = None) -> str:
    password1, _ = current_passwords()
    return _hash(f"{out_sum}:{inv_id}{_shp_suffix(extra)}:{password1}")


def signatures_match(expected: str, received: str) -> bool:
    left = (expected or "").strip().lower()
    right = (received or "").strip().lower()
    if not left or not right or len(left) != len(right):
        return False
    return hmac.compare_digest(left, right)


def verify_result(out_sum: str, inv_id: int, signature: str, extra: dict[str, str] | None = None) -> bool:
    return signatures_match(sign_result(out_sum, inv_id, extra), signature)


def verify_success(out_sum: str, inv_id: int, signature: str, extra: dict[str, str] | None = None) -> bool:
    return signatures_match(sign_success(out_sum, inv_id, extra), signature)


def payment_url(
    *,
    out_sum: str,
    inv_id: int,
    description: str,
    email: str | None = None,
    extra: dict[str, str] | None = None,
) -> str:
    params = {
        "MerchantLogin": settings.robokassa_merchant_login.strip(),
        "OutSum": out_sum,
        "InvId": str(inv_id),
        "Description": description[:100],
        "SignatureValue": sign_payment(out_sum, inv_id, extra),
        "Culture": "ru",
        "Encoding": "utf-8",
    }
    if settings.robokassa_is_test:
        params["IsTest"] = "1"
    if email:
        params["Email"] = email
    if extra:
        params.update(extra)
    return f"{PAYMENT_URL}?{urlencode(params)}"
