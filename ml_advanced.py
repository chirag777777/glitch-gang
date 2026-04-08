"""
Advanced Feature Engineering & ML Module for Telemetry Analysis
Predicts optimal inputs, analyzes trends, and generates real-time ready outputs
"""

import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.model_selection import train_test_split
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


# ============================================================================
# COMPREHENSIVE FEATURE ENGINEERING
# ============================================================================

def engineer_advanced_features(df: pd.DataFrame, dt: float = 0.02) -> pd.DataFrame:
    """
    Create comprehensive features from full telemetry dataset.
    
    Args:
        df: DataFrame with columns: speed, throttle_input, brake_input, steering_angle,
            combined_slip_angle, yaw_moment, pitch, roll, rpm, gear,
            wheel_speed_fl, wheel_speed_fr, wheel_speed_rl, wheel_speed_rr
        dt: Time delta (default 0.02s for 50Hz)
    
    Returns:
        DataFrame with original + engineered features
    """
    df = df.copy()
    
    # ========== KINEMATIC FEATURES ==========
    # Acceleration features
    df['accel'] = df['speed'].diff().fillna(0) / dt
    df['accel_filtered'] = df['accel'].rolling(window=3, center=True).mean().fillna(df['accel'])
    df['decel'] = df['accel'].clip(upper=0).abs()
    df['accel_magnitude'] = df['accel'].abs()
    
    # Jerk (smoothness)
    df['jerk'] = df['accel'].diff().fillna(0) / dt
    df['jerk_magnitude'] = df['jerk'].abs()
    df['jerk_filtered'] = df['jerk'].rolling(window=5).mean().fillna(0)
    
    # ========== YAWING & ROTATION FEATURES ==========
    df['yaw_abs'] = df['yaw_moment'].abs()
    df['yaw_rate'] = df['yaw_moment'].diff().fillna(0) / dt
    df['yaw_accel'] = df['yaw_rate'].diff().fillna(0) / dt
    
    df['pitch_abs'] = df['pitch'].abs()
    df['pitch_rate'] = df['pitch'].diff().fillna(0) / dt
    
    df['roll_abs'] = df['roll'].abs()
    df['roll_rate'] = df['roll'].diff().fillna(0) / dt
    
    # Combined rotation metric
    df['rotation_magnitude'] = np.sqrt(
        (df['yaw_abs'] ** 2).fillna(0) + 
        (df['pitch_abs'] ** 2).fillna(0) + 
        (df['roll_abs'] ** 2).fillna(0)
    )
    
    # ========== SLIP & TRACTION FEATURES ==========
    df['slip_angle'] = df['combined_slip_angle'].abs()
    df['slip_rate'] = df['slip_angle'].diff().fillna(0) / dt
    
    # Wheel slip calculation
    df['wheel_speed_avg'] = df[['wheel_speed_fl', 'wheel_speed_fr', 
                                 'wheel_speed_rl', 'wheel_speed_rr']].mean(axis=1)
    df['wheel_slip_ratio'] = (df['wheel_speed_avg'] - df['speed']).abs() / (df['speed'] + 0.1)
    df['wheel_slip_ratio'] = df['wheel_slip_ratio'].clip(0, 1)
    
    # Front vs Rear slip (load transfer indicator)
    df['front_wheel_avg'] = df[['wheel_speed_fl', 'wheel_speed_fr']].mean(axis=1)
    df['rear_wheel_avg'] = df[['wheel_speed_rl', 'wheel_speed_rr']].mean(axis=1)
    df['front_slip'] = (df['front_wheel_avg'] - df['speed']).abs() / (df['speed'] + 0.1)
    df['rear_slip'] = (df['rear_wheel_avg'] - df['speed']).abs() / (df['speed'] + 0.1)
    df['slip_balance'] = df['front_slip'] / (df['rear_slip'] + 0.01)  # >1 = understeer
    
    # ========== INPUT FEATURES ==========
    df['throttle_abs'] = df['throttle_input'].abs()
    df['throttle_change'] = df['throttle_input'].diff().fillna(0).abs()
    df['throttle_smooth'] = df['throttle_input'].rolling(window=5).mean().fillna(df['throttle_input'])
    df['throttle_jerk'] = df['throttle_change'].diff().fillna(0) / dt
    
    df['brake_abs'] = df['brake_input'].abs()
    df['brake_change'] = df['brake_input'].diff().fillna(0).abs()
    df['brake_smooth'] = df['brake_input'].rolling(window=5).mean().fillna(df['brake_input'])
    df['brake_jerk'] = df['brake_change'].diff().fillna(0) / dt
    
    df['steering_abs'] = df['steering_angle'].abs()
    df['steering_change'] = df['steering_angle'].diff().fillna(0).abs()
    df['steering_smooth'] = df['steering_angle'].rolling(window=5).mean().fillna(df['steering_angle'])
    df['steering_rate'] = df['steering_change'] / dt
    df['steering_accel'] = df['steering_rate'].diff().fillna(0) / dt
    
    # Combined input smoothness
    df['input_aggression'] = (df['throttle_change'] + df['brake_change'] + df['steering_change']) / 3
    df['input_smoothness'] = 1.0 / (df['input_aggression'] + 0.001)
    
    # ========== GEAR & RPM FEATURES ==========
    df['rpm_ratio'] = df['rpm'] / (df['rpm'].max() + 1)
    df['rpm_percent'] = (df['rpm'] / (df['rpm'].rolling(window=100).max() + 1)) * 100
    df['rpm_efficiency'] = 1.0 - np.abs(df['rpm_ratio'] - 0.7)  # Peak efficiency ~70%
    df['rpm_rate'] = df['rpm'].diff().fillna(0) / dt
    
    df['gear_match_penalty'] = df['gear'].apply(
        lambda g: 0 if 2000 <= (df.loc[df.index == df.index[df['gear'] == g].tolist()[0] if len(df[df['gear'] == g]) > 0 else 0, 'rpm'].values[0] if len(df[df['gear'] == g]) > 0 else 3000) <= 6000 else 1
    ).fillna(0)
    
    # ========== LATERAL DYNAMICS FEATURES ==========
    df['lateral_accel'] = (df['slip_angle'] * df['speed'] / 127).clip(0, 3)
    df['lateral_accel_g'] = df['lateral_accel'] / 9.81
    df['lateral_jerk'] = df['lateral_accel'].diff().fillna(0) / dt
    
    # ========== ENERGETIC FEATURES ==========
    df['kinetic_energy'] = 0.5 * (df['speed'] ** 2)
    df['energy_rate'] = df['kinetic_energy'].diff().fillna(0) / dt
    
    df['braking_power'] = df['brake_input'] * df['speed']
    df['throttle_power'] = df['throttle_input'] * (df['rpm'] / 7000)
    
    # ========== STABILITY METRICS ==========
    df['stability_index'] = (
        (1.0 - df['wheel_slip_ratio'].clip(0, 1)) * 0.4 +
        (1.0 - df['slip_angle'].clip(0, 30) / 30) * 0.3 +
        (1.0 - df['jerk_magnitude'].clip(0, 10) / 10) * 0.3
    )
    df['stability_index'] = df['stability_index'].rolling(window=5).mean().fillna(df['stability_index'])
    
    # Control authority (ability to command vehicle)
    df['control_authority'] = df['steering_rate'] * df['stability_index']
    
    # ========== TEMPORAL FEATURES ==========
    df['time_index'] = np.arange(len(df))
    df['corner_intensity'] = df['steering_abs'] * df['speed'] / 100
    
    return df


