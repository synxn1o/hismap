import { useNavigate } from "react-router-dom";
import type { MapLocation } from "./MapView";

interface MarkerPopupProps {
  location: MapLocation;
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
