import { MapContainer, TileLayer } from "react-leaflet";
import { LocationMarker } from "./LocationMarker";

// Center on ancient Silk Road region
const DEFAULT_CENTER: [number, number] = [35.0, 105.0];
const DEFAULT_ZOOM = 4;

interface MapLocation {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
}

interface MapViewProps {
  locations: MapLocation[];
  onLocationSelect: (id: number) => void;
}

export function MapView({ locations, onLocationSelect }: MapViewProps) {
  return (
    <MapContainer center={DEFAULT_CENTER} zoom={DEFAULT_ZOOM} className="h-full w-full">
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      {locations.map((loc) => (
        <LocationMarker key={loc.id} location={loc} onSelect={onLocationSelect} />
      ))}
    </MapContainer>
  );
}
