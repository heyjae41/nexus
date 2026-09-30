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

- `origin` is GitLab at `http://gitlab.ktbc.ai/heyjae/nexus.git`. Jenkins `edu-dev` (DEV-EKS) scans `axs/nexus-fe` and `axs/nexus-be` and fails the pipeline on Critical CVEs; frontend failures have come from Alpine packages in `docker/frontend.Dockerfile`.
- Service access is `Member.access_role` (`user` or `admin` only), separate from the profile role. Admins use the header Admin entry; `/admin` has 권한관리 and 글쓰기.
- Direct curation posts (뉴스레터, 컬럼, 가이드) use source `authored`, store images under `/api/media/authored`, and stay at the front of that category for 24 hours after publish (`AUTHORED_PRIORITY_HOURS`).
- Files under `.cursor/hooks/state/` are local continual-learning hook state, not application source, and should stay uncommitted.
