# AI Conversation Copilot — PR007

> A real-time, objective-aware AI assistant for meetings, sales calls, negotiations, and support conversations.

## Features (MVP — Sprints 1–3)

- 🎯 **Objective-aware sessions** — define your goal, audience, tone, and constraints before every conversation
- 📝 **Transcript input** — paste full transcripts or type manual notes
- 💡 **AI insights** — key points, questions, objections, risks, decisions, commitments, action items (powered by Groq / OpenAI)
- 📋 **Action item tracker** — editable to-do list with owners and due dates
- 📄 **Auto-generated summaries** — decisions, unresolved questions, follow-up email drafts
- 🎛️ **Objective coverage meter** — visual indicator of goal alignment
- 🔒 **Privacy by design** — audio off by default, session isolation, JWT auth, no API keys in frontend

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | HTML5, CSS3, Vanilla JS (ES Modules) |
| Backend API | Python 3.12+, FastAPI, Pydantic |
| Database | SQLite (dev) / PostgreSQL (prod) |
| ORM | SQLAlchemy 2.x (async) |
| AI Provider | Groq (llama-3.3-70b-versatile) / OpenAI |
| Auth | JWT (python-jose) + bcrypt |
| Deployment | Docker + Docker Compose |

## Quick Start (Local)

### 1. Clone and set up environment

```bash
cd pr007-conversation-copilot
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

### 2. Create Python virtual environment

```bash
cd backend
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install -r requirements.txt
```

### 3. Install aiosqlite (for SQLite dev mode)

```bash
pip install aiosqlite
```

### 4. Run the server

```bash
# From inside /backend:
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open **http://localhost:8000** in your browser.

The database (`copilot.db`) is auto-created on first run.

### 5. Run tests

```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

## Docker (Production)

```bash
# Copy and edit .env
cp .env.example .env
# Add GROQ_API_KEY and set POSTGRES_PASSWORD

docker-compose up --build
```

Open **http://localhost:8000**.

## Project Structure

```
pr007-conversation-copilot/
├── frontend/
│   ├── index.html          # Login / Register
│   ├── dashboard.html      # Session list + new session modal
│   ├── session.html        # Live session workspace
│   ├── css/
│   │   ├── base.css        # Design system + tokens
│   │   ├── components.css  # Dashboard components
│   │   └── session.css     # Session workspace
│   └── js/
│       ├── api.js          # Backend API client
│       └── components/
│           └── ui.js       # Toast, modal, helpers
├── backend/
│   ├── app/
│   │   ├── main.py         # FastAPI app + routing
│   │   ├── core/config.py  # Pydantic settings
│   │   ├── api/routes/
│   │   │   ├── auth.py     # Register / login / me
│   │   │   ├── sessions.py # Session CRUD
│   │   │   └── copilot.py  # Transcript, insights, actions, summary
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   ├── services/providers/
│   │   │   └── ai_adapter.py  # Groq / OpenAI adapter
│   │   ├── security/auth.py   # JWT + bcrypt
│   │   └── db/database.py     # Async engine + session
│   ├── tests/test_api.py
│   └── requirements.txt
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Meeting Integrations & Clarivue AI Intelligence Layer

Clarivue operates as an **objective-aware AI intelligence layer alongside existing meeting platforms** — including **Google Meet**, **Zoom**, and **Microsoft Teams**. Clarivue does NOT replace your meeting infrastructure, host video calls, or build custom WebRTC infrastructure.

### 1. Platform Connectors Dashboard (`/integrations`)

- **Honest Connection Statuses**:
  - `Not Connected` — Provider configured on server, but account not authorized.
  - `Configuration Required` — Provider client credentials (`CLIENT_ID` / `CLIENT_SECRET`) missing in backend `.env`.
  - `Connected` — Genuine active connection with authorized account email and sync timestamp.
  - `Sync Error` — Token refresh or authorization error.
  - `Coming Soon` — Feature in development.
- **Provider Capabilities**:
  - **Google Meet**: Browser Companion live caption stream, Workspace transcript sync, Google Calendar meeting linking.
  - **Zoom**: Cloud recording transcript ingestion, Webhook post-meeting sync, Meeting ID validation.
  - **Microsoft Teams**: Azure Entra ID OAuth, Microsoft Graph transcript read (`OnlineMeetings.Read`), deep linking.

### 2. Multi-Option Transcript Import (MVP without external APIs)

