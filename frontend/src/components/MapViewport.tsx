'use client';
import React, { useState } from 'react';
import DeckGL from '@deck.gl/react';
import { Map } from 'react-map-gl';
import { GeoJsonLayer, BitmapLayer } from '@deck.gl/layers';
import { TileLayer } from '@deck.gl/geo-layers';
import { Layers, Flame, Globe } from 'lucide-react';

const INITIAL_VIEW_STATE = {
  longitude: -121.8906, // San Jose, CA
  latitude: 37.3361,
  zoom: 15.2,
  pitch: 55,
  bearing: -20
};

interface MapViewportProps {
  geoJsonData: any;
  onSelectBuilding: (building: any) => void;
  selectedParcelId?: string | null;
}

type MapProvider = 'google-hybrid' | 'google-satellite' | 'esri-earth' | 'carto-dark' | 'osm' | 'mapbox-gl';

const MAP_PROVIDERS: Record<MapProvider, { name: string; url?: string; type: 'tile' | 'mapbox' }> = {
  'google-hybrid': {
    name: 'Google Earth Hybrid',
    url: 'https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}',
    type: 'tile'
  },
  'google-satellite': {
    name: 'Google Earth Satellite',
    url: 'https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
    type: 'tile'
  },
  'esri-earth': {
    name: 'ESRI World Imagery',
    url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
    type: 'tile'
  },
  'carto-dark': {
    name: 'Carto Dark Matter',
    url: 'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
    type: 'tile'
  },
  'osm': {
    name: 'OpenStreetMap',
    url: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
    type: 'tile'
  },
  'mapbox-gl': {
    name: 'Mapbox Vector Dark',
    type: 'mapbox'
  }
};

