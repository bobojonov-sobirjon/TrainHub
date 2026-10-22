#!/bin/bash
set -euo pipefail
APP=/var/www/trainhub/backend
SRC=/tmp/firebase-sa.json
DEST="${APP}/secrets/firebase-sa.json"
ENV="${APP}/.env"

if [ ! -f "${SRC}" ]; then
  echo "missing ${SRC}"
  exit 1
fi

mkdir -p "${APP}/secrets"
mv "${SRC}" "${DEST}"
chown -R trainhub:www-data "${APP}/secrets"
chmod 700 "${APP}/secrets"
chmod 600 "${DEST}"

python3 - <<'PY'
from pathlib import Path
path = Path("/var/www/trainhub/backend/.env")
line = "FIREBASE_CREDENTIALS_FILE=/var/www/trainhub/backend/secrets/firebase-sa.json"
text = path.read_text(encoding="utf-8") if path.exists() else ""
lines = [ln for ln in text.splitlines() if not ln.startswith("FIREBASE_CREDENTIALS_FILE=")]
lines.append(line)
path.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("credentials_file_set")
PY
chown trainhub:www-data "${ENV}"
chmod 600 "${ENV}"

systemctl restart trainhub-api
sleep 4
systemctl is-active trainhub-api
curl -fsS http://127.0.0.1:8005/health
echo

sudo -u trainhub "${APP}/.venv/bin/python" -c "from app.core.config import get_settings; get_settings.cache_clear(); from app.core.config import settings; from app.services.firebase import init_firebase; print('project', settings.firebase_project_id); print('file_set', bool(settings.firebase_credentials_file)); print('init', init_firebase())"
echo DONE
