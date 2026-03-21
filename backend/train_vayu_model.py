import torch
import torch.nn as nn
import torch.optim as optim
import numpy as np
import time
import os

print("="*60)
print(" VAYU DRISHTI - VIRTUAL SENSOR NETWORK TRAINING ENGINE")
print("="*60)

# Check for RTX 3050
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"[*] Detected Compute Device: {device.type.upper()}")
if device.type == 'cuda':
    print(f"[*] Native GPU Active: {torch.cuda.get_device_name(0)}")
    print(f"[*] VRAM Allocated: {round(torch.cuda.get_device_properties(0).total_memory / 1024**3, 1)} GB")
else:
    print("[!] CUDA not detected. Falling back to CPU. (Run 'pip install torch --index-url https://download.pytorch.org/whl/cu121' to enable RTX)")

# 1. GENERATE SYNTHETIC HISTORICAL DATA (Since it's a Hackathon, we simulate 3 months of past data)
print("\n[*] Synthesizing 50,000 historical spatial data points across Delhi's 251 wards...")
X_data = [] # Features: [Anchor_1_AQI, Anchor_2_AQI, Wind_Dir_X, Wind_Dir_Y, Ward_Lat, Ward_Lon]
y_data = [] # Target: local AQI for the specific Ward

for _ in range(50000):
    # Random weather conditions
    wind_x, wind_y = np.random.uniform(-1, 1, 2)
    # The 11 anchors randomly fluctuate between 50 and 450 AQI
    anchor_base = np.random.uniform(50, 450)
    
    # Target Ward coordinates (rough bounding box of Delhi)
    w_lat = np.random.uniform(28.4, 28.8)
    w_lon = np.random.uniform(76.9, 77.3)
    
    # We formulate the "true" target based on distance to the hypothetical center of the city (where pollution is worse)
    dist_to_center = np.sqrt((w_lat - 28.61)**2 + (w_lon - 77.20)**2)
    volatility = np.random.normal(0, 15) # Noise
    
    target_aqi = anchor_base + (wind_x * 20) - (dist_to_center * 150) + volatility
    target_aqi = max(10, min(500, target_aqi)) # Clamp between 10 and 500
    
    X_data.append([anchor_base, anchor_base * 0.9, wind_x, wind_y, w_lat, w_lon])
    y_data.append([target_aqi])

X_tensor = torch.FloatTensor(X_data).to(device)
y_tensor = torch.FloatTensor(y_data).to(device)

# 2. DEFINE THE TEMPORAL NEURAL NETWORK
class TemporalSpatialNet(nn.Module):
    def __init__(self):
        super(TemporalSpatialNet, self).__init__()
        # Architecture designed specifically for tabular spatial correlations
        self.network = nn.Sequential(
            nn.Linear(6, 64),
            nn.ReLU(),
            nn.Linear(64, 128),
            nn.ReLU(),
            nn.Dropout(0.2), # Prevent overfitting
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1) # Single output: PM2.5/AQI
        )
        
    def forward(self, x):
        return self.network(x)

model = TemporalSpatialNet().to(device)
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.005)

# 3. TRAIN ON LOCAL RTX 3050
print("\n[*] Initiating Neural Training Phase (100 Epochs)...")
start_time = time.time()

for epoch in range(1, 101):
    optimizer.zero_grad()
    predictions = model(X_tensor)
    loss = criterion(predictions, y_tensor)
    loss.backward()
    optimizer.step()
    
    if epoch % 10 == 0:
        print(f"    Epoch {epoch:03d}/100 | Target Loss (MSE): {loss.item():.4f}")

end_time = time.time()
print(f"\n[*] Training Complete in {round(end_time - start_time, 2)} seconds.")

# 4. EXPORT WEIGHTS FOR THE FASTAPI SERVER
os.makedirs('app/services', exist_ok=True)
export_path = 'app/services/vayu_spatial.pt'
torch.save(model.state_dict(), export_path)
print(f"[*] AI Tensor Weights successfully exported to: {export_path}")
print("[*] The FASTAPI Background ML Loop will seamlessly stream inferences from this binary now!")
print("="*60)
