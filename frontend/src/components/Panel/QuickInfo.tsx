import { MapPin, BookOpen, Globe } from "lucide-react";
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