export default function MapViewport({
  geoJsonData,
  onSelectBuilding,
  selectedParcelId,
}: MapViewportProps) {
  const [hoverInfo, setHoverInfo] = useState<any>(null);
  const [provider, setProvider] = useState<MapProvider>('google-hybrid');

  const activeProvider = MAP_PROVIDERS[provider];
  const mapboxToken = process.env.NEXT_PUBLIC_MAPBOX_TOKEN;
  const isMapboxActive = provider === 'mapbox-gl' && !!mapboxToken && mapboxToken.startsWith('pk.');

  // Deck.gl TileLayer using exact west, south, east, north bounds for BitmapLayer
  const tileLayer = new TileLayer({
    id: `base-tiles-${provider}`,
    data: activeProvider.url || MAP_PROVIDERS['google-hybrid'].url,
    minZoom: 0,
    maxZoom: 20,
    tileSize: 256,
    renderSubLayers: (props: any) => {
      if (!props || !props.tile || !props.tile.bbox) return null;
      const bbox = props.tile.bbox;
      const west = typeof bbox.west === 'number' ? bbox.west : bbox[0];
      const south = typeof bbox.south === 'number' ? bbox.south : bbox[1];
      const east = typeof bbox.east === 'number' ? bbox.east : bbox[2];
      const north = typeof bbox.north === 'number' ? bbox.north : bbox[3];
      return new BitmapLayer(props, {
        data: undefined,
        image: props.data,
        bounds: [west, south, east, north]
      });
    }
  });

  // 3D Extruded Buildings GeoJsonLayer
  const buildingLayer = new GeoJsonLayer({
    id: 'buildings-3d',
    data: geoJsonData || '/data/parcel_portfolio_san_jose_sample.geojson',
    extruded: true,
    wireframe: true,
    getElevation: (f: any) => (f.properties?.height || (f.properties?.stories ? f.properties.stories * 3.5 : 25)),
    getFillColor: (f: any) => {
      const pid = f.properties?.parcel_id;
      if (selectedParcelId && pid === selectedParcelId) {
        return [16, 185, 129, 240]; // Selected Emerald green
      }
      const tempDelta = f.properties?.temp_delta_f ?? f.properties?.temp_delta ?? 4.2;
      return tempDelta >= 3.5 
        ? [239, 68, 68, 220]   // Red Hotspot anomaly
        : [59, 130, 246, 200];  // Blue normal parcel
    },
    getLineColor: [255, 255, 255, 90],
    lineWidthMinPixels: 1,
    pickable: true,
    onHover: (info) => setHoverInfo(info),
    onClick: (info) => {
      if (info.object) {
        onSelectBuilding(info.object);
      }
    },
    updateTriggers: {
      getFillColor: [selectedParcelId]
    }
  });

  const layers = isMapboxActive ? [buildingLayer] : [tileLayer, buildingLayer];

  return (
    <div className="relative w-full h-[620px] rounded-2xl overflow-hidden shadow-2xl border border-slate-800 bg-slate-950">
      {/* Top Left Header & Controls */}
      <div className="absolute top-4 left-4 z-20 flex flex-wrap items-center gap-2.5">
        <div className="flex items-center gap-2 bg-slate-900/95 backdrop-blur-md px-3.5 py-2 rounded-xl border border-slate-800 shadow-lg text-xs font-semibold text-slate-200">
          <Layers className="w-4 h-4 text-emerald-400" />
          <span>FortyGuard 3D Thermal Layer</span>
          <span className="flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
            <Flame className="w-3 h-3" /> ΔT ≥ +3.5°F
          </span>
        </div>

        {/* Map Provider Selector */}
        <div className="flex items-center gap-1.5 bg-slate-900/95 backdrop-blur-md p-1 rounded-xl border border-slate-800 shadow-lg text-xs">
          <Globe className="w-3.5 h-3.5 text-emerald-400 ml-2 mr-0.5" />
          {(['google-hybrid', 'google-satellite', 'esri-earth', 'carto-dark'] as MapProvider[]).map((pKey) => (
            <button
              key={pKey}
              onClick={() => setProvider(pKey)}
              className={`px-2.5 py-1 rounded-lg transition font-medium text-[11px] ${
                provider === pKey 
                  ? 'bg-emerald-600 text-white shadow-sm font-semibold' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              {MAP_PROVIDERS[pKey].name.replace('Earth ', '').replace('World ', '')}
            </button>
          ))}
          {mapboxToken && (
            <button
              onClick={() => setProvider('mapbox-gl')}
              className={`px-2.5 py-1 rounded-lg transition font-medium text-[11px] ${
                provider === 'mapbox-gl' 
                  ? 'bg-emerald-600 text-white shadow-sm font-semibold' 
                  : 'text-slate-300 hover:text-white hover:bg-slate-800'
              }`}
            >
              Mapbox GL
            </button>
          )}
        </div>
      </div>

      {/* Map Legend */}
      <div className="absolute bottom-6 left-4 z-20 bg-slate-900/95 backdrop-blur-md px-4 py-3 rounded-xl border border-slate-800 shadow-lg text-xs space-y-1.5 text-slate-300">
        <div className="text-[11px] font-bold text-slate-400 uppercase tracking-wider mb-1 flex items-center justify-between gap-3">
          <span>Thermal Risk Scale</span>
          <span className="font-mono text-emerald-400 text-[10px]">{MAP_PROVIDERS[provider].name}</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-500 shadow-sm shadow-red-500/50"></span>
          <span>High Thermal Anomaly (ΔT ≥ +3.5°F)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-blue-500 shadow-sm shadow-blue-500/50"></span>
          <span>Baseline Ambient Parcel</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-emerald-500 shadow-sm shadow-emerald-500/50"></span>
          <span>Selected Target Intervention</span>
        </div>
      </div>

      <DeckGL
        initialViewState={INITIAL_VIEW_STATE}
        controller={true}
        layers={layers}
      >
        {isMapboxActive && (
          <Map
            mapboxAccessToken={mapboxToken}
            mapStyle="mapbox://styles/mapbox/dark-v11"
            reuseMaps
          />
        )}
      </DeckGL>

      {/* Hover Tooltip Overlay */}
      {hoverInfo && hoverInfo.object && (
        <div 
          className="absolute pointer-events-none z-30 bg-slate-900/95 backdrop-blur-md border border-emerald-500/40 px-3.5 py-2.5 rounded-xl shadow-xl text-xs space-y-1 text-white"
          style={{ left: hoverInfo.x + 12, top: hoverInfo.y + 12 }}
        >
          <div className="font-bold text-emerald-400 text-sm">
            {hoverInfo.object.properties?.name || 'San Jose Parcel'}
          </div>
          <div className="text-slate-400 font-mono text-[11px]">
            {hoverInfo.object.properties?.parcel_id}
          </div>
          <div className="flex items-center justify-between gap-4 pt-1 border-t border-slate-800">
            <span className="text-slate-400">Urban Heat ΔT:</span>
            <span className={`font-bold ${hoverInfo.object.properties?.temp_delta_f >= 3.5 ? 'text-red-400' : 'text-blue-400'}`}>
              +{hoverInfo.object.properties?.temp_delta_f || 4.2}°F
            </span>
          </div>
          <div className="flex items-center justify-between gap-4">
            <span className="text-slate-400">Priority Score:</span>
            <span className="font-mono text-emerald-300 font-semibold">
              {hoverInfo.object.properties?.priority_score || '955.5'}
            </span>
          </div>
        </div>
      )}
    </div>
  );
}
