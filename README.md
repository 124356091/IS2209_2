# Student Details
Brian MacEneaney (124356091)
Rory O'Kelly (124465506)
Dylan Meagher (124346621)
Keelin Collins (125123055)

# DeployHub

A lightweight integration service that aggregates project data from **PostgreSQL** and the **GitHub API**, exposing a consolidated REST API and dashboard UI.

Built for IS2209 — Integration & CI/CD Group Project.

## Architecture

```
┌──────────┐       ┌──────────────┐       ┌──────────────┐
│  Client   │──────▶│  Flask App   │──────▶│  PostgreSQL  │
│ (Browser/ │       │  (DeployHub) │       │  (Supabase)  │
│  curl)    │◀──────│              │──────▶│              │
└──────────┘       └──────────────┘       └──────────────┘
                          │
                          ▼
                   ┌──────────────┐
                   │  GitHub API  │
                   │  (external)  │
                   └──────────────┘
```

**Integration points:**
1. **PostgreSQL (Supabase)** — stores tracked projects (CRUD)
2. **GitHub REST API** — fetches live repository metadata (stars, forks, issues, language)

The `/api/projects/<id>/details` endpoint consolidates data from both sources.

## Quick Start

### With Docker Compose (recommended)

```bash
cp .env.example .env       # edit with your real values
docker compose up --build
```

App runs at `http://localhost:5000`.

### Without Docker

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env       # edit with your values
flask run
```

Requires a running PostgreSQL instance (see `DATABASE_URL` in `.env`).

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://localhost:5432/deployhub` |
| `GITHUB_TOKEN` | GitHub personal access token (optional, raises rate limit) | — |
| `SECRET_KEY` | Flask secret key | `dev-secret-change-me` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `CACHE_TTL_SECONDS` | GitHub API cache duration | `300` |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Dashboard UI |
| `GET` | `/health` | Health check (JSON) — reports DB & GitHub API status |
| `GET` | `/status` | Status page (HTML) — runtime diagnostics |
| `GET` | `/api/projects` | List all projects |
| `POST` | `/api/projects` | Create a project (`name`, `github_repo` required) |
| `GET` | `/api/projects/<id>` | Get a single project |
| `DELETE` | `/api/projects/<id>` | Delete a project |
| `GET` | `/api/projects/<id>/details` | **Consolidated**: project data + live GitHub info |

### Example Usage

```bash
# Add a project
curl -X POST http://localhost:5000/api/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Flask", "github_repo": "pallets/flask"}'

# Get consolidated details
curl http://localhost:5000/api/projects/1/details

# Health check
curl http://localhost:5000/health
```

## Running Tests

```bash
pip install -r requirements-dev.txt
pytest -v --cov=. --cov-report=term-missing
```

## CI/CD Pipeline

The GitHub Actions workflow (`.github/workflows/ci.yml`) runs on every PR and push to `main`:

1. **Lint** — `ruff check .`
2. **Test** — `pytest` with coverage report
3. **Build & Push** — Docker image built and pushed to GitHub Container Registry (GHCR)

Status checks must pass before PRs can be merged.

## Branching Strategy

- **Trunk-based** with short-lived feature branches
- Feature branches: `feature/<description>`
- Bug fixes: `fix/<description>`
- All changes land via pull request with at least one peer review

## Demo Steps

1. Start the app with `docker compose up --build`
2. Visit `http://localhost:5000/status` to verify dependencies
3. Add a project: `curl -X POST http://localhost:5000/api/projects -H "Content-Type: application/json" -d '{"name": "Flask", "github_repo": "pallets/flask"}'`
4. Visit `http://localhost:5000/` to see the dashboard with live GitHub data
5. Check consolidated data: `curl http://localhost:5000/api/projects/1/details`
6. Health check: `curl http://localhost:5000/health`


