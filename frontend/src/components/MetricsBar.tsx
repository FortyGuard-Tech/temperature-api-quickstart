'use client';
import React from 'react';
import { Thermometer, Flame, DollarSign, Leaf, Zap, ShieldCheck } from 'lucide-react';

interface MetricsBarProps {
  hotspotCount: number;
  totalParcels: number;
  avgTempF: number;
  projectedCoolingF?: number;
  annualSavingsUsd?: number;
  co2Tons?: number;
}

export default function MetricsBar({
  hotspotCount = 3,
  totalParcels = 6,
  avgTempF = 86.2,
  projectedCoolingF = 4.3,
  annualSavingsUsd = 68625.0,
  co2Tons = 228.75
}: MetricsBarProps) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-5 gap-3.5 w-full">
      {/* Metric 1: Avg Ambient Temp */}
      <div className="p-4 bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl flex items-center gap-3.5">
        <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-400">
          <Thermometer className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Avg Ambient Temp</div>
          <div className="text-xl font-extrabold text-white font-mono mt-0.5">{avgTempF}°F</div>
          <div className="text-[10px] text-amber-400/90">FortyGuard San Jose 2m</div>
        </div>
      </div>

      {/* Metric 2: Heat Anomalies */}
      <div className="p-4 bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl flex items-center gap-3.5">
        <div className="p-2.5 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400">
          <Flame className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Thermal Anomalies</div>
          <div className="text-xl font-extrabold text-red-400 font-mono mt-0.5">
            {hotspotCount} <span className="text-xs text-slate-400 font-normal">/ {totalParcels} Parcels</span>
          </div>
          <div className="text-[10px] text-red-400/90">ΔT ≥ +3.5°F Breach</div>
        </div>
      </div>

      {/* Metric 3: Projected Cooling */}
      <div className="p-4 bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl flex items-center gap-3.5">
        <div className="p-2.5 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400">
          <Zap className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Projected Cooling</div>
          <div className="text-xl font-extrabold text-emerald-400 font-mono mt-0.5">-{projectedCoolingF}°F</div>
          <div className="text-[10px] text-emerald-400/90">Cool Roof + Greening</div>
        </div>
      </div>

      {/* Metric 4: Economic Savings */}
      <div className="p-4 bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl flex items-center gap-3.5">
        <div className="p-2.5 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400">
          <DollarSign className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Annual HVAC Savings</div>
          <div className="text-xl font-extrabold text-white font-mono mt-0.5">
            ${annualSavingsUsd.toLocaleString()}<span className="text-xs text-slate-400">/yr</span>
          </div>
          <div className="text-[10px] text-teal-400/90">Peak Chiller Offset</div>
        </div>
      </div>

      {/* Metric 5: CO2 Offset */}
      <div className="p-4 bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl flex items-center gap-3.5 col-span-2 md:col-span-1">
        <div className="p-2.5 rounded-xl bg-green-500/10 border border-green-500/20 text-green-400">
          <Leaf className="w-5 h-5" />
        </div>
        <div>
          <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Carbon Offset</div>
          <div className="text-xl font-extrabold text-green-400 font-mono mt-0.5">{co2Tons} Tons</div>
          <div className="text-[10px] text-green-400/90">CO2e Annual Offset</div>
        </div>
      </div>
    </div>
  );
}
