# HiSMap Frontend Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the React + TypeScript frontend with Leaflet map, location markers, search bar, filter panel, and entry detail drawer — fully interactive and connected to the backend API.

**Design Standard:** All frontend work MUST follow the Swiss International Typographic Style defined in [`specs/design_standard.md`](../specs/design_standard.md). This covers colors, typography, borders, textures, component patterns, animations, and responsive strategy. Read it before implementing any UI.

**Architecture:** Vite + React 18 + TypeScript SPA. react-leaflet for map rendering. TanStack Query for API data fetching and caching. shadcn/ui for base components (overridden to Swiss style). Responsive layout: desktop gets left panel + map, mobile gets full-screen map + bottom drawer.

**Tech Stack:** React 18, TypeScript, Vite, react-leaflet, TanStack Query, Tailwind CSS, shadcn/ui, Inter (Google Fonts)

---

## File Structure

```
frontend/
├── index.html
├── package.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
├── tailwind.config.ts
├── postcss.config.js
├── components.json                  # shadcn/ui config
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css
│   ├── vite-env.d.ts
│   ├── types/
│   │   └── index.ts                 # API response types
│   ├── api/
│   │   └── client.ts                # API client (fetch wrapper)
│   │   └── hooks.ts                 # TanStack Query hooks
│   ├── components/
│   │   ├── Map/
│   │   │   ├── MapView.tsx          # Main Leaflet map
│   │   │   ├── LocationMarker.tsx   # Single marker component
│   │   │   └── MarkerPopup.tsx      # Popup on marker click
│   │   ├── Search/
│   │   │   └── SearchBar.tsx
│   │   ├── Filter/
│   │   │   └── FilterPanel.tsx
│   │   ├── Panel/
│   │   │   ├── ResultList.tsx       # Left panel entry list
│   │   │   ├── EntryDetail.tsx      # Detail drawer/modal
│   │   │   └── LocationDetail.tsx   # Four-layer location detail
│   │   └── Layout/
│   │       └── AppLayout.tsx        # Responsive layout shell
│   └── lib/
│       └── utils.ts                 # shadcn/ui utility (cn)
├── public/
│   └── favicon.ico
└── postcss.config.js
```

---

## Task 1: Project Scaffolding

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tsconfig.app.json`
- Create: `frontend/tsconfig.node.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/index.html`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/vite-env.d.ts`

- [ ] **Step 1: Create package.json**

```json
{
  "name": "hismap-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc -b && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-leaflet": "^4.2.1",
    "leaflet": "^1.9.4",
    "@tanstack/react-query": "^5.50.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.3.0",
    "lucide-react": "^0.400.0"
  },
  "devDependencies": {
    "@types/leaflet": "^1.9.12",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "@vitejs/plugin-react": "^4.3.1",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "tailwindcss": "^3.4.4",
    "typescript": "^5.5.2",
    "vite": "^5.3.1"
  }
}
```

- [ ] **Step 2: Create tsconfig files**

```json
// frontend/tsconfig.json
{
  "files": [],
  "references": [{ "path": "./tsconfig.app.json" }, { "path": "./tsconfig.node.json" }]
}
```

```json
// frontend/tsconfig.app.json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"]
}
```

```json
// frontend/tsconfig.node.json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "isolatedModules": true,
    "moduleDetection": "force",
    "noEmit": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
```

- [ ] **Step 3: Create vite.config.ts**

```typescript
// frontend/vite.config.ts
import react from "@vitejs/plugin-react";
import path from "path";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 4: Create index.html**

```html
<!-- frontend/index.html -->
<!doctype html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/x-icon" href="/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HiSMap - 古代游记地图</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;700;900&display=swap" rel="stylesheet" />
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 5: Create src files**

```typescript
// frontend/src/vite-env.d.ts
/// <reference types="vite/client" />
```

```css
/* frontend/src/index.css */
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root {
  height: 100%;
  margin: 0;
  padding: 0;
  font-family: "Inter", system-ui, sans-serif;
}

.leaflet-container {
  height: 100%;
  width: 100%;
}

/* Swiss texture patterns */
.swiss-grid-pattern {
  background-image:
    linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px);
  background-size: 24px 24px;
}

.swiss-dots {
  background-image: radial-gradient(circle, rgba(0,0,0,0.04) 1px, transparent 1px);
  background-size: 16px 16px;
}

.swiss-diagonal {
  background-image: repeating-linear-gradient(
    45deg,
    transparent,
    transparent 10px,
    rgba(0,0,0,0.02) 10px,
    rgba(0,0,0,0.02) 11px
  );
}
```

