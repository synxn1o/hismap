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
