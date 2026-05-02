import type { JournalEntry } from "@/types";

interface ResultListProps {
  entries: JournalEntry[];
  onSelect: (id: number) => void;
  selectedId: number | null;
  locationFilter?: { lat: number; lng: number; radiusKm: number } | null;
  onClearFilter?: () => void;
}

export function ResultList({ entries, onSelect, selectedId, locationFilter, onClearFilter }: ResultListProps) {
  if (entries.length === 0) {
    return (
      <div className="p-4 text-sm text-gray-400">
        {locationFilter ? "该位置附近暂无游记" : "暂无结果"}
      </div>
    );
  }

  return (
    <div className="overflow-y-auto">
      {locationFilter && (
        <div className="p-2 bg-blue-50 border-b flex items-center justify-between">
          <span className="text-xs text-blue-700">
            显示 {entries.length} 条附近游记
          </span>
          {onClearFilter && (
            <button
              onClick={onClearFilter}
              className="text-xs text-blue-600 hover:text-blue-800 underline"
            >
              清除筛选
            </button>
          )}
        </div>
      )}
      {entries.map((entry) => (
        <button
          key={entry.id}
          onClick={() => onSelect(entry.id)}
          className={`w-full text-left p-3 border-b hover:bg-gray-50 transition-colors ${
            selectedId === entry.id ? "bg-blue-50 border-l-2 border-l-blue-500" : ""
          }`}
        >
          <h3 className="font-medium text-sm mb-1">{entry.title}</h3>
          <div className="text-xs text-gray-600 line-clamp-2">
            {entry.excerpt_original || entry.original_text?.slice(0, 100)}
          </div>
          {(entry.summary_chinese || entry.summary_english) && (
            <div className="text-xs text-gray-500 line-clamp-1 mt-0.5">
              {entry.summary_chinese || entry.summary_english}
            </div>
          )}
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
