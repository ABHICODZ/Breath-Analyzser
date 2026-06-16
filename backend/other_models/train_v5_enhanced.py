#!/usr/bin/env python3
"""
Train v5 Model with Weather and Spatial Features
Enhanced model with 29 features (up from 12)
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
import pickle
import os
from datetime import datetime

print("="*80)
print("VayuDrishti v5 Model Training - Enhanced Features")
print("="*80)

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n[1/6] Loading enhanced dataset...")

df = pd.read_csv('dataset_extracted/training_data_v5_enhanced.csv')
df['Date'] = pd.to_datetime(df['Date'], format='mixed')

print(f"  Total records: {len(df)}")
print(f"  Total columns: {len(df.columns)}")

# ============================================================================
# PREPARE FEATURES
# ============================================================================

print("\n[2/6] Preparing features...")

# Encode categorical zone feature
le = LabelEncoder()
df['zone_encoded'] = le.fit_transform(df['zone'])

# Select features for training
feature_cols = [
    # Temporal features (5)
    'month', 'day_of_week', 'day_of_year', 'is_weekend', 'season',
    
    # Pollutant features (7)
    'NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3',
    
    # Spatial features (5)
    'zone_encoded', 'zone_lat', 'zone_lon', 
    'industrial_density', 'traffic_density',
    
    # Weather features (5)
    'temperature', 'humidity', 'wind_speed', 
    'pressure', 'precipitation',
    
    # Derived features (7)
    'temp_humidity_index', 'wind_chill',
    'pollution_accumulation', 'seasonal_pollution_factor',
    'traffic_weather_interaction', 'industrial_weather_interaction',
    'rain_effect'
]

target_cols = ['PM2.5', 'PM10']

print(f"  Features selected: {len(feature_cols)}")
print(f"    - Temporal: 5")
print(f"    - Pollutants: 7")
print(f"    - Spatial: 5")
print(f"    - Weather: 5")
print(f"    - Derived: 7")

# Handle missing values
for col in feature_cols:
    if col in df.columns:
        df[col] = df[col].fillna(df[col].median())
    else:
        print(f"  Warning: {col} not found, setting to 0")
        df[col] = 0

# Clean targets
df = df.dropna(subset=target_cols)
df = df[df['PM2.5'] < 999]
df = df[df['PM10'] < 999]

print(f"  Clean records: {len(df)}")

# ============================================================================
# PREPARE DATA
# ============================================================================

print("\n[3/6] Preparing training data...")

X = df[feature_cols].values
y = df[target_cols].values

# Remove any remaining NaN
mask = ~(np.isnan(X).any(axis=1) | np.isnan(y).any(axis=1))
X = X[mask]
y = y[mask]

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

print(f"  Train: {len(X_train)}, Test: {len(X_test)}")
print(f"  Feature shape: {X_train_scaled.shape}")

# Save scaler
with open('vayu_scaler_v5.pkl', 'wb') as f:
    pickle.dump(scaler, f)

# Save label encoder
with open('vayu_label_encoder_v5.pkl', 'wb') as f:
    pickle.dump(le, f)

print(f"  Saved scaler and label encoder")

# ============================================================================
# MODEL DEFINITION
# ============================================================================

print("\n[4/6] Defining model architecture...")

class EnhancedAQIModel(nn.Module):
    """Enhanced model with more features and capacity"""
    
    def __init__(self, input_dim):
        super().__init__()
        
        # Larger network to handle more features
        self.shared = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(512, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.2),
        )
        
        # PM2.5 head
        self.pm25_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1)
        )
        
        # PM10 head
        self.pm10_head = nn.Sequential(
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, 1)
        )
    
    def forward(self, x):
        shared_features = self.shared(x)
        pm25 = self.pm25_head(shared_features)
        pm10 = self.pm10_head(shared_features)
        return pm25, pm10

class AQIDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

print(f"  Model architecture: [512, 256, 128] + dual heads")
print(f"  Input features: {X_train_scaled.shape[1]}")

# ============================================================================
# TRAINING
# ============================================================================

print("\n[5/6] Training model...")

train_dataset = AQIDataset(X_train_scaled, y_train)
test_dataset = AQIDataset(X_test_scaled, y_test)

train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=64)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"  Device: {device}")

model = EnhancedAQIModel(input_dim=X_train_scaled.shape[1]).to(device)

# Count parameters
total_params = sum(p.numel() for p in model.parameters())
print(f"  Total parameters: {total_params:,}")

criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)

epochs = 200
best_loss = float('inf')

print(f"  Training for {epochs} epochs...")

for epoch in range(epochs):
    # Train
    model.train()
    train_loss = 0
    for X_batch, y_batch in train_loader:
        X_batch, y_batch = X_batch.to(device), y_batch.to(device)
        
        optimizer.zero_grad()
        pm25_pred, pm10_pred = model(X_batch)
        
        loss_pm25 = criterion(pm25_pred.squeeze(), y_batch[:, 0])
        loss_pm10 = criterion(pm10_pred.squeeze(), y_batch[:, 1])
        loss = loss_pm25 + loss_pm10
        
        loss.backward()
        optimizer.step()
        
        train_loss += loss.item()
    
    # Validate
    model.eval()
    test_loss = 0
    with torch.no_grad():
        for X_batch, y_batch in test_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            pm25_pred, pm10_pred = model(X_batch)
            
            loss_pm25 = criterion(pm25_pred.squeeze(), y_batch[:, 0])
            loss_pm10 = criterion(pm10_pred.squeeze(), y_batch[:, 1])
            loss = loss_pm25 + loss_pm10
            
            test_loss += loss.item()
    
    train_loss /= len(train_loader)
    test_loss /= len(test_loader)
    
    scheduler.step(test_loss)
    
    if (epoch + 1) % 40 == 0:
        print(f"  Epoch {epoch+1}/{epochs} - Train: {train_loss:.4f}, Test: {test_loss:.4f}")
    
    # Save best model
    if test_loss < best_loss:
        best_loss = test_loss
        torch.save(model.state_dict(), 'vayu_model_v5_best.pt')

print(f"\n  Training complete! Best test loss: {best_loss:.4f}")

# ============================================================================
# EVALUATE
# ============================================================================

print("\n[6/6] Evaluating model...")

model.eval()
all_pm25_pred = []
all_pm10_pred = []
all_pm25_true = []
all_pm10_true = []

with torch.no_grad():
    for X_batch, y_batch in test_loader:
        X_batch = X_batch.to(device)
        pm25_pred, pm10_pred = model(X_batch)
        
        all_pm25_pred.extend(pm25_pred.cpu().numpy().flatten())
        all_pm10_pred.extend(pm10_pred.cpu().numpy().flatten())
        all_pm25_true.extend(y_batch[:, 0].numpy())
        all_pm10_true.extend(y_batch[:, 1].numpy())

all_pm25_pred = np.array(all_pm25_pred)
all_pm10_pred = np.array(all_pm10_pred)
all_pm25_true = np.array(all_pm25_true)
all_pm10_true = np.array(all_pm10_true)

from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

pm25_mae = mean_absolute_error(all_pm25_true, all_pm25_pred)
pm25_rmse = np.sqrt(mean_squared_error(all_pm25_true, all_pm25_pred))
pm25_r2 = r2_score(all_pm25_true, all_pm25_pred)

pm10_mae = mean_absolute_error(all_pm10_true, all_pm10_pred)
pm10_rmse = np.sqrt(mean_squared_error(all_pm10_true, all_pm10_pred))
pm10_r2 = r2_score(all_pm10_true, all_pm10_pred)

pm25_within_20 = np.abs(all_pm25_pred - all_pm25_true) / (all_pm25_true + 1) < 0.2
pm10_within_20 = np.abs(all_pm10_pred - all_pm10_true) / (all_pm10_true + 1) < 0.2

print("\n" + "="*80)
print("FINAL RESULTS - v5 Model (Enhanced)")
print("="*80)

print(f"\nDataset: {len(X):,} samples (2015-2025)")
print(f"Features: {len(feature_cols)} (up from 12 in v4)")
print(f"Train/Test: {len(X_train)}/{len(X_test)}")

print("\nPM2.5 Metrics:")
print(f"  MAE:  {pm25_mae:.2f} µg/m³")
print(f"  RMSE: {pm25_rmse:.2f} µg/m³")
print(f"  R²:   {pm25_r2:.4f}")
print(f"  Accuracy (within 20%): {pm25_within_20.mean()*100:.1f}%")

print("\nPM10 Metrics:")
print(f"  MAE:  {pm10_mae:.2f} µg/m³")
print(f"  RMSE: {pm10_rmse:.2f} µg/m³")
print(f"  R²:   {pm10_r2:.4f}")
print(f"  Accuracy (within 20%): {pm10_within_20.mean()*100:.1f}%")

print("\n" + "="*80)
print("MODEL EVOLUTION")
print("="*80)

print("\nv3 Model (2,007 samples, 12 features):")
print("  PM2.5: 59.2% accuracy, MAE 23.03")
print("  PM10:  60.9% accuracy, MAE 43.78")

print("\nv4 Model (12,159 samples, 12 features):")
print("  PM2.5: 66.8% accuracy, MAE 19.60")
print("  PM10:  64.3% accuracy, MAE 37.92")

print(f"\nv5 Model ({len(X):,} samples, {len(feature_cols)} features):")
print(f"  PM2.5: {pm25_within_20.mean()*100:.1f}% accuracy, MAE {pm25_mae:.2f}")
print(f"  PM10:  {pm10_within_20.mean()*100:.1f}% accuracy, MAE {pm10_mae:.2f}")

improvement_pm25_v4 = pm25_within_20.mean()*100 - 66.8
improvement_pm10_v4 = pm10_within_20.mean()*100 - 64.3

improvement_pm25_v3 = pm25_within_20.mean()*100 - 59.2
improvement_pm10_v3 = pm10_within_20.mean()*100 - 60.9

print(f"\nImprovement over v4:")
print(f"  PM2.5: {improvement_pm25_v4:+.1f} percentage points")
print(f"  PM10:  {improvement_pm10_v4:+.1f} percentage points")

print(f"\nTotal improvement over v3:")
print(f"  PM2.5: {improvement_pm25_v3:+.1f} percentage points")
print(f"  PM10:  {improvement_pm10_v3:+.1f} percentage points")

# Check if we reached 75% target
if pm25_within_20.mean()*100 >= 75:
    print("\n🎉 TARGET ACHIEVED! PM2.5 accuracy >= 75%")
if pm10_within_20.mean()*100 >= 75:
    print("🎉 TARGET ACHIEVED! PM10 accuracy >= 75%")

print("\n" + "="*80)
print("FILES CREATED")
print("="*80)
print("  1. vayu_model_v5_best.pt - Enhanced model")
print("  2. vayu_scaler_v5.pkl - Feature scaler")
print("  3. vayu_label_encoder_v5.pkl - Zone encoder")
print(f"\nModel size: {total_params * 4 / 1024:.2f} KB")
print("\nNext steps:")
print("  1. Test: python test_aqi_validation.py")
print("  2. Deploy to production")
print("="*80)
