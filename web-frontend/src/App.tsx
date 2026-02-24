import React, { useState, useMemo } from 'react';
import LeafletMap from './components/LeafletMap';
import MapControl from './components/MapControl';

function generateDummyData() {
  const points = [];
  for (let i = 0; i < 500; i++) {
    points.push([
      40.7128 + (Math.random() - 0.5) * 0.1,
      -74.0060 + (Math.random() - 0.5) * 0.1,
      Math.random()
    ]);
  }
  return points;
}

function App() {
  const [healthSensitivity, setHealthSensitivity] = useState(50);
  const [isLoading, setIsLoading] = useState(false);
  const [routeStats, setRouteStats] = useState<any>(null);

  const [shortestRoute, setShortestRoute] = useState<any>(null);
  const [cleanestRoute, setCleanestRoute] = useState<any>(null);

  const heatmapData = useMemo(() => generateDummyData(), []);

  const handleCompareRoutes = () => {
    setIsLoading(true);
    setTimeout(() => {
      setRouteStats({
        exposure_reduction_pct: 17.1 + (healthSensitivity / 100 * 5),
        distance_increase_pct: 2.8 + (healthSensitivity / 100 * 2)
      });

      setShortestRoute([
        [40.7050, -74.0100],
        [40.7150, -73.9950],
        [40.7650, -73.9700]
      ]);

      setCleanestRoute([
        [40.7050, -74.0100],
        [40.7300, -74.0200],
        [40.7650, -73.9700]
      ]);

      setIsLoading(false);
    }, 800);
  };

  return (
    <div className="w-full h-screen relative bg-slate-900 overflow-hidden">

      <LeafletMap
        heatmapData={heatmapData}
        shortestRoute={shortestRoute}
        cleanestRoute={cleanestRoute}
      />

      <MapControl
        healthSensitivity={healthSensitivity}
        setHealthSensitivity={setHealthSensitivity}
        onCompareRoutes={handleCompareRoutes}
        isLoading={isLoading}
        routeStats={routeStats}
      />

    </div>
  );
}

export default App;
