# HiSMap

Historical travel journal exploration platform. Processes historical texts (Chinese/Arabic travel writing) through an LLM pipeline and displays extracted entries and locations on an interactive map.

## Why HiSMap

HiSMap helps readers explore historical travel writing through diverse cultural perspectives, not just a single narrative lens.

It converts long, cross-cultural texts into a map-first, multimedia experience with AI, making it easier to compare viewpoints, follow journeys geographically, and quickly retrieve context while traveling.

## Features

- **4-stage AI pipeline (ingest -> segment -> extract -> output)**: Supports PDF/TXT/MD/RTF/EPUB input, OCR for scanned PDFs, language detection, chapter/story segmentation, and structured extraction of locations, people, dates, summaries, credibility signals, and annotations.
- **Structured storage + reproducible outputs**: Writes extracted stories as JSON artifacts and persists normalized entities (books, authors, entries, locations, relations) into PostgreSQL.
- **Public query API**: FastAPI endpoints for locations, entries, books, authors, search, and filter options, plus static story JSON serving for rich detail views.
- **Admin API with authentication**: JWT-protected CRUD routes for managing books, authors, entries, and locations.
- **Interactive map experience**: Leaflet map with marker clustering, route arrows generated from entry sequences, map focus transitions, and OpenStreetMap deep links.
- **Reader-facing exploration tools**: Full-text and keyword search, dynasty/type/era filters, bilingual toggle (ZH/EN), entry detail panels, location detail layers, and related-location context.

## Use Cases

- **Comparative reading**: Compare how different travel writers describe the same region, route, or event.
- **Geo-guided historical reading**: Follow narratives on the map instead of reading long chapters in isolation.
- **Travel context lookup**: Quickly retrieve background for a location while planning or during a trip.
- **Digital humanities workflows**: Convert long-form historical sources into queryable, reusable datasets.

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

**Pipeline** — 4-stage LLM-powered text processing: ingest (PDF/EPUB/text/OCR) → segment → extract → store. Handles scanned PDFs via OCR, detects language, and uses LLMs to extract locations, dates, persons, and metadata from historical narratives.

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


