"""
ML Pipeline Orchestration & Integration Examples
Shows how to use ml_advanced module with full telemetry dataset
"""

import pandas as pd
import numpy as np
from ml_advanced import (
    engineer_advanced_features,
    build_input_prediction_models,
    predict_optimal_inputs,
    analyze_performance_trends,
    compute_combined_indices,
    prepare_realtime_outputs,
    get_feature_importance,
    scale_features_for_ml
)


def complete_ml_pipeline(df: pd.DataFrame) -> dict:
    """
    Execute complete ML pipeline for full telemetry analysis.
    
    Args:
        df: Raw telemetry DataFrame with columns:
            speed, throttle_input, brake_input, steering_angle,
            combined_slip_angle, yaw_moment, pitch, roll, rpm, gear,
            wheel_speed_fl, wheel_speed_fr, wheel_speed_rl, wheel_speed_rr
    
    Returns:
        Comprehensive results dict with all analysis outputs
    """
    
    # Step 1: Feature Engineering
    print("1. Engineering advanced features...")
    df_features = engineer_advanced_features(df)
    
    # Step 2: Build optimal input prediction models
    print("2. Training optimal input prediction models...")
    input_models = build_input_prediction_models(df_features)
    print(f"   - Throttle R²: {input_models['scores']['throttle_r2']:.3f}")
    print(f"   - Brake R²: {input_models['scores']['brake_r2']:.3f}")
    print(f"   - Steering R²: {input_models['scores']['steering_r2']:.3f}")
    
    # Step 3: Predict optimal inputs
    print("3. Predicting optimal inputs...")
    df_predictions = predict_optimal_inputs(df_features, input_models)
    
    # Step 4: Analyze performance trends
    print("4. Analyzing performance trends...")
    trends = analyze_performance_trends(df_predictions, window=50, segment_size=100)
    print(f"   - Overall trend: {trends['overall_trend']}")
    print(f"   - Improvement areas: {len(trends['improvement_opportunities'])}")
    
    # Step 5: Compute combined indices
    print("5. Computing combined indices...")
    df_scored = compute_combined_indices(df_predictions)
    
    # Step 6: Prepare real-time outputs
    print("6. Preparing real-time visualization outputs...")
    df_realtime = prepare_realtime_outputs(df_scored, include_predictions=True)
    
    # Step 7: Feature importance analysis
    print("7. Computing feature importance...")
    feature_importance = get_feature_importance(df_scored, 'performance_score', n_features=15)
    
    return {
        'df_full': df_scored,
        'df_realtime': df_realtime,
        'input_models': input_models,
        'trends': trends,
        'feature_importance': feature_importance,
        'summary': {
            'avg_performance': df_scored['performance_score'].mean(),
            'avg_stability': df_scored['stability_index'].mean() if 'stability_index' in df_scored.columns else None,
            'avg_efficiency': df_scored['input_efficiency'].mean() if 'input_efficiency' in df_scored.columns else None,
            'optimal_input_agreement': {
                'throttle': (1 - df_scored['throttle_error'].mean()).clip(0, 1) * 100,
                'brake': (1 - df_scored['brake_error'].mean()).clip(0, 1) * 100,
                'steering': (1 - (df_scored['steering_error'] / 3).clip(0, 1).mean()) * 100,
            }
        }
    }


def batch_segment_analysis(df: pd.DataFrame, segment_size: int = 500) -> list:
    """
    Analyze performance across multiple segments (laps/sections).
    
    Returns:
        List of segment-level performance summaries
    """
    segments = []
    
    for i in range(0, len(df), segment_size):
        segment = df.iloc[i:i+segment_size]
        
        if len(segment) < 10:
            continue
        
        segment_result = {
            'segment_id': len(segments),
            'start_idx': i,
            'end_idx': min(i + segment_size, len(df)),
            'length': len(segment),
            'metrics': {}
        }
        
        # Aggregate metrics
        for col in ['performance_score', 'stability_index', 'control_index', 
                    'traction_index', 'efficiency_index', 'input_efficiency']:
            if col in segment.columns:
                segment_result['metrics'][col] = {
                    'mean': segment[col].mean(),
                    'std': segment[col].std(),
                    'min': segment[col].min(),
                    'max': segment[col].max()
                }
        
        # Anomaly count
        segment_result['anomalies'] = int(segment['is_anomaly'].sum()) if 'is_anomaly' in segment.columns else 0
        
        segments.append(segment_result)
    
    return segments


