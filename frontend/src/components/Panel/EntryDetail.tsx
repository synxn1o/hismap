import { useEntry } from "@/api/hooks";
import { X } from "lucide-react";

interface EntryDetailProps {
  entryId: number;
  onClose: () => void;
}

export function EntryDetail({ entryId, onClose }: EntryDetailProps) {
  const { data: entry, isLoading } = useEntry(entryId);

  if (isLoading) {
    return (
      <div className="p-4">
        <div className="animate-pulse h-4 bg-gray-200 rounded w-3/4 mb-2" />
        <div className="animate-pulse h-4 bg-gray-200 rounded w-1/2" />
      </div>
    );
  }

  if (!entry) return null;

  return (
    <div className="h-full flex flex-col">
      <div className="flex items-center justify-between p-4 border-b">
        <h2 className="font-bold text-lg">{entry.title}</h2>
        <button onClick={onClose} className="p-1 hover:bg-gray-100 rounded">
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Meta info */}
        <div className="flex flex-wrap gap-2 text-sm text-gray-500">
          {entry.authors.map((a) => (
            <span key={a.id} className="bg-gray-100 px-2 py-0.5 rounded">{a.name}</span>
          ))}
          {entry.book && <span>《{entry.book.title}》</span>}
          {entry.chapter_reference && <span>{entry.chapter_reference}</span>}
          {entry.era_context && <span>{entry.era_context}</span>}
        </div>

        {/* Original text */}
        <div>
          <h3 className="text-sm font-medium text-gray-500 mb-1">原文</h3>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{entry.original_text}</p>
        </div>

        {/* Translations */}
        {entry.modern_translation && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">白话译文</h3>
            <p className="text-sm leading-relaxed">{entry.modern_translation}</p>
          </div>
        )}
        {entry.english_translation && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">English Translation</h3>
            <p className="text-sm leading-relaxed italic">{entry.english_translation}</p>
          </div>
        )}

        {/* Keywords */}
        {entry.keywords && entry.keywords.length > 0 && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">关键词</h3>
            <div className="flex flex-wrap gap-1">
              {entry.keywords.map((kw) => (
                <span key={kw} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Context */}
        {entry.political_context && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">政治背景</h3>
            <p className="text-sm">{entry.political_context}</p>
          </div>
        )}
        {entry.social_environment && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">社会环境</h3>
            <p className="text-sm">{entry.social_environment}</p>
          </div>
        )}
      </div>
    </div>
  );
}
