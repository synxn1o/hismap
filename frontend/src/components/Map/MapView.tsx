import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-markercluster";
import "react-leaflet-markercluster/styles";
import { LocationMarker } from "./LocationMarker";
import { RouteArrows } from "./RouteArrows";
import { getBookColor } from "@/lib/palettes";
import type { JournalEntry } from "@/types";

const DEFAULT_CENTER: [number, number] = [35.0, 105.0];
const DEFAULT_ZOOM = 4;

export interface MapLocation {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  ancient_name?: string | null;
  one_line_summary?: string | null;
  location_type?: string | null;
  ancient_region?: string | null;
  book_id?: number | null;
  importance?: number;
}

interface FocusTarget {
  locations: Array<{ latitude: number; longitude: number }>;
}

interface MapViewProps {
  locations: MapLocation[];
  focusTarget?: FocusTarget | null;
  entries?: JournalEntry[];
  onMarkerClick?: (location: MapLocation) => void;
}

function MapFocusHandler({ focusTarget }: { focusTarget?: FocusTarget | null }) {
  const map = useMap();

  useEffect(() => {
    if (!focusTarget || focusTarget.locations.length === 0) return;

    if (focusTarget.locations.length === 1) {
      map.flyTo([focusTarget.locations[0].latitude, focusTarget.locations[0].longitude], 8, {
        duration: 1.5,
      });
    } else {
      const bounds = focusTarget.locations.map(
        (loc) => [loc.latitude, loc.longitude] as [number, number]
      );
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 8, duration: 1.5 });
    }
  }, [map, focusTarget]);

  return null;
}

export function MapView({ locations, focusTarget, entries, onMarkerClick }: MapViewProps) {
  // Compute book color for each location
  const locationColors = useMemo(() => {
    const colorMap = new Map<number, string>();
    locations.forEach((loc) => {
      if (loc.book_id && !colorMap.has(loc.id)) {
        colorMap.set(loc.id, getBookColor(loc.book_id));
      }
    });
    return colorMap;
  }, [locations]);

  // Build route data: connect locations across entries within the same book
  const routes = useMemo(() => {
    if (!entries || entries.length === 0) return [];

    // Group entries by book_id
    const byBook = new Map<number, typeof entries>();
    entries.forEach((entry) => {
      const bookId = entry.book_id ?? 0;
      if (!byBook.has(bookId)) byBook.set(bookId, []);
      byBook.get(bookId)!.push(entry);
    });

    const result: Array<{
      entryId: number;
      locations: Array<{ latitude: number; longitude: number; order: number }>;
      color: string;
    }> = [];

    byBook.forEach((bookEntries, bookId) => {
      // Sort by entry id (proxy for chronological order)
      const sorted = [...bookEntries].sort((a, b) => a.id - b.id);

      // Collect all locations in sequence
      const routeLocations: Array<{ latitude: number; longitude: number; order: number }> = [];
      sorted.forEach((entry) => {
        entry.locations.forEach((loc) => {
          if (loc.latitude !== 0 && loc.longitude !== 0) {
            routeLocations.push({
              latitude: loc.latitude,
              longitude: loc.longitude,
              order: routeLocations.length,
            });
          }
        });
      });

      if (routeLocations.length >= 2) {
        result.push({
          entryId: bookId,
          locations: routeLocations,
          color: bookId ? getBookColor(bookId) : "#3B82F6",
        });
      }
    });

    return result;
  }, [entries]);

  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <MapFocusHandler focusTarget={focusTarget} />
      <MarkerClusterGroup
        chunkedLoading
        maxClusterRadius={60}
        spiderfyOnMaxZoom
        showCoverageOnHover={false}
      >
        {locations.map((loc) => (
          <LocationMarker
            key={loc.id}
            location={loc}
            color={locationColors.get(loc.id)}
            onMarkerClick={onMarkerClick}
          />
        ))}
      </MarkerClusterGroup>
      <RouteArrows routes={routes} />
    </MapContainer>
  );
}
