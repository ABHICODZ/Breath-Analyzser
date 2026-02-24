from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any
import networkx as nx
from app.services.routing_engine import AStarSpatioTemporalRouter

router = APIRouter()

class NavigationResponse(BaseModel):
    shortest_path_geojson: Dict[str, Any]
    cleanest_path_geojson: Dict[str, Any]
    stats: Dict[str, float]

def convert_path_to_geojson(G: nx.MultiDiGraph, path: List[Any], name: str, color: str) -> Dict[str, Any]:
    """Helper formatting the output path into Mapbox compatible GeoJSON."""
    coordinates = []
    for node in path:
        node_data = G.nodes.get(node, {})
        # OSMnx provides x (lon), y (lat)
        lon = node_data.get('x', 0.0)
        lat = node_data.get('y', 0.0)
        coordinates.append([lon, lat])

    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {
                    "name": name,
                    "color": color
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": coordinates
                }
            }
        ]
    }

@router.get("/route", response_model=NavigationResponse)
async def get_optimal_route(
    start_lat: float = Query(..., description="Starting node latitude"),
    start_lon: float = Query(..., description="Starting node longitude"),
    end_lat: float = Query(..., description="Destination node latitude"),
    end_lon: float = Query(..., description="Destination node longitude"),
    health_sensitivity: int = Query(50, ge=0, le=100, description="0 (Distance only) to 100 (Cleanest air only)")
):
    """
    Computes and compares the default shortest geographic path against
    the Spatio-Temporal Clean-Air route.
    """
    # 1. Fetch Global Graph 
    # In a full app context, this graph should be loaded in memory on startup.
    # We will instantiate a dummy graph here simulating the global state.
    G = nx.MultiDiGraph()
    G.add_node(1, y=start_lat, x=start_lon)
    G.add_node(2, y=end_lat, x=end_lon)
    G.add_node(3, y=(start_lat+end_lat)/2.0, x=(start_lon+end_lon)/2.0)
    
    # Clean indirect route
    G.add_edge(1, 3, length=300.0, predicted_pm25_avg=15.0)
    G.add_edge(3, 2, length=300.0, predicted_pm25_avg=12.0)
    # Polluted direct route
    G.add_edge(1, 2, length=500.0, predicted_pm25_avg=120.0)
    
    source_node = 1
    target_node = 2
    
    # 2. Initialize Router
    engine = AStarSpatioTemporalRouter(G)
    
    try:
        # 3. Compute Shortest Path (beta = 0.0)
        path_s, dist_s, exp_s = engine.compute_route(source_node, target_node, beta=0.0)
        
        # 4. Compute Cleanest Path (beta dynamically mapped: 0 -> 0.0, 100 -> 1.0)
        beta_val = health_sensitivity / 100.0
        path_c, dist_c, exp_c = engine.compute_route(source_node, target_node, beta=beta_val)
        
    except nx.NetworkXNoPath:
        raise HTTPException(status_code=404, detail="No feasible route found between coordinates.")
        
    # 5. Compile Statistics
    exposure_diff = exp_s - exp_c
    exposure_pct_reduction = (exposure_diff / exp_s * 100) if exp_s > 0 else 0
    
    distance_diff = dist_c - dist_s
    distance_pct_increase = (distance_diff / dist_s * 100) if dist_s > 0 else 0
            
    stats = {
        "shortest_dist_m": dist_s,
        "cleanest_dist_m": dist_c,
        "fastest_pm25_exposure": exp_s,
        "cleanest_pm25_exposure": exp_c,
        "exposure_reduction_pct": exposure_pct_reduction,
        "distance_increase_pct": distance_pct_increase
    }
    
    # 6. Build GeoJSON Maps
    gj_short = convert_path_to_geojson(G, path_s, "Shortest Route", "#FF0000")
    gj_clean = convert_path_to_geojson(G, path_c, "Clean Air Route", "#00FF00")

    return NavigationResponse(
        shortest_path_geojson=gj_short,
        cleanest_path_geojson=gj_clean,
        stats=stats
    )
