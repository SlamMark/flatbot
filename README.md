# FlatBot

Telegram bot that monitors Spanish real estate portals (Idealista, Fotocasa, Yaencontre via
[OpenProperties API](https://rapidapi.com/raulport/api/openproperties)) and sends alerts when new
listings match your saved filters.

## Features

- **Multi-portal search** — Idealista, Fotocasa and Yaencontre in one query
- **Flexible filters** — price, rooms, sqm, property type, source, location radius, three-state
  flags (temporal, ocupada, alquiler regulado, nuda propiedad), amenities
- **Telegram alerts** — individual cards for ≤3 matches, batched for larger sets, rate-limited
- **Interactive bot** — manage filters and trigger scans from Telegram without touching the server
- **Web portal** — HTMX-powered dashboard, filter CRUD, manual scan, config view
- **Scheduled scans** — configurable interval (default 30 min) via APScheduler
- **Daily SQLite backups** — automatic, keeps last 7 files
- **Optional portal auth** — cookie-based password protection

---

## Quick start (Docker Compose)

```bash
git clone <repo-url> flatbot && cd flatbot
cp .env.example .env
# Edit .env — fill in RAPIDAPI_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID
docker compose up --build
```

Portal is available at `http://localhost:8000`.

---

## Configuration

Copy `.env.example` to `.env` and fill in the values:

| Variable | Required | Description |
|---|---|---|
| `RAPIDAPI_KEY` | Yes | RapidAPI key for OpenProperties |
| `TELEGRAM_TOKEN` | Yes | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Yes | Your numeric chat ID (restricts bot to this chat) |
| `WEB_SECRET_KEY` | Yes | Random string for signing auth cookies |
| `WEB_PASSWORD` | No | Portal password; leave empty to disable auth |
| `DATABASE_URL` | No | SQLite path (default: `sqlite:////data/flatbot.db`) |
| `SCAN_INTERVAL_MINUTES` | No | Scan frequency in minutes (default: 30) |
| `LOG_LEVEL` | No | `DEBUG` / `INFO` / `WARNING` (default: `INFO`) |
| `MOCK_API` | No | `true` to use fixture data — no API calls (default: `false`) |
| `WEB_API_URL` | No | Bot → web URL (default: `http://web:8000` for Docker) |

---

## Telegram bot commands

| Command | Description |
|---|---|
| `/start`, `/help` | Show command list |
| `/filtros` | List all filters with active/inactive status |
| `/estado` | Active filter count + last scan statistics |
| `/pausar <id>` | Deactivate a filter |
| `/activar <id>` | Activate a filter |
| `/scan` | Trigger a manual scan immediately |
| `/buscar` | Show the 5 most recent matched listings |

---

## Web portal

| Path | Description |
|---|---|
| `/` | Dashboard — scan history, manual trigger |
| `/filters` | Filter list with toggle, duplicate, delete |
| `/filters/new` | Create a new filter |
| `/filters/<id>/edit` | Edit filter + "Probar filtro" live test |
| `/config` | Read-only view of active settings |
| `/login` / `/logout` | Auth (only shown when `WEB_PASSWORD` is set) |

---

## JSON API (used by bot)

| Endpoint | Description |
|---|---|
| `GET /api/status` | Active filters + last scan info |
| `GET /api/filters` | List all filters |
| `POST /api/filters/<id>/activate` | Activate filter |
| `POST /api/filters/<id>/deactivate` | Deactivate filter |
| `POST /api/scan/run` | Run scan, returns `ScanRun` JSON |
| `GET /api/matches/recent?limit=N` | Recent matches with listing detail |

---

## Deployment on Proxmox LXC

### Requirements

- Proxmox LXC with Debian 12 or Ubuntu 22.04
- Privileged container (needed for Docker) **or** use Podman/nerdctl in an unprivileged container

### First-time setup

```bash
# On the LXC host
git clone <repo-url> /opt/flatbot
cd /opt/flatbot
bash deploy/install.sh
```

`install.sh` installs Docker, copies `.env.example` → `.env`, builds images, and starts services.
Edit `/opt/flatbot/.env` before or after running the script and restart:

```bash
docker compose restart
```

### Reverse proxy (optional but recommended)

Expose the portal over HTTPS with nginx:

```nginx
server {
    listen 443 ssl;
    server_name flatbot.example.com;

    ssl_certificate     /etc/ssl/flatbot.crt;
    ssl_certificate_key /etc/ssl/flatbot.key;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Updates

```bash
cd /opt/flatbot
bash deploy/update.sh
```

---

## Development

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
cp .env.example .env   # set MOCK_API=true for offline dev

# Run tests
pytest

# Lint + type-check
ruff check .
mypy flatbot/

# Start web portal locally (uses fixture data when MOCK_API=true)
uvicorn flatbot.web.app:app --reload
```

---

## Architecture

```
flatbot/
  web/          FastAPI portal + JSON API (uvicorn)
    routes/
      dashboard.py   /  and /internal/scan/run
      filters.py     /filters CRUD (HTMX)
      api.py         /api/* JSON endpoints
      config.py      /config
      login.py       /login /logout
    auth.py          Cookie middleware (itsdangerous)
    templates/       Jinja2 + Bootstrap 5 + HTMX
  bot/          Telegram bot (python-telegram-bot 21, polling)
    handlers.py      Command handlers
    api_client.py    Async httpx → web JSON API
    main.py          PTB Application setup
  integrations/
    openproperties/  API client, DTO mapper, query builder
  scanner.py    Scan orchestration (fetch→match→dedup→alert→persist)
  scheduler.py  APScheduler (scan interval + daily backup)
  matching.py   Filter evaluation engine with scoring
  alerts.py     Telegram card formatter and sender
  models.py     SQLAlchemy ORM (Filter, Listing, Match, ScanRun, Setting)
  repos.py      Repository classes
  services/
    backup.py   SQLite hot backup (sqlite3 backup API)
    settings.py DB-stored runtime settings
```