Users can analyze conversations immediately without connecting external platform credentials:
- **Option A — Paste Transcript**: Direct dialogue paste with objective selection (Architecture Review, Sales Demo, 1-on-1, etc.) and instant sample loader.
- **Option B — Upload Transcript File**: Supports `.txt`, `.vtt`, `.srt`, `.json`, `.csv`, and `.pdf` files (<10MB) with automatic text and dialogue extraction.
- **Option C — Open Meeting Reference**: URL validation for `meet.google.com`, `zoom.us`, and `teams.microsoft.com` with honest privacy notice explaining that URLs alone do not grant audio access.

### 3. Clarivue AI Intelligence Layer Workspace

Displays grounded, editable conversation outputs:
- **Conversation Insights & Signals**: Key discussion points, important facts, Q&A pairs, risks, and objections with transcript quotes.
- **Smart Response Suggestions**: Proactive reply drafts, follow-ups, objection responses, and next steps with one-click clipboard copy.
- **Decision Ledger**: Verified decisions with supporting transcript excerpts, confirmation status toggle (`CONFIRMED` / `PENDING_REVIEW` / `SUPERSEDED`), and manual entry.
- **Action Items**: Explicit assignees, due dates, priority pills, and completion checkboxes.
- **Meeting Summary**: Executive summary, key points, unresolved questions, and Markdown / JSON export.

### 4. Browser Companion Extension Workflow

For real-time meeting transcription in Google Meet or Zoom web apps:
1. User joins their regular Google Meet or Zoom call in Chrome/Edge.
2. The **Clarivue Browser Companion Extension** captures live captions locally with full participant awareness.
3. Transcripts stream securely to `POST /api/v1/sessions/{id}/transcript`.
4. The Clarivue Intelligence Layer surfaces real-time insights, suggestions, and decisions without WebRTC audio tampering or privacy violations.

---

## API Reference

Interactive docs: `http://localhost:8000/api/docs`

| Method | Route | Description |
|--------|-------|-------------|
| POST | `/api/v1/auth/register` | Create account |
| POST | `/api/v1/auth/login` | Sign in → JWT |
| GET  | `/api/v1/auth/me` | Current user |
| GET  | `/api/v1/integrations` | List platform connectors with honest status |
| POST | `/api/v1/integrations/{provider}/connect` | Connect or configure platform credentials |
| POST | `/api/v1/integrations/{provider}/disconnect` | Disconnect platform connection |
| POST | `/api/v1/transcripts/validate-url` | Validate Google Meet, Zoom, Teams URL |
| POST | `/api/v1/transcripts/upload-file` | Parse TXT, VTT, SRT, JSON, CSV, PDF transcript |
| POST | `/api/v1/transcripts/import` | Ingest transcript dialogue into session |
| POST | `/api/v1/sessions/{id}/analyze` | Run full Clarivue AI Intelligence Layer |
| GET  | `/api/v1/sessions/{id}/decisions` | List decisions in session ledger |
| POST | `/api/v1/sessions/{id}/decisions` | Add decision to ledger |
| PATCH| `/api/v1/sessions/{id}/decisions/{did}` | Update decision status or text |
| POST | `/api/v1/sessions` | Create session |
| GET  | `/api/v1/sessions` | List sessions |
| GET  | `/api/v1/sessions/{id}` | Get session |
| PATCH | `/api/v1/sessions/{id}` | Update session |
| DELETE | `/api/v1/sessions/{id}` | Delete session |
| GET  | `/healthz` | Liveness check |

## Environment Variables

See [`.env.example`](.env.example) for all variables.

Key variables:
- `GROQ_API_KEY` / `AI_API_KEY` — LLM provider API key
- `APP_SECRET_KEY` — long random string for JWT signing
- `DATABASE_URL` — SQLite for dev (`sqlite+aiosqlite:///./copilot.db`), PostgreSQL for prod
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — Google Cloud OAuth credentials
- `ZOOM_CLIENT_ID` / `ZOOM_CLIENT_SECRET` — Zoom App Marketplace credentials
- `MICROSOFT_CLIENT_ID` / `MICROSOFT_CLIENT_SECRET` — Azure Entra ID credentials
- `OAUTH_REDIRECT_BASE_URL` — Base URL for OAuth callbacks

## Testing

Run all 17 backend unit and integration tests:

```bash
cd backend
.venv\Scripts\activate
pytest tests/ -v
```

## Security & Ethics Principles

- **No Covert Recording**: Clarivue never records or taps meetings without host and participant knowledge.
- **Honest Connection States**: Never falsely claim a platform is connected unless verified.
- **Backend Credential Isolation**: Client secrets and tokens remain strictly on the backend and are never sent to browser JavaScript.
- **No Hallucinated Commitments**: Decision and action items strictly reflect verifiable transcript statements.
