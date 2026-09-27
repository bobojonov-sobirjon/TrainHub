#!/bin/bash
set -euo pipefail
APP=/var/www/trainhub
SRC=/tmp/th-social
cp -f "$SRC/008_social_devices.sql" "$APP/backend/migrations/008_social_devices.sql"
cp -f "$SRC/config.py" "$APP/backend/app/core/config.py"
cp -f "$SRC/constants.py" "$APP/backend/app/core/constants.py"
cp -f "$SRC/auth_schema.py" "$APP/backend/app/schemas/auth.py"
cp -f "$SRC/social.py" "$APP/backend/app/services/social.py"
cp -f "$SRC/devices.py" "$APP/backend/app/services/devices.py"
cp -f "$SRC/auth_api.py" "$APP/backend/app/api/app/auth.py"
cp -f "$SRC/me.py" "$APP/backend/app/api/app/me.py"
cp -f "$SRC/main.py" "$APP/backend/app/main.py"
cp -f "$SRC/requirements.txt" "$APP/backend/requirements.txt"
grep -q TELEGRAM_BOT_TOKEN "$APP/backend/.env" || printf '\nGOOGLE_CLIENT_IDS=\nAPPLE_BUNDLE_IDS=\nTELEGRAM_BOT_TOKEN=\n' >> "$APP/backend/.env"
chown trainhub:www-data "$APP/backend/migrations/008_social_devices.sql" \
  "$APP/backend/app/core/config.py" "$APP/backend/app/core/constants.py" \
  "$APP/backend/app/schemas/auth.py" "$APP/backend/app/services/social.py" \
  "$APP/backend/app/services/devices.py" "$APP/backend/app/api/app/auth.py" \
  "$APP/backend/app/api/app/me.py" "$APP/backend/app/main.py" "$APP/backend/requirements.txt"
chmod 640 "$APP/backend/migrations/008_social_devices.sql" \
  "$APP/backend/app/core/config.py" "$APP/backend/app/core/constants.py" \
  "$APP/backend/app/schemas/auth.py" "$APP/backend/app/services/social.py" \
  "$APP/backend/app/services/devices.py" "$APP/backend/app/api/app/auth.py" \
  "$APP/backend/app/api/app/me.py" "$APP/backend/app/main.py" "$APP/backend/requirements.txt"
sudo -u trainhub bash -c "cd '$APP/backend' && .venv/bin/pip install -q -r requirements.txt && .venv/bin/python -m app.db.migrate"
systemctl restart trainhub-api
sleep 2
systemctl is-active trainhub-api
curl -fsS http://127.0.0.1:8005/openapi.json | python3 -c "import json,sys; p=json.load(sys.stdin)['paths'];
print('google' in str(p));
print([k for k in p if 'google' in k or 'apple' in k or 'telegram' in k or 'devices' in k])"
echo DONE
