import osmnx as ox
import networkx as nx
import geopandas as gpd
from shapely.geometry import Point
import numpy as np

# Configure osmnx settings
ox.settings.log_console = True
ox.settings.use_cache = True

class CityGraphExtractor:
    """
    Extracts road networks and building footprints from OpenStreetMap
    to construct the basis for the Spatio-Temporal Graph Neural Network.
    """
    def __init__(self, place_name: str, network_type: str = 'drive'):
        self.place_name = place_name
        self.network_type = network_type
        
        self.graph = None
        self.buildings = None

    def extract_infrastructure(self):
        """Fetches the road network and buildings for the given place."""
        print(f"Fetching road network for {self.place_name}...")
        self.graph = ox.graph_from_place(self.place_name, network_type=self.network_type, simplify=True)
        
        print(f"Fetching building footprints for {self.place_name}...")
        # Get building footprints
        try:
            self.buildings = ox.features_from_place(self.place_name, tags={'building': True})
        except Exception as e:
            print(f"Failed to fetch buildings: {e}")
            self.buildings = gpd.GeoDataFrame()
        
        # Project both to a local CRS (coordinate reference system) for accurate distance measurements in meters
        self.graph = ox.project_graph(self.graph)
        if not self.buildings.empty:
            self.buildings = self.buildings.to_crs(ox.graph_to_gdfs(self.graph, nodes=True)[0].crs)

    def calculate_canyon_metrics(self):
        """
        Approximates Street Canyon metrics (Aspect Ratio H/W and Sky View Factor - SVF)
        by assigning average building heights and street widths to edges.
        """
        if self.graph is None or self.buildings.empty:
            print("Graph or buildings not loaded. Call extract_infrastructure() first.")
            return

        print("Calculating street canyon metrics...")
        
        # Extract nodes and edges
        nodes, edges = ox.graph_to_gdfs(self.graph)
        
        # Estimate building heights (if 'height' tag is missing, assume 10m / ~3 stories)
        if 'height' in self.buildings.columns:
            self.buildings['height_num'] = self.buildings['height'].str.extract('([0-9.]+)').astype(float)
            self.buildings['height_num'] = self.buildings['height_num'].fillna(10.0)
        else:
            self.buildings['height_num'] = 10.0

        # Create spatial index for buildings for fast nearest-neighbor search
        building_sindex = self.buildings.sindex

        for u, v, key, data in self.graph.edges(keys=True, data=True):
            # 1. Estimate Street Width (W)
            # Default to 10m if width is missing
            width = 10.0
            if 'width' in data:
                try:
                    # Sometimes width is a list or string, try to parse
                    w_val = data['width']
                    if isinstance(w_val, list):
                        w_val = w_val[0]
                    width = float(str(w_val).split(' ')[0])
                except:
                    pass
            data['street_width'] = width

            # 2. Estimate average adjacent building height (H)
            edge_geometry = data.get('geometry')
            if edge_geometry:
                # Buffer the street centerline by 20 meters to find adjacent buildings
                search_area = edge_geometry.buffer(20)
                possible_matches_index = list(building_sindex.intersection(search_area.bounds))
                possible_matches = self.buildings.iloc[possible_matches_index]
                precise_matches = possible_matches[possible_matches.intersects(search_area)]
                
                if not precise_matches.empty:
                    avg_height = precise_matches['height_num'].mean()
                else:
                    avg_height = 0.0 # No buildings nearby
            else:
                avg_height = 0.0

            data['avg_building_height'] = avg_height

            # 3. Calculate Aspect Ratio (H/W)
            # Add a small epsilon to width to avoid division by zero
            aspect_ratio = avg_height / (width + 0.1)
            data['aspect_ratio'] = aspect_ratio
            
            # 4. Approximate Sky View Factor (SVF)
            # A simplified empirical relationship where SVF approaches 1 for low H/W and 0 for high H/W
            # e.g., SVF ~ cos(arctan(H / (0.5 * W)))
            theta = np.arctan(avg_height / (0.5 * width + 0.1))
            svf = np.cos(theta)
            data['svf'] = svf

    def get_graph(self):
        return self.graph

if __name__ == "__main__":
    # Test script for a small bounding box
    # Using a small neighborhood in Manhattan as an example for testing 
    # since we requested building footprints
    print("Initializing extractor for testing...")
    extractor = CityGraphExtractor("Financial District, Manhattan, New York, USA")
    extractor.extract_infrastructure()
    extractor.calculate_canyon_metrics()
    
    G = extractor.get_graph()
    if G:
        print(f"Graph generated with {len(G.nodes)} nodes and {len(G.edges)} edges.")
        
        # Print sample edge data
        sample_edge = list(G.edges(data=True))[0]
        print("\nSample edge data:")
        print(f"H/W Ratio: {sample_edge[2].get('aspect_ratio'):.2f}")
        print(f"SVF: {sample_edge[2].get('svf'):.2f}")
