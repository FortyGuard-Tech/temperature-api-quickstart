import { NextResponse } from 'next/server';

export async function GET() {
  try {
    const backendRes = await fetch('http://localhost:8000/api/v1/hotspots', { cache: 'no-store' });
    if (backendRes.ok) {
      const data = await backendRes.json();
      return NextResponse.json(data);
    }
  } catch (err) {
    console.warn('Proxy to FastAPI failed, generating client fallback hotspots...', err);
  }

  // Standalone fallback response if backend is offline
  return NextResponse.json({
    status: "success",
    data: {
      type: "FeatureCollection",
      features: [
        {
          type: "Feature",
          properties: {
            parcel_id: "APN-259-27-014",
            name: "Diridon Gateway",
            city: "San Jose",
            state: "CA",
            lot_acres: 3.33,
            zoning: "DC — Downtown Commercial",
            proposed_use: "Mixed-use office / residential",
            stories: 12,
            height: 42,
            temp_delta_f: 4.8,
            ambient_temp_f: 87.3,
            priority_score: 2266.7,
            is_hotspot: true,
            albedo: 0.18,
            canopy_pct: 0.05,
            roof_area_m2: 3500
          },
          geometry: {
            type: "Polygon",
            coordinates: [[
              [-121.90079, 37.33005],
              [-121.89920, 37.33005],
              [-121.89920, 37.33065],
              [-121.89956, 37.33094],
              [-121.90079, 37.33094],
              [-121.90079, 37.33005]
            ]]
          }
        },
        {
          type: "Feature",
          properties: {
            parcel_id: "APN-264-11-032",
            name: "SoFA District Infill",
            city: "San Jose",
            state: "CA",
            lot_acres: 1.76,
            zoning: "DC — Downtown Commercial",
            proposed_use: "Residential over ground-floor retail",
            stories: 8,
            height: 28,
            temp_delta_f: 5.2,
            ambient_temp_f: 87.7,
            priority_score: 955.5,
            is_hotspot: true,
            albedo: 0.20,
            canopy_pct: 0.08,
            roof_area_m2: 2150
          },
          geometry: {
            type: "Polygon",
            coordinates: [[
              [-121.88653, 37.32966],
              [-121.88546, 37.32966],
              [-121.88546, 37.33033],
              [-121.88653, 37.33033],
              [-121.88653, 37.32966]
            ]]
          }
        },
        {
          type: "Feature",
          properties: {
            parcel_id: "APN-467-22-105",
            name: "SJSU South Campus Edge",
            city: "San Jose",
            state: "CA",
            lot_acres: 2.73,
            zoning: "DC — Downtown Commercial",
            proposed_use: "Student housing",
            stories: 10,
            height: 35,
            temp_delta_f: 3.9,
            ambient_temp_f: 86.4,
            priority_score: 1123.2,
            is_hotspot: true,
            albedo: 0.22,
            canopy_pct: 0.10,
            roof_area_m2: 2880
          },
          geometry: {
            type: "Polygon",
            coordinates: [[
              [-121.87973, 37.33361],
              [-121.87826, 37.33361],
              [-121.87826, 37.33438],
              [-121.87973, 37.33438],
              [-121.87973, 37.33361]
            ]]
          }
        },
        {
          type: "Feature",
          properties: {
            parcel_id: "APN-472-09-017",
            name: "Spartan Keyes",
            city: "San Jose",
            state: "CA",
            lot_acres: 2.34,
            zoning: "RM — Residential Medium",
            proposed_use: "Townhome development",
            stories: 3,
            height: 10.5,
            temp_delta_f: 1.8,
            ambient_temp_f: 84.3,
            priority_score: 750.0,
            is_hotspot: false,
            albedo: 0.30,
            canopy_pct: 0.18,
            roof_area_m2: 3000
          },
          geometry: {
            type: "Polygon",
            coordinates: [[
              [-121.88359, 37.31759],
              [-121.88240, 37.31759],
              [-121.88240, 37.31840],
              [-121.88359, 37.31840],
              [-121.88359, 37.31759]
            ]]
          }
        }
      ]
    }
  });
}
