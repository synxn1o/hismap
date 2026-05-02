# Frontend Map & Panel Improvements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement frontend map enhancements (colored pins, route arrows, clustering), map-sidebar interactions (auto-focus, auto-filter), and structured content display in EntryDetail.

**Architecture:** Backend serves pipeline output as static files and adds `importance` to `entry_locations`. Frontend adds palette system, map interactions, clustering with importance-based merge logic, and JSON content parsing in EntryDetail.

**Tech Stack:** React 18, Leaflet, react-leaflet, react-leaflet-markercluster, leaflet-polylineDecorator, FastAPI StaticFiles, SQLAlchemy, Alembic

---

## File Structure

### Backend
| File | Action | Responsibility |
|------|--------|----------------|
| `backend/app/main.py` | Modify | Mount static files for pipeline output |
| `backend/app/models/associations.py` | Modify | Add `importance` column to `entry_locations` |
| `backend/alembic/versions/xxx_add_importance.py` | Create | Migration for importance column |
| `pipeline/stages/s4_output.py` | Modify | Write importance to entry_locations |

### Frontend
| File | Action | Responsibility |
|------|--------|----------------|
| `frontend/src/lib/palettes.ts` | Create | Color palette definitions and getBookColor function |
| `frontend/src/api/hooks.ts` | Modify | Add useStoryContent hook |
| `frontend/src/components/Panel/EntryDetail.tsx` | Modify | Fetch and render JSON content |
| `frontend/src/components/Map/MapView.tsx` | Modify | Add focusTarget, clustering, route arrows |
| `frontend/src/components/Map/LocationMarker.tsx` | Modify | Accept color prop |
| `frontend/src/components/Map/MarkerPopup.tsx` | Modify | Change to location filter button |
| `frontend/src/components/Map/RouteArrows.tsx` | Create | Route arrow drawing component |
| `frontend/src/components/Panel/ResultList.tsx` | Modify | Show location filter indicator |
| `frontend/src/App.tsx` | Modify | Add focusTarget, locationFilter state |

---

### Task 1: Backend — Static File Mount

**Files:**
- Modify: `backend/app/main.py:1-52`

- [ ] **Step 1: Add static file mount to main.py**

Add the static file mount after the CORS middleware in `backend/app/main.py`:

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings


def create_app() -> FastAPI:
    app = FastAPI(title=settings.PROJECT_NAME)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Serve pipeline output as static files
    app.mount("/static/output", StaticFiles(directory="../pipeline/output"), name="pipeline-output")

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    # ... rest of file unchanged
```

- [ ] **Step 2: Verify static files are accessible**

Start the backend and test:
```bash
cd backend && conda run -n hismap uvicorn app.main:app --reload
curl -s http://localhost:8000/static/output/ibn_battuta/ibn_battuta_0001_tangier.json | head -5
```
Expected: JSON content of the file

- [ ] **Step 3: Commit**

```bash
git add backend/app/main.py
git commit -m "feat: mount pipeline output as static files"
```

---

### Task 2: Backend — Add Importance Column

**Files:**
- Modify: `backend/app/models/associations.py:1-28`
- Create: `backend/alembic/versions/xxx_add_importance_to_entry_locations.py`

- [ ] **Step 1: Add importance column to associations.py**

Update `backend/app/models/associations.py`:

```python
from sqlalchemy import Column, ForeignKey, Integer, String, Table, Text

from app.core.database import Base

entry_locations = Table(
    "entry_locations",
    Base.metadata,
    Column("entry_id", Integer, ForeignKey("journal_entries.id", ondelete="CASCADE"), primary_key=True),
    Column("location_id", Integer, ForeignKey("locations.id", ondelete="CASCADE"), primary_key=True),
    Column("location_order", Integer, nullable=False, default=0),
    Column("importance", Integer, nullable=False, server_default="0"),
)

