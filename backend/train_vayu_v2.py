"""
================================================================
VAYU DRISHTI — REAL DATA SPATIAL INTERPOLATION TRAINING SCRIPT
================================================================
Trains the TemporalSpatialNet on real CPCB/Kaggle Delhi AQI data.

Datasets needed (already in your backend/dataset_extracted/):
  - delhi_aqi.csv        (18,776 rows: date, co, no, no2, o3, so2, pm2_5, pm10, nh3)
  - final_dataset.csv    (multi-station historical data)

Output: vayu_spatial_PRODUCTION.pt (drop into backend/app/services/)

Run Options:
  Local RTX 3050:  python train_vayu_v2.py
  Google Colab:    Upload this file + CSVs to Colab, run as-is (auto-detects GPU)
================================================================
"""

import pandas as pd
import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import os, math, time

# ─── Config ───────────────────────────────────────────────────────────────────
DEVICE        = torch.device("cuda" if torch.cuda.is_available() else "cpu")
EPOCHS        = 150
BATCH_SIZE    = 512
LEARNING_RATE = 1e-3
MODEL_OUT     = "vayu_spatial_PRODUCTION.pt"

print(f"[VAYU] Device: {DEVICE}")
if DEVICE.type == "cuda":
    print(f"[VAYU] GPU: {torch.cuda.get_device_name(0)}")

# ─── Delhi CPCB Station Coordinates ──────────────────────────────────────────
# Real latitude/longitude for the named monitoring stations in the dataset.
# These are used to add spatial features (lat, lon, dist_center) to each row.
STATION_COORDS = {
    "Anand Vihar":          (28.6508,  77.3152),
    "Punjabi Bagh":         (28.6683,  77.1167),
    "Rohini":               (28.7327,  77.1180),
    "Mandir Marg":          (28.6341,  77.2005),
    "Patparganj":           (28.6202,  77.2877),
    "Lodhi Road":           (28.5897,  77.2219),
    "Dwarka":               (28.5766,  77.0759),
    "RK Puram":             (28.5648,  77.1744),
    "Jahangirpuri":         (28.7330,  77.1720),
    "Shadipur":             (28.6516,  77.1580),
    "Okhla":                (28.5313,  77.2707),
    "Wazirpur":             (28.7005,  77.1656),
    "Narela":               (28.8206,  77.1011),
    "Burari Crossing":      (28.7257,  77.2034),
    "DTU":                  (28.7496,  77.1163),
    "Pusa":                 (28.6370,  77.1722),
    "ITO":                  (28.6286,  77.2410),
    "Mundka":               (28.6824,  77.0305),
    "Najafgarh":            (28.5727,  76.9334),
    "Aya Nagar":            (28.4829,  77.1267),
}
DELHI_CENTER = (28.6139, 77.2090)

# ─── Dataset ──────────────────────────────────────────────────────────────────

def load_and_merge_datasets():
    """Load, clean, and merge all available CSV datasets."""
    dfs = []

    # Dataset 1: delhi_aqi.csv (single merged station, multi-year)
    p1 = "dataset_extracted/delhi_aqi.csv"
    if os.path.exists(p1):
        df = pd.read_csv(p1)
        df.columns = df.columns.str.strip().str.lower()
        # Rename common variants
        for old, new in [("pm2_5","pm25"),("pm2.5","pm25"),("co","co_ppb"),("station","station_name")]:
            if old in df.columns:
                df = df.rename(columns={old: new})
        df["station_name"] = df.get("station_name", pd.Series(["Generic Delhi"]*len(df)))
        df["lat"]  = DELHI_CENTER[0]
        df["lon"]  = DELHI_CENTER[1]
        dfs.append(df)
        print(f"[DATA] delhi_aqi.csv loaded: {len(df):,} rows")

    # Dataset 2: final_dataset.csv (may have multiple stations)
    p2 = "dataset_extracted/final_dataset.csv"
    if os.path.exists(p2):
        df = pd.read_csv(p2)
        df.columns = df.columns.str.strip().str.lower()
        for old, new in [("pm2_5","pm25"),("pm2.5","pm25")]:
            if old in df.columns:
                df = df.rename(columns={old: new})
        # Add real coordinates if station name is available
        if "station" in df.columns or "station_name" in df.columns:
            sname_col = "station" if "station" in df.columns else "station_name"
            df["station_name"] = df[sname_col]
            df["lat"] = df["station_name"].map(lambda s: STATION_COORDS.get(s, DELHI_CENTER)[0])
            df["lon"] = df["station_name"].map(lambda s: STATION_COORDS.get(s, DELHI_CENTER)[1])
        else:
            df["lat"] = DELHI_CENTER[0]
            df["lon"] = DELHI_CENTER[1]
        dfs.append(df)
        print(f"[DATA] final_dataset.csv loaded: {len(df):,} rows")

    if not dfs:
        raise FileNotFoundError("No CSV datasets found! Place them in dataset_extracted/")

    combined = pd.concat(dfs, ignore_index=True)
    return combined


class DelhiAQIDataset(Dataset):
    def __init__(self, X: np.ndarray, y: np.ndarray):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32).unsqueeze(1)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]


