import { useParams, Link } from 'react-router-dom';
import { useEntry } from '../api/hooks';

export default function EntryPage() {
  const { id } = useParams<{ id: string }>();
  const { data: entry, isLoading, error } = useEntry(Number(id));

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-pulse text-gray-400">Loading...</div>
      </div>
    );
  }

  if (error || !entry) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center gap-4">
        <p className="text-gray-500">Entry not found</p>
        <Link to="/" className="text-blue-600 hover:text-blue-800">
          ← Return to map
        </Link>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center gap-3">
          <Link to="/" className="text-gray-500 hover:text-gray-700">
            ← Back
          </Link>
          <h1 className="text-lg font-semibold text-gray-900 truncate">{entry.title}</h1>
        </div>
      </div>

      <div className="max-w-4xl mx-auto px-4 py-6">
        {/* Metadata */}
        <div className="mb-6">
          {entry.authors.length > 0 && (
            <p className="text-sm text-gray-500">
              {entry.authors.map((a) => a.name).join(', ')}
              {entry.era_context && ` · ${entry.era_context}`}
            </p>
          )}
          {entry.chapter_reference && (
            <p className="text-sm text-gray-400">{entry.chapter_reference}</p>
          )}
          {entry.visit_date_approximate && (
            <p className="text-sm text-gray-400">Date: {entry.visit_date_approximate}</p>
          )}
        </div>

        {/* Excerpt + Summary */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Excerpt</h3>
            {entry.excerpt_original && (
              <p className="text-sm text-gray-600 italic mb-2">{entry.excerpt_original}</p>
            )}
            {entry.excerpt_translation && (
              <p className="text-sm text-gray-500">{entry.excerpt_translation}</p>
            )}
          </div>
          <div className="bg-white rounded-lg p-4 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Summary</h3>
            {entry.summary_chinese && (
              <p className="text-sm text-gray-600 mb-2">{entry.summary_chinese}</p>
            )}
            {entry.summary_english && (
              <p className="text-sm text-gray-500">{entry.summary_english}</p>
            )}
          </div>
        </div>

        {/* Full Original Text */}
        <div className="bg-white rounded-lg p-6 shadow-sm mb-8">
          <h3 className="text-sm font-semibold text-gray-700 mb-3">Full Original Text</h3>
          <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
            {entry.original_text}
          </div>
        </div>

        {/* Persons */}
        {entry.persons && entry.persons.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Persons</h3>
            <div className="flex flex-wrap gap-1">
              {entry.persons.map((p, i) => (
                <span key={i} className="px-2 py-1 bg-blue-100 text-blue-800 rounded text-xs">{p}</span>
              ))}
            </div>
          </div>
        )}

        {/* Keywords */}
        {entry.keywords && entry.keywords.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Keywords</h3>
            <div className="flex flex-wrap gap-1">
              {entry.keywords.map((k, i) => (
                <span key={i} className="px-2 py-1 bg-amber-100 text-amber-800 rounded text-xs">{k}</span>
              ))}
            </div>
          </div>
        )}

        {/* Locations */}
        {entry.locations.length > 0 && (
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Locations</h3>
            <div className="flex flex-wrap gap-2">
              {entry.locations.map((loc) => (
                <Link
                  key={loc.id}
                  to={`/locations/${loc.id}`}
                  className="px-3 py-1 bg-green-100 text-green-800 rounded text-xs hover:bg-green-200"
                >
                  {loc.name}
                </Link>
              ))}
            </div>
          </div>
        )}

        {/* Credibility */}
        {entry.credibility && (
          <div className="bg-white rounded-lg p-4 shadow-sm mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Credibility Assessment</h3>
            {entry.credibility.era_context ? (
              <p className="text-xs text-gray-600 mb-1"><strong>Era:</strong> {String(entry.credibility.era_context)}</p>
            ) : null}
            {entry.credibility.political_context ? (
              <p className="text-xs text-gray-600 mb-1"><strong>Political:</strong> {String(entry.credibility.political_context)}</p>
            ) : null}
            {entry.credibility.social_environment ? (
              <p className="text-xs text-gray-600 mb-1"><strong>Social:</strong> {String(entry.credibility.social_environment)}</p>
            ) : null}
            {entry.credibility.credibility_score !== undefined ? (
              <p className="text-xs text-gray-600 mb-1"><strong>Score:</strong> {String(entry.credibility.credibility_score)}</p>
            ) : null}
            {entry.credibility.notes ? (
              <p className="text-xs text-gray-500 mt-2">{String(entry.credibility.notes)}</p>
            ) : null}
          </div>
        )}

        {/* Annotations */}
        {entry.annotations && entry.annotations.length > 0 && (
          <div className="bg-white rounded-lg p-4 shadow-sm mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Sources & Annotations</h3>
            {(entry.annotations as Record<string, unknown>[]).map((ann, i) => (
              <div key={i} className="mb-2 last:mb-0">
                {ann.url ? (
                  <a href={String(ann.url)} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">
                    {String(ann.query || ann.url)}
                  </a>
                ) : (
                  <span className="text-xs text-gray-600">{String(ann.query || '')}</span>
                )}
                {ann.snippet ? <p className="text-xs text-gray-500 mt-0.5">{String(ann.snippet)}</p> : null}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
