import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { complaintAPI } from '../services/api';
import { MapPin, Filter, Layers } from 'lucide-react';

const createPinIcon = (color) => {
  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="${color}" width="30" height="30" stroke="#ffffff" stroke-width="1.5">
      <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
    </svg>
  `;
  return L.divIcon({
    html: svg,
    className: 'custom-leaflet-marker',
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30],
  });
};

const pinColors = {
  CRITICAL: '#e11d48',
  HIGH: '#f97316',
  MEDIUM: '#eab308',
  LOW: '#0284c7',
};

export default function GrievanceMap() {
  const mapContainerRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersLayerRef = useRef(null);

  const [complaints, setComplaints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedWard, setSelectedWard] = useState('ALL');

  // Fetch complaints
  useEffect(() => {
    const fetchLocations = async () => {
      try {
        setLoading(true);
        const data = await complaintAPI.list({ limit: 100 });
        setComplaints(data.filter((c) => c.latitude && c.longitude));
      } catch (err) {
        console.error("Map fetch error:", err);
      } finally {
        setLoading(false);
      }
    };
    fetchLocations();
  }, []);

  // Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapInstanceRef.current) return;

    const defaultLat = 28.6139;
    const defaultLon = 77.2090;

    const map = L.map(mapContainerRef.current).setView([defaultLat, defaultLon], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
    }).addTo(map);

    const markersGroup = L.layerGroup().addTo(map);
    markersLayerRef.current = markersGroup;
    mapInstanceRef.current = map;

    return () => {
      map.remove();
      mapInstanceRef.current = null;
    };
  }, []);

  // Update Markers when complaints or selectedWard changes
  useEffect(() => {
    if (!mapInstanceRef.current || !markersLayerRef.current) return;

    markersLayerRef.current.clearLayers();

    const filtered = selectedWard === 'ALL'
      ? complaints
      : complaints.filter((c) => c.ward === selectedWard);

    filtered.forEach((c) => {
      const color = pinColors[c.priority] || pinColors.LOW;
      const icon = createPinIcon(color);
      const marker = L.marker([c.latitude, c.longitude], { icon });

      const popupContent = `
        <div style="font-family: system-ui, sans-serif; font-size: 12px; max-width: 200px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
            <strong style="color: #0f172a;">${c.tracking_number}</strong>
            <span style="background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: bold; font-size: 10px;">${c.priority}</span>
          </div>
          <h4 style="margin: 0 0 4px 0; font-size: 13px; font-weight: bold; color: #1e293b;">${c.title}</h4>
          <p style="margin: 0 0 6px 0; color: #64748b; line-height: 1.3;">${c.description}</p>
          <div style="display: flex; justify-content: space-between; border-top: 1px solid #f1f5f9; padding-top: 4px; color: #475569; font-size: 10px;">
            <span>${c.ward || 'Zone'}</span>
            <span style="font-weight: bold; color: #0284c7;">${c.status}</span>
          </div>
        </div>
      `;
      marker.bindPopup(popupContent);
      markersLayerRef.current.addLayer(marker);
    });

    if (filtered.length > 0) {
      mapInstanceRef.current.setView([filtered[0].latitude, filtered[0].longitude], 13);
    }
  }, [complaints, selectedWard]);

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
      {/* Header & Controls */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 bg-white p-5 rounded-2xl border border-slate-200 shadow-sm">
        <div>
          <div className="flex items-center space-x-2 text-xs font-semibold text-sky-700 bg-sky-50 px-2.5 py-0.5 rounded-full w-fit mb-1">
            <Layers className="w-3.5 h-3.5" />
            <span>GIS Heatmap & Ward Triaging</span>
          </div>
          <h1 className="text-xl font-black text-slate-900">Geospatial Grievance Intelligence</h1>
          <p className="text-xs text-slate-500">Visualizing live citizen complaints across municipal zones</p>
        </div>

        <div className="flex items-center space-x-3">
          <span className="text-xs font-semibold text-slate-500 flex items-center">
            <Filter className="w-3.5 h-3.5 mr-1" /> Ward Filter:
          </span>
          <select
            value={selectedWard}
            onChange={(e) => setSelectedWard(e.target.value)}
            className="px-3 py-1.5 rounded-xl border border-slate-200 text-xs font-medium focus:ring-2 focus:ring-sky-500"
          >
            <option value="ALL">All Wards ({complaints.length} Points)</option>
            <option value="Ward 3 - East">Ward 3 - East</option>
            <option value="Ward 7 - Central">Ward 7 - Central</option>
            <option value="Ward 9 - South">Ward 9 - South</option>
            <option value="Ward 12 - North">Ward 12 - North</option>
          </select>
        </div>
      </div>

      {/* Map Card */}
      <div className="bg-white p-2 rounded-3xl border border-slate-200 shadow-lg overflow-hidden h-[600px] relative">
        <div ref={mapContainerRef} className="h-full w-full rounded-2xl" />

        {/* Legend */}
        <div className="absolute bottom-6 right-6 z-[1000] bg-white/95 backdrop-blur-md px-3.5 py-2.5 rounded-xl border border-slate-200 shadow-md text-xs space-y-1.5">
          <span className="font-bold text-slate-700 block text-[11px] uppercase">Grievance Priority</span>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-full bg-rose-600 inline-block"></span>
            <span className="text-slate-600 text-[11px]">Critical (Urgent Hazard)</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-full bg-orange-500 inline-block"></span>
            <span className="text-slate-600 text-[11px]">High Priority</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-full bg-yellow-500 inline-block"></span>
            <span className="text-slate-600 text-[11px]">Medium</span>
          </div>
          <div className="flex items-center space-x-1.5">
            <span className="w-3 h-3 rounded-full bg-sky-600 inline-block"></span>
            <span className="text-slate-600 text-[11px]">Low</span>
          </div>
        </div>
      </div>
    </div>
  );
}
