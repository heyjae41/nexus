# Repository Guidelines

## Project Structure & Module Organization

NEXUS is a responsive content service with a React/Vite SPA and a FastAPI API.

- `frontend/src/` contains views, reusable components, hooks, styles, and the API client.
- `backend/app/` contains routes, repositories, services, models, configuration, and database/cache code; SQL changes live in `backend/migrations/`.
- `test/backend/`, `test/api/`, and `test/frontend/` hold unit, API, and UI tests. Browser smoke tests are in `test/e2e/`.
- `contents/` stores published HTML source content. `docs/` contains setup, architecture, and design references.

Keep domain logic in the backend service/repository layers and keep React views focused on page composition.

## Build, Test, and Development Commands

```bash
# Backend (Python 3.11+)
pip install -r backend/requirements-dev.txt
PYTHONPATH=backend uvicorn app.main:app --port 8000 --reload
python -m pytest test
ruff check backend test

# Frontend (Node 22+)
cd frontend && npm install
npm run dev       # Vite development server
npm run build     # production bundle
npm test          # Vitest suite
npm run lint      # ESLint for frontend and browser tests
npm run e2e       # Playwright; requires local frontend and backend

# Full local stack
docker compose up -d --build
```

Use `python -m pytest test --cov=backend/app` when changing backend behavior; the project targets 80%+ coverage.

## Coding Style & Naming Conventions

Follow the surrounding code. Python uses four-space indentation, type annotations where helpful, `snake_case` functions/modules, and `PascalCase` classes. React uses ES modules, two-space indentation, `PascalCase.jsx` components/views, and `camelCase` hooks and helpers (for example, `usePagedList.js`). Do not add `console` output; ESLint warns on it. Run Ruff and ESLint before submitting.

## Testing Guidelines

Name Python tests `test_<behavior>` and place them beside the relevant layer; shared fixtures live in `test/conftest.py` and `test/api/conftest.py`. Name frontend tests after the feature, such as `Home.test.jsx`. Test observable behavior, including cache invalidation and API response contracts. Mark tests requiring PostgreSQL or Redis with `@pytest.mark.integration`.

## Commit & Pull Request Guidelines

Use concise, imperative Conventional Commit-style subjects seen in history: `feat: add route titles`, `fix: prevent stale HTML cache`, or `content: add guide`. Keep each commit focused. Pull requests should explain the user-visible change, list validation commands run, link the issue when available, and include screenshots for visual changes. Flag migration, environment-variable, or deployment implications explicitly.

## Security & Configuration

Copy `.env.example` to `.env`; never commit secrets or `.writer_whitelist`. Preserve validation and static-media security headers when modifying ingest, media, or external-content handling.

## Learned Workspace Facts

- `origin` is GitLab at `http://gitlab.ktbc.ai/heyjae/nexus.git`. Jenkins `edu-dev` (DEV-EKS) scans `axs/nexus-fe` and `axs/nexus-be` and fails the pipeline on Critical CVEs; frontend failures have come from Alpine packages in `docker/frontend.Dockerfile`. Change entries such as `Update nexus image to dev_N` are image-tag commits by `jenkins` on `cloud-infra/eks-apps` (`external/nexus/k8s/overlays/dev/kustomization.yaml`), not commits in this repo.
- `SUPER_ADMIN` is a comma-separated nickname list in the environment. Only those accounts open 권한관리 and set `Member.access_role` to `admin`. Role changes stay as a draft until the bottom-right 저장 button is clicked. That flag does not grant writing; writing and image upload require `access_role=admin`, which stays separate from the profile role.
- `members.access_role` comes from `backend/migrations/014_member_access_role.sql`. Seed and `create_all` do not ALTER existing tables, so an existing database needs that migration or login and `/api/me` fail when the column is missing.
- Dev pods do not read the repo `.env` and do not call AWS Secrets Manager (the pod has no AWS credentials, so a direct lookup returns `NoCredentialsError`). Runtime env is injected by ExternalSecret only for mapped keys: `nexus-app-credentials` (ap-northeast-2, including `SUPER_ADMIN`), `nexus-db-credentials` (`DB_USER`/`DB_PASSWORD`), and `nexus-mongodb-credentials`. A secret change needs ExternalSecret sync and a backend pod restart; rebuilding the image does not inject it.
- Direct curation posts (뉴스레터, 컬럼, 가이드) use source `authored` and stay at the front of that category for 24 hours after publish (`AUTHORED_PRIORITY_HOURS`). Only the author can edit one from the article detail; other members and collected posts cannot. Editor images are uploaded with `POST /api/admin/media` (max 5MB; frontend nginx `client_max_body_size` is 6m) and saved HTML keeps only `/api/media/...` paths, including absolute URLs rewritten to that path. Other image URLs are dropped on save.
- `.cursor/` is gitignored local IDE and hook state (including `.cursor/hooks/state/`) and should stay uncommitted.
- Persistent media (editor images under `authored/`, ingest thumbnails under `thumbnails/`) is written only below `settings.media_dir`. Dev pods mount S3 at `/app/media`, and `docker/backend.Dockerfile` pins `MEDIA_DIR=/app/media` because the pod does not read `.env`. Anything that must survive a pod restart goes under that path; the container filesystem elsewhere is ephemeral. Do not use write-then-rename or overwrite-in-place patterns there: the S3 mount rejects renames and overwrites, so writes are new randomly named files (editor images) or content-hash names skipped when present (thumbnails). The image also sets `MEDIA_REQUIRE_MOUNT=true`, so a pod whose `/app/media` is not a mount point refuses to start (`create_app` raises). Thumbnails lost before the mount existed are recreated with `POST /api/internal/media/backfill`; editor images from that period are gone and must be re-uploaded.
