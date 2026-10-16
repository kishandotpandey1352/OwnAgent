# LLM Studio Frontend

Next.js + TypeScript + Tailwind frontend for the finance inference workspace.

## Setup

```powershell
cd c:\Users\kisha\projects\financial-finetuning\finetuning-finance\frontend
npm install
copy .env.example .env.local
npm run dev
```

Open http://localhost:3000

## Environment

- `NEXT_PUBLIC_API_BASE_URL` points to the FastAPI gateway, usually `http://localhost:8000`
- `NEXT_PUBLIC_USE_MOCK_BACKEND=true` keeps the UI working when the gateway is offline
- Login stores a generic access token locally and forwards it as both `Authorization` and `X-API-Key`

## Notes

- Dashboard covers basic and premium chat workflows.
- Compare shows side-by-side provider output.
- History is stored in browser local storage until the backend adds persistence.