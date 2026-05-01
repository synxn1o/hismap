import { Marker, Popup } from "react-leaflet";
import { MarkerPopup } from "./MarkerPopup";
import type { MapLocation } from "./MapView";
import L from "leaflet";

const defaultIcon = L.icon({
  iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
  iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
  shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png",
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
});

interface LocationMarkerProps {
  location: MapLocation;
}

export function LocationMarker({ location }: LocationMarkerProps) {
  return (
    <Marker position={[location.latitude, location.longitude]} icon={defaultIcon}>
      <Popup>
        <MarkerPopup location={location} />
      </Popup>
    </Marker>
  );
}
