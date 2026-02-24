import torch
from torch_geometric.data import Data, Dataset
import pandas as pd
import numpy as np

class CityPollutionGraphDataset(Dataset):
    """
    Constructs a PyTorch Geometric Dataset from the OSMnx road graph
    and the TimescaleDB historical air quality measurements.
    """
    def __init__(self, root, transform=None, pre_transform=None):
        super(CityPollutionGraphDataset, self).__init__(root, transform, pre_transform)
        # self.graph_data = ... # Will hold the OSMnx NetworkX graph
        # self.timeseries_data = ... # Will hold the TimescaleDB history

    @property
    def raw_file_names(self):
        return []

    @property
    def processed_file_names(self):
        return ['data.pt']

    def download(self):
        pass

    def process(self):
        pass
        
    def len(self):
        # Return number of time-windows available for training
        return 0

    def get(self, idx):
        # Construct and return a single PyTorch Geometric Data object for time t
        return Data()
