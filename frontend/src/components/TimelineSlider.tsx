'use client';
import React from 'react';
import { Calendar, Play, RotateCcw, Clock } from 'lucide-react';

interface TimelineSliderProps {
  currentStep: number; // 0: 2024, 1: 2026, 2: 2028
  onTimelineChange: (step: number) => void;
}

const STAGES = [
  { year: '2024', label: 'Diridon Baseline', desc: 'Historical Reference' },
  { year: '2026', label: 'FortyGuard Peak Heatwave', desc: 'Active TCM Dataset' },
  { year: '2028', label: 'Retrofitted Mitigation', desc: 'Post-Agent Optimization' }
];

export default function TimelineSlider({ currentStep, onTimelineChange }: TimelineSliderProps) {
  return (
    <div className="p-4 bg-slate-900/90 backdrop-blur-md rounded-2xl border border-slate-800 shadow-xl space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs font-bold text-slate-300 uppercase tracking-wider">
          <Calendar className="w-4 h-4 text-emerald-400" />
          <span>Temporal Development Timeline</span>
        </div>
        <div className="text-xs font-mono px-2.5 py-0.5 rounded-full bg-slate-800 text-emerald-400 border border-slate-700">
          Stage: {STAGES[currentStep].year} — {STAGES[currentStep].label}
        </div>
      </div>

      {/* Slider Track */}
      <div className="relative pt-2 pb-1 px-2">
        <input 
          type="range"
          min="0"
          max="2"
          step="1"
          value={currentStep}
          onChange={(e) => onTimelineChange(parseInt(e.target.value))}
          className="w-full accent-emerald-500 bg-slate-800 h-2 rounded-lg cursor-pointer"
        />

        {/* Stage Labels */}
        <div className="grid grid-cols-3 gap-2 text-center pt-2">
          {STAGES.map((st, idx) => (
            <button
              key={st.year}
              onClick={() => onTimelineChange(idx)}
              className={`p-2 rounded-xl text-left transition border ${
                currentStep === idx 
                  ? 'bg-emerald-500/10 border-emerald-500/50 text-white shadow-md' 
                  : 'bg-slate-950/40 border-slate-800/80 text-slate-400 hover:text-slate-200'
              }`}
            >
              <div className="text-xs font-bold font-mono flex items-center justify-between">
                <span>{st.year}</span>
                {currentStep === idx && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-ping" />}
              </div>
              <div className="text-[11px] font-medium text-slate-200 truncate mt-0.5">{st.label}</div>
              <div className="text-[9px] text-slate-400 truncate">{st.desc}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
