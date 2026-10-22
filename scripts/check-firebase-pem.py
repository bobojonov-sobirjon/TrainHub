import json
from pathlib import Path

from cryptography.hazmat.primitives.serialization import load_pem_private_key

path = Path("/var/www/trainhub/backend/secrets/firebase-sa.json")
if not path.exists():
    path = Path(__file__).resolve().parents[1] / "backend" / "firebase-sa.json"
info = json.loads(path.read_text(encoding="utf-8"))
key = info.get("private_key", "")
print("path", path)
print("project", info.get("project_id"))
print("len", len(key), "newlines", key.count("\n"))
print("head", repr(key[:35]))
print("tail", repr(key[-35:]))
try:
    load_pem_private_key(key.encode("utf-8"), password=None)
    print("PEM_OK")
except Exception as exc:
    print("PEM_FAIL", type(exc).__name__, str(exc)[:160])
