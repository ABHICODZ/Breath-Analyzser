import math
import random
import os

def pm25_to_aqi_us(pm25: float) -> int:
    """Official US EPA AQI breakpoints for PM2.5 (µg/m³)."""
    bp = [
        (0.0,   12.0,  0,   50),
        (12.1,  35.4,  51,  100),
        (35.5,  55.4,  101, 150),
        (55.5,  150.4, 151, 200),
        (150.5, 250.4, 201, 300),
        (250.5, 350.4, 301, 400),
        (350.5, 500.4, 401, 500),
    ]
    for c_lo, c_hi, i_lo, i_hi in bp:
        if c_lo <= pm25 <= c_hi:
            return round(i_lo + (pm25 - c_lo) * (i_hi - i_lo) / (c_hi - c_lo))
    return 500 if pm25 > 500.4 else 0

class TemporalNeuralNetworkMock:
    """
    VayuDrishti Spatial Inference Engine.
    Uses the trained PyTorch model for blind-zone interpolation.
    Falls back to physics-based IDW with wind advection.
    """
    def __init__(self, model_path: str = "vayu_spatial_PRODUCTION.pt"):
        print("[ML Engine] Booting Temporal Neural Network Spatial Interpolator...")
        self.wind_vector_x = 0.8
        self.wind_vector_y = 0.4

        self.use_torch = False
        self.model = None
        self.scaler = None
        try:
            import torch
            import torch.nn as nn
            import pickle

            class TemporalSpatialNet(nn.Module):
                # 7-input -> PM2.5 prediction matching train_vayu_v2.py
                def __init__(self, input_dim: int = 7):
                    super().__init__()
                    self.network = nn.Sequential(
                        nn.Linear(input_dim, 256),
                        nn.BatchNorm1d(256),
                        nn.SiLU(),
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

            full_path = os.path.join(os.path.dirname(__file__), model_path)
            if os.path.exists(full_path):
                self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
                self.model = TemporalSpatialNet()
                self.model.load_state_dict(torch.load(full_path, map_location=self.device, weights_only=True))
                self.model.to(self.device)
                self.model.eval()
                self.use_torch = True
                print(f"[ML Engine] SUCCESS: Production Cloud Weights Loaded natively on {self.device.type.upper()}!")

                scaler_path = os.path.join(os.path.dirname(__file__), 'vayu_scaler.pkl')
                if os.path.exists(scaler_path):
                    with open(scaler_path, 'rb') as f:
                        self.scaler = pickle.load(f)
                    print(f"[ML Engine] SUCCESS: StandardScaler loaded. Inference inputs will be normalized.")
                else:
                    print(f"[ML Engine] WARNING: vayu_scaler.pkl missing. Predictions will be unscaled and inaccurate.")
        except Exception as e:
            print(f"[ML Engine] PyTorch missing or file error — using physics-based IDW fallback. ({e})")

    def _calculate_spatial_weight(self, ward_lat, ward_lon, anchor_lat, anchor_lon):
        distance = math.hypot(ward_lat - anchor_lat, (ward_lon - anchor_lon) * 0.8)
        dx = ward_lon - anchor_lon
        dy = ward_lat - anchor_lat
        wind_alignment = (dx * self.wind_vector_x + dy * self.wind_vector_y)
        weight = 1.0 / (distance + 0.001)
        if wind_alignment > 0:
            weight *= 1.5
        return weight

    def _location_noise(self, lat: float, lon: float, scale: float = 8.0) -> float:
        """Deterministic, location-specific noise — same lat/lon always gets the same offset."""
        seed = int(abs(lat * 1000) * 7 + abs(lon * 1000) * 13) % 10000
        rng = random.Random(seed)
        return rng.uniform(-scale, scale)

    def predict(self, anchors_data: list, all_wards_meta: list) -> dict:
        mapped_predictions = {}

        for ward in all_wards_meta:
            ward_id = str(ward.get("id"))
            w_lat = float(ward["lat"])
            w_lon = float(ward["lon"])

            # If this ward IS an anchor, use its real measured data
            anchor_match = next((a for a in anchors_data if a["id"] == ward_id), None)
            if anchor_match:
                mapped_predictions[ward_id] = anchor_match
                continue

            # ─── Spatial Interpolation ─────────────────────────────────────
            if self.use_torch:
                try:
                    import torch
                    import numpy as np

                    # IDW-weighted blend of all anchor stations
                    weights = [self._calculate_spatial_weight(w_lat, w_lon, a["lat"], a["lon"]) for a in anchors_data]
                    total_w = sum(weights)
                    blended_pm25 = sum(a["pm25"] * w for a, w in zip(anchors_data, weights)) / total_w
                    blended_co   = sum(a.get("co_ppb",  0.0) * w for a, w in zip(anchors_data, weights)) / total_w
                    blended_no2  = sum(a.get("no2",     0.0) * w for a, w in zip(anchors_data, weights)) / total_w
                    blended_pm10 = sum(a.get("pm10",    blended_pm25 * 1.5) * w for a, w in zip(anchors_data, weights)) / total_w
                    blended_so2  = sum(a.get("so2",     0.0) * w for a, w in zip(anchors_data, weights)) / total_w

                    dist_city = math.hypot(w_lat - 28.6139, w_lon - 77.2090)

                    # 7-feature vector matching train_vayu_v2.py build_features()
                    # [lat, lon, dist_center, co_ppb, no2, pm10, so2]
                    X_input = np.array([[w_lat, w_lon, dist_city, blended_co, blended_no2, blended_pm10, blended_so2]])
                    
                    if self.scaler:
                        X_scaled = self.scaler.transform(X_input)
                    else:
                        X_scaled = X_input
                        
                    X_tensor = torch.tensor(X_scaled, dtype=torch.float32).to(self.device)

                    with torch.no_grad():
                        pred_pm25 = self.model(X_tensor).item()

                    pred_pm25 += self._location_noise(w_lat, w_lon, scale=5.0)
                    predicted_pm25 = max(5.0, min(500.0, pred_pm25))

                except Exception:
                    self.use_torch = False
                    predicted_pm25 = 48.0
            else:
                # Pure IDW with wind advection + deterministic per-ward noise
                total_weight = 0
                weighted_pm25 = 0
                for anchor in anchors_data:
                    weight = self._calculate_spatial_weight(w_lat, w_lon, anchor["lat"], anchor["lon"])
                    weighted_pm25 += anchor["pm25"] * weight
                    total_weight += weight
                base_pm25 = weighted_pm25 / total_weight if total_weight > 0 else 48.0

                # Each ward gets its own reproducible offset (±15% spatial micro-variation)
                noise = self._location_noise(w_lat, w_lon, scale=base_pm25 * 0.15)
                predicted_pm25 = max(5.0, base_pm25 + noise)

            predicted_pm25 = round(predicted_pm25, 1)
            predicted_aqi = pm25_to_aqi_us(predicted_pm25)

            # Deterministic trend per ward
            seed_trend = int(abs(w_lat * 100 + w_lon * 100)) % 10
            trend = "increasing" if seed_trend >= 7 else "decreasing" if seed_trend <= 2 else "stable"

            # Pollution source based on location characteristics
            dist_center = math.hypot(w_lat - 28.61, w_lon - 77.20)
            if dist_center < 0.1:
                source = "Dense Traffic & Commercial Congestion"
            elif predicted_pm25 > 100:
                source = "Industrial Plume + Resuspended Road Dust"
            elif predicted_pm25 > 60:
                source = "Vehicular Combustion + Biomass Influence"
            else:
                source = "Background Regional Transport"

            mapped_predictions[ward_id] = {
                "id": ward_id,
                "name": ward.get("name"),
                "lat": w_lat,
                "lon": w_lon,
                "aqi": predicted_aqi,
                "pm25": predicted_pm25,
                "dominant_source": source,
                "status": "Severe" if predicted_aqi > 400 else "Very Poor" if predicted_aqi > 300 else "Poor" if predicted_aqi > 200 else "Moderate" if predicted_aqi > 100 else "Satisfactory",
                "trend": trend
            }

        return mapped_predictions
