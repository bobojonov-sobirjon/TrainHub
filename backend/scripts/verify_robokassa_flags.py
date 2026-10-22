from app.core.config import get_settings

get_settings.cache_clear()
s = get_settings()
print("is_test=" + str(s.robokassa_is_test).lower())
print("login=" + s.robokassa_merchant_login)
print("p1=" + str(bool(s.robokassa_password1.strip())).lower())
print("p2=" + str(bool(s.robokassa_password2.strip())).lower())
print("alg=" + s.robokassa_hash_alg)
