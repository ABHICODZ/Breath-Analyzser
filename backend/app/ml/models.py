import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv

class TGCNCell(nn.Module):
    """
    Temporal Graph Convolutional Network Cell.
    Combines spatial GCN logic with a temporal GRU mechanism.
    """
    def __init__(self, in_channels: int, out_channels: int):
        super(TGCNCell, self).__init__()
        # GRU Gates (Update and Reset) combining spatial and temporal features
        self.conv_z = GCNConv(in_channels + out_channels, out_channels)
        self.conv_r = GCNConv(in_channels + out_channels, out_channels)
        
        # Candidate hidden state convolution
        self.conv_h = GCNConv(in_channels + out_channels, out_channels)

    def forward(self, x, edge_index, edge_weight, hidden_state):
        """
        x: (Num_Nodes, In_Channels)
        edge_index: (2, Num_Edges)
        hidden_state: (Num_Nodes, Out_Channels)
        """
        # Concatenate current input and previous hidden state
        concat_x_h = torch.cat([x, hidden_state], dim=1)
        
        # Calculate Update (z) and Reset (r) gates via Graph Convolution
        z = torch.sigmoid(self.conv_z(concat_x_h, edge_index, edge_weight))
        r = torch.sigmoid(self.conv_r(concat_x_h, edge_index, edge_weight))
        
        # Calculate candidate hidden state
        # Reset gate controls how much of past hidden state to use
        concat_x_rh = torch.cat([x, r * hidden_state], dim=1)
        h_candidate = torch.tanh(self.conv_h(concat_x_rh, edge_index, edge_weight))
        
        # Final hidden state for this time step: interpolation governed by update gate
        h_new = z * hidden_state + (1 - z) * h_candidate
        
        return h_new

class AttentionLayer(nn.Module):
    """
    Temporal Attention mechanism to weigh the importance of different time steps
    in a recurrent sequence.
    """
    def __init__(self, hidden_size: int):
        super(AttentionLayer, self).__init__()
        self.attention_weights = nn.Parameter(torch.Tensor(hidden_size, hidden_size))
        self.attention_bias = nn.Parameter(torch.Tensor(hidden_size, 1))
        self.context_vector = nn.Parameter(torch.Tensor(hidden_size, 1))
        
        # Initialize parameters
        nn.init.xavier_uniform_(self.attention_weights)
        nn.init.zeros_(self.attention_bias)
        nn.init.xavier_uniform_(self.context_vector)

    def forward(self, hidden_states):
        """
        hidden_states: (Num_Nodes, Hidden_Size, Sequence_Length)
        """
        # Transform states
        # Shape manipulation to apply linear transform: (N, H, S) -> (N, S, H)
        hs_transposed = hidden_states.permute(0, 2, 1)
        
        # Compute scoring function
        # (N, S, H) @ (H, H) -> (N, S, H)
        score = torch.matmul(hs_transposed, self.attention_weights) 
        # Add bias and non-linearity
        score = torch.tanh(score + self.attention_bias.squeeze())
        
        # Compute alignment scores against the learned context vector
        # (N, S, H) @ (H, 1) -> (N, S, 1)
        alignment = torch.matmul(score, self.context_vector).squeeze(-1)
        
        # Softmax over the Sequence_Length dimension
        attention_weights = F.softmax(alignment, dim=1)
        
        # Apply attention weights to the original sequence
        # (N, S) * (N, H, S)... wait, we need to broadcast carefully.
        # attention_weights is (N, S), hidden_states is (N, H, S)
        attention_weights = attention_weights.unsqueeze(1) # (N, 1, S)
        
        # Weighted sum: (N, 1, S) * (N, H, S) -> sum over S -> (N, H)
        context = torch.sum(attention_weights * hidden_states, dim=2)
        
        return context

class A3TGCN(nn.Module):
    """
    Attention Temporal Graph Convolutional Network.
    Used to predict multivariate time-series on a spatial graph.
    """
    def __init__(self, node_features: int, hidden_dim: int, output_dim: int = 1):
        super(A3TGCN, self).__init__()
        self.hidden_dim = hidden_dim
        
        # Spatial-Temporal Cell
        self.tgcn_cell = TGCNCell(in_channels=node_features, out_channels=hidden_dim)
        
        # Temporal Attention Layer
        self.attention_layer = AttentionLayer(hidden_size=hidden_dim)
        
        # Final prediction fully-connected layer
        self.fc = nn.Linear(hidden_dim, output_dim)

    def forward(self, x, edge_index, edge_weight):
        """
        x: (Num_Nodes, Node_Features, Sequence_Length)
        edge_index: (2, Num_Edges)
        edge_weight: (Num_Edges,)
        """
        num_nodes, _, seq_len = x.shape
        device = x.device
        
        # Initialize the hidden state to zeros
        h = torch.zeros(num_nodes, self.hidden_dim).to(device)
        
        # Store hidden states across time steps
        hidden_states = []
        
        # Forward pass through time
        for t in range(seq_len):
            x_t = x[:, :, t] # Get node features at time step t
            h = self.tgcn_cell(x_t, edge_index, edge_weight, h)
            hidden_states.append(h)
            
        # Stack hidden states: (Num_Nodes, Hidden_Dim, Sequence_Length)
        hidden_states = torch.stack(hidden_states, dim=2)
        
        # Apply Attention Mechanism over the sequence
        context = self.attention_layer(hidden_states)
        
        # Make final prediction (e.g., predict next hour PM2.5)
        out = self.fc(context)
        
        return out

if __name__ == "__main__":
    # Smoke test the model dimensions
    num_nodes = 50
    node_features = 5
    seq_len = 12
    hidden_dim = 64
    num_edges = 200
    
    # Dummy Data
    x = torch.randn((num_nodes, node_features, seq_len))
    
    # 2 rows for source, target nodes
    edge_index = torch.randint(0, num_nodes, (2, num_edges)) 
    edge_weight = torch.rand((num_edges,))

    model = A3TGCN(node_features=node_features, hidden_dim=hidden_dim, output_dim=1)
    
    predictions = model(x, edge_index, edge_weight)
    print(f"Prediction output shape: {predictions.shape} - Expected: ({num_nodes}, 1)")
