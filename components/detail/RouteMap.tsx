"use client";

import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { useEffect, useMemo } from "react";
import { MapContainer, TileLayer, Polyline, CircleMarker, Marker, Tooltip, useMap } from "react-leaflet";
import type { QuestRequest, Stop } from "@/types/quest";

type Props = {
  stops: Stop[];
  origin: QuestRequest["location"];
  onStopClick?: (stop: Stop) => void;
};

function pin(order: number) {
  return L.divIcon({
    className: "", // drop Leaflet's default white square
    html: `<div class="route-pin">${order}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
  });
}

function FitBounds({ points }: { points: [number, number][] }) {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(L.latLngBounds(points), { padding: [32, 32], maxZoom: 15, animate: false });
  }, [map, points]);
  return null;
}

export default function RouteMap({ stops, origin, onStopClick }: Props) {
  const ordered = useMemo(() => [...stops].sort((a, b) => a.order - b.order), [stops]);
  const points = useMemo<[number, number][]>(
    () => [[origin.lat, origin.lng], ...ordered.map((s): [number, number] => [s.lat, s.lng])],
    [origin.lat, origin.lng, ordered],
  );

  return (
    <MapContainer
      center={points[0]}
      zoom={12}
      zoomSnap={0.25}
      zoomAnimation={false}
      scrollWheelZoom={false}
      zoomControl={false}
      className="quiet-map size-full"
    >
      <TileLayer
        url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
      />
      <Polyline positions={points} pathOptions={{ color: "#ffc72c", weight: 2.5, opacity: 0.9, lineJoin: "round" }} />
      <CircleMarker
        center={points[0]}
        radius={6}
        pathOptions={{ color: "#14161a", weight: 3, fillColor: "#f2f2f0", fillOpacity: 1 }}
      >
        <Tooltip direction="right" offset={[8, 0]}>
          Start · {origin.label || "Your location"}
        </Tooltip>
      </CircleMarker>
      {ordered.map((s) => (
        <Marker
          key={s.id}
          position={[s.lat, s.lng]}
          icon={pin(s.order)}
          title={`${s.order}. ${s.name}`}
          eventHandlers={{ click: () => onStopClick?.(s) }}
        >
          <Tooltip direction="top" offset={[0, -14]}>
            {s.order}. {s.name}
          </Tooltip>
        </Marker>
      ))}
      <FitBounds points={points} />
    </MapContainer>
  );
}
