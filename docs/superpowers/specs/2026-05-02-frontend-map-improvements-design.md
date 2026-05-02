# Frontend Map & Panel Improvements

**Date:** 2026-05-02
**Issues:** #5, #7
**Branch:** `feat/frontend-map-improvements`

## Summary

Combine frontend improvements from issues #5 and #7 into a single branch. Covers: content display in detail panel, map-sidebar interactions, colored pins, route arrows, and pin clustering. i18n deferred to a later fix.

## Scope

### In Scope
1. Parse and display structured JSON content in EntryDetail
2. Auto-focus map to locations when clicking an entry
3. Auto-filter sidebar entries when clicking a location marker
4. Colored pins per book with palette system
5. Route arrows between sequential locations
6. Pin clustering with importance-based merge logic
7. Add `importance` field to `entry_locations` association table

### Out of Scope
- i18n / multilingual UI support
- Backend API changes (except static file mount + migration)
- Pipeline changes (importance is already in JSON output)

---

## 1. Static File Serving for Pipeline Output

**Problem:** `original_text` field stores a file path (e.g., `pipeline/output/ibn_battuta/ibn_battuta_0001_tangier.json`). EntryDetail needs to display the structured content.

**Solution:** Mount `pipeline/output/` as static files in FastAPI.

**Implementation:**
- Add to `backend/app/main.py`:
  ```python
  from fastapi.staticfiles import StaticFiles
  app.mount("/static/output", StaticFiles(directory="../pipeline/output"), name="pipeline-output")
  ```
- `original_text` stores paths like `pipeline/output/ibn_battuta/ibn_battuta_0001.json`
- Frontend strips the `pipeline/output/` prefix and constructs URL:
  ```typescript
  const jsonPath = entry.original_text.replace("pipeline/output/", "");
  const url = `/static/output/${jsonPath}`;
  ```
- New hook `useStoryContent(path)` fetches and parses JSON
- EntryDetail renders: original passage, translations, entities, credibility, annotations

**Data flow:**
```
EntryDetail → useEntry(id) → entry.original_text (relative path)
           → fetch(`/static/output/${path}`)
           → parse JSON → render structured content
```

**JSON structure (from pipeline output):**
```json
{
  "id": "ibn_battuta_0008_mombasa",
  "title": "...",
  "original_text": "...",
  "translations": { "modern_chinese": "...", "english": "..." },
  "entities": { "locations": [...], "persons": [], "keywords": [...] },
  "credibility": { "credibility_score": 1.0, "notes": "..." },
  "annotations": [{ "importance": 4, "marker_title": "...", "short_popup": "..." }]
}
```

---

## 2. Map-Sidebar Interactions

### 2a. Auto-focus on Entry Click

**Problem:** Clicking an entry in the sidebar does nothing to the map.

**Solution:** When user selects an entry, pan/zoom the map to its locations.

**Implementation:**
- Add `focusTarget` state to App.tsx: `{ locations: Location[], entryId: number } | null`
- When `selectedEntryId` changes, compute focus target from entry's locations
- MapView accepts `focusTarget` prop, calls `map.flyTo()` (single location) or `map.fitBounds()` (multiple)
- Use `location_order` from entry data for correct sequencing

### 2b. Auto-filter on Marker Click

**Problem:** Clicking a map marker navigates away to a full page. No sidebar filtering.

**Solution:** Clicking a marker filters the sidebar to show only entries near that location.

**Implementation:**
- Add `locationFilter` state to App.tsx: `{ lat: number, lng: number, radiusKm: number } | null`
- Default radius: 10km
- Filter `displayEntries` by proximity (haversine formula or bounding box)
- ResultList shows filtered entries with a "Clear filter" button
- MarkerPopup's "查看详情" button changes to "筛选游记" (filter entries)

---

## 3. Colored Pins Per Book

**Problem:** All markers use the same default pin color. Hard to distinguish entries from different books.

**Solution:** Assign each book a distinct color from a preset palette.

