# HiSMap

Historical travel journal exploration platform. Processes historical texts (Chinese/Arabic travel writing) through an LLM pipeline and displays extracted entries and locations on an interactive map.

## Architecture

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Pipeline │────▸│ Database │◂────│ Backend  │
│ (Python) │     │(Postgres)│     │ (FastAPI)│
└──────────┘     └──────────┘     └────┬─────┘
                                       │ /api
                                       ▼
                                  ┌──────────┐
                                  │ Frontend │
                                  │ (React)  │
                                  └──────────┘
```

**Pipeline** — 4-stage LLM-powered text processing: ingest (PDF/text/OCR) → segment → extract → store. Handles scanned PDFs via OCR, detects language, and uses LLMs to extract locations, dates, persons, and metadata from historical narratives.

**Backend** — Async FastAPI API with public read endpoints and JWT-protected admin routes. SQLAlchemy + Alembic for database management.

**Frontend** — React + Leaflet interactive map with search, filtering by dynasty/era, and entry detail panels.

## Quick Start

```bash
# Prerequisites: Docker, conda (env: hismap), Node.js

# Start everything
./start.sh

# Or start individually:
cd backend && conda run -n hismap uvicorn app.main:app --reload
cd frontend && npm run dev
```

Backend runs on `:8000`, frontend on `:5173`.

## Pipeline Usage

```bash
cd pipeline
pip install -e ".[dev]"
python -m pipeline.runner path/to/book.pdf
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), Alembic, PostgreSQL
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Leaflet, React Query
- **Pipeline**: Pydantic v2, PyMuPDF, OpenAI-compatible LLM API