# ... rest unchanged
```

- [ ] **Step 2: Generate Alembic migration**

```bash
cd backend && conda run -n hismap alembic revision --autogenerate -m "add importance to entry_locations"
```

- [ ] **Step 3: Verify migration file**

Check the generated migration contains:
```python
op.add_column('entry_locations', sa.Column('importance', sa.Integer(), server_default='0', nullable=False))
```

- [ ] **Step 4: Run migration**

```bash
cd backend && conda run -n hismap alembic upgrade head
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/associations.py backend/alembic/versions/
git commit -m "feat: add importance column to entry_locations"
```

---

### Task 3: Backend — Update Pipeline S4 to Write Importance

**Files:**
- Modify: `pipeline/stages/s4_output.py:120-128`

- [ ] **Step 1: Update entry_locations insert to include importance**

In `pipeline/stages/s4_output.py`, update the loop at line 120:

```python
        for i, loc_data in enumerate(entities.get("locations", [])):
            name = loc_data.get("name", "")
            if name in loc_map:
                # Find importance from annotations
                importance = 0
                for ann in story.annotations or []:
                    if ann.get("marker_title", "").lower().startswith(name.lower()):
                        importance = ann.get("importance", 0)
                        break

                await session.execute(
                    entry_locations.insert().values(
                        entry_id=je.id,
                        location_id=loc_map[name].id,
                        location_order=i,
                        importance=importance,
                    )
                )
```

- [ ] **Step 2: Verify with pipeline test**

```bash
cd pipeline && conda run -n hismap pytest tests/ -k "output" -v -s
```

- [ ] **Step 3: Commit**

```bash
git add pipeline/stages/s4_output.py
git commit -m "feat: write importance to entry_locations in pipeline S4"
```

---

### Task 4: Frontend — Install Dependencies

**Files:**
- Modify: `frontend/package.json`

- [ ] **Step 1: Install markercluster and polyline decorator**

```bash
cd frontend && npm install react-leaflet-markercluster leaflet.markercluster leaflet-polylineDecorator
npm install -D @types/leaflet.markercluster
```

- [ ] **Step 2: Verify installation**

```bash
cd frontend && grep -E "markercluster|polylineDecorator" package.json
```

Expected: entries for `react-leaflet-markercluster`, `leaflet.markercluster`, `leaflet-polylineDecorator`

- [ ] **Step 3: Commit**

```bash
cd frontend && git add package.json package-lock.json
git commit -m "feat: add markercluster and polyline decorator dependencies"
```

---

### Task 5: Frontend — Create Palette System

**Files:**
- Create: `frontend/src/lib/palettes.ts`

- [ ] **Step 1: Create palettes.ts**

```typescript
export const palettes: Record<string, string[]> = {
  warm: [
    "#E63946", "#F4A261", "#2A9D8F", "#264653",
    "#E9C46A", "#606C38", "#DDA15E", "#BC6C25",
  ],
  ocean: [
    "#0077B6", "#00B4D8", "#90E0EF", "#CAF0F8",
    "#023E8A", "#48CAE4", "#ADE8F4", "#03045E",
  ],
  earth: [
    "#6B4226", "#C68642", "#8B6914", "#DAA520",
    "#556B2F", "#8FBC8F", "#B22222", "#CD853F",
  ],
};

