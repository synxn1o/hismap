# Frontend: Pipeline Revision UI Updates

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Update frontend components to display the new excerpt/summary fields from the revised pipeline, add a language preference toggle, and create an independent entry detail page.

**Architecture:** Replace `modern_translation`/`english_translation` display with `excerpt_original`/`excerpt_translation` + bilingual summary. Add `/entries/:id` route for full text viewing. Add localStorage-backed language preference toggle.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, React Router, React Query

**Depends on:** Pipeline revision plan (`2026-05-02-pipeline-revision.md`) — Tasks 1-16 must be complete first (backend schema changes and Alembic migration must be applied).

**Branch:** `feat/frontend-pipeline-revision`

---

## File Structure

- `frontend/src/types/index.ts` — **Modify:69-86** — update `JournalEntry` interface
- `frontend/src/lib/language.ts` — **Create** — language preference utility
- `frontend/src/components/Panel/ResultList.tsx` — **Modify** — show excerpt+summary instead of original_text
- `frontend/src/components/Panel/EntryDetail.tsx` — **Modify** — show excerpt+summary, add "View Full Text" button
- `frontend/src/components/Panel/EntryCard.tsx` — **Modify** — use new fields in tab display
- `frontend/src/components/Filter/FilterPanel.tsx` — **Modify** — add language toggle
- `frontend/src/pages/EntryPage.tsx` — **Create** — independent entry detail page
- `frontend/src/App.tsx` — **Modify** — add `/entries/:id` route, wire language preference

---

## Task 1: Update TypeScript Types

**Files:**
- Modify: `frontend/src/types/index.ts:69-86`

- [ ] **Step 1: Update JournalEntry interface**

In `frontend/src/types/index.ts`, replace the `JournalEntry` interface (lines 69-86):

```typescript
export interface JournalEntry {
  id: number;
  book_id: number | null;
  title: string;
  original_text: string;
  excerpt_original: string | null;
  excerpt_translation: string | null;
  summary_chinese: string | null;
  summary_english: string | null;
  chapter_reference: string | null;
  keywords: string[] | null;
  keyword_annotations: Record<string, unknown> | null;
  persons: string[] | null;
  dates: string[] | null;
  era_context: string | null;
  political_context: string | null;
  religious_context: string | null;
  social_environment: string | null;
  visit_date_approximate: string | null;
  credibility: Record<string, unknown> | null;
  annotations: unknown[] | null;
  locations: LocationBrief[];
  authors: AuthorBrief[];
}
```

- [ ] **Step 2: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: Compilation errors in components that reference removed fields (will fix in next tasks)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types/index.ts
git commit -m "feat(frontend): update JournalEntry type with excerpt/summary fields"
```

---

## Task 2: Update ResultList and EntryDetail Components

**Files:**
- Modify: `frontend/src/components/Panel/ResultList.tsx`
- Modify: `frontend/src/components/Panel/EntryDetail.tsx`
- Modify: `frontend/src/components/Panel/EntryCard.tsx`

- [ ] **Step 1: Update ResultList to show excerpt+summary**

In `frontend/src/components/Panel/ResultList.tsx`, replace the entry display (currently shows `original_text` with 2-line clamp) to show `excerpt_original` + `summary_chinese` (or `summary_english` based on language preference):

Replace the entry content section with:

```tsx
<div className="text-xs text-gray-600 line-clamp-2">
  {entry.excerpt_original || entry.original_text?.slice(0, 100)}
</div>
{(entry.summary_chinese || entry.summary_english) && (
  <div className="text-xs text-gray-500 line-clamp-1 mt-0.5">
    {entry.summary_chinese || entry.summary_english}
  </div>
)}
```

- [ ] **Step 2: Update EntryDetail to show excerpt+summary with "View Full Text" button**

In `frontend/src/components/Panel/EntryDetail.tsx`:

Replace the translation sections with excerpt+summary display:

```tsx
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
```

Add `import { Link } from 'react-router-dom';` at the top.

- [ ] **Step 3: Update EntryCard to use new fields**

In `frontend/src/components/Panel/EntryCard.tsx`, replace the tab content to show excerpt+summary instead of `modern_translation`/`english_translation`.

- [ ] **Step 4: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors (or only errors in files not yet updated)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/Panel/ResultList.tsx frontend/src/components/Panel/EntryDetail.tsx frontend/src/components/Panel/EntryCard.tsx
git commit -m "feat(frontend): update ResultList and EntryDetail to show excerpt/summary"
```

---

## Task 3: Create EntryPage and Add Route

