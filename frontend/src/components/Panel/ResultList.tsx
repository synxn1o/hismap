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
