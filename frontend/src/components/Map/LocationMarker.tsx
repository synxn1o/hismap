import { Marker, Popup } from "react-leaflet";
import { MarkerPopup } from "./MarkerPopup";
import L from "leaflet";

// Fix default marker icons in Leaflet + bundler
const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface MarkerLocation {
  id: number;
  name: string;
  latitude: number;
  longitude: number;
  ancient_name?: string | null;
  one_line_summary?: string | null;
  location_type?: string | null;
  ancient_region?: string | null;
}

interface LocationMarkerProps {
  location: MarkerLocation;
  onSelect: (id: number) => void;
}

export function LocationMarker({ location, onSelect }: LocationMarkerProps) {
  return (
    <Marker position={[location.latitude, location.longitude]} icon={defaultIcon}>
      <Popup>
        <MarkerPopup location={location} onSelect={onSelect} />
      </Popup>
    </Marker>
  );
}
