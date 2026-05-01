interface MarkerLocation {
  id: number;
  name: string;
  ancient_name?: string | null;
  one_line_summary?: string | null;
  location_type?: string | null;
  ancient_region?: string | null;
}

interface MarkerPopupProps {
  location: MarkerLocation;
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