export function getBookColor(bookId: number, palette: string[] = palettes.warm): string {
  return palette[bookId % palette.length];
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/palettes.ts
git commit -m "feat: add color palette system for book pins"
```

---

### Task 6: Frontend — Add useStoryContent Hook

**Files:**
- Modify: `frontend/src/api/hooks.ts:1-62`

- [ ] **Step 1: Add StoryContent type and hook**

Add to the end of `frontend/src/api/hooks.ts`:

```typescript
export interface StoryContent {
  id: string;
  title: string;
  original_text: string;
  translations: {
    modern_chinese?: string;
    english?: string;
  };
  entities: {
    locations: Array<{
      name: string;
      modern_name?: string;
      ancient_name?: string;
      lat: number;
      lng: number;
      location_type?: string;
      one_line_summary?: string;
    }>;
    persons: Array<{ name: string; description?: string }>;
    keywords: string[];
  };
  credibility: {
    credibility_score?: number;
    notes?: string;
    era_context?: string;
    political_context?: string;
    religious_context?: string;
    social_environment?: string;
  };
  annotations: Array<{
    importance?: number;
    marker_title?: string;
    short_popup?: string;
    display_category?: string;
  }>;
}

export function useStoryContent(originalText: string | null) {
  return useQuery({
    queryKey: ["storyContent", originalText],
    queryFn: async () => {
      if (!originalText) return null;
      const jsonPath = originalText.replace("pipeline/output/", "");
      const res = await fetch(`/static/output/${jsonPath}`);
      if (!res.ok) throw new Error(`Failed to fetch story: ${res.status}`);
      return res.json() as Promise<StoryContent>;
    },
    enabled: !!originalText,
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/api/hooks.ts
git commit -m "feat: add useStoryContent hook for fetching JSON content"
```

---

### Task 7: Frontend — Update EntryDetail with JSON Content

**Files:**
- Modify: `frontend/src/components/Panel/EntryDetail.tsx:1-93`

- [ ] **Step 1: Rewrite EntryDetail to display structured content**

Replace `frontend/src/components/Panel/EntryDetail.tsx`:

```typescript
import { useEntry, useStoryContent } from "@/api/hooks";
import { X } from "lucide-react";

interface EntryDetailProps {
  entryId: number;
  onClose: () => void;
}

export function EntryDetail({ entryId, onClose }: EntryDetailProps) {
  const { data: entry, isLoading } = useEntry(entryId);
  const { data: story, isLoading: storyLoading } = useStoryContent(entry?.original_text ?? null);

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="animate-pulse h-4 bg-gray-200 rounded w-3/4 mb-2" />
        <div className="animate-pulse h-4 bg-gray-200 rounded w-1/2" />
      </div>
    );
  }

  if (!entry) return null;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="font-bold text-lg">{entry.title}</h2>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Meta info */}
        <div className="flex flex-wrap gap-2 text-sm text-gray-500">
          {entry.authors.map((a) => (
            <span key={a.id} className="bg-gray-100 px-2 py-0.5 rounded">{a.name}</span>
          ))}
          {entry.book && <span>《{entry.book.title}》</span>}
          {entry.chapter_reference && <span>{entry.chapter_reference}</span>}
          {entry.era_context && <span>{entry.era_context}</span>}
        </div>

        {/* Original text */}
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-1">原文</h3>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {story?.original_text ?? entry.original_text}
          </p>
        </div>

        {/* Translations */}
        {(story?.translations?.modern_chinese ?? entry.modern_translation) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">白话译文</h3>
            <p className="text-sm leading-relaxed">
              {story?.translations?.modern_chinese ?? entry.modern_translation}
            </p>
          </div>
        )}
        {(story?.translations?.english ?? entry.english_translation) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">English Translation</h3>
            <p className="text-sm leading-relaxed italic">
              {story?.translations?.english ?? entry.english_translation}
            </p>
          </div>
        )}

        {/* Keywords */}
        {(story?.entities?.keywords ?? entry.keywords) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">关键词</h3>
            <div className="flex flex-wrap gap-1">
              {(story?.entities?.keywords ?? entry.keywords)?.map((kw) => (
                <span key={kw} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Credibility */}
        {story?.credibility && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">可信度</h3>
            {story.credibility.credibility_score !== undefined && (
              <p className="text-sm">评分: {story.credibility.credibility_score}</p>
            )}
            {story.credibility.notes && (
              <p className="text-sm text-gray-600">{story.credibility.notes}</p>
            )}
          </div>
        )}

        {/* Context */}
        {(story?.credibility?.political_context ?? entry.political_context) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">政治背景</h3>
            <p className="text-sm">{story?.credibility?.political_context ?? entry.political_context}</p>
          </div>
        )}
        {(story?.credibility?.social_environment ?? entry.social_environment) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">社会环境</h3>
            <p className="text-sm">{story?.credibility?.social_environment ?? entry.social_environment}</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Verify in browser**

Start dev server and click an entry to verify JSON content loads:
```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Panel/EntryDetail.tsx
git commit -m "feat: display structured JSON content in EntryDetail"
```

---

### Task 8: Frontend — Update LocationMarker with Color Prop

**Files:**
- Modify: `frontend/src/components/Map/LocationMarker.tsx:1-28`

- [ ] **Step 1: Add color prop to LocationMarker**

Replace `frontend/src/components/Map/LocationMarker.tsx`:

```typescript
import { Marker, Popup } from "react-leaflet";
import { MarkerPopup } from "./MarkerPopup";
import type { MapLocation } from "./MapView";
import L from "leaflet";

function createColoredIcon(color: string): L.Icon {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="25" height="41">
    <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24C24 5.4 18.6 0 12 0z" fill="${color}"/>
    <circle cx="12" cy="12" r="5" fill="white"/>
  </svg>`;
  return L.icon({
    iconUrl: `data:image/svg+xml;base64,${btoa(svg)}`,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  });
}

const defaultIcon = createColoredIcon("#3B82F6");

interface LocationMarkerProps {
  location: MapLocation;
  color?: string;
  onMarkerClick?: (location: MapLocation) => void;
}

export function LocationMarker({ location, color, onMarkerClick }: LocationMarkerProps) {
  const icon = color ? createColoredIcon(color) : defaultIcon;

  return (
    <Marker
      position={[location.latitude, location.longitude]}
      icon={icon}
      eventHandlers={{
        click: () => onMarkerClick?.(location),
      }}
    >
      <Popup>
        <MarkerPopup location={location} onFilterClick={() => onMarkerClick?.(location)} />
      </Popup>
    </Marker>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Map/LocationMarker.tsx
git commit -m "feat: add color prop and click handler to LocationMarker"
```

---

### Task 9: Frontend — Update MarkerPopup for Location Filtering

**Files:**
- Modify: `frontend/src/components/Map/MarkerPopup.tsx:1-32`

- [ ] **Step 1: Replace navigate button with filter button**

Replace `frontend/src/components/Map/MarkerPopup.tsx`:

```typescript
import type { MapLocation } from "./MapView";

interface MarkerPopupProps {
  location: MapLocation;
  onFilterClick?: () => void;
}

export function MarkerPopup({ location, onFilterClick }: MarkerPopupProps) {
  return (
    <div className="min-w-[200px]">
      <h3 className="font-bold text-base mb-1">{location.name}</h3>
      {location.ancient_name && location.ancient_name !== location.name && (
        <p className="text-sm text-gray-500 mb-1">古称: {location.ancient_name}</p>
      )}
      {location.one_line_summary && (
        <p className="text-sm text-gray-700 mb-2">{location.one_line_summary}</p>
      )}
      <div className="flex gap-2 text-xs text-gray-400">
        {location.location_type && <span>{location.location_type}</span>}
        {location.ancient_region && <span>{location.ancient_region}</span>}
      </div>
      <button
        onClick={onFilterClick}
        className="mt-2 text-sm text-blue-600 hover:text-blue-800 underline"
      >
        筛选游记
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Map/MarkerPopup.tsx
git commit -m "feat: change marker popup to filter entries by location"
```

---

### Task 10: Frontend — Create RouteArrows Component

**Files:**
- Create: `frontend/src/components/Map/RouteArrows.tsx`

- [ ] **Step 1: Create RouteArrows component**

```typescript
import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet-polylineDecorator";

interface RouteLocation {
  latitude: number;
  longitude: number;
  order: number;
}

interface RouteArrowsProps {
  routes: Array<{
    entryId: number;
    locations: RouteLocation[];
    color: string;
  }>;
}

export function RouteArrows({ routes }: RouteArrowsProps) {
  const map = useMap();

  useEffect(() => {
    const layers: L.Layer[] = [];

    routes.forEach((route) => {
      if (route.locations.length < 2) return;

      const sorted = [...route.locations].sort((a, b) => a.order - b.order);
      const latlngs = sorted.map((loc) => L.latLng(loc.latitude, loc.longitude));

      const polyline = L.polyline(latlngs, {
        color: route.color,
        weight: 2,
        opacity: 0.4,
      });

      const decorator = (L as any).polylineDecorator(polyline, {
        patterns: [
          {
            offset: "50%",
            repeat: "100px",
            symbol: (L as any).Symbol.arrowHead({
              pixelSize: 8,
              polygon: false,
              pathOptions: {
                color: route.color,
                weight: 2,
                opacity: 0.6,
              },
            }),
          },
        ],
      });

      layers.push(polyline, decorator);
      map.addLayer(polyline);
      map.addLayer(decorator);
    });

    return () => {
      layers.forEach((layer) => map.removeLayer(layer));
    };
  }, [map, routes]);

  return null;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Map/RouteArrows.tsx
git commit -m "feat: add RouteArrows component for travel paths"
```

---

### Task 11: Frontend — Update MapView with All Features

**Files:**
- Modify: `frontend/src/components/Map/MapView.tsx:1-34`

- [ ] **Step 1: Rewrite MapView with focusTarget, clustering, colored pins, route arrows**

Replace `frontend/src/components/Map/MapView.tsx`:

```typescript
import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-markercluster";
import { LocationMarker } from "./LocationMarker";
import { RouteArrows } from "./RouteArrows";
import { getBookColor } from "@/lib/palettes";
import type { JournalEntry, LocationBrief } from "@/types";

const DEFAULT_CENTER: [number, number] = [35.0, 105.0];
const DEFAULT_ZOOM = 4;

export interface MapLocation {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  ancient_name?: string | null;
  one_line_summary?: string | null;
  location_type?: string | null;
  ancient_region?: string | null;
  book_id?: number | null;
  importance?: number;
}

interface FocusTarget {
  locations: Array<{ latitude: number; longitude: number }>;
}

interface MapViewProps {
  locations: MapLocation[];
  focusTarget?: FocusTarget | null;
  entries?: JournalEntry[];
  onMarkerClick?: (location: MapLocation) => void;
}

function MapFocusHandler({ focusTarget }: { focusTarget?: FocusTarget | null }) {
  const map = useMap();

  useEffect(() => {
    if (!focusTarget || focusTarget.locations.length === 0) return;

    if (focusTarget.locations.length === 1) {
      map.flyTo([focusTarget.locations[0].latitude, focusTarget.locations[0].longitude], 8, {
        duration: 1.5,
      });
    } else {
      const bounds = focusTarget.locations.map(
        (loc) => [loc.latitude, loc.longitude] as [number, number]
      );
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 8, duration: 1.5 });
    }
  }, [map, focusTarget]);

  return null;
}

export function MapView({ locations, focusTarget, entries, onMarkerClick }: MapViewProps) {
  // Compute book color for each location
  const locationColors = useMemo(() => {
    const colorMap = new Map<number, string>();
    locations.forEach((loc) => {
      if (loc.book_id && !colorMap.has(loc.id)) {
        colorMap.set(loc.id, getBookColor(loc.book_id));
      }
    });
    return colorMap;
  }, [locations]);

  // Build route data from entries
  const routes = useMemo(() => {
    if (!entries) return [];
    return entries
      .filter((e) => e.locations.length >= 2)
      .map((entry) => ({
        entryId: entry.id,
        locations: entry.locations.map((loc, i) => ({
          latitude: (loc as any).latitude ?? 0,
          longitude: (loc as any).longitude ?? 0,
          order: i,
        })),
        color: entry.book_id ? getBookColor(entry.book_id) : "#3B82F6",
      }))
      .filter((r) => r.locations.every((l) => l.latitude !== 0));
  }, [entries]);

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapFocusHandler focusTarget={focusTarget} />
      <MarkerClusterGroup
        chunkedLoading
        maxClusterRadius={60}
        spiderfyOnMaxZoom
        showCoverageOnHover={false}
      >
        {locations.map((loc) => (
          <LocationMarker
            key={loc.id}
            location={loc}
            color={locationColors.get(loc.id)}
            onMarkerClick={onMarkerClick}
          />
        ))}
      </MarkerClusterGroup>
      <RouteArrows routes={routes} />
    </MapContainer>
  );
}
```

- [ ] **Step 2: Verify in browser**

Start dev server and verify:
- Map loads with clustered markers
- Markers have colors based on book_id
- No console errors

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/Map/MapView.tsx
git commit -m "feat: add focusTarget, colored pins, clustering, and route arrows to MapView"
```

---

### Task 12: Frontend — Update ResultList with Location Filter

**Files:**
- Modify: `frontend/src/components/Panel/ResultList.tsx:1-45`

- [ ] **Step 1: Add filter indicator and clear button**

Replace `frontend/src/components/Panel/ResultList.tsx`:

```typescript
import type { JournalEntry } from "@/types";

interface ResultListProps {
  entries: JournalEntry[];
  onSelect: (id: number) => void;
  selectedId: number | null;
  locationFilter?: { lat: number; lng: number; radiusKm: number } | null;
  onClearFilter?: () => void;
}

export function ResultList({ entries, onSelect, selectedId, locationFilter, onClearFilter }: ResultListProps) {
  if (entries.length === 0) {
    return (
      <div className="p-4 text-sm text-gray-400">
        {locationFilter ? "该位置附近暂无游记" : "暂无结果"}
      </div>
    );
  }

  return (
    <div className="overflow-y-auto">
      {locationFilter && (
        <div className="p-2 bg-blue-50 border-b flex items-center justify-between">
          <span className="text-xs text-blue-700">
            显示 {entries.length} 条附近游记
          </span>
          {onClearFilter && (
            <button
              onClick={onClearFilter}
              className="text-xs text-blue-600 hover:text-blue-800 underline"
            >
              清除筛选
            </button>
          )}
        </div>
      )}
      {entries.map((entry) => (
        <button
          key={entry.id}
          onClick={() => onSelect(entry.id)}
          className={`w-full text-left p-3 border-b hover:bg-gray-50 transition-colors ${
            selectedId === entry.id ? "bg-blue-50 border-l-2 border-l-blue-500" : ""
          }`}
        >
          <h3 className="font-medium text-sm mb-1">{entry.title}</h3>
          <p className="text-xs text-gray-500 line-clamp-2 mb-1">{entry.original_text}</p>
          <div className="flex gap-2 text-xs text-gray-400">
            {entry.authors.map((a) => (
              <span key={a.id}>{a.name}</span>
            ))}
            {entry.era_context && <span>{entry.era_context}</span>}
          </div>
          {entry.locations.length > 0 && (
            <div className="mt-1 flex gap-1 flex-wrap">
              {entry.locations.map((l) => (
                <span key={l.id} className="text-xs bg-gray-100 px-1.5 py-0.5 rounded">
                  {l.name}
                </span>
              ))}
            </div>
          )}
        </button>
      ))}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Panel/ResultList.tsx
git commit -m "feat: add location filter indicator to ResultList"
```

---

### Task 13: Frontend — Wire Up App.tsx

**Files:**
- Modify: `frontend/src/App.tsx:1-96`

- [ ] **Step 1: Add focusTarget and locationFilter state to HomePage**

Replace the `HomePage` function in `frontend/src/App.tsx`:

```typescript
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useMemo, useCallback } from "react";
import { MapView } from "./components/Map/MapView";
import { SearchBar } from "./components/Search/SearchBar";
import { FilterPanel, type FilterState } from "./components/Filter/FilterPanel";
import { ResultList } from "./components/Panel/ResultList";
import { EntryDetail } from "./components/Panel/EntryDetail";
import { LocationPage } from "./pages/LocationPage";
import { useEntries, useLocations, useSearch } from "./api/hooks";
import { ChevronUp, ChevronDown } from "lucide-react";
import type { MapLocation } from "./components/Map/MapView";

const queryClient = new QueryClient();

function haversineDistance(
  lat1: number, lon1: number,
  lat2: number, lon2: number
): number {
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

function HomePage() {
  const [filters, setFilters] = useState<FilterState>({ dynasty: "", locationType: "", era: "" });
  const { data: locations = [] } = useLocations({
    dynasty: filters.dynasty || undefined,
    type: filters.locationType || undefined,
  });
  const { data: entries = [] } = useEntries({
    dynasty: filters.dynasty || undefined,
    era: filters.era || undefined,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const { data: searchResults } = useSearch(searchQuery);
  const [selectedEntryId, setSelectedEntryId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [locationFilter, setLocationFilter] = useState<{
    lat: number;
    lng: number;
    radiusKm: number;
  } | null>(null);
  const [focusTarget, setFocusTarget] = useState<{
    locations: Array<{ latitude: number; longitude: number }>;
  } | null>(null);

  const displayEntriesRaw = searchQuery && searchResults ? searchResults : entries;
  const displayLocations = searchQuery && searchResults
    ? searchResults.flatMap((e) => e.locations).filter((l, i, arr) => arr.findIndex((x) => x.id === l.id) === i)
    : locations;

  // Apply location filter
  const displayEntries = useMemo(() => {
    if (!locationFilter) return displayEntriesRaw;
    return displayEntriesRaw.filter((entry) =>
      entry.locations.some((loc) => {
        const dist = haversineDistance(
          locationFilter.lat,
          locationFilter.lng,
          (loc as any).latitude ?? 0,
          (loc as any).longitude ?? 0
        );
        return dist <= locationFilter.radiusKm;
      })
    );
  }, [displayEntriesRaw, locationFilter]);

  // Handle entry selection — focus map on entry locations
  const handleSelectEntry = useCallback(
    (id: number) => {
      setSelectedEntryId(id);
      const entry = displayEntriesRaw.find((e) => e.id === id);
      if (entry && entry.locations.length > 0) {
        setFocusTarget({
          locations: entry.locations.map((loc) => ({
            latitude: (loc as any).latitude ?? 0,
            longitude: (loc as any).longitude ?? 0,
          })),
        });
      }
    },
    [displayEntriesRaw]
  );

  // Handle marker click — filter entries by location
  const handleMarkerClick = useCallback((location: MapLocation) => {
    setLocationFilter({
      lat: location.latitude,
      lng: location.longitude,
      radiusKm: 10,
    });
  }, []);

  return (
    <div className="h-full flex flex-col">
      <header className="h-14 border-b flex items-center px-4 gap-3 bg-white z-20">
        <h1 className="text-lg font-bold whitespace-nowrap">HiSMap</h1>
        <SearchBar onSearch={setSearchQuery} />
        <FilterPanel onChange={setFilters} />
      </header>
      <div className="flex-1 flex relative overflow-hidden">
        <aside className="hidden md:block w-80 border-r overflow-y-auto bg-white z-20">
          <div className="p-3 border-b text-sm text-gray-500">
            {displayEntries.length} 条游记
          </div>
          <ResultList
            entries={displayEntries}
            onSelect={handleSelectEntry}
            selectedId={selectedEntryId}
            locationFilter={locationFilter}
            onClearFilter={() => setLocationFilter(null)}
          />
        </aside>
        <div className="flex-1 relative z-0">
          <MapView
            locations={displayLocations}
            focusTarget={focusTarget}
            entries={displayEntriesRaw}
            onMarkerClick={handleMarkerClick}
          />
        </div>
        {selectedEntryId && (
          <div className="hidden md:block absolute right-0 top-0 bottom-0 w-96 bg-white border-l shadow-lg z-30">
            <EntryDetail entryId={selectedEntryId} onClose={() => setSelectedEntryId(null)} />
          </div>
        )}
        <div
          className={`md:hidden absolute bottom-0 left-0 right-0 bg-white border-t shadow-lg transition-transform duration-300 z-30 ${
            drawerOpen ? "translate-y-0" : "translate-y-[calc(100%-3rem)]"
          }`}
          style={{ maxHeight: "70vh" }}
        >
          <button
            onClick={() => setDrawerOpen(!drawerOpen)}
            className="w-full flex items-center justify-center py-2 border-b"
          >
            {drawerOpen ? <ChevronDown className="h-5 w-5" /> : <ChevronUp className="h-5 w-5" />}
            <span className="ml-2 text-sm text-gray-500">{displayEntries.length} 条游记</span>
          </button>
          <div className="overflow-y-auto" style={{ maxHeight: "calc(70vh - 3rem)" }}>
            {selectedEntryId ? (
              <EntryDetail entryId={selectedEntryId} onClose={() => setSelectedEntryId(null)} />
            ) : (
              <ResultList
                entries={displayEntries}
                onSelect={(id) => { handleSelectEntry(id); setDrawerOpen(true); }}
                selectedId={selectedEntryId}
                locationFilter={locationFilter}
                onClearFilter={() => setLocationFilter(null)}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/locations/:id" element={<LocationPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 2: Verify all features in browser**

Start dev server and test:
1. Click an entry in the sidebar — map should fly to its locations
2. Click a marker — sidebar should filter to nearby entries
3. "清除筛选" button should clear the filter
4. Markers should have colors based on book
5. Route arrows should appear for entries with 2+ locations
6. Clustering should work at low zoom levels

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.tsx
git commit -m "feat: wire up map interactions, filtering, and focus in App.tsx"
```

---

### Task 14: Frontend — Build Verification

**Files:**
- None (verification only)

- [ ] **Step 1: Run TypeScript check**

```bash
cd frontend && npx tsc --noEmit
```
Expected: No errors

- [ ] **Step 2: Run production build**

```bash
cd frontend && npm run build
```
Expected: Successful build with no errors

- [ ] **Step 3: Run backend tests**

```bash
cd backend && conda run -n hismap pytest
```
Expected: All tests pass

- [ ] **Step 4: Final commit if any fixes needed**

```bash
git add -A
git commit -m "fix: address build issues from frontend improvements"
```

---

## Summary

| Task | Description | Dependencies |
|------|-------------|--------------|
| 1 | Static file mount | None |
| 2 | Importance column + migration | None |
| 3 | Pipeline S4 writes importance | Task 2 |
| 4 | Install frontend dependencies | None |
| 5 | Create palette system | None |
| 6 | Add useStoryContent hook | Task 1 |
| 7 | Update EntryDetail | Task 6 |
| 8 | Update LocationMarker with color | None |
| 9 | Update MarkerPopup for filtering | None |
| 10 | Create RouteArrows component | Task 4 |
| 11 | Update MapView with all features | Tasks 4, 5, 8, 9, 10 |
| 12 | Update ResultList with filter | None |
| 13 | Wire up App.tsx | Tasks 7, 11, 12 |
| 14 | Build verification | All tasks |
