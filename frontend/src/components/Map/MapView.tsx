import { MapContainer, TileLayer } from "react-leaflet";
import { LocationMarker } from "./LocationMarker";

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
}

interface MapViewProps {
  locations: MapLocation[];
}

export function MapView({ locations }: MapViewProps) {
  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {locations.map((loc) => (
        <LocationMarker key={loc.id} location={loc} />
      ))}
    </MapContainer>
  );
}
