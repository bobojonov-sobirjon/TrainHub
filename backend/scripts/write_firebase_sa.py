import json
import re
from pathlib import Path

env_path = Path(__file__).resolve().parents[1] / ".env"
out_path = Path(__file__).resolve().parents[1] / "firebase-sa.json"
text = env_path.read_text(encoding="utf-8-sig")
vals: dict[str, str] = {}
for line in text.splitlines():
    if not line.startswith("FIREBASE_") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    vals[key] = value.strip().strip('"').strip("'")
private_key = vals.get("FIREBASE_PRIVATE_KEY", "").replace("\\n", "\n")
private_key = re.sub(r"-{3,}BEGIN PRIVATE KEY-{3,}", "-----BEGIN PRIVATE KEY-----", private_key)
private_key = re.sub(r"-{3,}END PRIVATE KEY-{3,}", "-----END PRIVATE KEY-----", private_key)
if private_key and not private_key.endswith("\n"):
    private_key += "\n"
info = {
    "type": vals.get("FIREBASE_TYPE", "service_account"),
    "project_id": vals.get("FIREBASE_PROJECT_ID", ""),
    "private_key_id": vals.get("FIREBASE_PRIVATE_KEY_ID", ""),
    "private_key": private_key,
    "client_email": vals.get("FIREBASE_CLIENT_EMAIL", ""),
    "client_id": vals.get("FIREBASE_CLIENT_ID", ""),
    "auth_uri": vals.get("FIREBASE_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"),
    "token_uri": vals.get("FIREBASE_TOKEN_URI", "https://oauth2.googleapis.com/token"),
    "auth_provider_x509_cert_url": vals.get("FIREBASE_AUTH_PROVIDER_X509_CERT_URL", ""),
    "client_x509_cert_url": vals.get("FIREBASE_CLIENT_X509_CERT_URL", ""),
    "universe_domain": vals.get("FIREBASE_UNIVERSE_DOMAIN", "googleapis.com"),
}
out_path.write_text(json.dumps(info), encoding="utf-8")
print("project", info["project_id"])
print("email_ok", bool(info["client_email"]))
print("key_begin", private_key.startswith("-----BEGIN PRIVATE KEY-----"))
print("key_end", "-----END PRIVATE KEY-----" in private_key)
print("key_newlines", private_key.count("\n"))