def compare_driver_performance(df_driver1: pd.DataFrame, df_driver2: pd.DataFrame) -> dict:
    """
    Compare performance metrics between two drivers.
    """
    
    def get_summary(df):
        return {
            'performance_score': df['performance_score'].mean() if 'performance_score' in df.columns else None,
            'stability': df['stability_index'].mean() if 'stability_index' in df.columns else None,
            'control': df['control_index'].mean() if 'control_index' in df.columns else None,
            'efficiency': df['efficiency_index'].mean() if 'efficiency_index' in df.columns else None,
            'aggression': df['aggression_index'].mean() if 'aggression_index' in df.columns else None,
            'anomalies': int(df['is_anomaly'].sum()) if 'is_anomaly' in df.columns else 0
        }
    
    summary1 = get_summary(df_driver1)
    summary2 = get_summary(df_driver2)
    
    comparison = {}
    for key in summary1:
        if summary1[key] is not None and summary2[key] is not None:
            diff = summary2[key] - summary1[key]
            pct_change = (diff / summary1[key] * 100) if summary1[key] != 0 else 0
            comparison[key] = {
                'driver1': summary1[key],
                'driver2': summary2[key],
                'difference': diff,
                'percent_change': pct_change,
                'winner': 'driver2' if (key != 'anomalies' and diff > 0) or (key == 'anomalies' and diff < 0) else 'driver1'
            }
    
    return comparison


def detect_critical_segments(df: pd.DataFrame, anomaly_threshold: float = 0.3) -> list:
    """
    Identify critical segments requiring attention.
    
    Returns list of critical segments with context
    """
    critical = []
    
    # Low stability
    if 'stability_index' in df.columns:
        low_stability = df[df['stability_index'] < (1 - anomaly_threshold)]
        if len(low_stability) > 0:
            critical.append({
                'type': 'low_stability',
                'count': len(low_stability),
                'severity': 'high' if len(low_stability) > len(df) * 0.1 else 'medium',
                'indices': low_stability.index.tolist()[:10],
                'recommendation': 'Improve suspension settings or driving technique'
            })
    
    # High wheel slip
    if 'wheel_slip_ratio' in df.columns:
        high_slip = df[df['wheel_slip_ratio'] > 0.4]
        if len(high_slip) > 0:
            critical.append({
                'type': 'wheel_spin',
                'count': len(high_slip),
                'severity': 'high' if len(high_slip) > len(df) * 0.05 else 'medium',
                'indices': high_slip.index.tolist()[:10],
                'recommendation': 'Reduce throttle aggression or adjust tire pressure'
            })
    
    # High jerk/jerky inputs
    if 'jerk_magnitude' in df.columns:
        jerk_threshold = df['jerk_magnitude'].quantile(0.9)
        high_jerk = df[df['jerk_magnitude'] > jerk_threshold]
        if len(high_jerk) > 0:
            critical.append({
                'type': 'jerky_inputs',
                'count': len(high_jerk),
                'severity': 'medium',
                'indices': high_jerk.index.tolist()[:10],
                'recommendation': 'Smooth throttle/brake transitions and steering inputs'
            })
    
    return critical


def generate_driver_profile(df: pd.DataFrame) -> dict:
    """
    Generate comprehensive driver profile from telemetry.
    """
    profile = {
        'driving_style': '',
        'strengths': [],
        'weaknesses': [],
        'rating': '',
        'recommendations': []
    }
    
    # Determine style based on aggression
    if 'aggression_index' in df.columns:
        agg_avg = df['aggression_index'].mean()
        if agg_avg > 70:
            profile['driving_style'] = 'Aggressive'
        elif agg_avg > 40:
            profile['driving_style'] = 'Balanced'
        else:
            profile['driving_style'] = 'Conservative'
    
    # Identify strengths
    if 'efficiency_index' in df.columns and df['efficiency_index'].mean() > 70:
        profile['strengths'].append('High efficiency and smooth throttle control')
    if 'control_index' in df.columns and df['control_index'].mean() > 75:
        profile['strengths'].append('Excellent vehicle control')
    if 'traction_index' in df.columns and df['traction_index'].mean() > 80:
        profile['strengths'].append('Good traction management')
    
    # Identify weaknesses
    if 'stability_index' in df.columns and df['stability_index'].mean() < 0.6:
        profile['weaknesses'].append('Stability issues - needs suspension/brake tuning')
    if 'input_smoothness' in df.columns and df['input_smoothness'].mean() < 50:
        profile['weaknesses'].append('Jerky inputs - needs smoother transitions')
    
    # Overall rating
    if 'performance_score' in df.columns:
        score = df['performance_score'].mean()
        if score > 80:
            profile['rating'] = 'Expert'
        elif score > 70:
            profile['rating'] = 'Advanced'
        elif score > 55:
            profile['rating'] = 'Intermediate'
        else:
            profile['rating'] = 'Beginner'
    
    # Recommendations
    profile['recommendations'] = [
        'Focus on ' + profile['weaknesses'][0] if profile['weaknesses'] else 'Maintain current technique',
        'Leverage ' + profile['strengths'][0] if profile['strengths'] else 'Steady improvement',
    ]
    
    return profile
