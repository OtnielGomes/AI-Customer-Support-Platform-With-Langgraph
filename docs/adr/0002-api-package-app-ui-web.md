# FastAPI lives in `app/`; Next.js lives in `web/`

The API package stays `app/` because FastAPI imports and `fastapi dev` expect that name. The UI stays a sibling `web/` because Next.js App Router also requires its own `app/` directory; nesting the frontend inside the Python package would collide (`app/app/`). Alternatives (`backend/`+`frontend/`, `apps/api`+`apps/web`) were rejected as rename churn with no domain gain.

Status: accepted

Considered Options:
- `app/` + `web/` (chosen)
- `backend/` + `frontend/` — breaks `from app...` and every skill/Compose path
- `apps/api` + `apps/web` — extra monorepo machinery for one product
