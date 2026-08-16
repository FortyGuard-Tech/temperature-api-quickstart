'use client';
import React from 'react';
import { Cpu, CheckCircle2, Clock, PlayCircle, AlertCircle, ArrowRight } from 'lucide-react';

interface StepLog {
  agent_name: string;
  status: string;
  summary: string;
  execution_time_ms?: number;
}

interface AgentStatusPanelProps {
  steps?: StepLog[];
  isRunning?: boolean;
  onRunPipeline?: () => void;
}

const AGENT_LABELS: Record<string, { label: string; role: string; desc: string }> = {
  AnomalyDetectorAgent: {
    label: 'Agent 1: Anomaly Detector',
    role: 'Thermal Isothermal Scanner',
    desc: 'Scans 2m ambient heatmaps for ΔT ≥ +3.5°F anomalies'
  },
  BuildingAuditorAgent: {
    label: 'Agent 2: Building Auditor',
    role: 'Structure Causality Scorer',
    desc: 'Calculates roof area, baseline SRI albedo & priority score'
  },
  MitigationSimulatorAgent: {
    label: 'Agent 3: Mitigation Simulator',
    role: 'Cool Roof & Greening ROI Engine',
    desc: 'Models temperature drop, HVAC cost savings & payback'
  },
  ReportGeneratorAgent: {
    label: 'Agent 4: Report Generator',
    role: 'GeoJSON & PDF Synthesizer',
    desc: 'Generates enriched GeoJSON and executive audit report'
  }
};

export default function AgentStatusPanel({ steps = [], isRunning = false, onRunPipeline }: AgentStatusPanelProps) {
  const agentKeys = ['AnomalyDetectorAgent', 'BuildingAuditorAgent', 'MitigationSimulatorAgent', 'ReportGeneratorAgent'];
  const stepMap = new Map(steps.map(s => [s.agent_name, s]));

  return (
    <div className="p-5 bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Cpu className="w-5 h-5 text-emerald-400" />
          <h4 className="text-sm font-bold text-white uppercase tracking-wider">Multi-Agent Autonomous Pipeline</h4>
        </div>
        <button
          onClick={onRunPipeline}
          disabled={isRunning}
          className="px-3.5 py-1.5 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 text-xs font-semibold rounded-lg border border-emerald-500/40 transition flex items-center gap-1.5"
        >
          {isRunning ? (
            <span className="animate-spin w-3.5 h-3.5 border-2 border-emerald-400 border-t-transparent rounded-full" />
          ) : (
            <PlayCircle className="w-3.5 h-3.5" />
          )}
          <span>{isRunning ? 'Running Pipeline...' : 'Trigger Full Pipeline'}</span>
        </button>
      </div>

      {/* Agents Workflow List */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        {agentKeys.map((key, idx) => {
          const info = AGENT_LABELS[key];
          const stepData = stepMap.get(key);
          const isDone = !!stepData;
          
          return (
            <div 
              key={key}
              className={`p-3 rounded-xl border transition text-xs space-y-1.5 ${
                isDone 
                  ? 'bg-slate-950/80 border-emerald-500/40 text-slate-200' 
                  : isRunning 
                    ? 'bg-slate-950/40 border-amber-500/40 text-slate-300 animate-pulse'
                    : 'bg-slate-950/40 border-slate-800 text-slate-400'
              }`}
            >
              <div className="flex items-center justify-between">
                <span className="font-bold text-emerald-400 font-mono text-[11px]">{info.label.split(':')[0]}</span>
                {isDone ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                ) : isRunning ? (
                  <Clock className="w-4 h-4 text-amber-400 animate-spin" />
                ) : (
                  <span className="w-2 h-2 rounded-full bg-slate-700" />
                )}
              </div>
              <div className="font-semibold text-white truncate">{info.role}</div>
              <div className="text-[10px] text-slate-400 leading-snug line-clamp-2">
                {stepData ? stepData.summary : info.desc}
              </div>
              {stepData?.execution_time_ms && (
                <div className="text-[9px] font-mono text-emerald-400/90 text-right pt-1 border-t border-slate-800/80">
                  {stepData.execution_time_ms} ms
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