```tsx
// frontend/src/main.tsx
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient();

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
);
```

```tsx
// frontend/src/App.tsx
export default function App() {
  return (
    <div className="h-full flex items-center justify-center">
      <h1 className="text-2xl font-bold">HiSMap - 古代游记地图</h1>
    </div>
  );
}
```

- [ ] **Step 6: Create Tailwind and PostCSS config**

```javascript
// frontend/postcss.config.js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

```typescript
// frontend/tailwind.config.ts
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        swiss: {
          bg: "#FFFFFF",
          fg: "#000000",
          muted: "#F2F2F2",
          accent: "#FF3000",
          border: "#000000",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      borderRadius: {
        none: "0px",
      },
    },
  },
  plugins: [],
};

export default config;
```

- [ ] **Step 7: Install dependencies and verify dev server**

Run: `cd frontend && npm install && npm run dev`

Open http://localhost:5173 — should see "HiSMap - 古代游记地图"

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat: scaffold Vite + React + TypeScript frontend"
```

---

## Task 2: API Client and Types

**Files:**
- Create: `frontend/src/types/index.ts`
- Create: `frontend/src/api/client.ts`
- Create: `frontend/src/api/hooks.ts`

- [ ] **Step 1: Create TypeScript types**

```typescript
// frontend/src/types/index.ts
export interface Location {
  id: number;
  name: string;
  modern_name: string | null;
  ancient_name: string | null;
  latitude: number;
  longitude: number;
  location_type: string | null;
  ancient_region: string | null;
  one_line_summary: string | null;
  location_rationale: string | null;
  academic_disputes: string | null;
  credibility_notes: string | null;
  today_remains: string | null;
}

export interface RelatedLocation {
  id: number;
  name: string;
  relation_type: string;
  description: string | null;
}

export interface LocationDetail extends Location {
  entries: JournalEntry[];
  related_locations: RelatedLocation[];
}

export interface AuthorBrief {
  id: number;
  name: string;
  dynasty: string | null;
}

export interface Author extends AuthorBrief {
  birth_year: number | null;
  death_year: number | null;
  biography: string | null;
}

export interface AuthorDetail extends Author {
  entries: JournalEntry[];
}

export interface BookBrief {
  id: number;
  title: string;
}

export interface Book extends BookBrief {
  author: string | null;
  dynasty: string | null;
  era_start: number | null;
  era_end: number | null;
  description: string | null;
}

export interface BookDetail extends Book {
  entries: JournalEntry[];
}

export interface LocationBrief {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

export interface JournalEntry {
  id: number;
  book_id: number | null;
  title: string;
  original_text: string;
  modern_translation: string | null;
  english_translation: string | null;
  chapter_reference: string | null;
  keywords: string[] | null;
  keyword_annotations: Record<string, unknown> | null;
  era_context: string | null;
  political_context: string | null;
  religious_context: string | null;
  social_environment: string | null;
  visit_date_approximate: string | null;
  locations: LocationBrief[];
  authors: AuthorBrief[];
}

export interface JournalEntryDetail extends JournalEntry {
  book: BookBrief | null;
}

export interface FilterOptions {
  dynasties: string[];
  authors: string[];
  location_types: string[];
  era_contexts: string[];
}
```

- [ ] **Step 2: Create API client**

