import { ArrowLeft, ExternalLink } from "lucide-react";
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
