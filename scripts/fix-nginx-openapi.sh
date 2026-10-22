#!/bin/bash
set -euo pipefail
CONF=/etc/nginx/sites-available/trainhub

python3 - <<'PY'
from pathlib import Path
p = Path("/etc/nginx/sites-available/trainhub")
text = p.read_text()
old = """    location /docs {
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
    }"""
new = """    location /docs {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 60s;
    }

    location /redoc {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_read_timeout 60s;
    }

    location /openapi.json {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_buffering off;
        proxy_read_timeout 60s;
    }

    location /health {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
    }

    location /media/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
    }"""
if old not in text:
    raise SystemExit("nginx block not found — abort")
p.write_text(text.replace(old, new, 1))
print("patched")
PY

nginx -t
systemctl reload nginx

python3 - <<'PY'
import json
import urllib.request
raw = urllib.request.urlopen("http://127.0.0.1/openapi.json", timeout=30).read()
json.loads(raw)
print("nginx_openapi_bytes", len(raw), "json_ok")
raw2 = urllib.request.urlopen("http://51.20.92.246/openapi.json", timeout=30).read()
json.loads(raw2)
print("public_openapi_bytes", len(raw2), "json_ok")
PY
echo DONE