# ============================================================================
# OPTIMAL INPUT PREDICTION
# ============================================================================

def build_input_prediction_models(
    df: pd.DataFrame, 
    test_size: float = 0.2,
    random_state: int = 42
) -> Dict:
    """
    Train models to predict optimal throttle, brake, and steering inputs.
    
    Args:
        df: DataFrame with engineered features
        test_size: Train/test split ratio
        random_state: Random state for reproducibility
    
    Returns:
        Dict with trained models and scalers
    """
    
    # Feature selection for prediction
    feature_cols = [
        'speed', 'rpm', 'accel_magnitude', 'slip_angle', 'yaw_abs',
        'pitch_abs', 'roll_abs', 'wheel_slip_ratio', 'slip_balance',
        'gear', 'lateral_accel_g', 'stability_index'
    ]
    
    feature_cols = [col for col in feature_cols if col in df.columns]
    
    # Prepare data
    X = df[feature_cols].fillna(0)
    y_throttle = df['throttle_input'].fillna(0)
    y_brake = df['brake_input'].fillna(0)
    y_steering = df['steering_angle'].fillna(0)
    
    # Scale features
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)
    
    # Train/test split
    X_train, X_test, yt_train, yt_test, yb_train, yb_test, ys_train, ys_test = train_test_split(
        X_scaled, y_throttle, y_brake, y_steering,
        test_size=test_size, random_state=random_state
    )
    
    # Train models (lighter models for real-time inference)
    throttle_model = Ridge(alpha=1.0)
    throttle_model.fit(X_train, yt_train)
    
    brake_model = Ridge(alpha=1.0)
    brake_model.fit(X_train, yb_train)
    
    steering_model = Ridge(alpha=0.5)
    steering_model.fit(X_train, ys_train)
    
    # Compute scores
    throttle_score = throttle_model.score(X_test, yt_test)
    brake_score = brake_model.score(X_test, yb_test)
    steering_score = steering_model.score(X_test, ys_test)
    
    return {
        'throttle_model': throttle_model,
        'brake_model': brake_model,
        'steering_model': steering_model,
        'scaler': scaler,
        'feature_cols': feature_cols,
        'scores': {
            'throttle_r2': throttle_score,
            'brake_r2': brake_score,
            'steering_r2': steering_score
        }
    }


