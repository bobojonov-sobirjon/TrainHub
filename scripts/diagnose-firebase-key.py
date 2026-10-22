import base64
import json
import string
from pathlib import Path

info = json.loads((Path(__file__).resolve().parents[1] / "backend" / "firebase-sa.json").read_text(encoding="utf-8"))
key = info["private_key"]
body = (
    key.replace("-----BEGIN PRIVATE KEY-----", "")
    .replace("-----END PRIVATE KEY-----", "")
    .replace("\n", "")
    .strip()
)
allowed = set(string.ascii_letters + string.digits + "+/=")
print("body_len", len(body))
print("bad_chars", sorted(set(body) - allowed))
print("mod4", len(body) % 4)
try:
    raw = base64.b64decode(body, validate=True)
    print("decoded_len", len(raw))
    print("der_head", raw[:8].hex())
except Exception as exc:
    print("b64_fail", type(exc).__name__, str(exc)[:120])
