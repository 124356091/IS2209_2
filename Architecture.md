Architecture Note — DeployHub
1. System Overview
DeployHub is a Flask-based web service that allows users to build and manage a personal Pokémon team. The application integrates two distinct data sources: a PostgreSQL database hosted on Supabase, which persists user data, and the PokeAPI, a public REST API which provides live Pokémon statistics. The system exposes both a browser-facing HTML dashboard and a JSON REST API.

2. Context Diagram (ONLY APPEARS NORMAL AS CODE/IN EDITOR VIEW)
                        ┌─────────────────────────────┐
                        │          User                │
                        │  (Browser / curl / Postman)  │
                        └────────────┬────────────────┘
                                     │ HTTP requests
                                     ▼
                        ┌─────────────────────────────┐
                        │        DeployHub             │
                        │       (Flask App)            │
                        │                             │
                        │  app.py        /health      │
                        │  db.py         /status      │
                        │  pokeapi_      /api/pokemon │
                        │  service.py    /            │
                        └────────┬──────────┬─────────┘
                                 │          │
               PostgreSQL        │          │   HTTPS
               (Supabase)        │          │
                                 ▼          ▼
                    ┌────────────────┐   ┌─────────────────┐
                    │   Supabase     │   │    PokeAPI       │
                    │  PostgreSQL    │   │ pokeapi.co/api   │
                    │  (favourites   │   │    /v2/pokemon   │
                    │   table)       │   │                  │
                    └────────────────┘   └─────────────────┘

3. Integration Points
3.1 PostgreSQL — Supabase
The application connects to a cloud-hosted PostgreSQL instance provided by Supabase. The connection is established using the psycopg library (PostgreSQL adapter for Python). The database URL is loaded from an environment variable (DATABASE_URL) following the 12-factor application methodology, meaning no credentials are ever hardcoded in the source code.

On startup, the application automatically creates a favourites table if one does not already exist. This table stores the Pokémon name, an optional nickname, optional notes, and a timestamp for each entry. All database operations (create, read, delete) are handled in db.py, which opens a new connection per request and commits or rolls back transactions as appropriate.

The health of the database connection is exposed at the /health and /status endpoints, where a test query (SELECT 1) is run to confirm reachability.

3.2 PokeAPI — External HTTP API
The PokeAPI (https://pokeapi.co/api/v2) is a free, open, and unauthenticated REST API providing comprehensive Pokémon data. When a user views the dashboard or requests details for a saved Pokémon, the application calls GET /pokemon/{name} on the PokeAPI and extracts the relevant fields: types, base stats (HP, Attack, Defence, Speed), height, weight, and sprite image URLs.

All outbound HTTP calls to the PokeAPI are made through a requests.Session configured with automatic retry logic via urllib3.util.retry.Retry. The session retries up to three times with exponential backoff on 502, 503, and 504 server error responses. Responses are also cached in memory for five minutes using a dictionary keyed by Pokémon name, which reduces redundant API calls and provides a fallback if the API becomes temporarily unavailable — in that case, the last known response is returned rather than an error.

3.3 Consolidated Endpoint
The endpoint GET /api/pokemon/<id>/details demonstrates the core integration of both sources. It first retrieves the saved record from PostgreSQL, then uses the stored Pokémon name to fetch live data from the PokeAPI, and returns both datasets merged into a single JSON response. This is the primary endpoint that satisfies the brief's requirement for a "consolidated endpoint presenting joined/processed results."

4. Application Structure
IS2209_2/
├── app.py                  # Flask routes and application entry point
├── config.py               # Environment variable configuration (12-factor)
├── db.py                   # PostgreSQL operations
├── pokeapi_service.py      # PokeAPI client with retry and caching
├── logging_config.py       # Structured logging with request IDs
├── templates/
│   ├── dashboard.html      # Main UI — Pokémon team view
│   └── status.html         # System diagnostics page
├── static/
│   └── style.css           # Front-end styling
├── tests/
│   ├── conftest.py         # Shared pytest fixtures
│   ├── test_health.py      # Health/status endpoint tests
│   └── test_projects.py    # CRUD and consolidated endpoint tests
├── .github/workflows/
│   └── ci.yml              # GitHub Actions CI pipeline
├── Dockerfile              # Container image definition
├── docker-compose.yaml     # Local development environment
└── .env.example            # Environment variable template

5. Branching Model
The project follows a trunk-based development strategy with short-lived feature branches. The main branch is treated as the production branch and is protected — direct pushes are blocked. All changes must be submitted via a pull request and require at least one peer review before merging.

Feature branches follow the naming convention feature/<description> (e.g. feature/pokeapi-integration). Bug fixes use fix/<description>. Branches are kept short-lived — typically merged within the same working session — to minimise merge conflicts.

Every pull request must pass the CI status check (defined in .github/workflows/ci.yml) before it can be merged. This ensures that no broken code can reach main. Once merged, the branch is deleted to keep the repository clean.

This model was chosen because it encourages frequent integration, reduces the risk of large diverging branches, and aligns with the Agile principle of continuous delivery.

6. CI/CD Pipeline Design
The GitHub Actions workflow (.github/workflows/ci.yml) is triggered on every pull request and every push to main.

Pipeline steps:

Checkout — The repository code is checked out onto the runner
Set up Python 3.11 — The correct runtime is installed
Install dependencies — pip install -r requirements.txt installs all required packages
Build Docker image — docker build -t test-image . confirms the container builds successfully
The pipeline acts as a gate: if the Docker build fails, the PR status check turns red and the merge button is blocked. This prevents broken or unbuildable code from ever reaching main.

Deployment is performed by pushing the built Docker image to GitHub Container Registry (GHCR). The image is tagged with the commit SHA for traceability, allowing any deployed version to be traced back to an exact commit. Environment-specific configuration (database credentials, API tokens) is injected at runtime via environment variables rather than baked into the image, keeping secrets out of the container.

7. Observability
The application implements structured logging throughout. Every log line is formatted to include a timestamp, log level, a short request_id (either generated per-request or passed in via the X-Request-ID header), and the response time in milliseconds. This makes it straightforward to trace a single user request end-to-end in the logs.

Runtime diagnostics are exposed at two endpoints: /health returns a JSON object with the status of each dependency (database and PokeAPI), and /status renders the same information as an HTML page. Both are designed to be checked by a monitoring tool or a team member without needing to inspect the logs.

