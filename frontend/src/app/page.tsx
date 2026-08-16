'use client';
import React, { useState, useEffect } from 'react';
import { Thermometer, ShieldAlert, Cpu, Sparkles, RefreshCw, Layers } from 'lucide-react';
import MetricsBar from '../components/MetricsBar';
import MapViewport from '../components/MapViewport';
import BuildingDrawer from '../components/BuildingDrawer';
import TimelineSlider from '../components/TimelineSlider';
import AgentStatusPanel from '../components/AgentStatusPanel';
import { fetchHotspots, triggerPipelineRun } from '../lib/api';

export default function DashboardPage() {
  const [geoJsonData, setGeoJsonData] = useState<any>(null);
  const [selectedBuilding, setSelectedBuilding] = useState<any>(null);
  const [timelineStep, setTimelineStep] = useState<number>(1); // Default: 2026 Peak Heatwave
  const [pipelineSteps, setPipelineSteps] = useState<any[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [runningPipeline, setRunningPipeline] = useState<boolean>(false);
  const [summaryMetrics, setSummaryMetrics] = useState<any>({
    hotspotCount: 3,
    totalParcels: 6,
    avgTempF: 86.2,
    projectedCoolingF: 4.3,
    annualSavingsUsd: 68625.0,
    co2Tons: 228.75
  });

  const loadData = async () => {
    setLoading(true);
    try {
      const res = await fetchHotspots();
      if (res && res.data) {
        setGeoJsonData(res.data);
        if (res.steps) {
          setPipelineSteps(res.steps);
        }
        // Select first parcel feature as initial target
        if (res.data.features && res.data.features.length > 0) {
          setSelectedBuilding(res.data.features[1] || res.data.features[0]);
        }
      }
    } catch (err) {
      console.error('Error loading hotspots data:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleRunFullPipeline = async () => {
    setRunningPipeline(true);
    try {
      const res = await triggerPipelineRun(0.70, 250);
      if (res && res.steps) {
        setPipelineSteps(res.steps);
      }
      if (res && res.final_geojson) {
        setGeoJsonData(res.final_geojson);
      }
    } catch (err) {
      console.error('Pipeline execution error:', err);
    } finally {
      setRunningPipeline(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-6 space-y-6 max-w-[1700px] mx-auto">
      {/* Top Header */}
      <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 p-5 bg-slate-900/90 backdrop-blur-xl border border-slate-800 rounded-2xl shadow-2xl">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-gradient-to-br from-emerald-500 to-teal-700 rounded-xl shadow-lg shadow-emerald-950/50">
            <Thermometer className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-2xl font-black text-white tracking-tight">ThermoAgent-AI</h1>
              <span className="px-2.5 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-semibold border border-emerald-500/30">
                FortyGuard San Jose Unified Pipeline
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-0.5">
              Multi-Agent Thermal Anomaly Isolator & Parametric Structure Mitigation Optimizer
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button 
            onClick={loadData}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-xl border border-slate-700 transition flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-emerald-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Reload Thermal Profile</span>
          </button>
        </div>
      </header>

      {/* Citywide Metrics Bar */}
      <MetricsBar 
        hotspotCount={summaryMetrics.hotspotCount}
        totalParcels={summaryMetrics.totalParcels}
        avgTempF={summaryMetrics.avgTempF}
        projectedCoolingF={summaryMetrics.projectedCoolingF}
        annualSavingsUsd={summaryMetrics.annualSavingsUsd}
        co2Tons={summaryMetrics.co2Tons}
      />

      {/* Multi-Agent Status Panel */}
      <AgentStatusPanel 
        steps={pipelineSteps}
        isRunning={runningPipeline}
        onRunPipeline={handleRunFullPipeline}
      />

      {/* Main Viewport & Inspection Split Screen */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: 3D Map Viewport + Timeline Slider */}
        <div className="lg:col-span-8 space-y-4">
          <MapViewport 
            geoJsonData={geoJsonData}
            onSelectBuilding={(b) => setSelectedBuilding(b)}
            selectedParcelId={selectedBuilding?.properties?.parcel_id}
          />

          <TimelineSlider 
            currentStep={timelineStep}
            onTimelineChange={(st) => setTimelineStep(st)}
          />
        </div>

        {/* Right Column: Structure Mitigation Optimizer Drawer */}
        <div className="lg:col-span-4">
          <BuildingDrawer 
            building={selectedBuilding}
          />
        </div>
      </div>
    </main>
  );
}
