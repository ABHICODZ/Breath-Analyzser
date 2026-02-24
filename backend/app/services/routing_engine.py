import networkx as nx
import heapq
import numpy as np
from typing import List, Dict, Tuple, Any

class AStarSpatioTemporalRouter:
    """
    A custom routing engine that modifies Dijkstra/A* to account for both 
    geographic distance and predicted dynamic pollutant concentrations.
    """
    def __init__(self, graph: nx.MultiDiGraph):
        self.graph = graph

    def _get_pollutant_integral(self, u: Any, v: Any, edge_data: Dict) -> float:
        """
        Simulates retrieving the integral of predicted pollutant concentration $P(t)$ 
        along the edge from the Spatio-Temporal Model outputs.
        """
        # In a fully integrated system, this would query the DB or ML Model states
        # For demonstration, we assume a static predicted value exists on the edge
        # or we generate a dummy predicted value based on edge attributes.
        
        # Pull PM2.5 prediction from edge if exists, else synthesize a dummy value
        pm25 = edge_data.get('predicted_pm25_avg', np.random.uniform(5.0, 150.0))
        
        # Return integration: PM2.5 * time_to_traverse
        # Assuming walking/driving speed of 5 m/s for basic time estimation
        length = edge_data.get('length', 10.0)
        time_to_traverse = length / 5.0 
        
        return pm25 * time_to_traverse

    def compute_route(self, source: Any, target: Any, beta: float = 0.5, alpha: float = 1.0) -> Tuple[List[Any], float, float]:
        """
        Computes the optimal path based on the custom Health-Cost function.
        Weight = (alpha * Distance) + (beta * Cumulative_Pollutant_Exposure)
        
        Args:
            source: Source node ID
            target: Target node ID
            beta: Health sensitivity factor (0.0 to 1.0)
            alpha: Distance priority factor (default 1.0)
            
        Returns:
            Tuple containing:
            1. The path (list of node IDs)
            2. Total route distance in meters
            3. Total PM2.5 exposure metric
        """
        if source not in self.graph or target not in self.graph:
            raise ValueError("Source or Target node not found in the graph.")

        # Priority queue stores tuples of (cost, current_node, path, total_distance, total_exposure)
        queue = [(0.0, source, [source], 0.0, 0.0)]
        
        # Track minimum costs to reach a node
        min_costs = {source: 0.0}

        while queue:
            # Pop the node with the lowest aggregated cost
            current_cost, current_node, path, total_dist, total_exp = heapq.heappop(queue)

            # If we reached the target, we have our optimal path
            if current_node == target:
                return path, total_dist, total_exp

            # It's possible we found a better route to this node since this tuple was queued
            if current_cost > min_costs.get(current_node, float('inf')):
                continue

            # Iterate over all outgoing edges
            for neighbor, edges in self.graph[current_node].items():
                # In a MultiDiGraph, there can be multiple edges between u and v
                # We simply evaluate the first one (0) 
                edge_data = edges[0]
                
                length = edge_data.get('length', 1.0)
                exposure = self._get_pollutant_integral(current_node, neighbor, edge_data)
                
                # Equation: Weight = (alpha * L) + (beta * P)
                edge_cost = (alpha * length) + (beta * exposure)
                
                new_cost = current_cost + edge_cost
                
                if new_cost < min_costs.get(neighbor, float('inf')):
                    min_costs[neighbor] = new_cost
                    new_dist = total_dist + length
                    new_exp = total_exp + exposure
                    
                    heapq.heappush(
                        queue, 
                        (new_cost, neighbor, path + [neighbor], new_dist, new_exp)
                    )

        raise nx.NetworkXNoPath(f"No path between {source} and {target}.")

if __name__ == "__main__":
    # Test Custom Router
    print("Testing CAR Routing Engine...")
    G = nx.MultiDiGraph()
    G.add_edge(1, 2, length=100.0, predicted_pm25_avg=10.0) # Clean, Short
    G.add_edge(1, 3, length=50.0, predicted_pm25_avg=150.0) # Polluted, Very Short
    G.add_edge(3, 2, length=60.0, predicted_pm25_avg=120.0)
    
    router = AStarSpatioTemporalRouter(G)
    
    # 1. Standard Shortest Path (Beta = 0)
    path_short, dist_short, exp_short = router.compute_route(1, 2, beta=0.0)
    print(f"Shortest Path: {path_short} | Dist: {dist_short} | Exp: {exp_short:.1f}")
    
    # 2. Maximum Health Sensitivity (Beta = 1.0)
    path_clean, dist_clean, exp_clean = router.compute_route(1, 2, beta=1.0)
    print(f"Cleanest Path: {path_clean} | Dist: {dist_clean} | Exp: {exp_clean:.1f}")
