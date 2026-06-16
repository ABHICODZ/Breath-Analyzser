#!/usr/bin/env python3
"""
Advanced Model Training with Hyperparameter Experimentation
Tries multiple architectures, learning rates, and batch sizes
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
import json

print("="*80)
print("VayuDrishti Advanced Training - Hyperparameter Experimentation")
print("="*80)

# ============================================================================
# CONFIGURATION
# ============================================================================

EXPERIMENTS = [
    {
        'name': 'baseline',
        'hidden_layers': [128, 64],
        'dropout': 0.3,
        'lr': 0.001,
        'batch_size': 32,
        'epochs': 100
    },
    {
        'name': 'deeper_network',
        'hidden_layers': [256, 128, 64, 32],
        'dropout': 0.3,
        'lr': 0.001,
        'batch_size': 32,
        'epochs': 100
    },
    {
        'name': 'wider_network',
        'hidden_layers': [256, 256],
        'dropout': 0.3,
        'lr': 0.001,
        'batch_size': 32,
        'epochs': 100
    },
    {
        'name': 'high_dropout',
        'hidden_layers': [128, 64],
        'dropout': 0.5,
        'lr': 0.001,
        'batch_size': 32,
        'epochs': 100
    },
    {
        'name': 'low_lr',
        'hidden_layers': [128, 64],
        'dropout': 0.3,
        'lr': 0.0001,
        'batch_size': 32,
        'epochs': 100
    },
    {
        'name': 'high_lr',
        'hidden_layers': [128, 64],
        'dropout': 0.3,
        'lr': 0.005,
        'batch_size': 32,
        'epochs': 100
    },
    {
        'name': 'large_batch',
        'hidden_layers': [128, 64],
        'dropout': 0.3,
        'lr': 0.001,
        'batch_size': 128,
        'epochs': 100
    },
    {
        'name': 'small_batch',
        'hidden_layers': [128, 64],
        'dropout': 0.3,
        'lr': 0.001,
        'batch_size': 16,
        'epochs': 100
    },
]

# ============================================================================
# LOAD DATA
# ============================================================================

print("\n[STEP 1] Loading datasets...")

# Try to load the new combined dataset first
if os.path.exists('dataset_extracted/training_data_clean.csv'):
    df_delhi = pd.read_csv('dataset_extracted/training_data_clean.csv')
    print(f"  Loaded NEW combined dataset (2015-2025)")
else:
    # Fallback to old datasets
    df = pd.read_csv('dataset_extracted/city_day.csv')
    df_delhi = df[df['City'] == 'Delhi'].copy()
    
    try:
        df_delhi_aqi = pd.read_csv('dataset_extracted/delhi_aqi.csv')
        df_delhi = pd.concat([df_delhi, df_delhi_aqi], ignore_index=True)
    except:
        pass
    print(f"  Loaded old datasets")

print(f"  Total records: {len(df_delhi)}")

# ============================================================================
# PREPROCESS
# ============================================================================

print("\n[STEP 2] Preprocessing...")

df_delhi['Date'] = pd.to_datetime(df_delhi['Date'], errors='coerce')
df_delhi = df_delhi.dropna(subset=['Date'])
df_delhi = df_delhi.sort_values('Date').reset_index(drop=True)

# Temporal features
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

print("\n[STEP 3] Preparing data...")

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

# ============================================================================
# MODEL DEFINITION
# ============================================================================

class FlexibleAQIModel(nn.Module):
    """Flexible architecture for experimentation"""
    
    def __init__(self, input_dim, hidden_layers, dropout):
        super().__init__()
        
        layers = []
        prev_dim = input_dim
        
        for hidden_dim in hidden_layers:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(dropout)
            ])
            prev_dim = hidden_dim
        
        self.shared = nn.Sequential(*layers)
        
        # PM2.5 head
        self.pm25_head = nn.Sequential(
            nn.Linear(prev_dim, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )
        
        # PM10 head
        self.pm10_head = nn.Sequential(
            nn.Linear(prev_dim, 32),
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
# TRAINING FUNCTION
# ============================================================================

def train_experiment(config, X_train, X_test, y_train, y_test):
    """Train a single experiment"""
    
    print(f"\n{'='*80}")
    print(f"Experiment: {config['name']}")
    print(f"{'='*80}")
    print(f"  Hidden layers: {config['hidden_layers']}")
    print(f"  Dropout: {config['dropout']}")
    print(f"  Learning rate: {config['lr']}")
    print(f"  Batch size: {config['batch_size']}")
    print(f"  Epochs: {config['epochs']}")
    
    # Create data loaders
    train_dataset = AQIDataset(X_train, y_train)
    test_dataset = AQIDataset(X_test, y_test)
    
    train_loader = DataLoader(train_dataset, batch_size=config['batch_size'], shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=config['batch_size'])
    
    # Initialize model
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model = FlexibleAQIModel(
        input_dim=X_train.shape[1],
        hidden_layers=config['hidden_layers'],
        dropout=config['dropout']
    ).to(device)
    
    # Loss and optimizer
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=config['lr'])
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=10, factor=0.5)
    
    # Training loop
    best_loss = float('inf')
    train_losses = []
    test_losses = []
    
    for epoch in range(config['epochs']):
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
        
        train_losses.append(train_loss)
        test_losses.append(test_loss)
        
        scheduler.step(test_loss)
        
        if (epoch + 1) % 20 == 0:
            print(f"  Epoch {epoch+1}/{config['epochs']} - Train: {train_loss:.4f}, Test: {test_loss:.4f}")
        
        # Save best model
        if test_loss < best_loss:
            best_loss = test_loss
            torch.save(model.state_dict(), f"models/{config['name']}_best.pt")
    
    # Evaluate
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
    
    pm25_within_20 = np.abs(all_pm25_pred - all_pm25_true) / (all_pm25_true + 1) < 0.2
    pm10_within_20 = np.abs(all_pm10_pred - all_pm10_true) / (all_pm10_true + 1) < 0.2
    
    results = {
        'name': config['name'],
        'config': config,
        'best_loss': best_loss,
        'pm25_mae': pm25_mae,
        'pm25_rmse': pm25_rmse,
        'pm25_r2': pm25_r2,
        'pm25_accuracy': pm25_within_20.mean() * 100,
        'pm10_mae': pm10_mae,
        'pm10_rmse': pm10_rmse,
        'pm10_r2': pm10_r2,
        'pm10_accuracy': pm10_within_20.mean() * 100,
        'train_losses': train_losses,
        'test_losses': test_losses
    }
    
    print(f"\n  Results:")
    print(f"    PM2.5 - MAE: {pm25_mae:.2f}, RMSE: {pm25_rmse:.2f}, R²: {pm25_r2:.4f}, Acc: {results['pm25_accuracy']:.1f}%")
    print(f"    PM10  - MAE: {pm10_mae:.2f}, RMSE: {pm10_rmse:.2f}, R²: {pm10_r2:.4f}, Acc: {results['pm10_accuracy']:.1f}%")
    
    return results

# ============================================================================
# RUN EXPERIMENTS
# ============================================================================

print("\n[STEP 4] Running experiments...")

# Create models directory
os.makedirs('models', exist_ok=True)

all_results = []

for config in EXPERIMENTS:
    results = train_experiment(config, X_train_scaled, X_test_scaled, y_train, y_test)
    all_results.append(results)

# ============================================================================
# COMPARE RESULTS
# ============================================================================

print(f"\n{'='*80}")
print("EXPERIMENT COMPARISON")
print(f"{'='*80}\n")

# Sort by PM2.5 accuracy
all_results.sort(key=lambda x: x['pm25_accuracy'], reverse=True)

print(f"{'Experiment':<20} {'PM2.5 Acc':<12} {'PM10 Acc':<12} {'PM2.5 MAE':<12} {'PM10 MAE':<12}")
print("-" * 80)

for r in all_results:
    print(f"{r['name']:<20} {r['pm25_accuracy']:>10.1f}% {r['pm10_accuracy']:>10.1f}% {r['pm25_mae']:>10.2f} {r['pm10_mae']:>10.2f}")

# Find best model
best_model = all_results[0]
print(f"\n{'='*80}")
print(f"BEST MODEL: {best_model['name']}")
print(f"{'='*80}")
print(f"  PM2.5 Accuracy: {best_model['pm25_accuracy']:.1f}%")
print(f"  PM10 Accuracy: {best_model['pm10_accuracy']:.1f}%")
print(f"  PM2.5 MAE: {best_model['pm25_mae']:.2f}")
print(f"  PM10 MAE: {best_model['pm10_mae']:.2f}")

# Save results
with open('experiment_results.json', 'w') as f:
    # Remove train/test losses for JSON serialization
    results_to_save = []
    for r in all_results:
        r_copy = r.copy()
        r_copy.pop('train_losses', None)
        r_copy.pop('test_losses', None)
        results_to_save.append(r_copy)
    json.dump(results_to_save, f, indent=2)

print(f"\n✓ Results saved to experiment_results.json")

# Copy best model
import shutil
shutil.copy(f"models/{best_model['name']}_best.pt", "vayu_model_v3_best.pt")
shutil.copy("vayu_scaler_v2.pkl", "vayu_scaler_v3.pkl")

print(f"✓ Best model copied to vayu_model_v3_best.pt")
print(f"\n{'='*80}")
print("TRAINING COMPLETE!")
print(f"{'='*80}")
