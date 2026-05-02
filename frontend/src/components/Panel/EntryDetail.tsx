import { useEntry, useStoryContent } from "@/api/hooks";
import { Link } from "react-router-dom";
import { X } from "lucide-react";

interface EntryDetailProps {
  entryId: number;
  onClose: () => void;
}

export function EntryDetail({ entryId, onClose }: EntryDetailProps) {
  const { data: entry, isLoading } = useEntry(entryId);
  const { data: story } = useStoryContent(entry?.original_text ?? null);

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
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {story?.original_text ?? entry.original_text}
          </p>
        </div>

        {/* Excerpt */}
        {entry.excerpt_original && (
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-1">Excerpt</h4>
            <p className="text-sm text-gray-600 italic">{entry.excerpt_original}</p>
            {entry.excerpt_translation && (
              <p className="text-sm text-gray-500 mt-1">{entry.excerpt_translation}</p>
            )}
          </div>
        )}

        {/* Summary */}
        {(entry.summary_chinese || entry.summary_english) && (
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-1">Summary</h4>
            {entry.summary_chinese && <p className="text-sm text-gray-600">{entry.summary_chinese}</p>}
            {entry.summary_english && <p className="text-sm text-gray-500 mt-1">{entry.summary_english}</p>}
          </div>
        )}

        {/* Persons */}
        {entry.persons && entry.persons.length > 0 && (
          <div className="mb-4">
            <h4 className="text-sm font-semibold text-gray-700 mb-1">Persons</h4>
            <div className="flex flex-wrap gap-1">
              {entry.persons.map((p, i) => (
                <span key={i} className="px-2 py-0.5 bg-blue-100 text-blue-800 rounded text-xs">{p}</span>
              ))}
            </div>
          </div>
        )}

        {/* View Full Text button */}
        <Link
          to={`/entries/${entry.id}`}
          className="inline-flex items-center gap-1 text-sm text-blue-600 hover:text-blue-800 mt-2"
        >
          View Full Text →
        </Link>

        {/* Keywords */}
        {(story?.entities?.keywords ?? entry.keywords) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">关键词</h3>
            <div className="flex flex-wrap gap-1">
              {(story?.entities?.keywords ?? entry.keywords)?.map((kw) => (
                <span key={kw} className="text-xs bg-blue-50 text-blue-700 px-2 py-0.5 rounded">
                  {kw}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* Credibility */}
        {story?.credibility && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">可信度</h3>
            {story.credibility.credibility_score !== undefined && (
              <p className="text-sm">评分: {story.credibility.credibility_score}</p>
            )}
            {story.credibility.notes && (
              <p className="text-sm text-gray-600">{story.credibility.notes}</p>
            )}
          </div>
        )}

        {/* Context */}
        {(story?.credibility?.political_context ?? entry.political_context) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">政治背景</h3>
            <p className="text-sm">{story?.credibility?.political_context ?? entry.political_context}</p>
          </div>
        )}
        {(story?.credibility?.social_environment ?? entry.social_environment) && (
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-1">社会环境</h3>
            <p className="text-sm">{story?.credibility?.social_environment ?? entry.social_environment}</p>
          </div>
        )}
      </div>
    </div>
  );
}
