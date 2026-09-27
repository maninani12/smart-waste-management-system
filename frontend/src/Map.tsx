import {
  MapContainer,
  TileLayer,
  CircleMarker,
  Popup,
  useMapEvents,
} from "react-leaflet";
import "leaflet/dist/leaflet.css";
function Picker({ onPick }: { onPick?: (lat: number, lng: number) => void }) {
  useMapEvents({ click: (e) => onPick?.(e.latlng.lat, e.latlng.lng) });
  return null;
}
export default function WasteMap({
  points,
  onPick,
}: {
  points: {
    latitude: number;
    longitude: number;
    label: string;
    count?: number;
  }[];
  onPick?: (lat: number, lng: number) => void;
}) {
  const p = points[0];
  return (
    <MapContainer
      key={p ? `${p.latitude.toFixed(2)},${p.longitude.toFixed(2)}` : "empty"}
      center={p ? [p.latitude, p.longitude] : [20.59, 78.96]}
      zoom={p ? 13 : 4}
      scrollWheelZoom={false}
      className="map"
    >
      <TileLayer
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
      />
      <Picker onPick={onPick} />
      {points.map((x, i) => (
        <CircleMarker
          key={i}
          center={[x.latitude, x.longitude]}
          radius={Math.min(22, 7 + (x.count || 1) * 2)}
          pathOptions={{
            color: "#137959",
            fillColor: "#34ad82",
            fillOpacity: 0.5,
          }}
        >
          <Popup>{x.label}</Popup>
        </CircleMarker>
      ))}
    </MapContainer>
  );
}
