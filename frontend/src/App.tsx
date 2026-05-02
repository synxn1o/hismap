import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState, useMemo, useCallback } from "react";
import { MapView } from "./components/Map/MapView";
import type { MapLocation } from "./components/Map/MapView";
import { SearchBar } from "./components/Search/SearchBar";
import { FilterPanel, type FilterState } from "./components/Filter/FilterPanel";
import { ResultList } from "./components/Panel/ResultList";
import { EntryDetail } from "./components/Panel/EntryDetail";
import { LocationPage } from "./pages/LocationPage";
import EntryPage from "./pages/EntryPage";
import { useEntries, useLocations, useSearch } from "./api/hooks";
import { ChevronUp, ChevronDown } from "lucide-react";

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
          loc.latitude,
          loc.longitude
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
            latitude: loc.latitude,
            longitude: loc.longitude,
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
          <Route path="/entries/:id" element={<EntryPage />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}
