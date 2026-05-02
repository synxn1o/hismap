import { useQuery } from "@tanstack/react-query";
import { api } from "./client";

export function useLocations(params?: { type?: string; dynasty?: string }) {
  return useQuery({
    queryKey: ["locations", params],
    queryFn: () => api.getLocations(params),
  });
}

export function useLocation(id: number) {
  return useQuery({
    queryKey: ["location", id],
    queryFn: () => api.getLocation(id),
    enabled: !!id,
  });
}

export function useEntries(params?: { dynasty?: string; author?: string; keyword?: string; era?: string }) {
  return useQuery({
    queryKey: ["entries", params],
    queryFn: () => api.getEntries(params),
  });
}

export function useEntry(id: number) {
  return useQuery({
    queryKey: ["entry", id],
    queryFn: () => api.getEntry(id),
    enabled: !!id,
  });
}

export function useSearch(query: string) {
  return useQuery({
    queryKey: ["search", query],
    queryFn: () => api.search(query),
    enabled: query.length > 0,
  });
}

export function useFilters() {
  return useQuery({
    queryKey: ["filters"],
    queryFn: () => api.getFilters(),
  });
}

export function useAuthors(dynasty?: string) {
  return useQuery({
    queryKey: ["authors", dynasty],
    queryFn: () => api.getAuthors(dynasty),
  });
}

export function useBooks() {
  return useQuery({
    queryKey: ["books"],
    queryFn: () => api.getBooks(),
  });
}

export interface StoryContent {
  id: string;
  title: string;
  original_text: string;
  translations: {
    modern_chinese?: string;
    english?: string;
  };
  entities: {
    locations: Array<{
      name: string;
      modern_name?: string;
      ancient_name?: string;
      lat: number;
      lng: number;
      location_type?: string;
      one_line_summary?: string;
    }>;
    persons: Array<{ name: string; description?: string }>;
    keywords: string[];
  };
  credibility: {
    credibility_score?: number;
    notes?: string;
    era_context?: string;
    political_context?: string;
    religious_context?: string;
    social_environment?: string;
  };
  annotations: Array<{
    importance?: number;
    marker_title?: string;
    short_popup?: string;
    display_category?: string;
  }>;
}

export function useStoryContent(originalText: string | null) {
  return useQuery({
    queryKey: ["storyContent", originalText],
    queryFn: async () => {
      if (!originalText) return null;
      const jsonPath = originalText.replace("pipeline/output/", "");
      const res = await fetch(`/static/output/${jsonPath}`);
      if (!res.ok) throw new Error(`Failed to fetch story: ${res.status}`);
      return res.json() as Promise<StoryContent>;
    },
    enabled: !!originalText,
  });
}
