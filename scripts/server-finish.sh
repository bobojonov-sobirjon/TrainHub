#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

APP_DIR=/var/www/trainhub
BACKEND_DIR="${APP_DIR}/backend"
ADMIN_DIR="${APP_DIR}/admin-panel"
SERVER_IP=51.20.92.246
API_PORT=8005
CRED_FILE=/root/trainhub-credentials.txt

chmod 755 /var/www
chown -R trainhub:www-data "${APP_DIR}"
chmod 750 "${APP_DIR}"

echo "==> Migrations and admin seed"
sudo -u trainhub bash -c "cd '${BACKEND_DIR}' && .venv/bin/python -m app.db.migrate"
sudo -u trainhub bash -c "cd '${BACKEND_DIR}' && .venv/bin/python scripts/seed_admin.py"

echo "==> Admin panel build"
# shellcheck disable=SC1090
source "${CRED_FILE}"
cat > "${ADMIN_DIR}/.env" <<EOF
VITE_API_URL=http://${SERVER_IP}:${API_PORT}
EOF
chown trainhub:www-data "${ADMIN_DIR}/.env"
chmod 600 "${ADMIN_DIR}/.env"
sudo -u trainhub bash -c "cd '${ADMIN_DIR}' && npm install && npm run build"
rm -rf "${ADMIN_DIR}/node_modules"

echo "==> systemd"
cat > /etc/systemd/system/trainhub-api.service <<EOF
[Unit]
Description=TrainHub FastAPI
After=network.target postgresql.service redis-server.service
Wants=postgresql.service redis-server.service

[Service]
Type=simple
User=trainhub
Group=www-data
WorkingDirectory=${BACKEND_DIR}
Environment=PATH=${BACKEND_DIR}/.venv/bin:/usr/bin
ExecStart=${BACKEND_DIR}/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT} --workers 1 --proxy-headers --forwarded-allow-ips=127.0.0.1
Restart=always
RestartSec=3
UMask=0027
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo "==> Nginx"
rm -f /etc/nginx/sites-enabled/default
cat > /etc/nginx/sites-available/trainhub <<'NGINX'
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;

    root /var/www/trainhub/admin-panel/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /docs {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
    }

    location /health {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
    }

    location /media/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
    }
}
NGINX
ln -sfn /etc/nginx/sites-available/trainhub /etc/nginx/sites-enabled/trainhub
nginx -t

echo "==> Final permissions"
chown -R trainhub:www-data "${APP_DIR}"
find "${APP_DIR}" -type d -exec chmod 750 {} \;
find "${APP_DIR}" -type f -exec chmod 640 {} \;
chmod 600 "${BACKEND_DIR}/.env"
chmod 600 "${ADMIN_DIR}/.env" 2>/dev/null || true
mkdir -p "${BACKEND_DIR}/media"
chmod 770 "${BACKEND_DIR}/media"
if [ -d "${BACKEND_DIR}/.venv/bin" ]; then
  find "${BACKEND_DIR}/.venv/bin" -type f -exec chmod 750 {} \;
fi

echo "==> Firewall"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 8005/tcp
ufw --force enable

echo "==> Start services"
systemctl daemon-reload
systemctl enable --now trainhub-api
systemctl restart trainhub-api
systemctl restart nginx

sleep 3
systemctl --no-pager --full status trainhub-api || true
curl -fsS "http://127.0.0.1:${API_PORT}/health"
echo
echo "==> Deploy finished. Credentials: ${CRED_FILE}"