**Files:**
- Create: `frontend/src/pages/EntryPage.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create EntryPage component**

Create `frontend/src/pages/EntryPage.tsx`:

```tsx
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
            {entry.credibility.era_context && (
              <p className="text-xs text-gray-600 mb-1"><strong>Era:</strong> {String(entry.credibility.era_context)}</p>
            )}
            {entry.credibility.political_context && (
              <p className="text-xs text-gray-600 mb-1"><strong>Political:</strong> {String(entry.credibility.political_context)}</p>
            )}
            {entry.credibility.social_environment && (
              <p className="text-xs text-gray-600 mb-1"><strong>Social:</strong> {String(entry.credibility.social_environment)}</p>
            )}
            {entry.credibility.credibility_score !== undefined && (
              <p className="text-xs text-gray-600 mb-1"><strong>Score:</strong> {String(entry.credibility.credibility_score)}</p>
            )}
            {entry.credibility.notes && (
              <p className="text-xs text-gray-500 mt-2">{String(entry.credibility.notes)}</p>
            )}
          </div>
        )}

        {/* Annotations */}
        {entry.annotations && entry.annotations.length > 0 && (
          <div className="bg-white rounded-lg p-4 shadow-sm mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-2">Sources & Annotations</h3>
            {entry.annotations.map((ann: Record<string, unknown>, i: number) => (
              <div key={i} className="mb-2 last:mb-0">
                {ann.url ? (
                  <a href={String(ann.url)} target="_blank" rel="noopener noreferrer" className="text-xs text-blue-600 hover:underline">
                    {String(ann.query || ann.url)}
                  </a>
                ) : (
                  <span className="text-xs text-gray-600">{String(ann.query || '')}</span>
                )}
                {ann.snippet && <p className="text-xs text-gray-500 mt-0.5">{String(ann.snippet)}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Add route to App.tsx**

In `frontend/src/App.tsx`, add the import and route:

Add import: `import EntryPage from './pages/EntryPage';`

Add route (inside `<Routes>`):
```tsx
<Route path="/entries/:id" element={<EntryPage />} />
```

- [ ] **Step 3: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 4: Verify build succeeds**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: Build succeeds

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/EntryPage.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add EntryPage with full text view at /entries/:id"
```

---

## Task 4: Language Preference Toggle

**Files:**
- Create: `frontend/src/lib/language.ts`
- Modify: `frontend/src/components/Panel/ResultList.tsx`
- Modify: `frontend/src/components/Panel/EntryDetail.tsx`
- Modify: `frontend/src/components/Filter/FilterPanel.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create language preference utility**

Create `frontend/src/lib/language.ts`:

```typescript
export type Language = 'zh' | 'en';

const STORAGE_KEY = 'hismap_language';

export function getLanguage(): Language {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'zh' || stored === 'en') return stored;
  return 'zh'; // default to Chinese
}

export function setLanguage(lang: Language): void {
  localStorage.setItem(STORAGE_KEY, lang);
}

export function getSummary(entry: { summary_chinese: string | null; summary_english: string | null }, lang: Language): string | null {
  return lang === 'zh' ? entry.summary_chinese : entry.summary_english;
}
```

- [ ] **Step 2: Add language toggle to FilterPanel**

In `frontend/src/components/Filter/FilterPanel.tsx`, add a language toggle button alongside the existing filter toggle. Import `getLanguage`, `setLanguage`, `Language` from `../lib/language`. Add state `const [lang, setLang] = useState<Language>(getLanguage)`. Add a button that toggles between 'zh' and 'en' and calls `setLanguage()` + `onLanguageChange(lang)` callback.

Add `onLanguageChange?: (lang: Language) => void` to the component props.

- [ ] **Step 3: Wire language preference into App.tsx**

In `frontend/src/App.tsx`:
- Add state: `const [language, setLanguage] = useState<Language>(getLanguage)`
- Pass `onLanguageChange={setLanguage}` to `FilterPanel`
- Pass `language` prop to `ResultList` and `EntryDetail`

- [ ] **Step 4: Update ResultList to use language preference**

In `frontend/src/components/Panel/ResultList.tsx`:
- Add `language` prop
- Use `getSummary(entry, language)` instead of `entry.summary_chinese || entry.summary_english`

- [ ] **Step 5: Update EntryDetail to use language preference**

In `frontend/src/components/Panel/EntryDetail.tsx`:
- Add `language` prop
- Show the preferred language summary first, with the other as secondary

- [ ] **Step 6: Verify TypeScript compiles**

Run: `cd frontend && npx tsc --noEmit 2>&1 | head -20`
Expected: No errors

- [ ] **Step 7: Verify build succeeds**

Run: `cd frontend && npm run build 2>&1 | tail -10`
Expected: Build succeeds

- [ ] **Step 8: Commit**

```bash
git add frontend/src/lib/language.ts frontend/src/components/Filter/FilterPanel.tsx frontend/src/components/Panel/ResultList.tsx frontend/src/components/Panel/EntryDetail.tsx frontend/src/App.tsx
git commit -m "feat(frontend): add language preference toggle for summary display"
```