**Implementation:**
- Create `src/lib/palettes.ts`:
  ```typescript
  export const palettes = {
    warm: ["#E63946", "#F4A261", "#2A9D8F", "#264653", "#E9C46A", "#606C38", "#DDA15E", "#BC6C25"],
    ocean: ["#0077B6", "#00B4D8", "#90E0EF", "#CAF0F8", "#023E8A", "#48CAE4", "#ADE8F4", "#03045E"],
    earth: ["#6B4226", "#C68642", "#8B6914", "#DAA520", "#556B2F", "#8FBC8F", "#B22222", "#CD853F"],
  };

  export function getBookColor(bookId: number, palette: string[] = palettes.warm): string {
    return palette[bookId % palette.length];
  }
  ```
- LocationMarker accepts `color` prop
- Book color passed through from App → MapView → LocationMarker
- If multiple books reference same location, use first book's color

---

## 4. Route Arrows

**Problem:** No visual indication of travel sequence between locations.

**Solution:** Draw semi-transparent arrows connecting locations in chronological order.

**Implementation:**
- Install `leaflet-polylineDecorator` for arrow heads
- For each entry with 2+ locations sorted by `location_order`:
  - Draw `Polyline` connecting locations
  - Add arrow decorators at midpoint or endpoints
- Style: 2px width, 40% opacity, entry's book color
- Skip if entry has < 2 locations or `location_order` is missing

**Blank value handling:**
- `visit_date_approximate: null` — acceptable, use `location_order` for sequencing
- `location_order` missing or locations < 2 — skip arrow drawing entirely

---

## 5. Pin Clustering

**Problem:** Many markers overlap at low zoom levels, creating clutter.

**Solution:** Use `react-leaflet-markercluster` with importance-based merge logic.

**Implementation:**
- Install `react-leaflet-markercluster` and `leaflet.markercluster`
- Replace individual `LocationMarker` components with `MarkerClusterGroup`
- Frontend computes `maxImportance` per location across its entries
- Merge strategy by zoom level:

| Zoom | Show individually | Merge into clusters |
|------|-------------------|---------------------|
| 8+   | All (0-5)         | None                |
| 6-7  | 3-5               | 0-2                 |
| 4-5  | 5                 | 0-4                 |
| <4   | 5                 | 0-4                 |

- Cluster icon: circle with count number, color intensity based on highest importance in cluster
- Custom `iconCreateFunction` to implement importance-based clustering

---

## 6. Database Changes

### Add `importance` to `entry_locations`

**Migration:**
```python
# alembic migration
op.add_column('entry_locations', sa.Column('importance', sa.Integer(), server_default='0'))
```

**Model update (`associations.py`):**
```python
Column("importance", Integer, nullable=False, server_default="0"),
```

**Constraint:** Discrete values only: 0, 1, 2, 3, 4, 5

**Pipeline integration:** Update `s4_output.py` to write `annotations[0].importance` to the `entry_locations` table when creating entry-location links (currently only writes `entry_id`, `location_id`, `location_order`).

---

## Files to Modify

### Backend
- `backend/app/main.py` — add static file mount
- `backend/app/models/associations.py` — add `importance` column
- `backend/alembic/versions/` — new migration

### Frontend
- `src/App.tsx` — add focusTarget, locationFilter state; pass to MapView/ResultList
- `src/components/Map/MapView.tsx` — accept focusTarget prop, add clustering, route arrows
- `src/components/Map/LocationMarker.tsx` — accept color prop
- `src/components/Map/MarkerPopup.tsx` — change "查看详情" to "筛选游记"
- `src/components/Panel/EntryDetail.tsx` — fetch and render JSON content
- `src/components/Panel/ResultList.tsx` — accept and display location filter
- `src/lib/palettes.ts` — new file, palette definitions
- `src/api/hooks.ts` — add useStoryContent hook

### New Dependencies
- `leaflet-polylineDecorator` — route arrows
- `react-leaflet-markercluster` — pin clustering

---

## Acceptance Criteria

- [ ] EntryDetail displays structured JSON content (original, translations, entities, credibility)
- [ ] Clicking an entry pans/zooms the map to its locations
- [ ] Clicking a marker filters the sidebar to nearby entries (10km radius)
- [ ] Pins are colored by book using a palette system
- [ ] Route arrows connect sequential locations within an entry
- [ ] Pins cluster at low zoom based on importance level
- [ ] `importance` field exists on `entry_locations` (0-5, discrete)
- [ ] All features work together without visual conflict
- [ ] Mobile-friendly (responsive, touch-compatible)
