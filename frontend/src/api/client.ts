const BASE = "/api";

async function fetchJSON<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export const api = {
  // Locations
  getLocations: (params?: { type?: string; dynasty?: string }) => {
    const qs = new URLSearchParams();
    if (params?.type) qs.set("type", params.type);
    if (params?.dynasty) qs.set("dynasty", params.dynasty);
    const query = qs.toString();
    return fetchJSON<import("../types").Location[]>(`/locations${query ? `?${query}` : ""}`);
  },

  getLocation: (id: number) =>
    fetchJSON<import("../types").LocationDetail>(`/locations/${id}`),

  // Entries
  getEntries: (params?: { dynasty?: string; author?: string; keyword?: string; era?: string }) => {
    const qs = new URLSearchParams();
    if (params?.dynasty) qs.set("dynasty", params.dynasty);
    if (params?.author) qs.set("author", params.author);
    if (params?.keyword) qs.set("keyword", params.keyword);
    if (params?.era) qs.set("era", params.era);
    const query = qs.toString();
    return fetchJSON<import("../types").JournalEntry[]>(`/entries${query ? `?${query}` : ""}`);
  },

  getEntry: (id: number) =>
    fetchJSON<import("../types").JournalEntryDetail>(`/entries/${id}`),

  // Authors
  getAuthors: (dynasty?: string) => {
    const qs = new URLSearchParams();
    if (dynasty) qs.set("dynasty", dynasty);
    const query = qs.toString();
    return fetchJSON<import("../types").Author[]>(`/authors${query ? `?${query}` : ""}`);
  },

  getAuthor: (id: number) =>
    fetchJSON<import("../types").AuthorDetail>(`/authors/${id}`),

  // Books
  getBooks: () => fetchJSON<import("../types").Book[]>("/books"),
  getBook: (id: number) => fetchJSON<import("../types").BookDetail>(`/books/${id}`),

  // Search
  search: (q: string) =>
    fetchJSON<import("../types").JournalEntry[]>(`/search?q=${encodeURIComponent(q)}`),

  // Filters
  getFilters: () => fetchJSON<import("../types").FilterOptions>("/filters"),
};
