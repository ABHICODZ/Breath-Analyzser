import React, { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

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

export default function LeafletMap({ heatmapData, shortestRoute, cleanestRoute }: LeafletMapProps) {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstance = useRef<L.Map | null>(null);
    const routingLayerGroup = useRef<L.LayerGroup | null>(null);

    // Initialize Map
    useEffect(() => {
        if (!mapRef.current) return;

        // Only initialize once
        if (!mapInstance.current) {
            mapInstance.current = L.map(mapRef.current, { zoomControl: false }).setView([17.3850, 78.4867], 12);

            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            }).addTo(mapInstance.current);

            routingLayerGroup.current = L.layerGroup().addTo(mapInstance.current);
        }

        return () => {
            // Cleanup on unmount
            if (mapInstance.current) {
                mapInstance.current.remove();
                mapInstance.current = null;
            }
        };
    }, []);

    // Handle Route Updates
    useEffect(() => {
        if (!mapInstance.current || !routingLayerGroup.current) return;

        // Clear previous routes
        routingLayerGroup.current.clearLayers();

        if (shortestRoute && shortestRoute.length > 0) {
            mapInstance.current.setView(shortestRoute[0], 13);

            L.polyline(shortestRoute, {
                color: '#ef4444',
                weight: 4,
                dashArray: '8, 8',
                opacity: 0.8
            }).addTo(routingLayerGroup.current);
        }

        if (cleanestRoute) {
            L.polyline(cleanestRoute, {
                color: '#10b981',
                weight: 6,
                opacity: 1.0
            }).addTo(routingLayerGroup.current);
        }

    }, [shortestRoute, cleanestRoute]);

    return (
        <div
            ref={mapRef}
            style={{ height: '100vh', width: '100vw', position: 'absolute', top: 0, left: 0 }}
        />
    );
}
