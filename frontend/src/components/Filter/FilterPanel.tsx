import { useFilters } from "@/api/hooks";
import { useState } from "react";
import { SlidersHorizontal } from "lucide-react";
import { getLanguage, setLanguage as storeLanguage, type Language } from "@/lib/language";

export interface FilterState {
  dynasty: string;
  locationType: string;
  era: string;
}

interface FilterPanelProps {
  onChange: (filters: FilterState) => void;
  onLanguageChange?: (lang: Language) => void;
}

export function FilterPanel({ onChange, onLanguageChange }: FilterPanelProps) {
  const { data: filterOptions } = useFilters();
  const [filters, setFilters] = useState<FilterState>({ dynasty: "", locationType: "", era: "" });
  const [open, setOpen] = useState(false);
  const [lang, setLang] = useState<Language>(getLanguage);

  const update = (key: keyof FilterState, value: string) => {
    const next = { ...filters, [key]: value };
    setFilters(next);
    onChange(next);
  };

  const toggleLanguage = () => {
    const next: Language = lang === 'zh' ? 'en' : 'zh';
    setLang(next);
    storeLanguage(next);
    onLanguageChange?.(next);
  };

  if (!filterOptions) return null;

  return (
    <div className="relative flex items-center gap-2">
      <button
        onClick={toggleLanguage}
        className="flex items-center gap-1 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50"
        title={lang === 'zh' ? 'Switch to English' : '切换到中文'}
      >
        {lang === 'zh' ? '中/EN' : 'EN/中'}
      </button>
      <button
        onClick={() => setOpen(!open)}
        className="flex items-center gap-1 px-3 py-2 border rounded-lg text-sm hover:bg-gray-50"
      >
        <SlidersHorizontal className="h-4 w-4" />
        筛选
      </button>

      {open && (
        <div className="absolute top-full right-0 mt-2 w-64 bg-white border rounded-lg shadow-lg p-4 z-50">
          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">朝代</label>
            <select
              value={filters.dynasty}
              onChange={(e) => update("dynasty", e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">全部</option>
              {filterOptions.dynasties.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">地点类型</label>
            <select
              value={filters.locationType}
              onChange={(e) => update("locationType", e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">全部</option>
              {filterOptions.location_types.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>

          <div className="mb-3">
            <label className="block text-xs font-medium text-gray-500 mb-1">时代背景</label>
            <select
              value={filters.era}
              onChange={(e) => update("era", e.target.value)}
              className="w-full border rounded px-2 py-1.5 text-sm"
            >
              <option value="">全部</option>
              {filterOptions.era_contexts.map((e) => (
                <option key={e} value={e}>{e}</option>
              ))}
            </select>
          </div>

          <button
            onClick={() => {
              setFilters({ dynasty: "", locationType: "", era: "" });
              onChange({ dynasty: "", locationType: "", era: "" });
            }}
            className="w-full text-sm text-gray-500 hover:text-gray-700"
          >
            重置筛选
          </button>
        </div>
      )}
    </div>
  );
}
