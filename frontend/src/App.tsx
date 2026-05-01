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
