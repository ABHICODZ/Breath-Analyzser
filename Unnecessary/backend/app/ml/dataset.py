import torch
from torch_geometric.data import Data, Dataset
import numpy as np

class SpatioTemporalDataset(Dataset):
    """
    Constructs PyTorch Geometric Graph dataset objects dynamically from
    TimescaleDB historical sensor records and OSMnx derived urban edges.
    """
    def __init__(self, num_nodes, sequence_length, transform=None, pre_transform=None):
        super(SpatioTemporalDataset, self).__init__(".", transform, pre_transform)
        self.num_nodes = num_nodes
        self.sequence_length = sequence_length
        
        # Simulate generating structural edge indices from an OSMnx graph.
        # Format required by torch_geometric is [2, Num_Edges]
        self.num_edges = self.num_nodes * 3 # Assume average degree of 3
        self.edge_index = self._generate_mock_edge_index()
        
        # Simulate assigning weights (could be distance combined with SVF / Canyon metrics)
        self.edge_weight = torch.rand((self.num_edges,), dtype=torch.float)

    def _generate_mock_edge_index(self):
        """Generates dummy connections mimicking road networks."""
        sources = torch.randint(0, self.num_nodes, (self.num_edges,))
        targets = torch.randint(0, self.num_nodes, (self.num_edges,))
        return torch.stack([sources, targets], dim=0)

    def len(self):
        # Represents total number of sliding window time-series sequences available
        return 100 

    def get(self, idx):
        """
        Fetches a single sliding window data point containing:
        1. Node Features over time: (Num_Nodes, Node_Features, Sequence_Length)
        2. Graph Connectivity: `edge_index`, `edge_weight`
        3. Target Labels: (Num_Nodes, 1) -> value at Sequence_Length + 1
        """
        # Feature shape representing: [PM2.5, NO2, Temperature, Humidity, Traffic_Volume]
        node_features = 5
        
        # Input History: X_t
        x = torch.randn((self.num_nodes, node_features, self.sequence_length), dtype=torch.float)
        
        # Future Label: Y_t+1 (Predicting future PM2.5 at all nodes)
        y = torch.randn((self.num_nodes, 1), dtype=torch.float)
        
        # Package into a PyTorch Geometric Data object
        data = Data(x=x, edge_index=self.edge_index, edge_attr=self.edge_weight, y=y)
        
        # Attach physics metadata to the batch object for the specialized loss function
        data.metadata = {
            'prev_concentrations': x[:, 0, -1].unsqueeze(1), # PM2.5 at last known step t
            'dt': 1.0,
            'wind_u': x[:, 2, -1].unsqueeze(1), # using temperature/wind proxy
            'wind_v': x[:, 3, -1].unsqueeze(1),
            'diffusion_coeff': 0.1
        }
        
        return data

if __name__ == "__main__":
    dataset = SpatioTemporalDataset(num_nodes=50, sequence_length=12)
    print(f"Dataset initialization successful. Total sequences: {len(dataset)}")
    
    sample = dataset[0]
    print(f"Sample Graph Data object: {sample}")
    print(f"Sample Feature Shape (X): {sample.x.shape}")
    print(f"Sample Label Shape (Y): {sample.y.shape}")
