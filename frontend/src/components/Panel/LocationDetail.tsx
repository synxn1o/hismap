import { useLocation } from "@/api/hooks";
import { X } from "lucide-react";

interface LocationDetailProps {
  locationId: number;
  onClose: () => void;
}

export function LocationDetail({ locationId, onClose }: LocationDetailProps) {
  const { data: location, isLoading } = useLocation(locationId);

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="animate-pulse h-4 bg-gray-200 rounded w-3/4 mb-2" />
        <div className="animate-pulse h-4 bg-gray-200 rounded w-1/2" />
      </div>
    );
  }

  if (!location) return null;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="font-bold text-lg">{location.name}</h2>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* 01. Quick Info */}
        <div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-red-600 font-bold text-xs tracking-widest">01.</span>
            <h3 className="text-sm font-bold uppercase">地点概述</h3>
          </div>
          {location.ancient_name && (
            <p className="text-sm text-gray-500">古称: {location.ancient_name}</p>
          )}
          {location.modern_name && (
            <p className="text-sm text-gray-500">今名: {location.modern_name}</p>
          )}
          {location.one_line_summary && (
            <p className="text-sm mt-2">{location.one_line_summary}</p>
          )}
          <div className="flex gap-2 mt-2 text-xs text-gray-400">
            {location.location_type && <span className="bg-gray-100 px-2 py-0.5 rounded">{location.location_type}</span>}
            {location.ancient_region && <span className="bg-gray-100 px-2 py-0.5 rounded">{location.ancient_region}</span>}
          </div>
        </div>

        {/* 02. Academic */}
        {location.location_rationale && (
          <div>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-red-600 font-bold text-xs tracking-widest">02.</span>
              <h3 className="text-sm font-bold uppercase">定位依据</h3>
            </div>
            <p className="text-sm leading-relaxed">{location.location_rationale}</p>
          </div>
        )}

        {/* 03. Disputes */}
        {location.academic_disputes && (
          <div>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-red-600 font-bold text-xs tracking-widest">03.</span>
              <h3 className="text-sm font-bold uppercase">学术争议</h3>
            </div>
            <p className="text-sm leading-relaxed">{location.academic_disputes}</p>
          </div>
        )}

        {/* 04. Related */}
        {location.related_locations && location.related_locations.length > 0 && (
          <div>
            <div className="flex items-baseline gap-2 mb-2">
              <span className="text-red-600 font-bold text-xs tracking-widest">04.</span>
              <h3 className="text-sm font-bold uppercase">关联地点</h3>
            </div>
            <div className="space-y-2">
              {location.related_locations.map((rel) => (
                <div key={rel.id} className="border p-3">
                  <p className="font-medium text-sm">{rel.name}</p>
                  <p className="text-xs text-gray-500">{rel.relation_type}</p>
                  {rel.description && <p className="text-xs text-gray-600 mt-1">{rel.description}</p>}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
