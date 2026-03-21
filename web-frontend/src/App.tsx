import React, { useState, useEffect } from 'react';
import LeafletMap from './components/LeafletMap';
import AuthOverlay from './components/AuthOverlay';
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

export default function App() {
  const [session, setSession] = useState<any>(null);
  const [userProfile, setUserProfile] = useState<any>(null);
  const [wards, setWards] = useState<any[]>([]);
  const [recs, setRecs] = useState<any[]>([]);
  const [selectedWard, setSelectedWard] = useState<any | null>(null);
  const [geeData, setGeeData] = useState<any | null>(null);
  const [geeLoading, setGeeLoading] = useState<boolean>(false);
  const [forecast, setForecast] = useState<any[]>([]);
  const [granularity, setGranularity] = useState<'ward'|'district'>('ward');

  useEffect(() => {
    if (!selectedWard) {
        setGeeData(null);
        setForecast([]);
        return;
    }
    const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8080";
    
    async function fetchGEE() {
        setGeeLoading(true);
        try {
            const res = await fetch(`${API_BASE}/api/v1/gee/analyze?lat=${selectedWard.lat}&lon=${selectedWard.lon}`);
            if (res.ok) setGeeData(await res.json());
        } catch (e) {
            console.error(e);
        } finally {
            setGeeLoading(false);
        }
    }
    
    async function fetchForecast() {
        try {
            const res = await fetch(`${API_BASE}/api/v1/dashboard/forecast?lat=${selectedWard.lat}&lon=${selectedWard.lon}`);
            if (res.ok) {
                const data = await res.json();
                const formatted = data.map((d: any) => ({
                    ...d,
                    day: new Date(d.time).toLocaleDateString('en-US', { weekday: 'short' })
                }));
                setForecast(formatted);
            }
        } catch (e) {
            console.error(e);
        }
    }
    
    fetchGEE();
    fetchForecast();
  }, [selectedWard]);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const API_BASE = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
        // Fetch LIVE Stats with dynamic filtering
        const statsRes = await fetch(`${API_BASE}/api/v1/dashboard/wards?level=${granularity}`);
        if (statsRes.ok) {
           const data = await statsRes.json();
           setWards(data);
        }
        
        // Fetch Policies
        const recsRes = await fetch(`${API_BASE}/api/v1/dashboard/recommendations`);
        if (recsRes.ok) setRecs(await recsRes.json());
      } catch (e) {
        console.error("Dashboard backend API error:", e);
      }
    }
    fetchDashboardData();
    
    // Set 60-second polling for live presentation
    const interval = setInterval(fetchDashboardData, 60000);
    return () => clearInterval(interval);
  }, [granularity]);

  // HACKATHON RBAC: Auto-lock Citizen to their assigned ward upon load
  useEffect(() => {
    if (userProfile?.role === 'citizen' && wards.length > 0 && !selectedWard) {
        const home = wards.find(w => w.name === userProfile.home_ward);
        if (home) setSelectedWard(home);
    }
  }, [userProfile, wards, selectedWard]);

  const handleWardClick = (ward: any) => {
    if (userProfile?.role === 'citizen' && ward.name !== userProfile.home_ward) {
        window.alert(`Restricted Protocol: As a registered Citizen, your clearance is locked to analyzing your home ward (${userProfile.home_ward}). Escalate to a Mayor or Ward Member 'Admin' account for holistic city tracking.`);
        return;
    }
    setSelectedWard(ward);
  };

  const avgAqi = wards.length > 0 ? Math.round(wards.reduce((acc, curr) => acc + curr.aqi, 0) / wards.length) : 0;

  return (
    <div className="w-screen h-screen relative font-sans text-slate-100 bg-slate-950 overflow-hidden">
      
      {/* ─── HACKATHON EDGE: Supabase Native Auth Gateway ─── */}
      <AuthOverlay session={session} setSession={setSession} userProfile={userProfile} setUserProfile={setUserProfile} />

      {/* FULLSCREEN Interactive Map */}
      <div className="absolute inset-0 z-0">
        <LeafletMap wards={wards} selectedWard={selectedWard} onWardClick={handleWardClick} granularity={granularity} />
      </div>

      {/* Floating Header */}
      <div className="absolute top-6 left-6 z-[1000] bg-slate-900/90 backdrop-blur-xl shadow-2xl rounded-2xl p-5 border border-slate-700">
        <div className="flex justify-between items-center gap-6">
            <div>
                <h1 className="text-2xl font-bold tracking-tight text-white flex items-center gap-3">
                  <span className="material-symbols-outlined text-blue-500 text-3xl">air</span>
                  VayuDrishti Tracker
                </h1>
                <p className="text-sm text-slate-400 font-medium tracking-wide mt-1 flex items-center gap-2">
                    <span className="relative flex h-2 w-2">
                        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                        <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                    </span>
                    Live OpenAQ Sensor Network
                </p>
            </div>
            
            {/* Multi-Resolution Segmentation Toggle - RBAC Block */}
            {!userProfile || userProfile.role === 'admin' ? (
                <div className="bg-slate-800 p-1 rounded-lg flex border border-slate-700">
                    <button 
                      onClick={() => { setGranularity('district'); setSelectedWard(null); setWards([]); }}
                      className={`px-4 py-1.5 rounded-md text-xs font-bold uppercase tracking-widest transition-all ${granularity === 'district' ? 'bg-slate-700 shadow text-white' : 'text-slate-400 hover:text-slate-200'}`}>
                        District View (11)
                    </button>
                    <button 
                      onClick={() => { setGranularity('ward'); setSelectedWard(null); setWards([]); }}
                      className={`px-4 py-1.5 rounded-md text-xs font-bold uppercase tracking-widest transition-all ${granularity === 'ward' ? 'bg-slate-700 shadow text-blue-400' : 'text-slate-400 hover:text-slate-200'}`}>
                        Ward View (272)
                    </button>
                </div>
            ) : (
                <div className="bg-slate-800 px-4 py-1.5 rounded-lg border border-slate-700">
                    <span className="text-xs font-bold uppercase tracking-widest text-emerald-400">Citizen Level Clearances</span>
                </div>
            )}
        </div>
      </div>

      {/* Floating Side Panel */}
      <div className="absolute top-36 left-6 w-[420px] bottom-6 flex flex-col gap-6 z-[1000]">
        
        {/* Detail Panel */}
        <div className={`bg-slate-900/90 backdrop-blur-xl shadow-2xl rounded-2xl p-6 border border-slate-700 transition-all duration-500 transform ${selectedWard ? 'translate-x-0 opacity-100 flex flex-col' : '-translate-x-full opacity-0 hidden'}`}>
            <div className="flex justify-between items-start mb-6">
                <h2 className="text-2xl font-black uppercase text-white truncate max-w-[80%]">{selectedWard?.name}</h2>
                <button onClick={() => setSelectedWard(null)} className="p-1.5 bg-slate-800 text-slate-400 hover:bg-slate-700 hover:text-white rounded-full">
                    <span className="material-symbols-outlined text-sm">close</span>
                </button>
            </div>

            <div className="flex items-center gap-4 mb-6">
                <div className={`text-6xl font-black ${selectedWard && selectedWard.aqi > 300 ? 'text-rose-500' : 'text-emerald-400'}`}>
                    {selectedWard?.aqi}
                </div>
                <div className="flex flex-col">
                    <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Live Zone AQI</span>
                    <span className={`px-2 py-0.5 mt-1 text-xs font-bold border rounded-md uppercase tracking-wide w-max ${selectedWard && selectedWard.aqi > 300 ? 'bg-rose-500/10 border-rose-500 text-rose-500' : 'bg-emerald-400/10 border-emerald-400 text-emerald-400'}`}>
                        {selectedWard?.status}
                    </span>
                </div>
            </div>

            {/* Google Earth Engine Deep Diagnostics */}
            <div className="mb-6 p-4 bg-slate-800/80 rounded-xl border border-blue-900/50 shadow-inner">
                <h3 className="text-[10px] font-black uppercase text-blue-400 tracking-widest mb-3 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[14px]">satellite_alt</span>
                    Sentinel-5P Satellite Diagnostics
                </h3>
                
                {geeLoading ? (
                    <div className="flex flex-col items-center justify-center p-4">
                        <div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mb-2"></div>
                        <p className="text-[10px] text-blue-400 font-mono tracking-widest uppercase animate-pulse">Scanning Geometries...</p>
                    </div>
                ) : geeData ? (
                    <div className="space-y-3 font-mono text-xs">
                        <div className="flex justify-between items-center border-b border-slate-700 pb-2">
                            <span className="text-slate-400 uppercase font-bold tracking-wider text-[10px]">Biomass CO Plume</span>
                            <span className="text-slate-200 font-bold">{geeData.biomass_burning_index} <span className="text-[9px] text-slate-500">mol/m²</span></span>
                        </div>
                        <div className="flex justify-between items-center border-b border-slate-700 pb-2">
                            <span className="text-slate-400 uppercase font-bold tracking-wider text-[10px]">Construction UVAI</span>
                            <span className="text-slate-200 font-bold">{geeData.construction_dust_index} <span className="text-[9px] text-slate-500">UVAI</span></span>
                        </div>
                        <div className="pt-2">
                            <span className="text-[9px] font-black text-blue-500 uppercase tracking-widest block text-center mb-1">Geological Source</span>
                            <div className="bg-blue-500/10 border border-blue-500/30 p-2 rounded text-blue-400 text-center font-bold text-[10px]">
                                {geeData.dominant_source}
                            </div>
                        </div>
                    </div>
                ) : (
                    <p className="text-[10px] text-slate-500 text-center italic">Initiate Ward Scan to establish secure Earth Engine connection.</p>
                )}
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="p-3 bg-slate-800 rounded-xl border border-slate-700 flex flex-col justify-center">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Raw PM2.5</span>
                    <span className="text-base font-bold text-slate-100">{selectedWard?.pm25} µg</span>
                </div>
                <div className="p-3 bg-slate-800 rounded-xl border border-slate-700 flex flex-col justify-center">
                    <span className="text-[9px] font-bold text-slate-400 uppercase tracking-widest block mb-1">Hourly Trend</span>
                    <span className="text-xs font-bold text-slate-200 uppercase flex items-center gap-1">
                        <span className="material-symbols-outlined text-sm">{selectedWard?.trend === 'increasing' ? 'trending_up' : 'trending_flat'}</span>
                        {selectedWard?.trend}
                    </span>
                </div>
            </div>

            {/* HACKATHON EDGE: Predictive CAMS Forecast Chart */}
            <div className="p-4 bg-slate-800/80 rounded-xl border border-emerald-900/50 shadow-inner">
                <h3 className="text-[10px] font-black uppercase text-emerald-400 tracking-widest mb-3 flex items-center gap-2">
                    <span className="material-symbols-outlined text-[14px]">query_stats</span>
                    8-Day CAMS AI Prediction
                </h3>
                {forecast.length > 0 ? (
                    <div className="h-32 w-full mt-2">
                        <ResponsiveContainer width="100%" height="100%">
                            <LineChart data={forecast}>
                                <XAxis dataKey="day" stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} />
                                <YAxis stroke="#64748b" fontSize={10} tickLine={false} axisLine={false} width={25} />
                                <Tooltip 
                                    contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155', fontSize: '12px' }}
                                    itemStyle={{ color: '#34d399', fontWeight: 'bold' }}
                                />
                                <Line type="monotone" dataKey="pm25" stroke="#34d399" strokeWidth={3} dot={{ r: 3, fill: '#10b981', strokeWidth: 0 }} activeDot={{ r: 5 }} />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                ) : (
                    <div className="flex justify-center py-6">
                        <div className="w-5 h-5 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
                    </div>
                )}
            </div>
        </div>

        {/* Tactical Feed Panel */}
        <div className={`flex-1 bg-slate-900 shadow-2xl rounded-2xl overflow-hidden flex flex-col border border-slate-700 transition-all duration-500 ${selectedWard ? 'hidden' : 'flex'}`}>
            <div className="p-4 bg-slate-800/50 border-b border-slate-700">
                <h3 className="text-[11px] font-black uppercase text-amber-400 tracking-widest flex items-center gap-2">
                    <span className="material-symbols-outlined text-[16px]">precision_manufacturing</span>
                    Groq Llama-3-70B Active Policy Feed
                </h3>
            </div>
            <div className="p-4 overflow-y-auto space-y-4">
                {recs.map(rec => (
                    <div key={rec.id} className="p-4 border border-slate-700 rounded-xl bg-slate-800/80 hover:border-slate-500 hover:bg-slate-800 transition-all shadow-inner">
                        <div className="flex justify-between items-start mb-2">
                            <span className="text-xs font-black text-blue-400 uppercase tracking-widest truncate max-w-[65%]">{rec.ward}</span>
                            <span className={`text-[9px] px-2 py-0.5 rounded-full border border-rose-500/50 text-rose-400 font-bold bg-rose-500/10 tracking-widest uppercase`}>
                                {rec.urgency} Priority
                            </span>
                        </div>
                        <p className="text-[13px] text-slate-200 font-medium leading-snug mb-3 mt-1">
                            {rec.action}
                        </p>
                        <div className="text-[10px] py-2 px-3 bg-slate-900 rounded-lg text-emerald-400 border border-emerald-900/30 flex items-center gap-2">
                            <span className="material-symbols-outlined text-[14px]">track_changes</span>
                            <strong>TARGET:</strong> {rec.impact}
                        </div>
                    </div>
                ))}
            </div>
        </div>

      </div>
    </div>
  );
}
