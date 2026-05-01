export interface Location {
  id: number;
  name: string;
  modern_name: string | null;
  ancient_name: string | null;
  latitude: number;
  longitude: number;
  location_type: string | null;
  ancient_region: string | null;
  one_line_summary: string | null;
  location_rationale: string | null;
  academic_disputes: string | null;
  credibility_notes: string | null;
  today_remains: string | null;
}

export interface RelatedLocation {
  id: number;
  name: string;
  relation_type: string;
  description: string | null;
}

export interface LocationDetail extends Location {
  entries: JournalEntry[];
  related_locations: RelatedLocation[];
}

export interface AuthorBrief {
  id: number;
  name: string;
  dynasty: string | null;
}

export interface Author extends AuthorBrief {
  birth_year: number | null;
  death_year: number | null;
  biography: string | null;
}

export interface AuthorDetail extends Author {
  entries: JournalEntry[];
}

export interface BookBrief {
  id: number;
  title: string;
}

export interface Book extends BookBrief {
  author: string | null;
  dynasty: string | null;
  era_start: number | null;
  era_end: number | null;
  description: string | null;
}

export interface BookDetail extends Book {
  entries: JournalEntry[];
}

export interface LocationBrief {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

export interface JournalEntry {
  id: number;
  book_id: number | null;
  title: string;
  original_text: string;
  modern_translation: string | null;
  english_translation: string | null;
  chapter_reference: string | null;
  keywords: string[] | null;
  keyword_annotations: Record<string, unknown> | null;
  era_context: string | null;
  political_context: string | null;
  religious_context: string | null;
  social_environment: string | null;
  visit_date_approximate: string | null;
  locations: LocationBrief[];
  authors: AuthorBrief[];
}

export interface JournalEntryDetail extends JournalEntry {
  book: BookBrief | null;
}

export interface FilterOptions {
  dynasties: string[];
  authors: string[];
  location_types: string[];
  era_contexts: string[];
}
