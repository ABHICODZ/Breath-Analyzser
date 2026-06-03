import torch
import torch.nn as nn

class PhysicsInformedLoss(nn.Module):
    """
    Computes a hybrid loss function combining standard Data Loss (MSE) 
    with a Physics-Informed regularization penalty based on a simplified 
    Advection-Diffusion-Reaction (ADR) equation for fluid dynamics.
    
    Total Loss = MSE_Loss + lambda_phy * Physics_Loss
    """
    def __init__(self, lambda_phy: float = 0.1):
        super(PhysicsInformedLoss, self).__init__()
        self.mse = nn.MSELoss()
        self.lambda_phy = lambda_phy

    def extract_spatial_gradients(self, predictions, coordinates):
        """
        Computes the spatial gradients (dC/dx, dC/dy) of the concentration.
        In a real graph network where coordinates are irregular, this requires
        computing differences along the edges connecting nodes. For simplicity
        in this proof-of-concept, we represent it abstractly.
        """
        # Placeholder for spatial differentiation logic along graph edges.
        # This function would take the predicted concentration at each node
        # and subtract coordinates defined by `edge_index` to form gradients.
        
        # Returning dummy zero-tensors for shape consistency
        batch_size = predictions.shape[0] if len(predictions.shape) > 1 else 1
        dC_dx = torch.zeros_like(predictions)
        dC_dy = torch.zeros_like(predictions)
        
        # Second derivatives (Diffusion)
        d2C_dx2 = torch.zeros_like(predictions)
        d2C_dy2 = torch.zeros_like(predictions)
        
        return dC_dx, dC_dy, d2C_dx2, d2C_dy2

    def calculate_adr_residual(self, predictions, prev_concentrations, dt, wind_x, wind_y, diffusion_coeff):
        """
        Calculates the residual error of the ADR equation:
        dC/dt + u(dC/dx) + v(dC/dy) - D(d2C/dx2 + d2C/dy2) = 0
        """
        # Temporal Derivative: dC/dt ~ (C_t - C_t-1) / dt
        dC_dt = (predictions - prev_concentrations) / dt
        
        # Spatial Gradients
        dC_dx, dC_dy, d2C_dx2, d2C_dy2 = self.extract_spatial_gradients(predictions, None)
        
        # Advection Term: u(dC/dx) + v(dC/dy)
        advection = wind_x * dC_dx + wind_y * dC_dy
        
        # Diffusion Term: D * Laplace(C)
        diffusion = diffusion_coeff * (d2C_dx2 + d2C_dy2)
        
        # The equation states that dC_dt + advection - diffusion = Source/Sink (ignored here for simplicity)
        # Therefore, the residual is:
        residual = dC_dt + advection - diffusion
        
        return residual

    def forward(self, predictions, targets, metadata=None):
        """
        Forward pass for the custom loss function.
        
        Args:
            predictions: Predicted pollutant concentration. (N, 1)
            targets: True ground-bound concentration. (N, 1)
            metadata: Dictionary containing physics constraints like wind vectors (u, v)
                      and previous time-step concentration.
        """
        # 1. Base Data Loss
        data_loss = self.mse(predictions, targets)
        
        # 2. Physics-Informed Residual Loss
        physics_loss = 0.0
        
        if metadata is not None:
            # Unpack environmental physical variables required for the ADR equation
            prev_concentrations = metadata.get('prev_concentrations', torch.zeros_like(predictions))
            dt = metadata.get('dt', 1.0) # Time step delta
            wind_x = metadata.get('wind_u', torch.zeros_like(predictions))
            wind_y = metadata.get('wind_v', torch.zeros_like(predictions))
            diffusion_coeff = metadata.get('diffusion_coeff', 0.01)
            
            # Compute Residual
            residual = self.calculate_adr_residual(
                predictions, prev_concentrations, dt, wind_x, wind_y, diffusion_coeff
            )
            
            # Physics loss is the Mean Squared Error of the residual (targeting 0)
            physics_loss = torch.mean(residual ** 2)
            
        # 3. Total Compound Loss
        total_loss = data_loss + (self.lambda_phy * physics_loss)
        
        return total_loss

if __name__ == "__main__":
    # Test Loss Function
    criterion = PhysicsInformedLoss(lambda_phy=0.5)
    
    preds = torch.tensor([[10.0], [12.0], [15.0]], requires_grad=True)
    targets = torch.tensor([[10.5], [11.8], [14.0]])
    
    # Include dummy physics parameters mimicking real wind conditions
    metadata = {
        'prev_concentrations': torch.tensor([[9.0], [11.0], [14.0]]),
        'dt': 1.0,
        'wind_u': torch.tensor([[0.5], [-0.2], [1.1]]),
        'wind_v': torch.tensor([[0.1], [0.8], [-0.5]]),
        'diffusion_coeff': 0.05
    }
    
    loss = criterion(preds, targets, metadata)
    print(f"Computed Hybrid Loss: {loss.item():.4f}")
    
    # Verify autograd graph doesn't break
    loss.backward()
    print(f"Gradient at predictions: \n{preds.grad}")
