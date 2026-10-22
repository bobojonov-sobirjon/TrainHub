from pathlib import Path

p = Path("/etc/nginx/sites-available/trainhub")
text = p.read_text(encoding="utf-8")
if "location /pay/" in text:
    print("nginx_pay_exists")
else:
    block = """    location /pay/ {
        proxy_pass http://127.0.0.1:8005;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

"""
    if "    location /docs {" not in text:
        raise SystemExit("docs block missing")
    p.write_text(text.replace("    location /docs {", block + "    location /docs {", 1), encoding="utf-8")
    print("nginx_pay_added")
