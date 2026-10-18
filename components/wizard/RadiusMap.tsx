"use client";

import "leaflet/dist/leaflet.css";
import { useEffect } from "react";
import { MapContainer, TileLayer, Circle, CircleMarker, useMap } from "react-leaflet";

const METERS_PER_MILE = 1609.344;
// The view zooms out in steps so the circle visibly grows inside each band.
const BANDS_MILES = [3, 10, 30, 100];

type Props = {
  lat: number;
  lng: number;
  radiusMiles: number;
};

function fitZoom(lat: number, radiusMeters: number, halfPx: number) {
  return Math.log2((156543.03 * Math.cos((lat * Math.PI) / 180) * halfPx) / radiusMeters);
}

function View({ lat, lng, radiusMiles }: Props) {
  const map = useMap();
  const band = BANDS_MILES.find((b) => radiusMiles <= b) ?? BANDS_MILES.at(-1)!;

  useEffect(() => {
    const { x, y } = map.getSize();
    const zoom = fitZoom(lat, band * METERS_PER_MILE * 1.08, Math.min(x, y) / 2);
    map.setView([lat, lng], zoom, { animate: false });
  }, [map, lat, lng, band]);

  return null;
}

export default function RadiusMap({ lat, lng, radiusMiles }: Props) {
  return (
    <MapContainer
      center={[lat, lng]}
      zoom={10}
      zoomSnap={0}
      // Animated zooms can finish after the step unmounts and crash Leaflet, so zoom changes snap.
      zoomAnimation={false}
      dragging={false}
      scrollWheelZoom={false}
      doubleClickZoom={false}
      touchZoom={false}
      boxZoom={false}
      keyboard={false}
      zoomControl={false}
      className="quiet-map size-full"
    >
      <TileLayer
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />
      <Circle
        center={[lat, lng]}
        radius={radiusMiles * METERS_PER_MILE}
        pathOptions={{ color: "#ffc72c", weight: 1.5, fillColor: "#ffc72c", fillOpacity: 0.14 }}
      />
      <CircleMarker
        center={[lat, lng]}
        radius={6}
        pathOptions={{ color: "#14161a", weight: 3, fillColor: "#ffc72c", fillOpacity: 1 }}
      />
      <View lat={lat} lng={lng} radiusMiles={radiusMiles} />
    </MapContainer>
  );
}
