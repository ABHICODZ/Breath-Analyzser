#!/usr/bin/env python3
"""
Fast Training for v4 Model - Using Best Architecture Only
Trains only the wider_network architecture with new data
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
print("VayuDrishti v4 Model Training (Fast)")
print("="*80)

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n[1/5] Loading NEW dataset (2015-2025)...")

df_delhi = pd.read_csv('dataset_extracted/training_data_clean.csv')
print(f"  Total records: {len(df_delhi)}")

# ============================================================================
# PREPROCESS
# ============================================================================

print("\n[2/5] Preprocessing...")

df_delhi['Date'] = pd.to_datetime(df_delhi['Date'], errors='coerce')
df_delhi = df_delhi.dropna(subset=['Date'])
df_delhi = df_delhi.sort_values('Date').reset_index(drop=True)

# Temporal features (already in the dataset, but recalculate to be sure)
df_delhi['year'] = df_delhi['Date'].dt.year
df_delhi['month'] = df_delhi['Date'].dt.month
df_delhi['day'] = df_delhi['Date'].dt.day
df_delhi['day_of_week'] = df_delhi['Date'].dt.dayofweek
df_delhi['day_of_year'] = df_delhi['Date'].dt.dayofyear
df_delhi['is_weekend'] = (df_delhi['day_of_week'] >= 5).astype(int)

def get_season(month):
    if month in [12, 1, 2]:
        return 0
    elif month in [3, 4, 5]:
        return 1
    elif month in [6, 7, 8]:
        return 2
    else:
        return 3

df_delhi['season'] = df_delhi['month'].apply(get_season)

# Features
feature_cols = ['month', 'day_of_week', 'day_of_year', 'is_weekend', 'season']
pollutant_cols = ['NO', 'NO2', 'NOx', 'NH3', 'CO', 'SO2', 'O3']
for col in pollutant_cols:
    if col in df_delhi.columns:
        feature_cols.append(col)

target_cols = ['PM2.5', 'PM10']

df_clean = df_delhi.dropna(subset=['PM2.5', 'PM10'], how='all').copy()

for col in feature_cols:
    if col in df_clean.columns:
        df_clean[col] = df_clean[col].fillna(df_clean[col].median())
    else:
        df_clean[col] = 0

df_clean['PM2.5'] = df_clean['PM2.5'].ffill().bfill()
df_clean['PM10'] = df_clean['PM10'].ffill().bfill()
df_clean = df_clean[df_clean['PM2.5'] < 999]
df_clean = df_clean[df_clean['PM10'] < 999]

print(f"  Clean records: {len(df_clean)}")

# ============================================================================
# PREPARE DATA
# ============================================================================

print("\n[3/5] Preparing data...")

X = df_clean[feature_cols].values
y = df_clean[target_cols].values

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

# Save scaler
with open('vayu_scaler_v4.pkl', 'wb') as f:
    pickle.dump(scaler, f)
print(f"  Saved scaler")

# ============================================================================
# MODEL DEFINITION
# ============================================================================

class WiderAQIModel(nn.Module):
    """Wider network architecture (best from v3)"""
    
    def __init__(self, input_dim):
        super().__init__()
        
        self.shared = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
            
            nn.Linear(256, 256),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.Dropout(0.3),
        )
        
        # PM2.5 head
        self.pm25_head = nn.Sequential(
            nn.Linear(256, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        # PM10 head
        self.pm10_head = nn.Sequential(
            nn.Linear(256, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
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

# ============================================================================
# TRAINING
# ============================================================================

print("\n[4/5] Training model...")

train_dataset = AQIDataset(X_train_scaled, y_train)
test_dataset = AQIDataset(X_test_scaled, y_test)

train_loader = DataLoader(train_dataset, batch_size=32, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=32)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print(f"  Device: {device}")

model = WiderAQIModel(input_dim=X_train_scaled.shape[1]).to(device)

criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)

epochs = 150
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
    
    if (epoch + 1) % 30 == 0:
        print(f"  Epoch {epoch+1}/{epochs} - Train: {train_loss:.4f}, Test: {test_loss:.4f}")
    
    # Save best model
    if test_loss < best_loss:
        best_loss = test_loss
        torch.save(model.state_dict(), 'vayu_model_v4_best.pt')

print(f"\n  Training complete! Best test loss: {best_loss:.4f}")

# ============================================================================
# EVALUATE
# ============================================================================

print("\n[5/5] Evaluating model...")

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
print("FINAL RESULTS - v4 Model")
print("="*80)
print(f"\nDataset: {len(X)} samples (2015-2025)")
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
print("COMPARISON")
print("="*80)
print("\nv3 Model (2,007 samples):")
print("  PM2.5: 59.2% accuracy, MAE 23.03")
print("  PM10:  60.9% accuracy, MAE 43.78")

print(f"\nv4 Model ({len(X):,} samples):")
print(f"  PM2.5: {pm25_within_20.mean()*100:.1f}% accuracy, MAE {pm25_mae:.2f}")
print(f"  PM10:  {pm10_within_20.mean()*100:.1f}% accuracy, MAE {pm10_mae:.2f}")

improvement_pm25 = pm25_within_20.mean()*100 - 59.2
improvement_pm10 = pm10_within_20.mean()*100 - 60.9

print(f"\nImprovement:")
print(f"  PM2.5: {improvement_pm25:+.1f} percentage points")
print(f"  PM10:  {improvement_pm10:+.1f} percentage points")

print("\n" + "="*80)
print("FILES CREATED")
print("="*80)
print("  1. vayu_model_v4_best.pt - Trained model")
print("  2. vayu_scaler_v4.pkl - Feature scaler")
print("\nNext steps:")
print("  1. Test: python test_aqi_validation.py")
print("  2. Deploy to production")
print("="*80)
