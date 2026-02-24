import React, { useEffect, useState, useMemo } from 'react';
import { MapContainer, TileLayer, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
// import 'leaflet.heat/dist/leaflet-heat.js';

// Leaflet requires these icon fixups when grouped with React bundlers
import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';
let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow
});
L.Marker.prototype.options.icon = DefaultIcon;

interface LeafletMapProps {
    heatmapData: number[][];
    shortestRoute: [number, number][] | null;
    cleanestRoute: [number, number][] | null;
}

const HeatmapLayer = ({ data }: { data: number[][] }) => {
    // Temperarily disabled due to CJS require error in Vite
    return null;
};

export default function LeafletMap({ heatmapData, shortestRoute, cleanestRoute }: LeafletMapProps) {
    // NYC Coordinates Initial Load
    const center: [number, number] = [40.7128, -74.0060];

    return (
        <div style={{ height: '100vh', width: '100vw', position: 'absolute', top: 0, left: 0 }}>
            <MapContainer
                center={center}
                zoom={12.5}
                style={{ height: '100%', width: '100%' }}
                zoomControl={false}
            >
                <TileLayer
                    url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
                />

                <HeatmapLayer data={heatmapData} />

                {shortestRoute && (
                    <Polyline
                        positions={shortestRoute}
                        pathOptions={{ color: '#ef4444', weight: 4, dashArray: '8, 8', opacity: 0.8 }}
                    />
                )}

                {cleanestRoute && (
                    <Polyline
                        positions={cleanestRoute}
                        pathOptions={{ color: '#10b981', weight: 6, opacity: 1.0 }}
                    />
                )}
            </MapContainer>
        </div>
    );
}
