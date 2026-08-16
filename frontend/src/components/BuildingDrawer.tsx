'use client';
import React, { useState, useEffect } from 'react';
import { Sliders, Sun, TreePine, Zap, DollarSign, Clock, FileText, Sparkles, Building2 } from 'lucide-react';
import { runSimulation } from '../lib/api';

interface BuildingDrawerProps {
  building: any;
  onClose?: () => void;
}

export default function BuildingDrawer({ building, onClose }: BuildingDrawerProps) {
  const [albedo, setAlbedo] = useState<number>(0.75);
  const [canopy, setCanopy] = useState<number>(250);
  const [loading, setLoading] = useState<boolean>(false);
  const [simResult, setSimResult] = useState<any>(null);

  const props = building?.properties || {
    parcel_id: 'APN-264-11-032',
    name: 'SoFA District Infill',
    proposed_use: 'Residential over ground-floor retail',
    roof_area_m2: 2150,
    temp_delta_f: 5.2,
    priority_score: 955.5,
    albedo: 0.20
  };

  const handleRunSimulation = async () => {
    setLoading(true);
    try {
      const roofArea = props.roof_area_m2 || 1500;
      const res = await runSimulation(roofArea, albedo, canopy, props.parcel_id);
      if (res && res.simulation) {
        setSimResult(res.simulation);
      }
    } catch (err) {
      console.error('Simulation call error:', err);
    } finally {
      setLoading(false);
    }
  };

  // Run initial simulation on structure load
  useEffect(() => {
    handleRunSimulation();
  }, [building]);

  const handleDownloadPdf = () => {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const pdfUrl = `${backendUrl}/api/v1/report/pdf/${props.parcel_id}?target_albedo=${albedo}&canopy_area=${canopy}`;
    window.open(pdfUrl, '_blank');
  };

  return (
    <div className="p-6 bg-slate-900/95 backdrop-blur-xl border border-slate-800 rounded-2xl text-white space-y-5 shadow-2xl">
      {/* Drawer Header */}
      <div className="flex items-start justify-between pb-4 border-b border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-emerald-400 font-semibold text-xs tracking-wide uppercase mb-1">
            <Building2 className="w-4 h-4" /> Structure Mitigation Optimizer
          </div>
          <h3 className="text-xl font-extrabold text-white">
            {props.name || 'San Jose Parcel'}
          </h3>
          <p className="text-xs font-mono text-slate-400 mt-0.5">
            APN: {props.parcel_id || 'APN-264-11-032'}
          </p>
        </div>
        {props.temp_delta_f >= 3.5 && (
          <span className="px-2.5 py-1 rounded-full bg-red-500/20 text-red-400 text-xs font-semibold border border-red-500/30 animate-pulse-glow">
            Priority Hotspot
          </span>
        )}
      </div>

      {/* Structural Metadata Grid */}
      <div className="grid grid-cols-2 gap-3 text-xs bg-slate-950/60 p-3.5 rounded-xl border border-slate-800/80">
        <div>
          <span className="text-slate-400 block">Zoning / Use:</span>
          <span className="font-medium text-slate-200 truncate block">{props.proposed_use || 'Downtown Mixed Use'}</span>
        </div>
        <div>
          <span className="text-slate-400 block">Roof Area:</span>
          <span className="font-semibold text-emerald-400">{props.roof_area_m2 || 2150} m²</span>
        </div>
        <div>
          <span className="text-slate-400 block">Baseline ΔT:</span>
          <span className="font-semibold text-red-400">+{props.temp_delta_f || 4.2}°F</span>
        </div>
        <div>
          <span className="text-slate-400 block">Priority Score:</span>
          <span className="font-semibold text-emerald-400">{props.priority_score || 955.5}</span>
        </div>
      </div>

      {/* Parametric Sliders */}
      <div className="space-y-4 pt-1">
        {/* Albedo Slider */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <label className="font-semibold text-slate-200 flex items-center gap-1.5">
              <Sun className="w-3.5 h-3.5 text-amber-400" /> Target Albedo (SRI):
            </label>
            <span className="font-mono text-emerald-400 font-bold text-sm bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              {albedo.toFixed(2)}
            </span>
          </div>
          <input 
            type="range" 
            min="0.20" 
            max="0.95" 
            step="0.05" 
            value={albedo} 
            onChange={(e) => setAlbedo(parseFloat(e.target.value))} 
            className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>0.20 (Asphalt Dark)</span>
            <span>0.70 (Cool Elastomer)</span>
            <span>0.95 (Ultra-Reflective)</span>
          </div>
        </div>

        {/* Canopy Expansion Slider */}
        <div className="space-y-2">
          <div className="flex justify-between items-center text-xs">
            <label className="font-semibold text-slate-200 flex items-center gap-1.5">
              <TreePine className="w-3.5 h-3.5 text-emerald-400" /> Add Canopy Greening:
            </label>
            <span className="font-mono text-emerald-400 font-bold text-sm bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
              {canopy} m²
            </span>
          </div>
          <input 
            type="range" 
            min="0" 
            max="1000" 
            step="50" 
            value={canopy} 
            onChange={(e) => setCanopy(parseFloat(e.target.value))} 
            className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
          />
          <div className="flex justify-between text-[10px] text-slate-400">
            <span>0 m²</span>
            <span>500 m²</span>
            <span>1,000 m²</span>
          </div>
        </div>
      </div>

      {/* Action Button */}
      <button 
        onClick={handleRunSimulation}
        disabled={loading}
        className="w-full py-3 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 font-bold rounded-xl text-white text-sm transition shadow-lg shadow-emerald-900/40 flex items-center justify-center gap-2"
      >
        {loading ? (
          <span className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full" />
        ) : (
          <Sparkles className="w-4 h-4" />
        )}
        <span>{loading ? 'Executing Agent Simulation...' : 'Run Agent Simulation'}</span>
      </button>

      {/* Simulation Results Display */}
      {simResult && (
        <div className="mt-3 p-4 bg-slate-950/80 rounded-xl space-y-3 border border-emerald-500/30 shadow-inner">
          <div className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center justify-between">
            <span>Agent 3 Simulation Output</span>
            <span className="text-[10px] text-slate-400 font-mono">Modeled HVAC ROI</span>
          </div>

          <div className="grid grid-cols-2 gap-3 text-xs">
            <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[10px] block">Projected Cooling</span>
              <span className="text-base font-extrabold text-emerald-400">
                -{simResult.projected_temp_drop_f}°F
              </span>
            </div>

            <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[10px] block">Annual HVAC Savings</span>
              <span className="text-base font-extrabold text-emerald-400">
                ${simResult.annual_hvac_savings_usd?.toLocaleString()}/yr
              </span>
            </div>

            <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[10px] block">Payback Period</span>
              <span className="text-base font-extrabold text-slate-200">
                {simResult.payback_years} Years
              </span>
            </div>

            <div className="p-2.5 bg-slate-900/90 rounded-lg border border-slate-800">
              <span className="text-slate-400 text-[10px] block">CO2 Reduction</span>
              <span className="text-base font-extrabold text-teal-400">
                {simResult.co2_reduction_tons} Tons/yr
              </span>
            </div>
          </div>

          {/* Download PDF Trigger */}
          <button 
            onClick={handleDownloadPdf}
            className="w-full py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition flex items-center justify-center gap-2 mt-2"
          >
            <FileText className="w-3.5 h-3.5 text-emerald-400" />
            <span>Download Agent 4 Executive Audit PDF</span>
          </button>
        </div>
      )}
    </div>
  );
}
