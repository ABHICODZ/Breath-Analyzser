import React, { useEffect, useRef } from 'react';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
// @ts-ignore
import 'leaflet-velocity';
import 'leaflet-velocity/dist/leaflet-velocity.css';

import icon from 'leaflet/dist/images/marker-icon.png';
import iconShadow from 'leaflet/dist/images/marker-shadow.png';

let DefaultIcon = L.icon({
    iconUrl: icon,
    shadowUrl: iconShadow,
    iconSize: [25, 41],
    iconAnchor: [12, 41]
});
L.Marker.prototype.options.icon = DefaultIcon;

interface LeafletMapProps {
    wards: any[];
    selectedWard: any | null;
    onWardClick: (ward: any) => void;
    granularity: 'ward' | 'district';
    disableWind?: boolean;
    layer?: 'aqi' | 'pm25' | 'sources';
}

export default function LeafletMap({ wards, selectedWard, onWardClick, granularity, disableWind = false, layer = 'aqi' }: LeafletMapProps) {
    const mapRef = useRef<HTMLDivElement>(null);
    const mapInstance = useRef<L.Map | null>(null);
    const geoJsonLayer = useRef<L.GeoJSON | null>(null);

    // 1. Initialize Map once
    useEffect(() => {
        if (!mapRef.current) return;
        if (!mapInstance.current) {
            mapInstance.current = L.map(mapRef.current, { zoomControl: false }).setView([28.6139, 77.2090], 11);
            // Switched to Military-Grade Deep Dark Matter rendering layer
            L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
                attribution: '&copy; OpenStreetMap contributors'
            }).addTo(mapInstance.current);
            L.control.zoom({ position: 'bottomright' }).addTo(mapInstance.current);
            
            // Wind layer disabled for admin dashboard to prevent CORS issues
            // Can be re-enabled when backend CORS is configured properly
        }
        return () => {
            if (mapInstance.current) {
                mapInstance.current.remove();
                mapInstance.current = null;
            }
        };
    }, []);

    // 2. React to API Data and Bind Real Values with Layer Support
    useEffect(() => {
        if (!mapInstance.current || wards.length === 0) return;

        const geojsonFile = granularity === 'ward' ? '/Delhi_Wards.geojson' : '/delhi_wards.geojson';
        
        fetch(geojsonFile)
            .then(res => res.json())
            .then(data => {
                if (geoJsonLayer.current) {
                    mapInstance.current!.removeLayer(geoJsonLayer.current);
                }

                geoJsonLayer.current = L.geoJSON(data, {
                    style: (feature) => {
                        const featureId = feature?.properties?.ward_no || feature?.properties?.name || feature?.properties?.ward_name;
                        const wardData = wards.find(w => w.id === String(featureId));
                        const isSelected = selectedWard && selectedWard.id === String(featureId);
                        
                        let color = '#3b82f6'; // Deep blue fallback
                        if (wardData) {
                            // Different color schemes based on layer
                            if (layer === 'aqi') {
                                if (wardData.aqi > 300) color = '#ef4444'; // Red
                                else if (wardData.aqi > 200) color = '#f97316'; // Orange
                                else if (wardData.aqi > 100) color = '#f59e0b'; // Yellow
                                else color = '#10b981'; // Emerald
                            } else if (layer === 'pm25') {
                                const pm25 = wardData.pm25 || 0;
                                if (pm25 > 250) color = '#dc2626'; // Dark red
                                else if (pm25 > 150) color = '#f97316'; // Orange
                                else if (pm25 > 75) color = '#fbbf24'; // Amber
                                else color = '#22c55e'; // Green
                            } else if (layer === 'sources') {
                                // Color by dominant source
                                const source = wardData.dominant_source || 'Unknown';
                                if (source.includes('Traffic')) color = '#ef4444';
                                else if (source.includes('Industrial')) color = '#f59e0b';
                                else if (source.includes('Construction')) color = '#8b5cf6';
                                else if (source.includes('Residential')) color = '#06b6d4';
                                else color = '#64748b';
                            }
                        }

                        return {
                            color: color,
                            weight: isSelected ? 4 : 2,
                            fillColor: color,
                            fillOpacity: isSelected ? 0.7 : 0.35,
                            dashArray: isSelected ? '' : '4'
                        };
                    },
                    onEachFeature: (feature, layer_obj) => {
                        const featureId = feature?.properties?.ward_no || feature?.properties?.name || feature?.properties?.ward_name;
                        
                        // Robust lookup: First by ID, then by Name
                        let wardData = wards.find(w => w.id === String(featureId));
                        if (!wardData) {
                            const fallbackName = feature?.properties?.name || feature?.properties?.ward_name || '';
                            if (fallbackName) {
                                wardData = wards.find(w => w.name.toLowerCase() === fallbackName.toLowerCase());
                            }
                        }

                        // Add visual hover effects
                        layer_obj.on('mouseover', function (e) {
                            const targetLayer = e.target;
                            targetLayer.setStyle({
                                weight: 4,
                                color: '#ffffff',
                                dashArray: '',
                                fillOpacity: 0.8
                            });
                            targetLayer.bringToFront();
                        });

                        layer_obj.on('mouseout', function (e) {
                            if (geoJsonLayer.current) {
                                geoJsonLayer.current.resetStyle(e.target);
                            }
                        });

                        // Always bind a tooltip
                        const wardName = wardData ? wardData.name : (feature?.properties?.name || feature?.properties?.ward_name || `Ward ${featureId}`);
                        let tooltipContent = `<div style="text-align:center; padding: 4px;"><b>${wardName}</b><br/>`;

                        if (wardData) {
                            layer_obj.on('click', () => {
                                onWardClick(wardData);
                                if (mapInstance.current) {
                                    mapInstance.current.flyTo([wardData.lat, wardData.lon], 13, { duration: 1.0 });
                                }
                            });
                            
                            if (layer === 'aqi') {
                                tooltipContent += `<span style="color:#64748b; font-size:10px;">AQI: </span><strong style="font-size:14px; color:${wardData.aqi > 300 ? '#ef4444' : '#f97316'};">${wardData.aqi}</strong>`;
                            } else if (layer === 'pm25') {
                                tooltipContent += `<span style="color:#64748b; font-size:10px;">PM2.5: </span><strong style="font-size:14px;">${wardData.pm25} µg/m³</strong>`;
                            } else if (layer === 'sources') {
                                tooltipContent += `<span style="color:#64748b; font-size:10px;">Source: </span><strong style="font-size:12px;">${wardData.dominant_source}</strong>`;
                            }
                        } else {
                            tooltipContent += `<span style="color:#64748b; font-size:10px;">Data not available</span>`;
                        }
                        
                        tooltipContent += `</div>`;
                        layer_obj.bindTooltip(tooltipContent, { direction: 'top', sticky: true, className: 'custom-tooltip' });
                    }
                }).addTo(mapInstance.current!);
            })
            .catch(err => console.error("Error loading ward geojson:", err));

    }, [wards, selectedWard, layer]);

    return (
        <div
            ref={mapRef}
            style={{ height: '100%', width: '100%' }}
        />
    );
}
