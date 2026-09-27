#!/bin/bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive

APP_DIR=/var/www/trainhub
BACKEND_DIR="${APP_DIR}/backend"
ADMIN_DIR="${APP_DIR}/admin-panel"
REPO_URL=https://github.com/bobojonov-sobirjon/TrainHub.git
SERVER_IP=51.20.92.246
API_PORT=8005
CRED_FILE=/root/trainhub-credentials.txt

echo "==> Packages"
apt-get update -y
apt-get install -y \
  git curl ca-certificates ufw \
  build-essential python3 python3-venv python3-pip python3-dev \
  postgresql postgresql-contrib \
  redis-server \
  nginx \
  nodejs npm

echo "==> System user"
if ! id trainhub >/dev/null 2>&1; then
  useradd --system --home "${APP_DIR}" --shell /usr/sbin/nologin trainhub
fi

echo "==> Clone repo into ${APP_DIR}"
mkdir -p /var/www
if [ -d "${APP_DIR}/.git" ]; then
  git -C "${APP_DIR}" fetch --all
  git -C "${APP_DIR}" reset --hard origin/main
else
  rm -rf "${APP_DIR}"
  git clone --depth 1 "${REPO_URL}" "${APP_DIR}"
fi

echo "==> Secrets"
if [ ! -f "${CRED_FILE}" ]; then
  DB_PASS="$(openssl rand -hex 16)"
  JWT_SECRET="$(openssl rand -hex 32)"
  ADMIN_PASS="$(openssl rand -hex 12)"
  cat > "${CRED_FILE}" <<EOF
DB_NAME=trainhub_db
DB_USER=trainhub
DB_PASS=${DB_PASS}
JWT_SECRET=${JWT_SECRET}
ADMIN_EMAIL=admin@trainhub.local
ADMIN_PASS=${ADMIN_PASS}
API_URL=http://${SERVER_IP}:${API_PORT}
ADMIN_URL=http://${SERVER_IP}
EOF
  chmod 600 "${CRED_FILE}"
fi
# shellcheck disable=SC1090
source "${CRED_FILE}"

echo "==> PostgreSQL user and database"
systemctl enable --now postgresql
sudo -u postgres psql -v ON_ERROR_STOP=1 <<SQL
DO \$\$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${DB_USER}') THEN
    CREATE ROLE ${DB_USER} LOGIN PASSWORD '${DB_PASS}';
  ELSE
    ALTER ROLE ${DB_USER} WITH LOGIN PASSWORD '${DB_PASS}';
  END IF;
END
\$\$;
SELECT 'CREATE DATABASE ${DB_NAME} OWNER ${DB_USER}'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '${DB_NAME}')\gexec
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL

sudo -u postgres psql -v ON_ERROR_STOP=1 -d "${DB_NAME}" <<SQL
GRANT ALL ON SCHEMA public TO ${DB_USER};
ALTER SCHEMA public OWNER TO ${DB_USER};
SQL

echo "==> Redis"
sed -i 's/^bind .*/bind 127.0.0.1 ::1/' /etc/redis/redis.conf
systemctl enable --now redis-server
systemctl restart redis-server

echo "==> Backend .env"
cat > "${BACKEND_DIR}/.env" <<EOF
APP_ENV=production
APP_NAME=TrainHub
APP_DEBUG=false
API_HOST=0.0.0.0
API_PORT=${API_PORT}

DATABASE_URL=postgresql://${DB_USER}:${DB_PASS}@127.0.0.1:5432/${DB_NAME}
DATABASE_SSL=false
REDIS_URL=redis://127.0.0.1:6379/0

JWT_SECRET=${JWT_SECRET}
JWT_ACCESS_EXPIRE_MINUTES=15
JWT_REFRESH_EXPIRE_DAYS=14

STORAGE_BACKEND=local
MEDIA_DIR=media
PUBLIC_BASE_URL=http://${SERVER_IP}:${API_PORT}

APP_ORIGINS=http://${SERVER_IP},http://${SERVER_IP}:${API_PORT}
ADMIN_ORIGINS=http://${SERVER_IP},http://${SERVER_IP}:${API_PORT}

SEED_ADMIN_EMAIL=${ADMIN_EMAIL}
SEED_ADMIN_PASSWORD=${ADMIN_PASS}
EOF
chmod 600 "${BACKEND_DIR}/.env"
mkdir -p "${BACKEND_DIR}/media"

echo "==> Python venv"
if [ ! -x "${BACKEND_DIR}/.venv/bin/python" ]; then
  python3 -m venv "${BACKEND_DIR}/.venv"
fi
"${BACKEND_DIR}/.venv/bin/pip" install --upgrade pip
"${BACKEND_DIR}/.venv/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"

echo "==> Permissions before migrate"
chown -R trainhub:www-data "${APP_DIR}"
chmod 755 /var/www
chmod 750 "${APP_DIR}"

echo "==> Migrations and admin seed"
sudo -u trainhub bash -c "cd '${BACKEND_DIR}' && .venv/bin/python -m app.db.migrate"
sudo -u trainhub bash -c "cd '${BACKEND_DIR}' && .venv/bin/python scripts/seed_admin.py"

echo "==> Admin panel build"
cat > "${ADMIN_DIR}/.env" <<EOF
VITE_API_URL=http://${SERVER_IP}:${API_PORT}
EOF
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

echo "==> Nginx admin + API proxy"
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
chmod 770 "${BACKEND_DIR}/media"
if [ -d "${BACKEND_DIR}/.venv/bin" ]; then
  find "${BACKEND_DIR}/.venv/bin" -type f -exec chmod 750 {} \;
fi
# git hooks / scripts that must execute
chmod 750 "${APP_DIR}/.git/hooks/"* 2>/dev/null || true

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

sleep 2
systemctl --no-pager --full status trainhub-api || true
curl -fsS "http://127.0.0.1:${API_PORT}/health" || true
echo
echo "==> Deploy done"
cat "${CRED_FILE}"
