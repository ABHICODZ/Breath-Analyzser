#!/usr/bin/env python3
"""
Simple Model Training Script for VayuDrishti
Uses existing datasets - no API calls needed
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
import pickle
import os
from datetime import datetime

print("="*80)
print("VayuDrishti Model Training")
print("="*80)

# ============================================================================
# STEP 1: Load and Prepare Data
# ============================================================================

print("\n[STEP 1/6] Loading datasets...")

# Load city_day.csv (main dataset)
df = pd.read_csv('dataset_extracted/city_day.csv')
print(f"  Loaded city_day.csv: {len(df)} records")

# Filter for Delhi only
df_delhi = df[df['City'] == 'Delhi'].copy()
print(f"  Filtered Delhi data: {len(df_delhi)} records")

# Load delhi_aqi.csv if exists
try:
    df_delhi_aqi = pd.read_csv('dataset_extracted/delhi_aqi.csv')
    print(f"  Loaded delhi_aqi.csv: {len(df_delhi_aqi)} records")
    # Combine datasets
    df_delhi = pd.concat([df_delhi, df_delhi_aqi], ignore_index=True)
    print(f"  Combined total: {len(df_delhi)} records")
except:
    print("  delhi_aqi.csv not found, using city_day.csv only")

# ============================================================================
# STEP 2: Data Preprocessing
# ============================================================================

print("\n[STEP 2/6] Preprocessing data...")

# Convert date to datetime
df_delhi['Date'] = pd.to_datetime(df_delhi['Date'], errors='coerce')

# Remove rows with no date
df_delhi = df_delhi.dropna(subset=['Date'])

# Sort by date
df_delhi = df_delhi.sort_values('Date').reset_index(drop=True)

# Add temporal features
df_delhi['year'] = df_delhi['Date'].dt.year
df_delhi['month'] = df_delhi['Date'].dt.month
df_delhi['day'] = df_delhi['Date'].dt.day
df_delhi['day_of_week'] = df_delhi['Date'].dt.dayofweek
df_delhi['day_of_year'] = df_delhi['Date'].dt.dayofyear
df_delhi['is_weekend'] = (df_delhi['day_of_week'] >= 5).astype(int)

# Add season
def get_season(month):
    if month in [12, 1, 2]:
        return 0  # winter
    elif month in [3, 4, 5]:
        return 1  # spring
    elif month in [6, 7, 8]:
        return 2  # summer
    else:
        return 3  # autumn

df_delhi['season'] = df_delhi['month'].apply(get_season)

print(f"  Date range: {df_delhi['Date'].min()} to {df_delhi['Date'].max()}")
print(f"  Added temporal features")

# ============================================================================
# STEP 3: Feature Engineering
# ============================================================================

print("\n[STEP 3/6] Engineering features...")

# Select features
feature_cols = ['month', 'day_of_week', 'day_of_year', 'is_weekend', 'season']

# Add pollutant features if available
pollutant_cols = ['NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3']
for col in pollutant_cols:
    if col in df_delhi.columns:
        feature_cols.append(col)

# Target variables
target_cols = ['PM2.5', 'PM10']

# Keep only rows with PM2.5 or PM10
df_clean = df_delhi.dropna(subset=['PM2.5', 'PM10'], how='all').copy()

print(f"  Records with PM data: {len(df_clean)}")

# Fill missing values
for col in feature_cols:
    if col in df_clean.columns:
        df_clean[col] = df_clean[col].fillna(df_clean[col].median())
    else:
        df_clean[col] = 0

# Fill missing PM values with forward fill
df_clean['PM2.5'] = df_clean['PM2.5'].ffill().bfill()
df_clean['PM10'] = df_clean['PM10'].ffill().bfill()

# Remove extreme outliers
df_clean = df_clean[df_clean['PM2.5'] < 999]
df_clean = df_clean[df_clean['PM10'] < 999]

print(f"  Final dataset: {len(df_clean)} records")
print(f"  Features: {len(feature_cols)}")
print(f"  Feature list: {feature_cols}")

# ============================================================================
# STEP 4: Prepare Training Data
# ============================================================================

print("\n[STEP 4/6] Preparing training data...")

# Extract features and targets
X = df_clean[feature_cols].values
y = df_clean[target_cols].values

# Remove any remaining NaN
mask = ~(np.isnan(X).any(axis=1) | np.isnan(y).any(axis=1))
X = X[mask]
y = y[mask]

print(f"  Training samples: {len(X)}")
print(f"  Feature shape: {X.shape}")
print(f"  Target shape: {y.shape}")

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

print(f"  Train set: {len(X_train)} samples")
print(f"  Test set: {len(X_test)} samples")

# Scale features
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

# Save scaler
with open('vayu_scaler_v2.pkl', 'wb') as f:
    pickle.dump(scaler, f)
print(f"  ✓ Saved scaler to vayu_scaler_v2.pkl")

# ============================================================================
# STEP 5: Define and Train Model
# ============================================================================

print("\n[STEP 5/6] Training model...")

class ImprovedAQIModel(nn.Module):
    """Dual-output model for PM2.5 and PM10 prediction"""
    
    def __init__(self, input_dim):
        super().__init__()
        
        self.shared = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(128, 64),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.Dropout(0.2),
        )
        
        # PM2.5 head
        self.pm25_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        # PM10 head
        self.pm10_head = nn.Sequential(
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
    
    def forward(self, x):
        shared_features = self.shared(x)
        pm25 = self.pm25_head(shared_features)
        pm10 = self.pm10_head(shared_features)
        return pm25, pm10

# Create dataset
class AQIDataset(Dataset):
    def __init__(self, X, y):
        self.X = torch.FloatTensor(X)
        self.y = torch.FloatTensor(y)
    
    def __len__(self):
        return len(self.X)
    
    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]

# Create data loaders
train_dataset = AQIDataset(X_train_scaled, y_train)
test_dataset = AQIDataset(X_test_scaled, y_test)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32)

# Initialize model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"  Using device: {device}")

model = ImprovedAQIModel(input_dim=X_train_scaled.shape[1]).to(device)

# Loss and optimizer
criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

# Training loop
epochs = 50
best_loss = float('inf')

print(f"  Training for {epochs} epochs...")
print()

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
    
    if (epoch + 1) % 10 == 0:
        print(f"  Epoch {epoch+1}/{epochs} - Train Loss: {train_loss:.4f}, Test Loss: {test_loss:.4f}")
    
    # Save best model
    if test_loss < best_loss:
        best_loss = test_loss
        torch.save(model.state_dict(), 'vayu_model_v2_best.pt')

print(f"\n  ✓ Training complete!")
print(f"  ✓ Best test loss: {best_loss:.4f}")
print(f"  ✓ Saved model to vayu_model_v2_best.pt")

# ============================================================================
# STEP 6: Evaluate Model
# ============================================================================

print("\n[STEP 6/6] Evaluating model...")

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

# Calculate metrics
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

pm25_mae = mean_absolute_error(all_pm25_true, all_pm25_pred)
pm25_rmse = np.sqrt(mean_squared_error(all_pm25_true, all_pm25_pred))
pm25_r2 = r2_score(all_pm25_true, all_pm25_pred)

pm10_mae = mean_absolute_error(all_pm10_true, all_pm10_pred)
pm10_rmse = np.sqrt(mean_squared_error(all_pm10_true, all_pm10_pred))
pm10_r2 = r2_score(all_pm10_true, all_pm10_pred)

print("\n" + "="*80)
print("FINAL RESULTS")
print("="*80)
print("\nPM2.5 Metrics:")
print(f"  MAE:  {pm25_mae:.2f} µg/m³")
print(f"  RMSE: {pm25_rmse:.2f} µg/m³")
print(f"  R²:   {pm25_r2:.4f}")

print("\nPM10 Metrics:")
print(f"  MAE:  {pm10_mae:.2f} µg/m³")
print(f"  RMSE: {pm10_rmse:.2f} µg/m³")
print(f"  R²:   {pm10_r2:.4f}")

# Calculate accuracy (within 20% of actual)
pm25_within_20 = np.abs(all_pm25_pred - all_pm25_true) / (all_pm25_true + 1) < 0.2
pm10_within_20 = np.abs(all_pm10_pred - all_pm10_true) / (all_pm10_true + 1) < 0.2

print(f"\nAccuracy (within 20%):")
print(f"  PM2.5: {pm25_within_20.mean()*100:.1f}%")
print(f"  PM10:  {pm10_within_20.mean()*100:.1f}%")

print("\n" + "="*80)
print("✓ TRAINING COMPLETE!")
print("="*80)
print("\nFiles created:")
print("  1. vayu_model_v2_best.pt - Trained model")
print("  2. vayu_scaler_v2.pkl - Feature scaler")
print("\nNext steps:")
print("  1. Copy these files to app/services/")
print("  2. Update ml_engine.py to use new model")
print("  3. Test with: python test_aqi_validation.py")
print("="*80)
