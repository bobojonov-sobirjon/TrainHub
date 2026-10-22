from pathlib import Path

env_path = Path("/var/www/trainhub/backend/.env")
frag = Path("/tmp/robokassa.env.fragment").read_text(encoding="utf-8")
lines = []
skip_blank_after = False
for ln in env_path.read_text(encoding="utf-8").splitlines():
    if ln.startswith("ROBOKASSA_") or ln.startswith("# Robokassa"):
        skip_blank_after = True
        continue
    if skip_blank_after and not ln.strip():
        continue
    skip_blank_after = False
    lines.append(ln)
text = "\n".join(lines).rstrip() + "\n\n" + frag.strip() + "\n"
env_path.write_text(text, encoding="utf-8")
keys = [x.split("=", 1)[0] for x in text.splitlines() if x.startswith("ROBOKASSA_")]
is_test = next(x.split("=", 1)[1] for x in text.splitlines() if x.startswith("ROBOKASSA_IS_TEST="))
print("env_keys", len(keys))
print("is_test", is_test)
