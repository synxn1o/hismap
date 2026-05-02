# HiSMap Location Detail Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the four-layer location detail page: Quick Understanding, Original Text & Translations, Modern Explanation, and Relationship Network — the core content page of HiSMap.

**Architecture:** A full-page or slide-over panel that loads when a user clicks a location marker or navigates to `/locations/:id`. Uses TanStack Query to fetch location detail (with nested entries and related locations). Four sections rendered as scrollable cards with tab switching for translations.

**Tech Stack:** React 18, TypeScript, TanStack Query, Tailwind CSS, lucide-react icons

---

## File Structure

```
frontend/src/
├── components/
│   ├── Panel/
│   │   ├── LocationDetail.tsx       # Main four-layer detail page
│   │   ├── QuickInfo.tsx            # Layer 1: quick understanding
│   │   ├── EntryCard.tsx            # Layer 2: single entry with tab switching
│   │   ├── ModernExplanation.tsx    # Layer 3: academic content
│   │   └── RelationNetwork.tsx      # Layer 4: related locations
│   └── Map/
│       └── MapView.tsx              # Modify: zoom to selected location
├── pages/
│   └── LocationPage.tsx             # Standalone page route /locations/:id
└── App.tsx                          # Add router
```

---

## Task 1: Add React Router

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/pages/LocationPage.tsx`

- [ ] **Step 1: Install react-router-dom**

Run: `cd frontend && npm install react-router-dom`

- [ ] **Step 2: Add routes to App.tsx**

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";
import { MapView } from "./components/Map/MapView";
import { SearchBar } from "./components/Search/SearchBar";
import { FilterPanel, type FilterState } from "./components/Filter/FilterPanel";
import { ResultList } from "./components/Panel/ResultList";
import { EntryDetail } from "./components/Panel/EntryDetail";
import { LocationPage } from "./pages/LocationPage";
import { useEntries, useLocations, useSearch } from "./api/hooks";
import { ChevronUp, ChevronDown } from "lucide-react";

const queryClient = new QueryClient();

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
        <aside className="hidden md:block w-80 border-r overflow-y-auto bg-white z-10">
          <div className="p-3 border-b text-sm text-gray-500">{displayEntries.length} 条游记</div>
          <ResultList entries={displayEntries} onSelect={setSelectedEntryId} selectedId={selectedEntryId} />
        </aside>
        <div className="flex-1">
          <MapView locations={displayLocations} onLocationSelect={() => {}} />
        </div>
        {selectedEntryId && (
          <div className="hidden md:block absolute right-0 top-0 bottom-0 w-96 bg-white border-l shadow-lg z-20">
            <EntryDetail entryId={selectedEntryId} onClose={() => setSelectedEntryId(null)} />
          </div>
        )}
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
                onSelect={(id) => { setSelectedEntryId(id); setDrawerOpen(true); }}
                selectedId={selectedEntryId}
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

Note: The `main.tsx` QueryClientProvider wrapping needs to be removed since it's now in App.tsx.

- [ ] **Step 3: Update main.tsx**

```tsx
// frontend/src/main.tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
```

- [ ] **Step 4: Create placeholder LocationPage**

```tsx
// frontend/src/pages/LocationPage.tsx
import { useParams, useNavigate } from "react-router-dom";
import { useLocation } from "@/api/hooks";
import { LocationDetail } from "@/components/Panel/LocationDetail";

