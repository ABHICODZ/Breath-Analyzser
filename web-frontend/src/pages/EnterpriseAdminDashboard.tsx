import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import LeafletMap from '../components/LeafletMap';
import { LineChart, Line, PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer } from 'recharts';

interface AdminDashboardProps {
  userProfile: any;
  session: any;
  onBack: () => void;
}

interface OverviewData {
  total_complaints: number;
  active_tasks: number;
  critical_zones: number;
  avg_aqi: number;
}

interface Metadata {
  sources: string[];
  timestamp: string;
  query_time_ms: number;
}

export default function EnterpriseAdminDashboard({ userProfile, session, onBack }: AdminDashboardProps) {
  const [activeTab, setActiveTab] = useState<'overview' | 'analytics' | 'council'>('overview');
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [overviewMeta, setOverviewMeta] = useState<Metadata | null>(null);
  const [hotspots, setHotspots] = useState<any[]>([]);
  const [hotspotsMeta, setHotspotsMeta] = useState<Metadata | null>(null);
  const [distribution, setDistribution] = useState<any>(null);
  const [distributionMeta, setDistributionMeta] = useState<Metadata | null>(null);
  const [complaintHeatmap, setComplaintHeatmap] = useState<any[]>([]);
  const [heatmapMeta, setHeatmapMeta] = useState<Metadata | null>(null);
  const [wards, setWards] = useState<any[]>([]);
  const [selectedWard, setSelectedWard] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  
  // Policy Simulator State
  const [showSimulator, setShowSimulator] = useState(false);
  const [simParams, setSimParams] = useState({
    trafficReduction: 50,
    industrialReduction: 30,
    constructionBan: false,
    duration: 7
  });
  const [simResult, setSimResult] = useState<any>(null);
  const [simulating, setSimulating] = useState(false);
  
  // Scenario Library
  const policyScenarios = [
    {
      name: "Emergency Protocol",
      description: "Severe pollution emergency response",
      params: { trafficReduction: 80, industrialReduction: 70, constructionBan: true, duration: 3 }
    },
    {
      name: "Moderate Intervention",
      description: "Balanced approach for sustained improvement",
      params: { trafficReduction: 50, industrialReduction: 40, constructionBan: false, duration: 14 }
    },
    {
      name: "Traffic Focus",
      description: "Target vehicular emissions",
      params: { trafficReduction: 90, industrialReduction: 20, constructionBan: false, duration: 7 }
    },
    {
      name: "Industrial Crackdown",
      description: "Focus on industrial pollution sources",
      params: { trafficReduction: 30, industrialReduction: 80, constructionBan: true, duration: 10 }
    },
    {
      name: "Long-term Strategy",
      description: "Sustainable 30-day policy",
      params: { trafficReduction: 40, industrialReduction: 35, constructionBan: false, duration: 30 }
    }
  ];

  // Map Layer State
  const [mapLayer, setMapLayer] = useState<'aqi' | 'pm25' | 'sources'>('aqi');
  
  // Debug Panel State
  const [showDebug, setShowDebug] = useState(true);

  const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8080';

  useEffect(() => {
    fetchAllData();
    const interval = setInterval(fetchAllData, 30000);
    return () => clearInterval(interval);
  }, []);

  const fetchAllData = async () => {
    console.log('[ADMIN] Starting data fetch...');
    setLoading(true);
    setError(null);
    
    if (!session?.access_token) {
      console.error('[ADMIN] No access token!');
      setError('Authentication required');
      setLoading(false);
      return;
    }
    
    const headers = {
      'Authorization': `Bearer ${session.access_token}`,
      'Content-Type': 'application/json'
    };
    
    try {
      console.log('[ADMIN] Fetching overview...');
      const overviewRes = await fetch(`${API_BASE}/api/v1/admin/analytics/overview`, { headers });
      console.log('[ADMIN] Overview response:', overviewRes.status);
      if (!overviewRes.ok) throw new Error(`Overview API returned ${overviewRes.status}`);
      const overviewData = await overviewRes.json();
      console.log('[ADMIN] Overview data:', overviewData);
      setOverview(overviewData.data);
      setOverviewMeta(overviewData.metadata);

      console.log('[ADMIN] Fetching hotspots...');
      const hotspotsRes = await fetch(`${API_BASE}/api/v1/admin/analytics/hotspots?threshold=200`, { headers });
      if (!hotspotsRes.ok) throw new Error(`Hotspots API returned ${hotspotsRes.status}`);
      const hotspotsData = await hotspotsRes.json();
      console.log('[ADMIN] Hotspots:', hotspotsData.data?.length);
      setHotspots(hotspotsData.data);
      setHotspotsMeta(hotspotsData.metadata);

      console.log('[ADMIN] Fetching distribution...');
      const distRes = await fetch(`${API_BASE}/api/v1/admin/analytics/distribution`, { headers });
      if (!distRes.ok) throw new Error(`Distribution API returned ${distRes.status}`);
      const distData = await distRes.json();
      console.log('[ADMIN] Distribution:', distData.data);
      setDistribution(distData.data);
      setDistributionMeta(distData.metadata);

      console.log('[ADMIN] Fetching heatmap...');
      const heatmapRes = await fetch(`${API_BASE}/api/v1/admin/analytics/complaints-heatmap?days=7`, { headers });
      if (!heatmapRes.ok) throw new Error(`Heatmap API returned ${heatmapRes.status}`);
      const heatmapData = await heatmapRes.json();
      console.log('[ADMIN] Heatmap:', heatmapData.data?.length);
      setComplaintHeatmap(heatmapData.data);
      setHeatmapMeta(heatmapData.metadata);

      console.log('[ADMIN] Fetching wards...');
      const wardsRes = await fetch(`${API_BASE}/api/v1/dashboard/wards?level=ward`);
      if (!wardsRes.ok) throw new Error(`Wards API returned ${wardsRes.status}`);
      const wardsData = await wardsRes.json();
      console.log('[ADMIN] Wards:', wardsData?.length);
      setWards(wardsData);

      console.log('[ADMIN] All data fetched successfully!');
      setLoading(false);
    } catch (err: any) {
      console.error('[ADMIN] Data fetch error:', err);
      setError(err.message);
      setLoading(false);
    }
  };

  const runPolicySimulation = async () => {
    if (!session?.access_token) {
      alert('Authentication required');
      return;
    }
    
    setSimulating(true);
    
    try {
      // Calculate average AQI from wards
      const avgAQI = wards.reduce((sum, w) => sum + w.aqi, 0) / wards.length;
      
      // Call backend mathematical model API
      const res = await fetch(`${API_BASE}/api/v1/admin/policy/simulate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${session.access_token}`
        },
        body: JSON.stringify({
          current_aqi: avgAQI,
          traffic_reduction: simParams.trafficReduction,
          industrial_reduction: simParams.industrialReduction,
          construction_ban: simParams.constructionBan,
          duration: simParams.duration
        })
      });
      
      if (!res.ok) {
        throw new Error(`Simulation API returned ${res.status}`);
      }
      
      const data = await res.json();
      
      // Map backend response to frontend format
      setSimResult({
        currentAQI: Math.round(data.current_aqi),
        predictedAQI: Math.round(data.predicted_aqi),
        aqiReduction: Math.round(data.aqi_reduction),
        percentChange: data.percent_change.toFixed(1),
        affectedWards: data.affected_wards,
        estimatedCost: Math.round(data.estimated_cost),
        healthBenefit: data.health_benefit,
        confidence: data.confidence,
        breakdown: data.breakdown,
        methodology: data.methodology
      });
      
    } catch (err: any) {
      console.error('[POLICY SIM] Error:', err);
      alert(`Simulation failed: ${err.message}`);
    } finally {
      setSimulating(false);
    }
  };

  const COLORS = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

  if (loading && !overview) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950/20 to-slate-950 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-white text-lg">Loading real-time data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950/20 to-slate-950 flex items-center justify-center p-8">
        <div className="bg-red-900/20 border border-red-500 rounded-xl p-8 max-w-2xl w-full">
          <div className="flex items-center gap-4 mb-4">
            <span className="material-symbols-outlined text-red-500 text-5xl">error</span>
            <div>
              <h2 className="text-xl font-bold text-white mb-2">Data Source Error</h2>
              <p className="text-red-400 text-sm">{error}</p>
            </div>
          </div>
          <div className="mt-6 p-4 bg-slate-900/50 rounded-lg">
            <p className="text-xs text-slate-400 mb-2">Debug Info:</p>
            <pre className="text-xs text-slate-300 overflow-auto">{JSON.stringify({
              hasSession: !!session,
              hasToken: !!session?.access_token,
              apiBase: API_BASE,
              overview: overview,
              hotspots: hotspots?.length,
              distribution: distribution
            }, null, 2)}</pre>
          </div>
          <button
            onClick={fetchAllData}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 w-full font-bold"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-blue-950/20 to-slate-950 text-white">
      <header className="bg-slate-950/60 backdrop-blur-2xl border-b border-white/10 px-8 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button onClick={onBack} className="p-2 hover:bg-slate-800 rounded-lg">
              <span className="material-symbols-outlined">arrow_back</span>
            </button>
            <div>
              <h1 className="text-2xl font-black uppercase">Enterprise Admin Dashboard</h1>
              <p className="text-xs text-slate-400">Real-time governance platform - Zero hardcoded data</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            {overviewMeta && (
              <div className="text-xs text-slate-400">
                Last updated: {new Date(overviewMeta.timestamp).toLocaleTimeString()}
                <span className="ml-2 text-green-400">({overviewMeta.query_time_ms}ms)</span>
              </div>
            )}
            <div className="flex items-center gap-2 bg-green-500/20 px-3 py-1 rounded-lg">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse" />
              <span className="text-sm font-bold text-green-400">LIVE</span>
            </div>
          </div>
        </div>

        <div className="flex gap-2 mt-4">
          {[
            { id: 'overview', label: 'Real-Time Overview', icon: 'dashboard' },
            { id: 'analytics', label: 'Deep Analytics', icon: 'analytics' },
            { id: 'council', label: 'AI Council', icon: 'groups' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg font-bold text-sm ${
                activeTab === tab.id
                  ? 'bg-gradient-to-r from-purple-600 to-pink-600'
                  : 'bg-slate-900/50 text-slate-400 hover:text-white'
              }`}
            >
              <span className="material-symbols-outlined text-lg">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>
      </header>

      <main className="p-6">
        {/* COLLAPSIBLE DEBUG PANEL */}
        <div className="mb-6">
          <button
            onClick={() => setShowDebug(!showDebug)}
            className="w-full flex items-center justify-between p-4 bg-cyan-900/30 border-2 border-cyan-500 rounded-xl hover:bg-cyan-900/40 transition-colors"
          >
            <h3 className="text-cyan-400 font-bold text-xl flex items-center gap-2">
              <span className="material-symbols-outlined">bug_report</span>
              SYSTEM STATUS (Real-Time Debug)
            </h3>
            <span className="material-symbols-outlined text-cyan-400">
              {showDebug ? 'expand_less' : 'expand_more'}
            </span>
          </button>
          
          {showDebug && (
            <div className="mt-2 p-6 bg-cyan-900/20 border-2 border-cyan-500/50 rounded-xl">
              <div className="grid grid-cols-3 gap-4 text-sm">
                <div className="bg-slate-900 p-3 rounded">
                  <div className="text-slate-400 text-xs">Overview Data</div>
                  <div className={`text-lg font-bold ${overview ? 'text-green-400' : 'text-red-400'}`}>
                    {overview ? '✓ LOADED' : '❌ MISSING'}
                  </div>
                  {overview && (
                    <div className="text-xs text-slate-500 mt-1">
                      Complaints: {overview.total_complaints} | Tasks: {overview.active_tasks}
                    </div>
                  )}
                </div>
                <div className="bg-slate-900 p-3 rounded">
                  <div className="text-slate-400 text-xs">Wards</div>
                  <div className="text-lg font-bold text-white">{wards?.length || 0} wards</div>
                </div>
                <div className="bg-slate-900 p-3 rounded">
                  <div className="text-slate-400 text-xs">Hotspots</div>
                  <div className={`text-lg font-bold ${hotspots?.length > 0 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {hotspots?.length || 0} zones
                  </div>
                </div>
                <div className="bg-slate-900 p-3 rounded">
                  <div className="text-slate-400 text-xs">Distribution</div>
                  <div className={`text-lg font-bold ${distribution ? 'text-green-400' : 'text-red-400'}`}>
                    {distribution ? '✓ LOADED' : '❌ MISSING'}
                  </div>
                </div>
                <div className="bg-slate-900 p-3 rounded">
                  <div className="text-slate-400 text-xs">Loading State</div>
                  <div className={`text-lg font-bold ${loading ? 'text-yellow-400' : 'text-green-400'}`}>
                    {loading ? '⏳ YES' : '✓ NO'}
                  </div>
                </div>
                <div className="bg-slate-900 p-3 rounded">
                  <div className="text-slate-400 text-xs">Error</div>
                  <div className={`text-lg font-bold ${error ? 'text-red-400' : 'text-green-400'}`}>
                    {error || '✓ NONE'}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {activeTab === 'overview' && overview && (
          <div className="space-y-6">
            <div className="grid grid-cols-4 gap-4">
              {[
                { label: 'Total Complaints', value: overview.total_complaints, icon: 'report', color: 'from-red-600 to-orange-600' },
                { label: 'Active Tasks', value: overview.active_tasks, icon: 'task_alt', color: 'from-blue-600 to-cyan-600' },
                { label: 'Critical Zones', value: overview.critical_zones, icon: 'warning', color: 'from-yellow-600 to-amber-600' },
                { label: 'Avg City AQI', value: overview.avg_aqi, icon: 'air', color: 'from-purple-600 to-pink-600' }
              ].map((stat, i) => (
                <motion.div
                  key={i}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="bg-slate-900/50 border border-slate-800 rounded-xl p-6"
                >
                  <div className="flex items-center justify-between mb-4">
                    <div className={`w-12 h-12 rounded-lg bg-gradient-to-r ${stat.color} flex items-center justify-center`}>
                      <span className="material-symbols-outlined text-white text-2xl">{stat.icon}</span>
                    </div>
                    <span className="text-3xl font-black">{stat.value}</span>
                  </div>
                  <p className="text-sm text-slate-400 font-bold uppercase">{stat.label}</p>
                </motion.div>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex justify-between items-center">
                  <h3 className="font-bold text-sm uppercase">Live AQI Heatmap ({wards.length} wards)</h3>
                  <div className="flex gap-2">
                    {[
                      { id: 'aqi', label: 'AQI', icon: 'air' },
                      { id: 'pm25', label: 'PM2.5', icon: 'blur_on' },
                      { id: 'sources', label: 'Sources', icon: 'factory' }
                    ].map((layer) => (
                      <button
                        key={layer.id}
                        onClick={() => setMapLayer(layer.id as any)}
                        className={`px-3 py-1 rounded text-xs font-bold flex items-center gap-1 ${
                          mapLayer === layer.id
                            ? 'bg-cyan-500 text-white'
                            : 'bg-slate-800 text-slate-400 hover:text-white'
                        }`}
                      >
                        <span className="material-symbols-outlined text-sm">{layer.icon}</span>
                        {layer.label}
                      </button>
                    ))}
                  </div>
                </div>
                <div className="h-[400px] relative">
                  <LeafletMap 
                    wards={wards} 
                    selectedWard={selectedWard} 
                    onWardClick={setSelectedWard} 
                    granularity="ward" 
                    disableWind={true}
                    layer={mapLayer}
                  />
                </div>
              </div>

              <div className="bg-slate-900/50 border border-slate-800 rounded-xl overflow-hidden">
                <div className="bg-slate-900 px-4 py-3 border-b border-slate-800 flex justify-between items-center">
                  <h3 className="font-bold text-sm uppercase flex items-center gap-2">
                    <span className="material-symbols-outlined text-purple-400">science</span>
                    Digital Twin Policy Simulator
                  </h3>
                  <button
                    onClick={() => setShowSimulator(!showSimulator)}
                    className="px-3 py-1 bg-purple-600 text-white rounded text-xs font-bold hover:bg-purple-700 flex items-center gap-1"
                  >
                    <span className="material-symbols-outlined text-sm">{showSimulator ? 'visibility_off' : 'visibility'}</span>
                    {showSimulator ? 'Hide' : 'Show'}
                  </button>
                </div>
                {showSimulator ? (
                  <div className="p-6 space-y-4">
                    {/* Scenario Library */}
                    <div className="mb-4">
                      <p className="text-xs text-slate-400 mb-2 font-bold">QUICK SCENARIOS:</p>
                      <div className="grid grid-cols-2 gap-2">
                        {policyScenarios.map((scenario, i) => (
                          <button
                            key={i}
                            onClick={() => setSimParams(scenario.params)}
                            className="p-3 bg-slate-900 hover:bg-slate-800 border border-slate-700 rounded-lg text-left transition-colors"
                          >
                            <div className="text-sm font-bold text-white mb-1">{scenario.name}</div>
                            <div className="text-xs text-slate-400">{scenario.description}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                    
                    <div className="border-t border-slate-700 pt-4">
                      <p className="text-xs text-slate-400 mb-3 font-bold">CUSTOM PARAMETERS:</p>
                      <div className="space-y-3">
                        <div>
                          <label className="text-xs text-slate-400 block mb-2">Traffic Reduction: {simParams.trafficReduction}%</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={simParams.trafficReduction}
                            onChange={(e) => setSimParams({...simParams, trafficReduction: parseInt(e.target.value)})}
                            className="w-full"
                          />
                        </div>
                        <div>
                          <label className="text-xs text-slate-400 block mb-2">Industrial Reduction: {simParams.industrialReduction}%</label>
                          <input
                            type="range"
                            min="0"
                            max="100"
                            value={simParams.industrialReduction}
                            onChange={(e) => setSimParams({...simParams, industrialReduction: parseInt(e.target.value)})}
                            className="w-full"
                          />
                        </div>
                        <div className="flex items-center gap-2">
                          <input
                            type="checkbox"
                            checked={simParams.constructionBan}
                            onChange={(e) => setSimParams({...simParams, constructionBan: e.target.checked})}
                            className="w-4 h-4"
                          />
                          <label className="text-sm text-white">Construction Ban (15% reduction)</label>
                        </div>
                        <div>
                          <label className="text-xs text-slate-400 block mb-2">Duration: {simParams.duration} days</label>
                          <input
                            type="range"
                            min="1"
                            max="30"
                            value={simParams.duration}
                            onChange={(e) => setSimParams({...simParams, duration: parseInt(e.target.value)})}
                            className="w-full"
                          />
                        </div>
                      </div>
                    </div>
                    
                    <button
                      onClick={runPolicySimulation}
                      disabled={simulating}
                      className="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-bold rounded-lg hover:shadow-lg disabled:opacity-50 flex items-center justify-center gap-2"
                    >
                      {simulating ? (
                        <>
                          <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                          Simulating...
                        </>
                      ) : (
                        <>
                          <span className="material-symbols-outlined">play_arrow</span>
                          Run Simulation
                        </>
                      )}
                    </button>
                    
                    {simResult && (
                      <div className="mt-4 space-y-3 border-t border-slate-700 pt-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="material-symbols-outlined text-green-400">check_circle</span>
                            <span className="text-sm font-bold text-green-400">Simulation Complete</span>
                          </div>
                          {simResult.methodology && (
                            <div className="px-2 py-1 bg-blue-900/30 border border-blue-500/30 rounded text-xs text-blue-300">
                              <span className="material-symbols-outlined text-xs mr-1">science</span>
                              {simResult.methodology}
                            </div>
                          )}
                        </div>
                        
                        {/* Before/After Comparison */}
                        <div className="grid grid-cols-2 gap-4">
                          <div className="bg-red-900/20 border border-red-500/30 p-4 rounded-lg">
                            <div className="text-xs text-red-400 mb-1">CURRENT STATE</div>
                            <div className="text-3xl font-bold text-red-400">{simResult.currentAQI}</div>
                            <div className="text-xs text-slate-400">Average AQI</div>
                          </div>
                          <div className="bg-green-900/20 border border-green-500/30 p-4 rounded-lg">
                            <div className="text-xs text-green-400 mb-1">PREDICTED STATE</div>
                            <div className="text-3xl font-bold text-green-400">{simResult.predictedAQI}</div>
                            <div className="text-xs text-slate-400">After {simParams.duration} days</div>
                          </div>
                        </div>
                        
                        {/* Impact Metrics */}
                        <div className="bg-slate-950 p-4 rounded-lg">
                          <div className="text-center mb-3">
                            <div className="text-3xl font-bold text-cyan-400">-{simResult.aqiReduction} AQI</div>
                            <div className="text-xs text-slate-400">{simResult.percentChange}% improvement</div>
                          </div>
                          
                          <div className="grid grid-cols-2 gap-2 text-xs">
                            <div className="bg-slate-900 p-2 rounded">
                              <div className="text-slate-400">Affected Wards</div>
                              <div className="text-white font-bold">{simResult.affectedWards}</div>
                            </div>
                            <div className="bg-slate-900 p-2 rounded">
                              <div className="text-slate-400">Est. Cost</div>
                              <div className="text-white font-bold">₹{(simResult.estimatedCost / 100000).toFixed(1)}L</div>
                            </div>
                            <div className="bg-slate-900 p-2 rounded">
                              <div className="text-slate-400">Health Benefit</div>
                              <div className="text-white font-bold">{simResult.healthBenefit} lives</div>
                            </div>
                            <div className="bg-slate-900 p-2 rounded">
                              <div className="text-slate-400">Confidence</div>
                              <div className="text-white font-bold">{(simResult.confidence * 100).toFixed(0)}%</div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Cost-Benefit Analysis */}
                        <div className="bg-slate-900 p-3 rounded-lg">
                          <div className="text-xs text-slate-400 mb-2 font-bold">COST-BENEFIT ANALYSIS:</div>
                          <div className="space-y-1 text-xs">
                            <div className="flex justify-between">
                              <span className="text-slate-400">Cost per AQI point reduced:</span>
                              <span className="text-white font-bold">₹{((simResult.estimatedCost / 100000) / simResult.aqiReduction).toFixed(2)}L</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">Lives saved per day:</span>
                              <span className="text-white font-bold">{Math.round(simResult.healthBenefit / simParams.duration)}</span>
                            </div>
                            <div className="flex justify-between">
                              <span className="text-slate-400">ROI (health value):</span>
                              <span className="text-green-400 font-bold">{((simResult.healthBenefit * 50) / (simResult.estimatedCost / 100000)).toFixed(1)}x</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="h-[400px] relative">
                    <LeafletMap 
                      wards={hotspots.length > 0 ? hotspots : wards.slice(0, 10)} 
                      selectedWard={selectedWard} 
                      onWardClick={setSelectedWard} 
                      granularity="ward" 
                      disableWind={true}
                      layer="aqi"
                    />
                  </div>
                )}
              </div>
            </div>

            {distribution && (
              <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
                <h3 className="font-bold text-sm uppercase mb-4">AQI Distribution</h3>
                <div className="grid grid-cols-4 gap-4">
                  {[
                    { name: 'Good', value: distribution.good, color: '#3b82f6' },
                    { name: 'Moderate', value: distribution.moderate, color: '#10b981' },
                    { name: 'Unhealthy', value: distribution.unhealthy, color: '#f59e0b' },
                    { name: 'Hazardous', value: distribution.hazardous, color: '#ef4444' }
                  ].map((item, i) => (
                    <div key={i} className="text-center p-4 bg-slate-900 rounded-lg">
                      <div className="w-12 h-12 rounded-full mx-auto mb-2" style={{ backgroundColor: item.color }} />
                      <div className="text-2xl font-bold">{item.value}</div>
                      <div className="text-xs text-slate-400">{item.name}</div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'analytics' && (
          <div className="space-y-6">
            {/* Ward Rankings */}
            <div className="grid grid-cols-2 gap-6">
              {/* Top 10 Worst */}
              <div className="bg-slate-900/50 border border-red-500/30 rounded-xl p-6">
                <h3 className="text-red-400 font-bold text-lg mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined">warning</span>
                  Top 10 Worst AQI Wards
                </h3>
                <div className="space-y-2">
                  {wards.sort((a, b) => b.aqi - a.aqi).slice(0, 10).map((ward, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-900 p-3 rounded-lg hover:bg-slate-800 cursor-pointer" onClick={() => setSelectedWard(ward)}>
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold text-red-400">#{i + 1}</span>
                        <div>
                          <div className="font-bold text-white">{ward.name}</div>
                          <div className="text-xs text-slate-400">{ward.dominant_source}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-red-400">{ward.aqi}</div>
                        <div className="text-xs text-slate-400">{ward.pm25} µg/m³</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Top 10 Best */}
              <div className="bg-slate-900/50 border border-green-500/30 rounded-xl p-6">
                <h3 className="text-green-400 font-bold text-lg mb-4 flex items-center gap-2">
                  <span className="material-symbols-outlined">check_circle</span>
                  Top 10 Best AQI Wards
                </h3>
                <div className="space-y-2">
                  {wards.sort((a, b) => a.aqi - b.aqi).slice(0, 10).map((ward, i) => (
                    <div key={i} className="flex items-center justify-between bg-slate-900 p-3 rounded-lg hover:bg-slate-800 cursor-pointer" onClick={() => setSelectedWard(ward)}>
                      <div className="flex items-center gap-3">
                        <span className="text-2xl font-bold text-green-400">#{i + 1}</span>
                        <div>
                          <div className="font-bold text-white">{ward.name}</div>
                          <div className="text-xs text-slate-400">{ward.dominant_source}</div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-2xl font-bold text-green-400">{ward.aqi}</div>
                        <div className="text-xs text-slate-400">{ward.pm25} µg/m³</div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Statistical Summary */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="font-bold text-lg mb-4">City-Wide Statistical Analysis</h3>
              <div className="grid grid-cols-5 gap-4">
                {[
                  { label: 'Average AQI', value: Math.round(wards.reduce((sum, w) => sum + w.aqi, 0) / wards.length), color: 'text-cyan-400' },
                  { label: 'Median AQI', value: wards.sort((a, b) => a.aqi - b.aqi)[Math.floor(wards.length / 2)]?.aqi || 0, color: 'text-blue-400' },
                  { label: 'Min AQI', value: Math.min(...wards.map(w => w.aqi)), color: 'text-green-400' },
                  { label: 'Max AQI', value: Math.max(...wards.map(w => w.aqi)), color: 'text-red-400' },
                  { label: 'Std Dev', value: Math.round(Math.sqrt(wards.reduce((sum, w) => sum + Math.pow(w.aqi - (wards.reduce((s, x) => s + x.aqi, 0) / wards.length), 2), 0) / wards.length)), color: 'text-purple-400' }
                ].map((stat, i) => (
                  <div key={i} className="bg-slate-900 p-4 rounded-lg text-center">
                    <div className={`text-3xl font-bold ${stat.color}`}>{stat.value}</div>
                    <div className="text-xs text-slate-400 mt-1">{stat.label}</div>
                  </div>
                ))}
              </div>
            </div>

            {/* Bar Chart - Top 20 Wards */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="font-bold text-lg mb-4">Top 20 Wards by AQI</h3>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={wards.sort((a, b) => b.aqi - a.aqi).slice(0, 20).map(w => ({ name: w.name.substring(0, 15), aqi: w.aqi }))}>
                  <XAxis dataKey="name" angle={-45} textAnchor="end" height={100} stroke="#64748b" fontSize={10} />
                  <YAxis stroke="#64748b" fontSize={12} />
                  <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155' }} />
                  <Line type="monotone" dataKey="aqi" stroke="#ef4444" strokeWidth={3} dot={{ fill: '#ef4444', r: 4 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Pollution Source Breakdown */}
            <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
              <h3 className="font-bold text-lg mb-4">Pollution Source Distribution</h3>
              <div className="grid grid-cols-4 gap-4">
                {(Object.entries(
                  wards.reduce((acc, w) => {
                    acc[w.dominant_source] = (acc[w.dominant_source] || 0) + 1;
                    return acc;
                  }, {} as Record<string, number>)
                ) as [string, number][]).map(([source, count], i) => (
                  <div key={i} className="bg-slate-900 p-4 rounded-lg">
                    <div className="text-2xl font-bold text-cyan-400">{count}</div>
                    <div className="text-xs text-slate-400 mt-1">{source}</div>
                    <div className="text-xs text-slate-600 mt-1">{((count / wards.length) * 100).toFixed(1)}% of wards</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'council' && (
          <CouncilTab session={session} />
        )}
      </main>
    </div>
  );
}


// Council Tab Component
function CouncilTab({ session }: { session: any }) {
  const [scenario, setScenario] = useState('');
  const [councilDecision, setCouncilDecision] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [agents, setAgents] = useState<any[]>([]);
  
  const API_BASE = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8080';

  useEffect(() => {
    fetchAgents();
  }, []);

  const fetchAgents = async () => {
    try {
      const token = session?.access_token;
      const res = await fetch(`${API_BASE}/api/v1/admin/council/agents`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (res.ok) {
        const data = await res.json();
        setAgents(data.data || []);
      }
    } catch (err) {
      console.error('[COUNCIL] Failed to fetch agents:', err);
    }
  };

  const conveneCouncil = async () => {
    if (!scenario.trim()) return;
    
    setLoading(true);
    try {
      const token = session?.access_token;
      const res = await fetch(`${API_BASE}/api/v1/admin/council/convene`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ scenario: scenario.trim(), context: {} })
      });
      
      if (res.ok) {
        const decision = await res.json();
        setCouncilDecision(decision);
      } else {
        alert('Failed to convene council: ' + res.statusText);
      }
    } catch (err) {
      console.error('[COUNCIL] Error:', err);
      alert('Error convening council');
    } finally {
      setLoading(false);
    }
  };

  const presetScenarios = [
    "Should we implement odd-even vehicle restrictions?",
    "Emergency response for AQI > 400",
    "Ban construction activities for 7 days",
    "Increase industrial emission penalties",
    "Deploy mobile air purifiers in critical zones"
  ];

  const getVoteColor = (vote: string) => {
    if (vote === 'APPROVE') return 'text-green-400 bg-green-500/20';
    if (vote === 'MODIFY') return 'text-yellow-400 bg-yellow-500/20';
    return 'text-red-400 bg-red-500/20';
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-900/50 to-purple-900/50 border border-indigo-500/30 rounded-xl p-6">
        <h2 className="text-2xl font-bold mb-2 flex items-center gap-2">
          <span className="material-symbols-outlined text-indigo-400">groups</span>
          AI Governance Council
        </h2>
        <p className="text-slate-300 mb-4">
          Multi-agent decision system simulating real municipal governance with 5 AI agents representing different perspectives.
        </p>
        
        {/* Council Agents */}
        <div className="grid grid-cols-5 gap-3">
          {agents.map((agent, i) => (
            <div key={i} className="bg-slate-900/50 border border-slate-700 rounded-lg p-3 text-center">
              <div className="w-12 h-12 mx-auto mb-2 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center">
                <span className="material-symbols-outlined text-white">person</span>
              </div>
              <p className="text-xs font-bold text-white mb-1">{agent.name}</p>
              <p className="text-xs text-slate-400">{agent.role}</p>
            </div>
          ))}
        </div>
      </div>

      {/* Scenario Input */}
      <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
        <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
          <span className="material-symbols-outlined text-purple-400">gavel</span>
          Propose Policy Decision
        </h3>
        
        {/* Preset Scenarios */}
        <div className="mb-4 p-4 bg-slate-900 rounded-lg border border-slate-700">
          <p className="text-xs text-slate-400 mb-2 font-bold">PRESET SCENARIOS:</p>
          <div className="flex flex-wrap gap-2">
            {presetScenarios.map((preset, i) => (
              <button
                key={i}
                onClick={() => setScenario(preset)}
                className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs rounded-lg border border-slate-600"
              >
                {preset}
              </button>
            ))}
          </div>
        </div>
        
        <div className="flex gap-3">
          <input
            type="text"
            value={scenario}
            onChange={(e) => setScenario(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && conveneCouncil()}
            placeholder="Describe the policy decision or scenario..."
            className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-4 py-3 text-white placeholder-slate-500"
          />
          <button
            onClick={conveneCouncil}
            disabled={loading || !scenario.trim()}
            className="px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white font-bold rounded-lg hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading ? (
              <>
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Deliberating...
              </>
            ) : (
              <>
                <span className="material-symbols-outlined">how_to_vote</span>
                Convene Council
              </>
            )}
          </button>
        </div>
      </div>

      {/* Council Decision */}
      {councilDecision && (
        <div className="space-y-6">
          {/* Situation Summary */}
          <div className="bg-slate-900/50 border border-blue-500/30 rounded-xl p-6">
            <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
              <span className="material-symbols-outlined text-blue-400">assessment</span>
              Situation Analysis
            </h3>
            <p className="text-slate-300 mb-4">{councilDecision.situation_summary}</p>
            
            <div className="grid grid-cols-4 gap-4">
              <div className="bg-slate-900 border border-slate-700 rounded-lg p-3">
                <p className="text-xs text-slate-400 mb-1">Total Wards</p>
                <p className="text-2xl font-bold text-white">{councilDecision.key_data_points.total_wards}</p>
              </div>
              <div className="bg-slate-900 border border-red-500/30 rounded-lg p-3">
                <p className="text-xs text-slate-400 mb-1">Critical Zones</p>
                <p className="text-2xl font-bold text-red-400">{councilDecision.key_data_points.critical_zones}</p>
              </div>
              <div className="bg-slate-900 border border-yellow-500/30 rounded-lg p-3">
                <p className="text-xs text-slate-400 mb-1">Avg AQI</p>
                <p className="text-2xl font-bold text-yellow-400">{councilDecision.key_data_points.avg_aqi}</p>
              </div>
              <div className="bg-slate-900 border border-purple-500/30 rounded-lg p-3">
                <p className="text-xs text-slate-400 mb-1">Confidence</p>
                <p className="text-2xl font-bold text-purple-400">{(councilDecision.confidence_level * 100).toFixed(0)}%</p>
              </div>
            </div>
          </div>

          {/* DEBATE TRANSCRIPT - NEW FEATURE */}
          {councilDecision.debate_transcript && councilDecision.debate_transcript.length > 0 && (
            <div className="bg-slate-900/50 border border-indigo-500/30 rounded-xl p-6">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <span className="material-symbols-outlined text-indigo-400">chat</span>
                Live Council Debate (3 Rounds)
              </h3>
              
              <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
                {councilDecision.debate_transcript.map((msg: any, i: number) => {
                  const getEmotionColor = (emotion: string) => {
                    if (emotion === 'frustrated') return 'border-red-500/50 bg-red-900/20';
                    if (emotion === 'concerned') return 'border-yellow-500/50 bg-yellow-900/20';
                    if (emotion === 'supportive') return 'border-green-500/50 bg-green-900/20';
                    return 'border-slate-700 bg-slate-900/50';
                  };
                  
                  const getEmotionIcon = (emotion: string) => {
                    if (emotion === 'frustrated') return 'warning';
                    if (emotion === 'concerned') return 'error';
                    if (emotion === 'supportive') return 'check_circle';
                    return 'chat_bubble';
                  };
                  
                  return (
                    <div key={i} className={`border rounded-lg p-4 ${getEmotionColor(msg.emotion)}`}>
                      <div className="flex items-start gap-3">
                        <div className="w-10 h-10 rounded-full bg-gradient-to-br from-indigo-500 to-purple-500 flex items-center justify-center flex-shrink-0">
                          <span className="material-symbols-outlined text-white text-sm">person</span>
                        </div>
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="font-bold text-white text-sm">{msg.agent_name}</span>
                            <span className="text-xs text-slate-400">• {msg.role}</span>
                            <span className="px-2 py-0.5 bg-indigo-500/20 text-indigo-300 text-xs rounded">
                              Round {msg.round}
                            </span>
                            <span className={`material-symbols-outlined text-xs ${
                              msg.emotion === 'frustrated' ? 'text-red-400' :
                              msg.emotion === 'concerned' ? 'text-yellow-400' :
                              msg.emotion === 'supportive' ? 'text-green-400' :
                              'text-slate-400'
                            }`}>
                              {getEmotionIcon(msg.emotion)}
                            </span>
                          </div>
                          {msg.responding_to && (
                            <p className="text-xs text-slate-500 mb-2 italic">
                              Responding to {msg.responding_to}
                            </p>
                          )}
                          <p className="text-sm text-slate-200 leading-relaxed">{msg.message}</p>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
              
              <div className="mt-4 pt-4 border-t border-slate-700 flex items-center gap-4 text-xs text-slate-400">
                <span>Total Messages: {councilDecision.debate_transcript.length}</span>
                <span>•</span>
                <span>Debate Rounds: {councilDecision.metadata.debate_rounds}</span>
                <span>•</span>
                <span className="text-green-400">Consensus Reached</span>
              </div>
            </div>
          )}

          {/* Consensus & Conflicts */}
          {(councilDecision.consensus_points?.length > 0 || councilDecision.conflicts_identified?.length > 0) && (
            <div className="grid grid-cols-2 gap-4">
              {councilDecision.conflicts_identified?.length > 0 && (
                <div className="bg-orange-900/20 border border-orange-500/30 rounded-xl p-4">
                  <h4 className="text-sm font-bold mb-2 flex items-center gap-2 text-orange-400">
                    <span className="material-symbols-outlined text-sm">warning</span>
                    Conflicts Identified
                  </h4>
                  <ul className="space-y-1">
                    {councilDecision.conflicts_identified.map((conflict: string, i: number) => (
                      <li key={i} className="text-xs text-orange-200 flex items-start gap-1">
                        <span className="material-symbols-outlined text-xs mt-0.5">error</span>
                        {conflict}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
              
              {councilDecision.consensus_points?.length > 0 && (
                <div className="bg-green-900/20 border border-green-500/30 rounded-xl p-4">
                  <h4 className="text-sm font-bold mb-2 flex items-center gap-2 text-green-400">
                    <span className="material-symbols-outlined text-sm">check_circle</span>
                    Consensus Achieved
                  </h4>
                  <ul className="space-y-1">
                    {councilDecision.consensus_points.map((point: string, i: number) => (
                      <li key={i} className="text-xs text-green-200 flex items-start gap-1">
                        <span className="material-symbols-outlined text-xs mt-0.5">check</span>
                        {point}
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Agent Opinions */}
          <div className="bg-slate-900/50 border border-slate-800 rounded-xl p-6">
            <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
              <span className="material-symbols-outlined text-purple-400">how_to_vote</span>
              Final Votes & Positions
            </h3>
            
            <div className="space-y-4">
              {councilDecision.agent_opinions.map((opinion: any, i: number) => (
                <div key={i} className="bg-slate-900 border border-slate-700 rounded-lg p-4">
                  <div className="flex items-start justify-between mb-3">
                    <div>
                      <p className="font-bold text-white">{opinion.agent_name}</p>
                      <p className="text-xs text-slate-400">{opinion.role}</p>
                      {opinion.vote_changed && (
                        <p className="text-xs text-yellow-400 mt-1 flex items-center gap-1">
                          <span className="material-symbols-outlined text-xs">sync</span>
                          Vote changed: {opinion.initial_vote} → {opinion.vote}
                        </p>
                      )}
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`px-3 py-1 rounded-lg text-xs font-bold ${getVoteColor(opinion.vote)}`}>
                        {opinion.vote}
                      </span>
                      <span className="px-2 py-1 bg-slate-800 text-slate-300 text-xs rounded">
                        Priority: {opinion.priority_score}/10
                      </span>
                    </div>
                  </div>
                  
                  <p className="text-sm text-slate-300 mb-2">{opinion.analysis}</p>
                  
                  <div className="mt-3 pt-3 border-t border-slate-700">
                    <p className="text-xs text-slate-400 mb-1">Recommendation:</p>
                    <p className="text-sm text-white">{opinion.recommendation}</p>
                  </div>
                  
                  <div className="mt-2">
                    <p className="text-xs text-slate-400 mb-1">Reasoning:</p>
                    <p className="text-xs text-slate-300 italic">{opinion.reasoning}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Conflicts */}
          {councilDecision.conflicts_identified.length > 0 && (
            <div className="bg-orange-900/20 border border-orange-500/30 rounded-xl p-6">
              <h3 className="text-lg font-bold mb-3 flex items-center gap-2">
                <span className="material-symbols-outlined text-orange-400">warning</span>
                Conflicts Identified
              </h3>
              <ul className="space-y-2">
                {councilDecision.conflicts_identified.map((conflict: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-orange-200">
                    <span className="material-symbols-outlined text-orange-400 text-lg">error</span>
                    {conflict}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Final Decision */}
          <div className="bg-gradient-to-r from-green-900/30 to-blue-900/30 border border-green-500/30 rounded-xl p-6">
            <h3 className="text-xl font-bold mb-3 flex items-center gap-2">
              <span className="material-symbols-outlined text-green-400">check_circle</span>
              Final Council Decision
            </h3>
            <p className="text-lg text-white mb-4">{councilDecision.final_decision}</p>
            
            <div className="mb-4">
              <p className="text-sm text-slate-400 mb-2">Recommended Actions:</p>
              <ul className="space-y-2">
                {councilDecision.recommended_actions.map((action: string, i: number) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-slate-200">
                    <span className="material-symbols-outlined text-green-400 text-lg">arrow_right</span>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
            
            <div className="pt-4 border-t border-slate-700">
              <p className="text-sm text-slate-400 mb-1">Expected Outcome:</p>
              <p className="text-sm text-slate-200">{councilDecision.expected_outcome}</p>
            </div>
            
            <div className="mt-4 flex items-center gap-4 text-xs text-slate-400">
              <span>Votes: APPROVE {councilDecision.metadata.votes.APPROVE} | MODIFY {councilDecision.metadata.votes.MODIFY} | REJECT {councilDecision.metadata.votes.REJECT}</span>
              <span>•</span>
              <span>Query Time: {councilDecision.metadata.query_time_ms}ms</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
