"""
Premium Features Module - Advanced Analytics & Predictions
Features: Lap prediction, Driver comparison, Benchmark scoring, Real-time tracking
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


# ============================================================================
# DATA CLASSES
# ============================================================================

@dataclass
class DriverProfile:
    """Complete driver profile with stats and tendencies"""
    name: str
    total_laps: int
    best_lap_time: float
    average_lap_time: float
    consistency_score: float
    smoothness_score: float
    aggression_level: float  # 0-100 (0=defensive, 100=aggressive)
    style: str  # aggressive, smooth, consistent, defensive
    preferred_brake_point: float  # meters into corner
    preferred_throttle_point: float
    strength_areas: List[str]
    weakness_areas: List[str]


@dataclass
class BenchmarkResult:
    """Benchmark comparison result"""
    metric: str
    current_value: float
    benchmark_value: float
    difference: float
    percentage_diff: float
    status: str  # "ahead", "behind", "matched"


# ============================================================================
# LAP TIME PREDICTION
# ============================================================================

def predict_lap_time(df: pd.DataFrame, training_history: Optional[List[float]] = None) -> Tuple[float, float]:
    """
    Predict final lap time based on current progress
    
    Returns: (predicted_time, confidence)
    """
    
    if 'time' not in df.columns or len(df) < 10:
        return 0, 0
    
    current_distance = df['distance_traveled'].max() if 'distance_traveled' in df.columns else len(df)
    total_distance = df['distance_traveled'].max() if 'distance_traveled' in df.columns else len(df)
    
    # Current pace
    elapsed_time = df['time'].max()
    pace = elapsed_time / (current_distance + 0.1)
    predicted_total = pace * total_distance
    
    # Confidence based on completion percentage
    completion = current_distance / (total_distance + 0.1)
    confidence = min(completion, 0.95)  # Max 95% confidence
    
    # Adjust if we have historical data
    if training_history and len(training_history) > 0:
        historical_avg = np.mean(training_history)
        historical_std = np.std(training_history)
        
        # Bias towards historical average with decay
        weight = 1 - completion if completion < 0.5 else completion
        predicted_total = (predicted_total * completion) + (historical_avg * (1 - weight))
        
        # Confidence increases with historical data
        confidence = min(0.95, confidence + (len(training_history) * 0.05))
    
    return predicted_total, confidence


# ============================================================================
# CORNER BRAKING ANALYSIS
# ============================================================================

def analyze_braking_points(df: pd.DataFrame, sensitivity: float = 0.15) -> List[Dict]:
    """
    Analyze braking points and efficiency
    """
    
    if 'brake_input' not in df.columns or 'distance_traveled' not in df.columns:
        return []
    
    brake_events = []
    
    # Find braking zones (brake input > threshold)
    brake_mask = df['brake_input'] > 0.2
    
    # Detect onsets of braking
    brake_starts = np.where((brake_mask & ~brake_mask.shift(fill_value=False)))[0]
    
    for start_idx in brake_starts[:10]:  # Top 10 braking points
        end_idx = min(start_idx + 30, len(df) - 1)
        braking_section = df.iloc[start_idx:end_idx]
        
        decel_rate = (braking_section['speed'].iloc[-1] - braking_section['speed'].iloc[0]) / (len(braking_section) + 1)
        
        brake_events.append({
            'distance': float(braking_section['distance_traveled'].iloc[0]),
            'initial_speed': float(braking_section['speed'].iloc[0]),
            'final_speed': float(braking_section['speed'].iloc[-1]),
            'deceleration': abs(decel_rate),
            'brake_depth': float(braking_section['brake_input'].max()),
            'smoothness': float(100 - (braking_section['brake_input'].diff().abs().mean() * 100)),
        })
    
    return brake_events


# ============================================================================
# ACCELERATION ZONE ANALYSIS
# ============================================================================

def analyze_acceleration_zones(df: pd.DataFrame) -> List[Dict]:
    """
    Analyze acceleration efficiency and traction
    """
    
    if 'throttle_input' not in df.columns or 'distance_traveled' not in df.columns:
        return []
    
    accel_zones = []
    
    # Find acceleration zones
    throttle_mask = df['throttle_input'] > 0.5
    throttle_starts = np.where((throttle_mask & ~throttle_mask.shift(fill_value=False)))[0]
    
    for start_idx in throttle_starts[:10]:
        end_idx = min(start_idx + 30, len(df) - 1)
        accel_section = df.iloc[start_idx:end_idx]
        
        speed_gain = accel_section['speed'].iloc[-1] - accel_section['speed'].iloc[0]
        accel_rate = speed_gain / (len(accel_section) + 1)
        
        accel_zones.append({
            'distance': float(accel_section['distance_traveled'].iloc[0]),
            'initial_speed': float(accel_section['speed'].iloc[0]),
            'final_speed': float(accel_section['speed'].iloc[-1]),
            'acceleration': accel_rate,
            'throttle_depth': float(accel_section['throttle_input'].max()),
            'efficiency': float(speed_gain / (accel_section['throttle_input'].mean() + 0.1)),
            'traction_loss': float(('traction_loss' in accel_section and accel_section['traction_loss'].sum()) or 0),
        })
    
    return accel_zones


# ============================================================================
# DRIVER CONSISTENCY ANALYSIS
# ============================================================================

def analyze_consistency(df: pd.DataFrame, lap_history: Optional[List[pd.DataFrame]] = None) -> Dict:
    """
    Analyze driver consistency across multiple metrics
    """
    
    consistency_metrics = {}
    
    # Speed consistency
    if 'speed' in df.columns:
        speed_std = df['speed'].std()
        speed_consistency = max(0, 100 - (speed_std * 5))
        consistency_metrics['speed_consistency'] = float(speed_consistency)
    
    # Line consistency (if GPS available)
    if 'latitude' in df.columns and 'longitude' in df.columns:
        # Calculate deviation from average line
        avg_lat = df['latitude'].mean()
        avg_lon = df['longitude'].mean()
        deviation = np.sqrt((df['latitude'] - avg_lat)**2 + (df['longitude'] - avg_lon)**2).mean()
        line_consistency = max(0, 100 - (deviation * 1000))
        consistency_metrics['line_consistency'] = float(line_consistency)
    
    # Braking consistency
    if 'brake_input' in df.columns:
        brake_sections = df[df['brake_input'] > 0.2]
        if len(brake_sections) > 0:
            brake_std = brake_sections['brake_input'].std()
            brake_consistency = max(0, 100 - (brake_std * 50))
            consistency_metrics['brake_consistency'] = float(brake_consistency)
    
    # Throttle consistency
    if 'throttle_input' in df.columns:
        throttle_sections = df[df['throttle_input'] > 0.2]
        if len(throttle_sections) > 0:
            throttle_std = throttle_sections['throttle_input'].std()
            throttle_consistency = max(0, 100 - (throttle_std * 50))
            consistency_metrics['throttle_consistency'] = float(throttle_consistency)
    
    # Historical consistency (if lap history provided)
    if lap_history and len(lap_history) > 1:
        lap_times = [lap['time'].max() for lap in lap_history if 'time' in lap.columns]
        if len(lap_times) > 1:
            lap_time_std = np.std(lap_times)
            lap_time_consistency = max(0, 100 - (lap_time_std / (np.mean(lap_times) + 0.1) * 100))
            consistency_metrics['lap_time_consistency'] = float(lap_time_consistency)
    
    # Overall consistency
    if consistency_metrics:
        overall = np.mean(list(consistency_metrics.values()))
        consistency_metrics['overall_consistency'] = float(overall)
    
    return consistency_metrics


# ============================================================================
# SECTOR-WISE PERFORMANCE
# ============================================================================

def analyze_sector_performance(df: pd.DataFrame, n_sectors: int = 3) -> Dict[str, Dict]:
    """
    Divide lap into sectors and analyze performance in each
    """
    
    sector_data = {}
    
    if 'distance_traveled' not in df.columns:
        return sector_data
    
    total_distance = df['distance_traveled'].max()
    sector_size = total_distance / n_sectors
    
    for i in range(n_sectors):
        sector_start = i * sector_size
        sector_end = (i + 1) * sector_size
        
        mask = (df['distance_traveled'] >= sector_start) & (df['distance_traveled'] < sector_end)
        sector_df = df[mask]
        
        if len(sector_df) == 0:
            continue
        
        sector_num = i + 1
        sector_data[f'sector_{sector_num}'] = {
            'distance_range': f"{sector_start:.0f}-{sector_end:.0f}m",
            'avg_speed': float(sector_df['speed'].mean()),
            'max_speed': float(sector_df['speed'].max()),
            'min_speed': float(sector_df['speed'].min()),
            'avg_throttle': float(sector_df['throttle_input'].mean() if 'throttle_input' in sector_df else 0),
            'avg_brake': float(sector_df['brake_input'].mean() if 'brake_input' in sector_df else 0),
            'max_steering': float(sector_df['steering_abs'].max() if 'steering_abs' in sector_df else 0),
            'time_in_sector': float(sector_df['time'].max() - sector_df['time'].min() if 'time' in sector_df else 0),
        }
    
    return sector_data


# ============================================================================
# BENCHMARK SCORING SYSTEM
# ============================================================================

def benchmark_performance(df: pd.DataFrame, reference_df: pd.DataFrame) -> List[BenchmarkResult]:
    """
    Compare current lap against reference lap
    """
    
    results = []
    
    metrics_to_compare = [
        ('lap_time', lambda x: x['time'].max() if 'time' in x else 0, 'lower_is_better'),
        ('avg_speed', lambda x: x['speed'].mean() if 'speed' in x else 0, 'higher_is_better'),
        ('speed_consistency', lambda x: 100 - x['speed'].std() * 5 if 'speed' in x else 0, 'higher_is_better'),
        ('smoothness', lambda x: x['control_smoothness'].mean() if 'control_smoothness' in x else 50, 'higher_is_better'),
        ('efficiency', lambda x: x['rpm_efficiency'].mean() if 'rpm_efficiency' in x else 50, 'higher_is_better'),
    ]
    
    for metric_name, metric_func, preference in metrics_to_compare:
        current_val = metric_func(df)
        reference_val = metric_func(reference_df)
        
        if reference_val == 0:
            continue
        
        diff = current_val - reference_val
        pct_diff = (diff / abs(reference_val + 0.001)) * 100
        
        if preference == 'higher_is_better':
            status = 'ahead' if diff > 0 else 'behind'
        else:
            status = 'ahead' if diff < 0 else 'behind'
        
        results.append(BenchmarkResult(
            metric=metric_name,
            current_value=current_val,
            benchmark_value=reference_val,
            difference=diff,
            percentage_diff=pct_diff,
            status=status
        ))
    
    return results


# ============================================================================
# DRIVER PROFILE GENERATION
# ============================================================================

def generate_driver_profile(lap_history: List[pd.DataFrame], driver_name: str = "Driver") -> DriverProfile:
    """
    Generate comprehensive driver profile from lap history
    """
    
    if not lap_history:
        return DriverProfile(
            name=driver_name,
            total_laps=0,
            best_lap_time=0,
            average_lap_time=0,
            consistency_score=0,
            smoothness_score=0,
            aggression_level=0,
            style="unknown",
            preferred_brake_point=0,
            preferred_throttle_point=0,
            strength_areas=[],
            weakness_areas=[]
        )
    
    lap_times = []
    consistency_scores = []
    smoothness_scores = []
    brake_points = []
    throttle_points = []
    aggression_levels = []
    
    for lap in lap_history:
        if 'time' in lap:
            lap_times.append(lap['time'].max())
        
        if 'speed_consistency' in lap:
            consistency_scores.append(lap['speed_consistency'].mean())
        
        if 'control_smoothness' in lap:
            smoothness_scores.append(lap['control_smoothness'].mean())
        
        if 'brake_input' in lap and 'distance_traveled' in lap:
            brake_mask = lap['brake_input'] > 0.5
            if brake_mask.any():
                brake_points.append(lap[brake_mask]['distance_traveled'].mean())
        
        if 'throttle_input' in lap:
            aggression = (lap['throttle_input'] > 0.7).sum() / len(lap) * 100
            aggression_levels.append(aggression)
    
    # Determine style
    avg_consistency = np.mean(consistency_scores) if consistency_scores else 50
    avg_smoothness = np.mean(smoothness_scores) if smoothness_scores else 50
    avg_aggression = np.mean(aggression_levels) if aggression_levels else 50
    
    if avg_aggression > 60 and avg_smoothness < 40:
        style = "aggressive"
    elif avg_smoothness > 70:
        style = "smooth"
    elif avg_consistency > 80:
        style = "consistent"
    else:
        style = "balanced"
    
    # Identify strengths and weaknesses
    strengths = []
    weaknesses = []
    
    if avg_consistency > 75:
        strengths.append("High consistency")
    else:
        weaknesses.append("Improve consistency")
    
    if avg_smoothness > 75:
        strengths.append("Smooth inputs")
    else:
        weaknesses.append("Smooth inputs")
    
    if len(lap_times) > 1 and np.std(lap_times) / np.mean(lap_times) < 0.05:
        strengths.append("Repeatable performance")
    else:
        weaknesses.append("Lap variability")
    
    return DriverProfile(
        name=driver_name,
        total_laps=len(lap_history),
        best_lap_time=float(min(lap_times)) if lap_times else 0,
        average_lap_time=float(np.mean(lap_times)) if lap_times else 0,
        consistency_score=float(np.mean(consistency_scores)) if consistency_scores else 0,
        smoothness_score=float(np.mean(smoothness_scores)) if smoothness_scores else 0,
        aggression_level=float(np.mean(aggression_levels)) if aggression_levels else 0,
        style=style,
        preferred_brake_point=float(np.mean(brake_points)) if brake_points else 0,
        preferred_throttle_point=0,
        strength_areas=strengths,
        weakness_areas=weaknesses
    )


# ============================================================================
# IMPROVEMENT RECOMMENDATIONS
# ============================================================================

def generate_recommendations(df: pd.DataFrame, profile: Optional[DriverProfile] = None) -> List[str]:
    """
    Generate personalized improvement recommendations
    """
    
    recommendations = []
    
    # Speed consistency
    if 'speed_consistency' in df.columns and df['speed_consistency'].mean() < 60:
        recommendations.append("🎯 Focus on maintaining consistent speed through corners - reduce speed variation")
    
    # Braking
    if 'brake_smoothness' in df.columns and df['brake_smoothness'].mean() < 50:
        recommendations.append("🛑 Improve brake modulation - apply brakes more progressively")
    
    # Throttle
    if 'throttle_input' in df.columns and df['throttle_input'].max() > 0.9:
        recommendations.append("⚡ Use more smooth throttle application - avoid sudden full throttle")
    
    # Steering precision
    if 'steering_angle' in df.columns and df['steering_angle'].std() > 10:
        recommendations.append("🎪 Refine steering inputs - aim for more precise steering movements")
    
    # RPM efficiency
    if 'rpm_efficiency' in df.columns and df['rpm_efficiency'].mean() < 60:
        recommendations.append("⚙️ Work on RPM management - shift at optimal points")
    
    # Profile-based
    if profile:
        if profile.style == 'aggressive' and profile.smoothness_score < 50:
            recommendations.append("😎 You're driving aggressively - consider calming inputs for consistency")
        elif profile.style == 'smooth' and profile.lap_times and len(profile.lap_times) > 1:
            recommendations.append("🏁 Your smooth style is good! Try pushing a bit harder for speed gains")
    
    return recommendations[:5]  # Top 5 recommendations