export function LocationPage() {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: location, isLoading } = useLocation(Number(id));

  if (isLoading) {
    return <div className="h-full flex items-center justify-center">加载中...</div>;
  }

  if (!location) {
    return (
      <div className="h-full flex flex-col items-center justify-center gap-4">
        <p className="text-gray-500">地点未找到</p>
        <button onClick={() => navigate("/")} className="text-blue-600 underline">返回地图</button>
      </div>
    );
  }

  return <LocationDetail location={location} onBack={() => navigate("/")} />;
}
```

- [ ] **Step 5: Commit**

```bash
git add frontend/
git commit -m "feat: add react-router with location detail page route"
```

---

## Task 2: Quick Info Section (Layer 1)

**Files:**
- Create: `frontend/src/components/Panel/QuickInfo.tsx`

- [ ] **Step 1: Create QuickInfo component**

```tsx
// frontend/src/components/Panel/QuickInfo.tsx
import { MapPin, Users, BookOpen, Globe } from "lucide-react";
import type { LocationDetail as LocationDetailType } from "@/types";

interface QuickInfoProps {
  location: LocationDetailType;
}

export function QuickInfo({ location }: QuickInfoProps) {
  return (
    <div className="p-4 border-b bg-gray-50">
      {/* Location name */}
      <div className="mb-3">
        <h1 className="text-xl font-bold mb-1">{location.name}</h1>
        {location.ancient_name && location.ancient_name !== location.name && (
          <p className="text-sm text-gray-500">古称: {location.ancient_name}</p>
        )}
        {location.modern_name && location.modern_name !== location.name && (
          <p className="text-sm text-gray-500">今称: {location.modern_name}</p>
        )}
      </div>

      {/* One-line summary */}
      {location.one_line_summary && (
        <p className="text-sm text-gray-700 mb-3 italic border-l-2 border-blue-300 pl-3">
          {location.one_line_summary}
        </p>
      )}

      {/* Quick facts */}
      <div className="grid grid-cols-2 gap-2 text-sm">
        {location.location_type && (
          <div className="flex items-center gap-1.5 text-gray-600">
            <MapPin className="h-4 w-4 text-gray-400" />
            {location.location_type}
          </div>
        )}
        {location.ancient_region && (
          <div className="flex items-center gap-1.5 text-gray-600">
            <Globe className="h-4 w-4 text-gray-400" />
            {location.ancient_region}
          </div>
        )}
        <div className="flex items-center gap-1.5 text-gray-600">
          <MapPin className="h-4 w-4 text-gray-400" />
          {location.latitude.toFixed(4)}, {location.longitude.toFixed(4)}
        </div>
        {location.entries.length > 0 && (
          <div className="flex items-center gap-1.5 text-gray-600">
            <BookOpen className="h-4 w-4 text-gray-400" />
            {location.entries.length} 条游记
          </div>
        )}
      </div>

      {/* Related travelers */}
      {location.entries.length > 0 && (
        <div className="mt-3">
          <p className="text-xs text-gray-400 mb-1">相关旅行者</p>
          <div className="flex flex-wrap gap-1">
            {[...new Set(location.entries.flatMap((e) => e.authors.map((a) => a.name)))].map((name) => (
              <span key={name} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded-full">
                {name}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Panel/QuickInfo.tsx
git commit -m "feat: add QuickInfo section for location detail page"
```

---

## Task 3: Entry Card with Translation Tabs (Layer 2)

**Files:**
- Create: `frontend/src/components/Panel/EntryCard.tsx`

- [ ] **Step 1: Create EntryCard component**

```tsx
// frontend/src/components/Panel/EntryCard.tsx
import { useState } from "react";
import type { JournalEntry } from "@/types";

type TranslationTab = "original" | "english" | "modern";

interface EntryCardProps {
  entry: JournalEntry;
}

export function EntryCard({ entry }: EntryCardProps) {
  const [activeTab, setActiveTab] = useState<TranslationTab>("original");

  const tabs: { key: TranslationTab; label: string; available: boolean }[] = [
    { key: "original", label: "原文", available: true },
    { key: "english", label: "English", available: !!entry.english_translation },
    { key: "modern", label: "白话译文", available: !!entry.modern_translation },
  ];

  const availableTabs = tabs.filter((t) => t.available);

  const activeContent: Record<TranslationTab, string | null> = {
    original: entry.original_text,
    english: entry.english_translation,
    modern: entry.modern_translation,
  };

  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Header */}
      <div className="p-3 bg-gray-50 border-b">
        <div className="flex items-center justify-between">
          <div>
            {entry.authors.map((a) => (
              <span key={a.id} className="text-sm font-medium mr-2">{a.name}</span>
            ))}
            {entry.visit_date_approximate && (
              <span className="text-xs text-gray-400">{entry.visit_date_approximate}年</span>
            )}
          </div>
        </div>
        {entry.book && (
          <p className="text-xs text-gray-500 mt-0.5">
            《{entry.book.title}》{entry.chapter_reference && ` ${entry.chapter_reference}`}
          </p>
        )}
      </div>

      {/* Tabs */}
      {availableTabs.length > 1 && (
        <div className="flex border-b">
          {availableTabs.map((tab) => (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={`px-4 py-2 text-sm ${
                activeTab === tab.key
                  ? "border-b-2 border-blue-500 text-blue-600 font-medium"
                  : "text-gray-500 hover:text-gray-700"
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>
      )}

      {/* Content */}
      <div className="p-3">
        <p className="text-sm leading-relaxed whitespace-pre-wrap">
          {activeContent[activeTab]}
        </p>
      </div>

      {/* Keywords */}
      {entry.keywords && entry.keywords.length > 0 && (
        <div className="px-3 pb-3">
          <div className="flex flex-wrap gap-1">
            {entry.keywords.map((kw) => (
              <span key={kw} className="text-xs bg-amber-50 text-amber-700 px-2 py-0.5 rounded">
                {kw}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Panel/EntryCard.tsx
git commit -m "feat: add EntryCard with translation tab switching"
```

---

## Task 4: Modern Explanation Section (Layer 3)

**Files:**
- Create: `frontend/src/components/Panel/ModernExplanation.tsx`

- [ ] **Step 1: Create ModernExplanation component**

```tsx
// frontend/src/components/Panel/ModernExplanation.tsx
import { BookOpen, AlertTriangle, CheckCircle, HelpCircle } from "lucide-react";
import type { LocationDetail as LocationDetailType } from "@/types";

interface ModernExplanationProps {
  location: LocationDetailType;
}

export function ModernExplanation({ location }: ModernExplanationProps) {
  const sections = [
    {
      title: "古今对应",
      icon: MapPin,
      content: location.location_rationale,
    },
    {
      title: "学术争议",
      icon: AlertTriangle,
      content: location.academic_disputes,
    },
    {
      title: "可信度分析",
      icon: CheckCircle,
      content: location.credibility_notes,
    },
    {
      title: "今日遗迹",
      icon: HelpCircle,
      content: location.today_remains,
    },
  ].filter((s) => s.content);

  if (sections.length === 0) {
    return null;
  }

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-3">现代解释</h2>
      <div className="space-y-3">
        {sections.map((section) => (
          <div key={section.title} className="border rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <section.icon className="h-4 w-4 text-gray-400" />
              <h3 className="text-sm font-medium">{section.title}</h3>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{section.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

// Fix missing import
import { MapPin } from "lucide-react";
```

Wait, that has a duplicate import. Let me fix.

```tsx
// frontend/src/components/Panel/ModernExplanation.tsx
import { BookOpen, AlertTriangle, CheckCircle, HelpCircle, MapPin } from "lucide-react";
import type { LocationDetail as LocationDetailType } from "@/types";

interface ModernExplanationProps {
  location: LocationDetailType;
}

export function ModernExplanation({ location }: ModernExplanationProps) {
  const sections = [
    { title: "古今对应", icon: MapPin, content: location.location_rationale },
    { title: "学术争议", icon: AlertTriangle, content: location.academic_disputes },
    { title: "可信度分析", icon: CheckCircle, content: location.credibility_notes },
    { title: "今日遗迹", icon: HelpCircle, content: location.today_remains },
  ].filter((s) => s.content);

  if (sections.length === 0) return null;

  return (
    <div className="p-4">
      <h2 className="text-lg font-bold mb-3">现代解释</h2>
      <div className="space-y-3">
        {sections.map((section) => (
          <div key={section.title} className="border rounded-lg p-3">
            <div className="flex items-center gap-2 mb-2">
              <section.icon className="h-4 w-4 text-gray-400" />
              <h3 className="text-sm font-medium">{section.title}</h3>
            </div>
            <p className="text-sm text-gray-700 leading-relaxed">{section.content}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Panel/ModernExplanation.tsx
git commit -m "feat: add ModernExplanation section for location detail"
```

---

## Task 5: Relation Network Section (Layer 4)

**Files:**
- Create: `frontend/src/components/Panel/RelationNetwork.tsx`

- [ ] **Step 1: Create RelationNetwork component**

```tsx
// frontend/src/components/Panel/RelationNetwork.tsx
import { useNavigate } from "react-router-dom";
import { ArrowRight, Network } from "lucide-react";
import type { LocationDetail as LocationDetailType } from "@/types";

interface RelationNetworkProps {
  location: LocationDetailType;
}

export function RelationNetwork({ location }: RelationNetworkProps) {
  const navigate = useNavigate();

  if (location.related_locations.length === 0) return null;

  return (
    <div className="p-4">
      <div className="flex items-center gap-2 mb-3">
        <Network className="h-5 w-5 text-gray-400" />
        <h2 className="text-lg font-bold">关系网络</h2>
      </div>
      <div className="space-y-2">
        {location.related_locations.map((rel) => (
          <button
            key={rel.id}
            onClick={() => navigate(`/locations/${rel.id}`)}
            className="w-full flex items-center justify-between p-3 border rounded-lg hover:bg-gray-50 transition-colors text-left"
          >
            <div>
              <p className="text-sm font-medium">{rel.name}</p>
              <p className="text-xs text-gray-500">{rel.relation_type}</p>
              {rel.description && (
                <p className="text-xs text-gray-400 mt-0.5">{rel.description}</p>
              )}
            </div>
            <ArrowRight className="h-4 w-4 text-gray-400" />
          </button>
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Panel/RelationNetwork.tsx
git commit -m "feat: add RelationNetwork section for location detail"
```

---

## Task 6: Location Detail Container

**Files:**
- Create: `frontend/src/components/Panel/LocationDetail.tsx`
- Modify: `frontend/src/components/Panel/LocationDetail.tsx`

- [ ] **Step 1: Create LocationDetail container**

```tsx
// frontend/src/components/Panel/LocationDetail.tsx
import { ArrowLeft, MapPin, ExternalLink } from "lucide-react";
import type { LocationDetail as LocationDetailType } from "@/types";
import { QuickInfo } from "./QuickInfo";
import { EntryCard } from "./EntryCard";
import { ModernExplanation } from "./ModernExplanation";
import { RelationNetwork } from "./RelationNetwork";

interface LocationDetailProps {
  location: LocationDetailType;
  onBack: () => void;
}

export function LocationDetail({ location, onBack }: LocationDetailProps) {
  return (
    <div className="h-full flex flex-col bg-white">
      {/* Top bar */}
      <div className="flex items-center gap-2 p-3 border-b">
        <button onClick={onBack} className="p-1 hover:bg-gray-100 rounded">
          <ArrowLeft className="h-5 w-5" />
        </button>
        <h2 className="font-bold text-base flex-1">{location.name}</h2>
        <a
          href={`https://www.openstreetmap.org/?mlat=${location.latitude}&mlon=${location.longitude}#map=14/${location.latitude}/${location.longitude}`}
          target="_blank"
          rel="noopener noreferrer"
          className="p-1 hover:bg-gray-100 rounded text-gray-400 hover:text-gray-600"
          title="在 OpenStreetMap 中查看"
        >
          <ExternalLink className="h-4 w-4" />
        </a>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Layer 1: Quick Understanding */}
        <QuickInfo location={location} />

        {/* Layer 2: Original Text & Translations */}
        {location.entries.length > 0 && (
          <div className="p-4">
            <h2 className="text-lg font-bold mb-3">原文与译文</h2>
            <div className="space-y-3">
              {location.entries.map((entry) => (
                <EntryCard key={entry.id} entry={entry} />
              ))}
            </div>
          </div>
        )}

        {/* Layer 3: Modern Explanation */}
        <ModernExplanation location={location} />

        {/* Layer 4: Relation Network */}
        <RelationNetwork location={location} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/Panel/LocationDetail.tsx
git commit -m "feat: add LocationDetail container with four-layer structure"
```

---

## Task 7: Wire Location Marker Clicks to Detail Page

**Files:**
- Modify: `frontend/src/components/Map/MarkerPopup.tsx`
- Modify: `frontend/src/components/Map/MapView.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Update MarkerPopup to navigate to location page**

```tsx
// frontend/src/components/Map/MarkerPopup.tsx
import { useNavigate } from "react-router-dom";
import type { Location } from "@/types";

interface MarkerPopupProps {
  location: Location;
}

export function MarkerPopup({ location }: MarkerPopupProps) {
  const navigate = useNavigate();

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
        onClick={() => navigate(`/locations/${location.id}`)}
        className="mt-2 text-sm text-blue-600 hover:text-blue-800 underline"
      >
        查看详情
      </button>
    </div>
  );
}
```

- [ ] **Step 2: Update MapView to remove onLocationSelect prop**

```tsx
// frontend/src/components/Map/MapView.tsx
import { MapContainer, TileLayer } from "react-leaflet";
import type { Location } from "@/types";
import { LocationMarker } from "./LocationMarker";

const DEFAULT_CENTER: [number, number] = [35.0, 105.0];
const DEFAULT_ZOOM = 4;

interface MapViewProps {
  locations: Location[];
}

export function MapView({ locations }: MapViewProps) {
  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {locations.map((loc) => (
        <LocationMarker key={loc.id} location={loc} />
      ))}
    </MapContainer>
  );
}
```

- [ ] **Step 3: Update LocationMarker to remove onSelect prop**

```tsx
// frontend/src/components/Map/LocationMarker.tsx
import { Marker, Popup } from "react-leaflet";
import type { Location } from "@/types";
import { MarkerPopup } from "./MarkerPopup";
import L from "leaflet";

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
}

export function LocationMarker({ location }: LocationMarkerProps) {
  return (
    <Marker position={[location.latitude, location.longitude]} icon={defaultIcon}>
      <Popup>
        <MarkerPopup location={location} />
      </Popup>
    </Marker>
  );
}
```

- [ ] **Step 4: Update App.tsx to remove onLocationSelect from MapView calls**

Remove `onLocationSelect` prop from all `<MapView>` calls in App.tsx.

- [ ] **Step 5: Verify navigation flow**

Start dev server: `cd frontend && npm run dev`

1. Homepage shows map with markers
2. Click a marker → popup shows
3. Click "查看详情" → navigates to `/locations/:id`
4. Location detail page shows four layers
5. Click back arrow → returns to homepage
6. Click related location → navigates to that location

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat: wire location marker clicks to detail page navigation"
```

---

## Summary

This plan produces:

- **React Router** with `/` (homepage) and `/locations/:id` (detail page)
- **QuickInfo section** — name, ancient/modern names, summary, coordinates, traveler list
- **EntryCard with tabs** — original text, English translation, modern translation, keywords
- **ModernExplanation section** — location rationale, academic disputes, credibility, today's remains
- **RelationNetwork section** — clickable list of related locations with navigation
- **Navigation flow** — marker popup → detail page → back to map → related locations

**Next plans:**
1. **Admin CMS UI** — Simple admin interface for content management
2. **Data Pipeline** — PDF processing and LLM extraction
