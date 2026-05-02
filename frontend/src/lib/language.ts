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