```typescript
// frontend/src/api/client.ts
const BASE = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  // Locations
  getLocations: (params?: { type?: string; dynasty?: string }) => {
    const qs = new URLSearchParams();
    if (params?.type) qs.set("type", params.type);
    if (params?.dynasty) qs.set("dynasty", params.dynasty);
    const query = qs.toString();
    return fetchJSON<import("../types").Location[]>(`/locations${query ? `?${query}` : ""}`);
  },

  getLocation: (id: number) =>
    fetchJSON<import("../types").LocationDetail>(`/locations/${id}`),

  // Entries
  getEntries: (params?: { dynasty?: string; author?: string; keyword?: string; era?: string }) => {
    const qs = new URLSearchParams();
    if (params?.dynasty) qs.set("dynasty", params.dynasty);
    if (params?.author) qs.set("author", params.author);
    if (params?.keyword) qs.set("keyword", params.keyword);
    if (params?.era) qs.set("era", params.era);
    const query = qs.toString();
    return fetchJSON<import("../types").JournalEntry[]>(`/entries${query ? `?${query}` : ""}`);
  },

  getEntry: (id: number) =>
    fetchJSON<import("../types").JournalEntryDetail>(`/entries/${id}`),

  // Authors
  getAuthors: (dynasty?: string) => {
    const qs = new URLSearchParams();
    if (dynasty) qs.set("dynasty", dynasty);
    const query = qs.toString();
    return fetchJSON<import("../types").Author[]>(`/authors${query ? `?${query}` : ""}`);
  },

  getAuthor: (id: number) =>
    fetchJSON<import("../types").AuthorDetail>(`/authors/${id}`),

  // Books
  getBooks: () => fetchJSON<import("../types").Book[]>("/books"),
  getBook: (id: number) => fetchJSON<import("../types").BookDetail>(`/books/${id}`),

  // Search
  search: (q: string) =>
    fetchJSON<import("../types").JournalEntry[]>(`/search?q=${encodeURIComponent(q)}`),

  // Filters
  getFilters: () => fetchJSON<import("../types").FilterOptions>("/filters"),
};
```

- [ ] **Step 3: Create TanStack Query hooks**

```typescript
// frontend/src/api/hooks.ts
import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export function useLocations(params?: { type?: string; dynasty?: string }) {
  return useQuery({
    queryKey: ["locations", params],
    queryFn: () => api.getLocations(params),
  });
}

export function useLocation(id: number) {
  return useQuery({
    queryKey: ["location", id],
    queryFn: () => api.getLocation(id),
    enabled: !!id,
  });
}

export function useEntries(params?: { dynasty?: string; author?: string; keyword?: string; era?: string }) {
  return useQuery({
    queryKey: ["entries", params],
    queryFn: () => api.getEntries(params),
  });
}

export function useEntry(id: number) {
  return useQuery({
    queryKey: ["entry", id],
    queryFn: () => api.getEntry(id),
    enabled: !!id,
  });
}

export function useSearch(query: string) {
  return useQuery({
    queryKey: ["search", query],
    queryFn: () => api.search(query),
    enabled: query.length > 0,
  });
}

export function useFilters() {
  return useQuery({
    queryKey: ["filters"],
    queryFn: () => api.getFilters(),
  });
}

export function useAuthors(dynasty?: string) {
  return useQuery({
    queryKey: ["authors", dynasty],
    queryFn: () => api.getAuthors(dynasty),
  });
}

export function useBooks() {
  return useQuery({
    queryKey: ["books"],
    queryFn: () => api.getBooks(),
  });
}
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/types/ frontend/src/api/
git commit -m "feat: add TypeScript types, API client, and TanStack Query hooks"
```

---

## Task 3: Map Component with Location Markers

**Files:**
- Create: `frontend/src/components/Map/MapView.tsx`
- Create: `frontend/src/components/Map/LocationMarker.tsx`
- Create: `frontend/src/components/Map/MarkerPopup.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create MarkerPopup component**

```tsx
// frontend/src/components/Map/MarkerPopup.tsx
import type { Location } from "@/types";

interface MarkerPopupProps {
  location: Location;
  onSelect: (id: number) => void;
}

