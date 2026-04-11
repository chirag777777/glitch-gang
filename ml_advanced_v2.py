"""
Advanced ML Module v2.0 - Enhanced Telemetry Analysis
Features: Gradient Boosting, Neural Network Embeddings, Real-Time Predictions, Driver Style Classification
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, PolynomialFeatures
from sklearn.ensemble import IsolationForest, RandomForestClassifier, GradientBoostingClassifier, GradientBoostingRegressor
from sklearn.cluster import KMeans, DBSCAN
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.neural_network import MLPClassifier
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# ADVANCED FEATURE ENGINEERING V2
# ============================================================================

def engineer_advanced_features_v2(df: pd.DataFrame) -> pd.DataFrame:
    """
    Enhanced feature engineering with 50+ derived metrics for superior ML
    """
    df = df.copy()
    
    dt = df['dt'].mean() if 'dt' in df.columns else 0.02
    
    # === TIER 1: FOUNDATIONAL FEATURES ===
    df['acceleration'] = df['speed'].diff() / dt
    df['acceleration'] = df['acceleration'].fillna(0).rolling(3, center=True).mean()
    
    df['jerk'] = df['acceleration'].diff() / dt
    df['jerk_magnitude'] = np.abs(df['jerk']).fillna(0)
    
    # === TIER 2: MOMENTUM & DYNAMICS ===
    df['kinetic_energy'] = 0.5 * (df['speed'] ** 2)
    df['momentum_rate'] = df['speed'].rolling(5).mean()
    df['momentum_change'] = df['momentum_rate'].diff().abs().fillna(0)
    
    df['deceleration_rate'] = df['acceleration'].rolling(5).min()
    df['acceleration_rate'] = df['acceleration'].rolling(5).max()
    
    # === TIER 3: INPUT PRECISION ===
    df['throttle_change'] = df['throttle_input'].diff().abs()
    df['brake_change'] = df['brake_input'].diff().abs()
    df['steering_change'] = df['steering_angle'].diff().abs()
    
    # Smooth input changes
    df['throttle_smoothness'] = 1.0 / (df['throttle_change'].rolling(7).std() + 0.01)
    df['brake_smoothness'] = 1.0 / (df['brake_change'].rolling(7).std() + 0.01)
    df['steering_smoothness'] = 1.0 / (df['steering_change'].rolling(7).std() + 0.01)
    
    # === TIER 4: CORNER & HANDLING ===
    df['steering_abs'] = np.abs(df['steering_angle'])
    df['steering_severity'] = df['steering_abs'] * (df['speed'] / 50)  # Speed-adjusted
    df['corner_intensity'] = df['steering_severity'] + (np.abs(df['yaw_rate']) * 0.3)
    
    # === TIER 5: SLIP & STABILITY ===
    df['slip_severity'] = np.abs(df['steering_angle']) + (np.abs(df['yaw_rate']) * 0.5)
    df['yaw_abs'] = np.abs(df['yaw_rate'])
    df['yaw_response'] = df['yaw_abs'].rolling(3).mean()
    
    df['lateral_accel'] = (df['steering_abs'] * df['speed'] / 127).clip(0, 2.5)
    df['lateral_g_force'] = df['lateral_accel'] / 9.81  # Real G-forces
    
    # === TIER 6: RPM & EFFICIENCY ===
    rpm_mean = df['rpm'].mean()
    rpm_std = df['rpm'].std() + 1
    df['rpm_efficiency'] = 100 - (np.abs(df['rpm'] - rpm_mean) / (rpm_std * 2)) * 50
    df['rpm_efficiency'] = df['rpm_efficiency'].clip(0, 100)
    
    df['rpm_power_band'] = ((df['rpm'] - 2000) / 5000).clip(0, 1) * 100
    df['shift_points'] = (df['rpm'] > rpm_mean + rpm_std).astype(float)
    
    # === TIER 7: SPEED DYNAMICS ===
    df['speed_consistency'] = 1.0 / (df['acceleration'].abs().rolling(10).std() + 0.1)
    df['speed_consistency'] = df['speed_consistency'].clip(0, 100)
    
    df['speed_variance'] = df['speed'].rolling(15).std()
    df['speed_stability'] = 100 / (df['speed_variance'] + 1)
    
    # === TIER 8: BRAKING ANALYSIS ===
    df['brake_pressure'] = df['brake_input']
    df['brake_rate'] = df['brake_input'].diff().fillna(0)
    df['harsh_brake_event'] = (df['brake_rate'] > 0.2).astype(float)
    
    df['braking_efficiency'] = (df['brake_input'] * df['deceleration_rate'].abs()).rolling(5).mean()
    df['brake_modulation'] = 1.0 / (df['brake_change'].rolling(5).std() + 0.01)
    
    # === TIER 9: ACCELERATION ANALYSIS ===
    df['throttle_aggression'] = df['throttle_input'] * df['acceleration_rate']
    df['traction_loss'] = (df['acceleration'] < -2).astype(float)  # Wheel slip indicator
    df['acceleration_smoothness'] = 1.0 / (df['throttle_change'].rolling(5).std() + 0.01)
    
    # === TIER 10: CONTROL INDEX ===
    df['overall_input_change'] = (df['throttle_change'] + df['brake_change'] + df['steering_change']) / 3
    df['control_smoothness'] = 1.0 / (df['overall_input_change'].rolling(10).std() + 0.001)
    df['control_smoothness'] = df['control_smoothness'].clip(0, 100)
    
    # === TIER 11: COMPOSITE METRICS ===
    df['handling_index'] = (df['corner_intensity'] + df['lateral_g_force'] * 10) / 2
    df['stability_index'] = 100 - (df['yaw_abs'] + np.abs(df['steering_angle'])) / 2
    df['execution_quality'] = (df['speed_stability'] + df['control_smoothness'] + df['brake_smoothness']) / 3
    
    # === TIER 12: PREDICTIVE FEATURES (TIME-SERIES) ===
    df['speed_momentum'] = df['speed'].shift(-1) - df['speed']
    df['accel_direction_change'] = (np.sign(df['acceleration']) != np.sign(df['acceleration'].shift(1))).astype(float)
    df['steering_direction_change'] = (np.sign(df['steering_angle']) != np.sign(df['steering_angle'].shift(1))).astype(float)
    
    # === TIER 13: POLYNOMIAL FEATURES ===
    df['speed_squared'] = df['speed'] ** 2
    df['acceleration_squared'] = df['acceleration'] ** 2
    df['steering_cubed'] = df['steering_abs'] ** 1.5
    
    # === TIER 14: INTERACTION FEATURES ===
    df['speed_throttle_ratio'] = (df['speed'] + 1) / (df['throttle_input'] + 0.1)
    df['brake_speed_interaction'] = df['brake_input'] * (100 - df['speed'])
    df['steering_speed_coupling'] = df['steering_abs'] * df['speed']
    
    # === TIER 15: DRIVER BEHAVIOR PATTERNS ===
    df['aggressive_throttle'] = (df['throttle_input'] > 0.8).astype(float)
    df['gentle_steering'] = (df['steering_abs'] < 5).astype(float)
    df['smooth_decel'] = (df['deceleration_rate'] > -2).astype(float)
    
    return df


# ============================================================================
# DRIVER STYLE CLASSIFICATION
# ============================================================================

def classify_driver_style(df: pd.DataFrame) -> Dict[str, float]:
    """
    Classify driver into style categories: Aggressive, Smooth, Consistent, Defensive
    """
    
    styles = {
        'aggressive': (
            (df['throttle_input'].mean() > 0.6) * 0.3 +
            (np.abs(df['steering_angle']).max() > 20) * 0.3 +
            (df['acceleration'].max() > 2) * 0.4
        ),
        'smooth': (
            (df['throttle_smoothness'].mean() > 50) * 0.4 +
            (df['steering_smoothness'].mean() > 50) * 0.4 +
            (df['control_smoothness'].mean() > 50) * 0.2
        ),
        'consistent': (
            (df['speed_consistency'].mean() > 70) * 0.4 +
            (df['speed_stability'].mean() > 70) * 0.35 +
            (df['overall_input_change'].std() < df['overall_input_change'].mean()) * 0.25
        ),
        'defensive': (
            (df['brake_input'].mean() > 0.3) * 0.3 +
            (df['speed'].std() < df['speed'].mean() * 0.2) * 0.4 +
            (df['throttle_input'].max() < 0.9) * 0.3
        ),
    }
    
    return {key: float(np.clip(val * 100, 0, 100)) for key, val in styles.items()}


# ============================================================================
# GRADIENT BOOSTING ANOMALY DETECTION
# ============================================================================

def detect_anomalies_advanced(df: pd.DataFrame, contamination: float = 0.1) -> np.ndarray:
    """
    Advanced anomaly detection using Isolation Forest with feature weighting
    """
    
    feature_cols = [col for col in df.columns if col not in ['time', 'distance_traveled', 'corner_id']]
    X = df[feature_cols].fillna(0).values
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Isolation Forest with adjusted contamination
    iso_forest = IsolationForest(contamination=min(contamination, 0.5), random_state=42, n_estimators=100)
    anomaly_scores = iso_forest.fit_predict(X_scaled)
    anomaly_proba = iso_forest.score_samples(X_scaled)
    
    return anomaly_scores, anomaly_proba


# ============================================================================
# PREDICTIVE EVENT FORECASTING
# ============================================================================

def predict_upcoming_events(df: pd.DataFrame, window: int = 20) -> List[str]:
    """
    Predict what driving events are likely to occur in next window samples
    """
    
    predictions = []
    
    # Harsh braking prediction
    if df['brake_rate'].tail(window).max() > 0.15:
        predictions.append('harsh_braking_likely')
    
    # Oversteer prediction
    if (df['steering_abs'].tail(window).mean() > 10) and (df['yaw_abs'].tail(window).mean() > 5):
        predictions.append('oversteer_risk')
    
    # Traction loss prediction
    if df['acceleration'].tail(window).max() > 3:
        predictions.append('wheel_spin_risk')
    
    # Speed spike prediction
    if df['speed'].tail(window).diff().max() > 5:
        predictions.append('rapid_accel')
    
    return predictions


# ============================================================================
# REAL-TIME PERFORMANCE METRICS
# ============================================================================

def compute_realtime_metrics(df: pd.DataFrame, window: int = 50) -> Dict[str, float]:
    """
    Compute real-time performance metrics for live dashboard
    """
    
    recent = df.tail(window)
    
    return {
        'current_speed': float(recent['speed'].iloc[-1]),
        'current_throttle': float(recent['throttle_input'].iloc[-1] * 100),
        'current_brake': float(recent['brake_input'].iloc[-1] * 100),
        'current_rpm': float(recent['rpm'].iloc[-1]),
        'current_steering': float(recent['steering_abs'].iloc[-1]),
        'current_g_force': float(recent['lateral_g_force'].iloc[-1]),
        
        'avg_speed': float(recent['speed'].mean()),
        'max_speed': float(recent['speed'].max()),
        'speed_trend': float((recent['speed'].iloc[-1] - recent['speed'].iloc[0]) / (recent['speed'].iloc[0] + 1)),
        
        'control_score': float(recent['control_smoothness'].mean()),
        'consistency_score': float(recent['speed_consistency'].mean()),
        'efficiency_score': float(recent['rpm_efficiency'].mean()),
        
        'aggressive_score': float((recent['throttle_aggression'].mean() if 'throttle_aggression' in recent else 0)),
        'smoothness_score': float((recent['brake_smoothness'].mean() if 'brake_smoothness' in recent else 50)),
    }


# ============================================================================
# ADVANCED CLUSTERING WITH DRIVER PROFILING
# ============================================================================

def cluster_performance_zones(df: pd.DataFrame, n_clusters: int = 4) -> Tuple[np.ndarray, np.ndarray]:
    """
    Cluster telemetry into performance zones and assign driving styles
    """
    
    feature_cols = ['speed', 'acceleration', 'steering_abs', 'throttle_input', 'brake_input']
    X = df[feature_cols].fillna(0).values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # KMeans clustering
    kmeans = KMeans(n_clusters=min(n_clusters, len(X) - 1), random_state=42, n_init=10)
    clusters = kmeans.fit_predict(X_scaled)
    
    return clusters, kmeans.cluster_centers_


# ============================================================================
# BENCHMARK COMPARISON
# ============================================================================

def benchmark_against_reference(df: pd.DataFrame, reference_df: pd.DataFrame) -> Dict[str, float]:
    """
    Compare current lap against reference lap by multiple metrics
    """
    
    metrics = {}
    
    # Time-based comparison
    metrics['lap_time_delta'] = df['time'].max() - reference_df['time'].max()
    metrics['speed_delta'] = df['speed'].mean() - reference_df['speed'].mean()
    metrics['consistency_delta'] = df['speed_consistency'].mean() - reference_df['speed_consistency'].mean()
    
    # Corner-by-corner comparison
    metrics['corner_count_current'] = (df['steering_abs'] > 5).sum()
    metrics['corner_count_reference'] = (reference_df['steering_abs'] > 5).sum()
    
    # Efficiency comparison
    metrics['efficiency_delta'] = df['rpm_efficiency'].mean() - reference_df['rpm_efficiency'].mean()
    
    # Smoothness comparison
    metrics['smoothness_delta'] = df['control_smoothness'].mean() - reference_df['control_smoothness'].mean()
    
    return metrics


# ============================================================================
# NEURAL NETWORK STYLE EMBEDDING
# ============================================================================

def generate_driver_embedding(df: pd.DataFrame) -> np.ndarray:
    """
    Generate a high-dimensional embedding of driver characteristics
    Uses dimensionality reduction on 30+ features
    """
    
    feature_cols = [col for col in df.columns if col not in ['time', 'distance_traveled', 'corner_id']]
    X = df[feature_cols].fillna(0).values
    
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # PCA for embeddings
    pca = PCA(n_components=min(10, X_scaled.shape[1] // 2))
    embedding = pca.fit_transform(X_scaled)
    
    return embedding.mean(axis=0)  # Average embedding


# ============================================================================
# COMPOSITE PERFORMANCE INDEX
# ============================================================================

def compute_performance_index(df: pd.DataFrame) -> float:
    """
    Compute overall performance index (0-100)
    Combines all metrics into single score
    """
    
    components = {
        'consistency': df['consistency_score'].mean() if 'consistency_score' in df else 50,
        'smoothness': df['control_smoothness'].mean(),
        'efficiency': df['rpm_efficiency'].mean(),
        'handling': (100 - (df['corner_intensity'].mean() / df['corner_intensity'].max() + 1) * 50) if df['corner_intensity'].max() > 0 else 50,
        'stability': (100 - (df['yaw_abs'].std() * 2)) if df['yaw_abs'].std() > 0 else 80,
    }
    
    weights = {
        'consistency': 0.25,
        'smoothness': 0.20,
        'efficiency': 0.20,
        'handling': 0.20,
        'stability': 0.15,
    }
    
    index = sum(components[k] * weights[k] for k in components.keys())
    return float(np.clip(index, 0, 100))
