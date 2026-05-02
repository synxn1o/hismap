import { Marker, Popup } from "react-leaflet";
import { MarkerPopup } from "./MarkerPopup";
import type { MapLocation } from "./MapView";
import L from "leaflet";

function createColoredIcon(color: string): L.Icon {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 36" width="25" height="41">
    <path d="M12 0C5.4 0 0 5.4 0 12c0 9 12 24 12 24s12-15 12-24C24 5.4 18.6 0 12 0z" fill="${color}"/>
    <circle cx="12" cy="12" r="5" fill="white"/>
  </svg>`;
  return L.icon({
    iconUrl: `data:image/svg+xml;base64,${btoa(svg)}`,
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
  });
}

const defaultIcon = createColoredIcon("#3B82F6");

interface LocationMarkerProps {
  location: MapLocation;
  color?: string;
  onMarkerClick?: (location: MapLocation) => void;
}

export function LocationMarker({ location, color, onMarkerClick }: LocationMarkerProps) {
  const icon = color ? createColoredIcon(color) : defaultIcon;

  return (
    <Marker
      position={[location.latitude, location.longitude]}
      icon={icon}
      eventHandlers={{
        click: () => onMarkerClick?.(location),
      }}
    >
      <Popup>
        <MarkerPopup location={location} onFilterClick={() => onMarkerClick?.(location)} />
      </Popup>
    </Marker>
  );
}