export function MarkerPopup({ location, onSelect }: MarkerPopupProps) {
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
        onClick={() => onSelect(location.id)}
        className="mt-2 text-sm text-blue-600 hover:text-blue-800 underline"
      >
        查看详情
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Create LocationMarker component**

```tsx
// frontend/src/components/Map/LocationMarker.tsx
import { Marker, Popup } from "react-leaflet";
import type { Location } from "@/types";
import { MarkerPopup } from "./MarkerPopup";
import L from "leaflet";

// Fix default marker icons in Leaflet + bundler
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface LocationMarkerProps {
  location: Location;
  onSelect: (id: number) => void;
}

export function LocationMarker({ location, onSelect }: LocationMarkerProps) {
  return (
    <Marker position={[location.latitude, location.longitude]} icon={defaultIcon}>
      <Popup>
        <MarkerPopup location={location} onSelect={onSelect} />
      </Popup>
    </Marker>
  );
}
```

- [ ] **Step 3: Create MapView component**

```tsx
// frontend/src/components/Map/MapView.tsx
import { MapContainer, TileLayer } from "react-leaflet";
import type { Location } from "@/types";
import { LocationMarker } from "./LocationMarker";

// Center on ancient Silk Road region
const DEFAULT_CENTER: [number, number] = [35.0, 105.0];
const DEFAULT_ZOOM = 4;

interface MapViewProps {
  locations: Location[];
  onLocationSelect: (id: number) => void;
}

export function MapView({ locations, onLocationSelect }: MapViewProps) {
  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {locations.map((loc) => (
        <LocationMarker key={loc.id} location={loc} onSelect={onLocationSelect} />
      ))}
    </MapContainer>
  );
}
```

- [ ] **Step 4: Update App.tsx to show map**

```tsx
// frontend/src/App.tsx
import { useState } from "react";
import { MapView } from "./components/Map/MapView";
import { useLocations } from "./api/hooks";

export default function App() {
  const { data: locations = [], isLoading } = useLocations();
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null);

  return (
    <div className="h-full flex flex-col">
      {/* Simple header for now */}
      <header className="h-14 border-b flex items-center px-4 bg-white z-10">
        <h1 className="text-lg font-bold">HiSMap 古代游记地图</h1>
        {isLoading && <span className="ml-4 text-sm text-gray-400">加载中...</span>}
      </header>
      {/* Map fills remaining space */}
      <div className="flex-1">
        <MapView locations={locations} onLocationSelect={setSelectedLocationId} />
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Add Tailwind utility `cn`**

```typescript
// frontend/src/lib/utils.ts
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

- [ ] **Step 6: Install dependencies and verify**

Run: `cd frontend && npm install`

Start dev server: `cd frontend && npm run dev`

Open http://localhost:5173 — should see a full-screen map with OpenStreetMap tiles. No markers yet (backend not running is fine — empty array).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/
git commit -m "feat: add Leaflet map with location markers and popups"
```

---

## Task 4: Search Bar

**Files:**
- Create: `frontend/src/components/Search/SearchBar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create SearchBar component**

```tsx
// frontend/src/components/Search/SearchBar.tsx
import { useState } from "react";
import { Search } from "lucide-react";

interface SearchBarProps {
  onSearch: (query: string) => void;
}

export function SearchBar({ onSearch }: SearchBarProps) {
  const [value, setValue] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      onSearch(value.trim());
    }
  };

  return (
    <form onSubmit={handleSubmit} className="relative flex-1 max-w-md">
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
      <input
        type="text"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="搜索游记、地点、关键词..."
        className="w-full pl-10 pr-4 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
      />
    </form>
  );
}
```

- [ ] **Step 2: Integrate SearchBar into App**

```tsx
// frontend/src/App.tsx
import { useState } from "react";
import { MapView } from "./components/Map/MapView";
import { SearchBar } from "./components/Search/SearchBar";
import { useLocations, useSearch } from "./api/hooks";

export default function App() {
  const { data: locations = [], isLoading } = useLocations();
  const [searchQuery, setSearchQuery] = useState("");
  const { data: searchResults } = useSearch(searchQuery);
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null);

  // If searching, show search result locations on map; otherwise show all
  const displayLocations = searchQuery && searchResults
    ? searchResults.flatMap((e) => e.locations).filter((l, i, arr) => arr.findIndex((x) => x.id === l.id) === i)
    : locations;

  return (
    <div className="h-full flex flex-col">
      <header className="h-14 border-b flex items-center px-4 gap-4 bg-white z-10">
        <h1 className="text-lg font-bold whitespace-nowrap">HiSMap</h1>
        <SearchBar onSearch={setSearchQuery} />
        {isLoading && <span className="text-sm text-gray-400">加载中...</span>}
      </header>
      <div className="flex-1">
        <MapView locations={displayLocations} onLocationSelect={setSelectedLocationId} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add search bar with map filtering"
```

---

## Task 5: Filter Panel

**Files:**
- Create: `frontend/src/components/Filter/FilterPanel.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create FilterPanel component**

```tsx
// frontend/src/components/Filter/FilterPanel.tsx
import { useFilters } from "@/api/hooks";
import { useState } from "react";
import { SlidersHorizontal } from "lucide-react";

export interface FilterState {
  dynasty: string;
  locationType: string;
  era: string;
}

interface FilterPanelProps {
  onChange: (filters: FilterState) => void;
}

export function FilterPanel({ onChange }: FilterPanelProps) {
  const { data: filterOptions } = useFilters();
  const [filters, setFilters] = useState<FilterState>({ dynasty: "", locationType: "", era: "" });
  const [open, setOpen] = useState(false);

  const update = (key: keyof FilterState, value: string) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    onChange(next);
  };

  if (!filterOptions) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50"
      >
        <SlidersHorizontal className="h-4 w-4" />
        筛选
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-2 w-64 bg-white border rounded-lg shadow-lg p-4 z-50">
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">朝代</label>
            <select
              value={filters.dynasty}
              onChange={(e) => update("dynasty", e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">全部</option>
              {filterOptions.dynasties.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">地点类型</label>
            <select
              value={filters.locationType}
              onChange={(e) => update("locationType", e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">全部</option>
              {filterOptions.location_types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">时代背景</label>
            <select
              value={filters.era}
              onChange={(e) => update("era", e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">全部</option>
              {filterOptions.era_contexts.map((e) => (
                <option key={e} value={e}>{e}</option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              setFilters({ dynasty: "", locationType: "", era: "" });
              onChange({ dynasty: "", locationType: "", era: "" });
            }}
            className="w-full text-sm text-gray-500 hover:text-gray-700"
          >
            重置筛选
          </button>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Integrate FilterPanel into App**

```tsx
// frontend/src/App.tsx
import { useState } from "react";
import { MapView } from "./components/Map/MapView";
import { SearchBar } from "./components/Search/SearchBar";
import { FilterPanel, type FilterState } from "./components/Filter/FilterPanel";
import { useLocations, useSearch } from "./api/hooks";

export default function App() {
  const [filters, setFilters] = useState<FilterState>({ dynasty: "", locationType: "", era: "" });
  const { data: locations = [], isLoading } = useLocations({
    dynasty: filters.dynasty || undefined,
    type: filters.locationType || undefined,
  });
  const [searchQuery, setSearchQuery] = useState("");
  const { data: searchResults } = useSearch(searchQuery);
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null);

  const displayLocations = searchQuery && searchResults
    ? searchResults.flatMap((e) => e.locations).filter((l, i, arr) => arr.findIndex((x) => x.id === l.id) === i)
    : locations;

  return (
    <div className="h-full flex flex-col">
      <header className="h-14 border-b flex items-center px-4 gap-4 bg-white z-10">
        <h1 className="text-lg font-bold whitespace-nowrap">HiSMap</h1>
        <SearchBar onSearch={setSearchQuery} />
        <FilterPanel onChange={setFilters} />
        {isLoading && <span className="text-sm text-gray-400">加载中...</span>}
      </header>
      <div className="flex-1">
        <MapView locations={displayLocations} onLocationSelect={setSelectedLocationId} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add filter panel with dynasty, type, and era filters"
```

---

## Task 6: Result List Panel (Desktop Sidebar)

**Files:**
- Create: `frontend/src/components/Panel/ResultList.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create ResultList component**

```tsx
// frontend/src/components/Panel/ResultList.tsx
import type { JournalEntry } from "@/types";

interface ResultListProps {
  entries: JournalEntry[];
  onSelect: (id: number) => void;
  selectedId: number | null;
}

export function ResultList({ entries, onSelect, selectedId }: ResultListProps) {
  if (entries.length === 0) {
    return <div className="p-4 text-sm text-gray-400">暂无结果</div>;
  }

  return (
    <div className="overflow-y-auto">
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

- [ ] **Step 2: Integrate into App with sidebar layout**

```tsx
// frontend/src/App.tsx
import { useState } from "react";
import { MapView } from "./components/Map/MapView";
import { SearchBar } from "./components/Search/SearchBar";
import { FilterPanel, type FilterState } from "./components/Filter/FilterPanel";
import { ResultList } from "./components/Panel/ResultList";
import { useEntries, useLocations, useSearch } from "./api/hooks";

export default function App() {
  const [filters, setFilters] = useState<FilterState>({ dynasty: "", locationType: "", era: "" });
  const { data: locations = [], isLoading } = useLocations({
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
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null);

  const displayEntries = searchQuery && searchResults ? searchResults : entries;
  const displayLocations = searchQuery && searchResults
    ? searchResults.flatMap((e) => e.locations).filter((l, i, arr) => arr.findIndex((x) => x.id === l.id) === i)
    : locations;

  return (
    <div className="h-full flex flex-col">
      <header className="h-14 border-b flex items-center px-4 gap-4 bg-white z-10">
        <h1 className="text-lg font-bold whitespace-nowrap">HiSMap</h1>
        <SearchBar onSearch={setSearchQuery} />
        <FilterPanel onChange={setFilters} />
      </header>
      <div className="flex-1 flex">
        {/* Left sidebar — desktop only */}
        <aside className="hidden md:block w-80 border-r overflow-y-auto bg-white">
          <div className="p-3 border-b text-sm text-gray-500">
            {displayEntries.length} 条游记
          </div>
          <ResultList
            entries={displayEntries}
            onSelect={setSelectedEntryId}
            selectedId={selectedEntryId}
          />
        </aside>
        {/* Map */}
        <div className="flex-1">
          <MapView locations={displayLocations} onLocationSelect={setSelectedLocationId} />
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add result list sidebar for desktop layout"
```

---

## Task 7: Entry Detail Drawer

**Files:**
- Create: `frontend/src/components/Panel/EntryDetail.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create EntryDetail component**

```tsx
// frontend/src/components/Panel/EntryDetail.tsx
import { useEntry } from "@/api/hooks";
import { X } from "lucide-react";

interface EntryDetailProps {
  entryId: number;
  onClose: () => void;
}

export function EntryDetail({ entryId, onClose }: EntryDetailProps) {
  const { data: entry, isLoading } = useEntry(entryId);

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
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{entry.original_text}</p>
        </div>

        {/* Translations */}
        {entry.modern_translation && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">白话译文</h3>
            <p className="text-sm leading-relaxed">{entry.modern_translation}</p>
          </div>
        )}
        {entry.english_translation && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">English Translation</h3>
            <p className="text-sm leading-relaxed italic">{entry.english_translation}</p>
          </div>
        )}

        {/* Keywords */}
        {entry.keywords && entry.keywords.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">关键词</h3>
            <div className="flex flex-wrap gap-1">
              {entry.keywords.map((kw) => (
                <span key={kw} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Context */}
        {entry.political_context && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">政治背景</h3>
            <p className="text-sm">{entry.political_context}</p>
          </div>
        )}
        {entry.social_environment && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">社会环境</h3>
            <p className="text-sm">{entry.social_environment}</p>
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Integrate EntryDetail into App as a slide-over panel**

Update `frontend/src/App.tsx` — add the detail panel as a right-side drawer that appears when an entry is selected:

```tsx
// frontend/src/App.tsx
import { useState } from "react";
import { MapView } from "./components/Map/MapView";
import { SearchBar } from "./components/Search/SearchBar";
import { FilterPanel, type FilterState } from "./components/Filter/FilterPanel";
import { ResultList } from "./components/Panel/ResultList";
import { EntryDetail } from "./components/Panel/EntryDetail";
import { useEntries, useLocations, useSearch } from "./api/hooks";

export default function App() {
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
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null);

  const displayEntries = searchQuery && searchResults ? searchResults : entries;
  const displayLocations = searchQuery && searchResults
    ? searchResults.flatMap((e) => e.locations).filter((l, i, arr) => arr.findIndex((x) => x.id === l.id) === i)
    : locations;

  return (
    <div className="h-full flex flex-col">
      <header className="h-14 border-b flex items-center px-4 gap-4 bg-white z-10">
        <h1 className="text-lg font-bold whitespace-nowrap">HiSMap</h1>
        <SearchBar onSearch={setSearchQuery} />
        <FilterPanel onChange={setFilters} />
      </header>
      <div className="flex-1 flex relative">
        {/* Left sidebar */}
        <aside className="hidden md:block w-80 border-r overflow-y-auto bg-white z-10">
          <div className="p-3 border-b text-sm text-gray-500">{displayEntries.length} 条游记</div>
          <ResultList entries={displayEntries} onSelect={setSelectedEntryId} selectedId={selectedEntryId} />
        </aside>

        {/* Map */}
        <div className="flex-1">
          <MapView locations={displayLocations} onLocationSelect={setSelectedLocationId} />
        </div>

        {/* Entry detail drawer */}
        {selectedEntryId && (
          <div className="absolute right-0 top-0 bottom-0 w-full md:w-96 bg-white border-l shadow-lg z-20">
            <EntryDetail entryId={selectedEntryId} onClose={() => setSelectedEntryId(null)} />
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add entry detail drawer with original text, translations, and context"
```

---

## Task 8: Mobile Bottom Drawer

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/Panel/ResultList.tsx`

- [ ] **Step 1: Add mobile bottom drawer for entries**

On mobile (< 768px), the sidebar is hidden. Instead, show a bottom drawer that can be pulled up to reveal the entry list and detail.

Update `frontend/src/App.tsx`:

```tsx
// frontend/src/App.tsx
import { useState } from "react";
import { MapView } from "./components/Map/MapView";
import { SearchBar } from "./components/Search/SearchBar";
import { FilterPanel, type FilterState } from "./components/Filter/FilterPanel";
import { ResultList } from "./components/Panel/ResultList";
import { EntryDetail } from "./components/Panel/EntryDetail";
import { useEntries, useLocations, useSearch } from "./api/hooks";
import { ChevronUp, ChevronDown } from "lucide-react";

export default function App() {
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
  const [selectedLocationId, setSelectedLocationId] = useState<number | null>(null);
  const [drawerOpen, setDrawerOpen] = useState(false);

  const displayEntries = searchQuery && searchResults ? searchResults : entries;
  const displayLocations = searchQuery && searchResults
    ? searchResults.flatMap((e) => e.locations).filter((l, i, arr) => arr.findIndex((x) => x.id === l.id) === i)
    : locations;

  return (
    <div className="h-full flex flex-col">
      <header className="h-14 border-b flex items-center px-4 gap-3 bg-white z-10">
        <h1 className="text-lg font-bold whitespace-nowrap">HiSMap</h1>
        <SearchBar onSearch={setSearchQuery} />
        <FilterPanel onChange={setFilters} />
      </header>
      <div className="flex-1 flex relative overflow-hidden">
        {/* Desktop sidebar */}
        <aside className="hidden md:block w-80 border-r overflow-y-auto bg-white z-10">
          <div className="p-3 border-b text-sm text-gray-500">{displayEntries.length} 条游记</div>
          <ResultList entries={displayEntries} onSelect={setSelectedEntryId} selectedId={selectedEntryId} />
        </aside>

        {/* Map */}
        <div className="flex-1">
          <MapView locations={displayLocations} onLocationSelect={setSelectedLocationId} />
        </div>

        {/* Desktop entry detail */}
        {selectedEntryId && (
          <div className="hidden md:block absolute right-0 top-0 bottom-0 w-96 bg-white border-l shadow-lg z-20">
            <EntryDetail entryId={selectedEntryId} onClose={() => setSelectedEntryId(null)} />
          </div>
        )}

        {/* Mobile bottom drawer */}
        <div
          className={`md:hidden absolute bottom-0 left-0 right-0 bg-white border-t shadow-lg transition-transform duration-300 z-20 ${
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
                onSelect={(id) => {
                  setSelectedEntryId(id);
                  setDrawerOpen(true);
                }}
                selectedId={selectedEntryId}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Test responsive layout**

Start dev server: `cd frontend && npm run dev`

- Desktop (wide browser): Should see left sidebar + map + detail drawer
- Mobile (narrow browser or dev tools): Should see full-screen map + bottom drawer handle

- [ ] **Step 3: Commit**

```bash
git add frontend/src/
git commit -m "feat: add mobile bottom drawer with responsive layout"
```

---

## Summary

This plan produces a fully functional frontend with:

- **Leaflet map** with OpenStreetMap tiles and location markers
- **Marker popups** showing location name, summary, and type
- **Search bar** that filters map markers by keyword
- **Filter panel** for dynasty, location type, and era context
- **Result list sidebar** (desktop) showing matching entries
- **Entry detail drawer** with original text, translations, keywords, and context
- **Mobile bottom drawer** with pull-up interaction
- **TanStack Query** for data fetching with caching
- **Responsive layout** — desktop sidebar, mobile bottom drawer

**Next plans:**
1. **Location Detail Page** — Four-layer detail (quick info, original/translation, modern explanation, relations)
2. **Admin CMS UI** — Simple admin interface
3. **Data Pipeline** — PDF processing and LLM extraction
