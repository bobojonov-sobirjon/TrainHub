# TrainHub admin panel

Vite + React + TypeScript. Dark / lime tokens from Figma. Talks only to `/api/v1/admin`.

## Auth storage tradeoff

Access + refresh tokens are in `sessionStorage` for this foundation.

- Pros: simple SPA, survives refresh, tab-scoped.
- Cons: XSS can read tokens. Later we should move refresh to `HttpOnly` cookie on the same admin origin.

## Run

```bash
cd admin-panel
cp .env.example .env
npm install
npm run dev
```

Needs backend at `http://127.0.0.1:8000` and a seeded admin user.