def predict_optimal_inputs(
    df: pd.DataFrame,
    models: Dict,
    feature_cols: Optional[List[str]] = None
) -> pd.DataFrame:
    """
    Predict optimal driving inputs based on current vehicle state.
    
    Args:
        df: Input DataFrame with engineered features
        models: Dict with trained models and scaler
        feature_cols: Optional override for feature columns
    
    Returns:
        DataFrame with predicted optimal inputs and deltas
    """
    df = df.copy()
    
    if feature_cols is None:
        feature_cols = models['feature_cols']
    
    # Extract and scale features
    X = df[feature_cols].fillna(0)
    X_scaled = models['scaler'].transform(X)
    
    # Make predictions
    df['throttle_optimal'] = models['throttle_model'].predict(X_scaled).clip(0, 1)
    df['brake_optimal'] = models['brake_model'].predict(X_scaled).clip(0, 1)
    df['steering_optimal'] = models['steering_model'].predict(X_scaled).clip(-3, 3)
    
    # Compute deltas and suggestions
    df['throttle_delta'] = df['throttle_input'] - df['throttle_optimal']
    df['brake_delta'] = df['brake_input'] - df['brake_optimal']
    df['steering_delta'] = df['steering_angle'] - df['steering_optimal']
    
    df['throttle_error'] = df['throttle_delta'].abs()
    df['brake_error'] = df['brake_delta'].abs()
    df['steering_error'] = df['steering_delta'].abs()
    
    # Combined input efficiency (how close to optimal)
    df['input_efficiency'] = 1.0 - (
        0.4 * np.clip(df['throttle_error'], 0, 1) +
        0.4 * np.clip(df['brake_error'], 0, 1) +
        0.2 * np.clip(df['steering_error'] / 3, 0, 1)
    )
    
    # Generate suggestions
    df['throttle_suggestion'] = df['throttle_delta'].apply(
        lambda x: 'increase' if x < -0.2 else ('decrease' if x > 0.2 else 'maintain')
    )
    df['brake_suggestion'] = df['brake_delta'].apply(
        lambda x: 'increase' if x < -0.2 else ('decrease' if x > 0.2 else 'maintain')
    )
    df['steering_suggestion'] = df['steering_delta'].apply(
        lambda x: 'more' if x < -0.5 else ('less' if x > 0.5 else 'maintain')
    )
    
    return df


