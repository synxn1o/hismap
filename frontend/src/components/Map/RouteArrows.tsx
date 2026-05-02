import { useEffect } from "react";
import { useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet-polylinedecorator";

interface RouteLocation {
  latitude: number;
  longitude: number;
  order: number;
}

interface RouteArrowsProps {
  routes: Array<{
    entryId: number;
    locations: RouteLocation[];
    color: string;
  }>;
}

export function RouteArrows({ routes }: RouteArrowsProps) {
  const map = useMap();

  useEffect(() => {
    const layers: L.Layer[] = [];

    routes.forEach((route) => {
      if (route.locations.length < 2) return;

      const sorted = [...route.locations].sort((a, b) => a.order - b.order);
      const latlngs = sorted.map((loc) => L.latLng(loc.latitude, loc.longitude));

      const polyline = L.polyline(latlngs, {
        color: route.color,
        weight: 2,
        opacity: 0.4,
      });

      const decorator = (L as any).polylineDecorator(polyline, {
        patterns: [
          {
            offset: "50%",
            repeat: "100px",
            symbol: (L as any).Symbol.arrowHead({
              pixelSize: 8,
              polygon: false,
              pathOptions: {
                color: route.color,
                weight: 2,
                opacity: 0.6,
              },
            }),
          },
        ],
      });

      layers.push(polyline, decorator);
      map.addLayer(polyline);
      map.addLayer(decorator);
    });

    return () => {
      layers.forEach((layer) => map.removeLayer(layer));
    };
  }, [map, routes]);

  return null;
}