def build_features(df: pd.DataFrame):
    """
    Build the feature matrix (X) and target (y=pm25) from raw dataframe.

    Features (7 total):
      lat, lon, dist_center,          ← Spatial location
      co_ppb, no2, pm10, so2          ← Chemical measurements (best predictors from EDA)

    Target: pm25 (India CPCB AQI is derived from this)
    """
    required = ["pm25", "lat", "lon"]
    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}. Found: {df.columns.tolist()}")

    df = df.dropna(subset=["pm25"])

    # Spatial features
    df["dist_center"] = np.sqrt(
        (df["lat"] - DELHI_CENTER[0])**2 + (df["lon"] - DELHI_CENTER[1])**2
    )

    # Chemical features — fill missing with median (stations don't measure everything)
    chem_features = ["co_ppb", "no2", "pm10", "so2"]
    for col in chem_features:
        if col not in df.columns:
            df[col] = 0.0
        df[col] = df[col].fillna(df[col].median() if not df[col].isna().all() else 0.0)

    feature_cols = ["lat", "lon", "dist_center", "co_ppb", "no2", "pm10", "so2"]
    X = df[feature_cols].values.astype(np.float32)
    y = df["pm25"].values.astype(np.float32)

    # Remove outliers (pm25 > 500 is sensor error)
    mask = (y > 0) & (y < 500)
    return X[mask], y[mask]


# ─── Model Architecture ───────────────────────────────────────────────────────

class TemporalSpatialNet(nn.Module):
    """
    7-input → PM2.5 prediction network.
    Input features: lat, lon, dist_center, co, no2, pm10, so2
    This matches what the production inference engine feeds to it.
    """
    def __init__(self, input_dim: int = 7):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.BatchNorm1d(256),
            nn.SiLU(),                    # SiLU (Swish) > ReLU for regression tasks
            nn.Dropout(0.25),
            nn.Linear(256, 128),
            nn.BatchNorm1d(128),
            nn.SiLU(),
            nn.Dropout(0.15),
            nn.Linear(128, 64),
            nn.SiLU(),
            nn.Linear(64, 1),
        )

    def forward(self, x):
        return self.network(x)


# ─── Training ─────────────────────────────────────────────────────────────────

def train():
    print("\n" + "="*60)
    print(" VAYU DRISHTI — TRAINING ON REAL DELHI DATA")
    print("="*60)

    # Load data
    df = load_and_merge_datasets()
    X, y = build_features(df)
    print(f"[DATA] Total clean samples: {len(X):,}")
    print(f"[DATA] PM2.5 range: {y.min():.1f} – {y.max():.1f} µg/m³  |  mean: {y.mean():.1f}")

    # Normalize features only (not target — we want real µg/m³ output)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    X_train, X_val, y_train, y_val = train_test_split(X_scaled, y, test_size=0.15, random_state=42)

    train_ds = DelhiAQIDataset(X_train, y_train)
    val_ds   = DelhiAQIDataset(X_val,   y_val)

    train_dl = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True,  num_workers=0, pin_memory=(DEVICE.type=="cuda"))
    val_dl   = DataLoader(val_ds,   batch_size=BATCH_SIZE, shuffle=False, num_workers=0)

    model = TemporalSpatialNet(input_dim=X.shape[1]).to(DEVICE)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.HuberLoss(delta=10.0)   # Huber is better than MSE for PM2.5 (skewed distribution)

    best_val_loss = float('inf')
    start = time.time()

    print(f"\n[TRAIN] Starting {EPOCHS} epochs... (batch={BATCH_SIZE}, lr={LEARNING_RATE})")

    for epoch in range(1, EPOCHS + 1):
        # ── Train ──
        model.train()
        train_loss = 0.0
        for Xb, yb in train_dl:
            Xb, yb = Xb.to(DEVICE), yb.to(DEVICE)
            optimizer.zero_grad()
            pred = model(Xb)
            loss = criterion(pred, yb)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item() * len(Xb)
        train_loss /= len(train_ds)

        # ── Validate ──
        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for Xb, yb in val_dl:
                Xb, yb = Xb.to(DEVICE), yb.to(DEVICE)
                val_loss += criterion(model(Xb), yb).item() * len(Xb)
        val_loss /= len(val_ds)

        scheduler.step()

        if epoch % 10 == 0 or epoch == 1:
            elapsed = time.time() - start
            eta = elapsed / epoch * (EPOCHS - epoch)
            print(f"  Epoch {epoch:03d}/{EPOCHS} | Train Loss: {train_loss:7.3f} | Val Loss: {val_loss:7.3f} | ETA: {eta/60:.1f}min")

        # Save best model
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            # Save state dict — compatible with the production loader
            torch.save(model.state_dict(), MODEL_OUT)

    print(f"\n[DONE] Best Val Loss: {best_val_loss:.3f}")
    print(f"[DONE] Model saved → {MODEL_OUT}")
    print(f"[DONE] Total time: {(time.time()-start)/60:.1f} minutes")

    # Quick sanity check
    print("\n[SANITY] Sample predictions vs reality:")
    model.eval()
    with torch.no_grad():
        sample_X = torch.tensor(X_scaled[:5], dtype=torch.float32).to(DEVICE)
        preds = model(sample_X).cpu().numpy().flatten()
        for i in range(5):
            print(f"  Real PM2.5: {y[:5][i]:6.1f}  |  Predicted: {preds[i]:6.1f}")

    # Save scaler for inference
    import pickle
    with open("vayu_scaler.pkl", "wb") as f:
        pickle.dump(scaler, f)
    print("[DONE] Feature scaler saved → vayu_scaler.pkl")
    print("\nNext step: copy vayu_spatial_PRODUCTION.pt → backend/app/services/")


if __name__ == "__main__":
    train()