# ============================================================================
# PERFORMANCE TREND ANALYSIS
# ============================================================================

def analyze_performance_trends(
    df: pd.DataFrame,
    window: int = 50,
    segment_size: Optional[int] = None
) -> Dict:
    """
    Analyze performance trends over time/laps.
    
    Args:
        df: DataFrame with performance metrics
        window: Rolling window size for trend analysis
        segment_size: Optional segment size for lap-by-lap analysis
    
    Returns:
        Dict with trend metrics and insights
    """
    
    # Compute rolling metrics
    trends = {}
    
    metrics = ['stability_index', 'input_smoothness', 'wheel_slip_ratio', 
               'lateral_accel_g', 'jerk_magnitude', 'input_efficiency']
    
    for metric in metrics:
        if metric in df.columns:
            trends[f'{metric}_rolling_mean'] = df[metric].rolling(window=window, min_periods=1).mean()
            trends[f'{metric}_rolling_std'] = df[metric].rolling(window=window, min_periods=1).std()
            
            # Trend direction (improving vs degrading)
            rolling_mean = trends[f'{metric}_rolling_mean']
            if len(rolling_mean) > 1:
                trend_direction = rolling_mean.diff().fillna(0)
                trends[f'{metric}_trend'] = trend_direction.apply(
                    lambda x: 'improving' if x > 0 else ('degrading' if x < 0 else 'stable')
                )
    
    # Segment-wise analysis
    if segment_size and len(df) > segment_size:
        segments = []
        for i in range(0, len(df), segment_size):
            segment = df.iloc[i:i+segment_size]
            if len(segment) > 0:
                seg_metrics = {
                    'segment': i // segment_size,
                    'stability_avg': segment['stability_index'].mean() if 'stability_index' in segment.columns else 0,
                    'smoothness_avg': segment['input_smoothness'].mean() if 'input_smoothness' in segment.columns else 0,
                    'efficiency_avg': segment['input_efficiency'].mean() if 'input_efficiency' in segment.columns else 0,
                    'slip_avg': segment['wheel_slip_ratio'].mean() if 'wheel_slip_ratio' in segment.columns else 0,
                }
                segments.append(seg_metrics)
        
        trends['segment_analysis'] = pd.DataFrame(segments)
    
    # Overall trend detection
    if 'stability_index' in df.columns and len(df) > window * 2:
        early = df['stability_index'].iloc[:len(df)//2].mean()
        late = df['stability_index'].iloc[len(df)//2:].mean()
        overall_trend = 'improving' if late > early else 'degrading'
    else:
        overall_trend = 'stable'
    
    trends['overall_trend'] = overall_trend
    trends['improvement_opportunities'] = identify_improvement_areas(df)
    
    return trends


def identify_improvement_areas(df: pd.DataFrame) -> List[Dict]:
    """
    Identify specific areas for improvement.
    """
    improvements = []
    
    # High slip areas
    if 'wheel_slip_ratio' in df.columns:
        high_slip = df[df['wheel_slip_ratio'] > 0.3]
        if len(high_slip) > 0:
            improvements.append({
                'area': 'Traction Control',
                'issue': f'{len(high_slip)} points with high wheel slip',
                'suggestion': 'Reduce throttle application or increase tire pressure'
            })
    
    # High jerk areas
    if 'jerk_magnitude' in df.columns:
        high_jerk = df[df['jerk_magnitude'] > df['jerk_magnitude'].quantile(0.85)]
        if len(high_jerk) > 0:
            improvements.append({
                'area': 'Input Smoothness',
                'issue': f'{len(high_jerk)} sudden input changes',
                'suggestion': 'Smooth throttle/brake transitions; less snap steering'
            })
    
    # Low stability areas
    if 'stability_index' in df.columns:
        low_stability = df[df['stability_index'] < 0.5]
        if len(low_stability) > 0:
            improvements.append({
                'area': 'Vehicle Stability',
                'issue': f'{len(low_stability)} unstable points',
                'suggestion': 'Adjust suspension, brake balance, or driving line'
            })
    
    # High lateral acceleration
    if 'lateral_accel_g' in df.columns:
        high_lateral = df[df['lateral_accel_g'] > 1.2]
        if len(high_lateral) > 0:
            improvements.append({
                'area': 'Cornering Technique',
                'issue': f'{len(high_lateral)} high lateral loads',
                'suggestion': 'Reduce entry speed or improve mid-corner line'
            })
    
    return improvements


# ============================================================================
# COMBINED INDICES FOR REAL-TIME SCORING
# ============================================================================

def compute_combined_indices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute advanced combined indices for comprehensive vehicle assessment.
    """
    df = df.copy()
    
    # TRACTION INDEX (0-100): How much grip is maintained
    if 'wheel_slip_ratio' in df.columns and 'slip_balance' in df.columns:
        df['traction_index'] = (
            (1.0 - df['wheel_slip_ratio'].clip(0, 1)) * 0.6 +
            (1.0 - np.abs(df['slip_balance'] - 1.0).clip(0, 1)) * 0.4
        ) * 100
    else:
        df['traction_index'] = 50
    
    # CONTROL INDEX (0-100): How much driver is in control
    control_factors = []
    if 'input_smoothness' in df.columns:
        control_factors.append(df['input_smoothness'].clip(0, 1))
    if 'steering_smooth' in df.columns:
        # Smoother steering = more control
        steering_control = (1.0 - (df['steering_change'] / df['steering_change'].max()).clip(0, 1))
        control_factors.append(steering_control)
    if 'stability_index' in df.columns:
        control_factors.append(df['stability_index'])
    
    if control_factors:
        df['control_index'] = np.mean(control_factors, axis=0) * 100
    else:
        df['control_index'] = 50
    
    # AGGRESSION INDEX (0-100): How aggressive is the driving
    if 'input_aggression' in df.columns and 'lateral_accel_g' in df.columns:
        df['aggression_index'] = (
            (df['input_aggression'] / (df['input_aggression'].max() + 0.1)) * 0.5 +
            (df['lateral_accel_g'] / 3.0) * 0.5
        ) * 100
        df['aggression_index'] = df['aggression_index'].clip(0, 100)
    else:
        df['aggression_index'] = 0
    
    # EFFICIENCY INDEX (0-100): Fuel/energy efficiency (inverse of power use)
    if 'throttle_power' in df.columns and 'braking_power' in df.columns:
        max_power = max(
            df['throttle_power'].max() if df['throttle_power'].max() > 0 else 1,
            df['braking_power'].max() if df['braking_power'].max() > 0 else 1
        )
        df['efficiency_index'] = 100 * (1.0 - (
            (df['throttle_power'] / max_power * 0.6) + 
            (df['braking_power'] / max_power * 0.4)
        ).clip(0, 1))
    else:
        df['efficiency_index'] = 50
    
    # COMPOSITE PERFORMANCE SCORE (0-100)
    # Weight: Traction(25%), Control(35%), Efficiency(25%), Safety(15%)
    df['performance_score'] = (
        df['traction_index'] * 0.25 +
        df['control_index'] * 0.35 +
        df['efficiency_index'] * 0.25 +
        (100 - df['aggression_index']) * 0.15
    )
    
    # QUALITY RATING
    df['quality_rating'] = pd.cut(
        df['performance_score'],
        bins=[0, 40, 60, 75, 90, 100],
        labels=['Poor', 'Fair', 'Good', 'Excellent', 'Outstanding']
    )
    
    return df


# ============================================================================
# REAL-TIME VISUALIZATION OUTPUTS
# ============================================================================

def prepare_realtime_outputs(
    df: pd.DataFrame,
    include_predictions: bool = True
) -> pd.DataFrame:
    """
    Structure DataFrame for real-time visualization with per-timestep outputs.
    
    Returns minimal yet informative columns for plotting.
    """
    output_df = pd.DataFrame()
    
    # Time dimension
    if 'time_index' in df.columns:
        output_df['time'] = df['time_index']
    else:
        output_df['time'] = np.arange(len(df))
    
    # Core metrics
    core_metrics = [
        'speed', 'rpm', 'slip_angle', 'steering_abs',
        'stability_index', 'control_index', 'performance_score'
    ]
    for metric in core_metrics:
        if metric in df.columns:
            output_df[metric] = df[metric]
    
    # Real-time scoring
    scoring_metrics = [
        'traction_index', 'control_index', 'aggression_index', 
        'efficiency_index', 'input_efficiency', 'quality_rating'
    ]
    for metric in scoring_metrics:
        if metric in df.columns:
            output_df[metric] = df[metric]
    
    # Anomaly/critical flags
    output_df['is_anomaly'] = 0
    if 'wheel_slip_ratio' in df.columns:
        output_df.loc[df['wheel_slip_ratio'] > 0.4, 'is_anomaly'] = 1
    if 'jerk_magnitude' in df.columns:
        output_df.loc[df['jerk_magnitude'] > df['jerk_magnitude'].quantile(0.9), 'is_anomaly'] = 1
    if 'stability_index' in df.columns:
        output_df.loc[df['stability_index'] < 0.4, 'is_anomaly'] = 1
    
    # Add anomaly type
    output_df['anomaly_type'] = 'normal'
    if 'wheel_slip_ratio' in df.columns:
        output_df.loc[(df['wheel_slip_ratio'] > 0.4) & (df['throttle_input'] > 0.7), 'anomaly_type'] = 'wheel_spin'
    output_df.loc[(df['brake_input'] > 0.8) & (df['jerk_magnitude'] > df['jerk_magnitude'].quantile(0.9)), 'anomaly_type'] = 'harsh_braking'
    output_df.loc[df['stability_index'] < 0.3, 'anomaly_type'] = 'instability'
    
    # Optional: Predictions
    if include_predictions:
        prediction_metrics = [
            'throttle_optimal', 'brake_optimal', 'steering_optimal',
            'input_efficiency'
        ]
        for metric in prediction_metrics:
            if metric in df.columns:
                output_df[metric] = df[metric]
    
    return output_df


# ============================================================================
# FEATURE OPTIMIZATION & SELECTION
# ============================================================================

def get_feature_importance(
    df: pd.DataFrame,
    target_col: str = 'performance_score',
    n_features: int = 15
) -> pd.DataFrame:
    """
    Identify most important features using RandomForest.
    """
    from sklearn.ensemble import RandomForestRegressor
    
    # Select numeric columns
    feature_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    target_col = [t for t in df.columns if t == target_col and t in feature_cols]
    
    if not target_col or target_col[0] not in feature_cols:
        return pd.DataFrame()
    
    feature_cols = [col for col in feature_cols if col != target_col[0]]
    
    X = df[feature_cols].fillna(0)
    y = df[target_col[0]].fillna(y.mean() if 'y' in locals() else 50)
    
    # Train lightweight model
    model = RandomForestRegressor(n_estimators=50, max_depth=10, random_state=42)
    model.fit(X, y)
    
    # Get importances
    importances = pd.DataFrame({
        'feature': feature_cols,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    return importances.head(n_features)


def scale_features_for_ml(
    df: pd.DataFrame,
    feature_cols: List[str],
    method: str = 'standard',
    fit_df: Optional[pd.DataFrame] = None
) -> Tuple[pd.DataFrame, StandardScaler]:
    """
    Scale features for ML model input.
    
    Args:
        df: Input DataFrame
        feature_cols: Columns to scale
        method: 'standard' or 'minmax'
        fit_df: Optional DataFrame to fit scaler on
    
    Returns:
        Tuple of (scaled_df, scaler)
    """
    if method == 'standard':
        scaler = StandardScaler()
    else:
        scaler = MinMaxScaler()
    
    fit_on = fit_df if fit_df is not None else df
    scaler.fit(fit_on[feature_cols].fillna(0))
    
    df_scaled = df.copy()
    df_scaled[feature_cols] = scaler.transform(df[feature_cols].fillna(0))
    
    return df_scaled, scaler

