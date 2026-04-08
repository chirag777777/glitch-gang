"""
ML Integration utilities for the telemetry analysis app
Shows how to integrate ML pipeline results into existing analysis
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from ml_module import (
    engineer_advanced_features,
    detect_anomalies,
    cluster_driving_styles,
    interpret_clusters,
    train_driving_quality_model,
    predict_driving_quality,
    compute_ml_scores,
    generate_ml_insights,
    run_ml_pipeline
)


# ============================================================================
# INTEGRATION HELPER: Add ML Results to Existing Bundle
# ============================================================================

def enrich_analysis_with_ml(df: pd.DataFrame, existing_scores: Dict) -> Dict:
    """
    Enhance existing telemetry analysis with ML results
    
    Args:
        df: DataFrame with engineered features already computed
        existing_scores: Previous scores from traditional analysis
    
    Returns:
        Enhanced scores dict combining traditional + ML metrics
    """
    # Run ML pipeline
    ml_results = run_ml_pipeline(df)
    
    # Merge scores
    enhanced_scores = existing_scores.copy()
    enhanced_scores.update(ml_results['ml_scores'])
    
    return {
        'scores': enhanced_scores,
        'ml_results': ml_results,
        'df_enriched': ml_results['df']
    }


# ============================================================================
# ADVANCED TURN ANALYSIS USING ML
# ============================================================================

def analyze_turn_with_ml(df: pd.DataFrame, turn_data: pd.DataFrame, 
                         quality_model, kmeans_model) -> Dict:
    """
    Analyze a single turn using ML context
    
    Args:
        df: Full lap DataFrame with ML features
        turn_data: DataFrame subset for one turn
        quality_model: Trained quality classifier
        kmeans_model: Trained clustering model
    
    Returns:
        Dict with turn-specific ML insights
    """
    from sklearn.preprocessing import StandardScaler
    
    analysis = {
        'turn_quality': turn_data['quality_pred'].mean(),
        'turn_stability': turn_data['stability_index'].mean(),
        'turn_smoothness': 100 - (turn_data['input_change'].mean() * 100),
        'anomaly_count': (turn_data['anomaly'] == -1).sum(),
        'max_slip': turn_data['slip_severity'].max(),
        'max_lateral_g': turn_data['lateral_accel_g'].max()
    }
    
    # Identify issues
    issues = []
    if analysis['max_slip'] > 3:
        issues.append('High slip angle - reduce entry speed or improve line')
    if analysis['turn_stability'] > 50:
        issues.append('Instability - check brake balance and suspension')
    if analysis['turn_smoothness'] < 40:
        issues.append('Jerky inputs - smoother steering and pedal transitions')
    if analysis['anomaly_count'] > 0:
        issues.append('Unusual dynamics - review suspension or tire condition')
    
    analysis['issues'] = issues
    
    # Recommendation based on ML
    if len(issues) == 0:
        analysis['recommendation'] = 'Excellent turn - maintain consistency'
    elif len(issues) == 1:
        analysis['recommendation'] = f'Focus on: {issues[0]}'
    else:
        analysis['recommendation'] = 'Multiple issues - prioritize brake and entry speed adjustments'
    
    return analysis


# ============================================================================
# DRIVER PROFILE GENERATION
# ============================================================================

def generate_driver_profile(df: pd.DataFrame, ml_results: Dict) -> Dict:
    """
    Create comprehensive driver profile from ML analysis
    
    Args:
        df: Full telemetry DataFrame
        ml_results: Output from run_ml_pipeline()
    
    Returns:
        Dict describing driver characteristics
    """
    clusters = ml_results['clusters']
    cluster_names = ml_results['cluster_names']
    quality_preds = ml_results['quality_predictions']
    feature_importance = ml_results['feature_importance']
    ml_scores = ml_results['ml_scores']
    
    # Dominant style
    dominant_style = cluster_names.get(
        clusters.mode()[0],
        'Mixed'
    )
    
    # Quality consistency
    quality_ratio = (quality_preds == 1).sum() / len(quality_preds) * 100
    
    # Key strengths and weaknesses
    sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
    top_strengths = sorted_features[:3]
    top_weaknesses = sorted_features[-3:]
    
    profile = {
        'dominant_style': dominant_style,
        'quality_consistency': quality_ratio,
        'stability_rating': ml_scores['stability_score'],
        'smoothness_rating': ml_scores['smoothness_score'],
        'control_rating': ml_scores['control_score'],
        'overall_ml_score': ml_scores['ml_score'],
        'key_strengths': [f[0] for f in top_strengths if f[1] > 0.1],
        'areas_for_improvement': [f[0] for f in top_weaknesses if f[1] < 0.05],
        'anomaly_rate': (1 - ml_scores['normal_ratio'] / 100) * 100,
        'driving_consistency': 100 - (clusters.value_counts().max() / len(clusters) * 100)
    }
    
    return profile


# ============================================================================
# SUSPENSION RECOMMENDATIONS USING ML
# ============================================================================

def generate_ml_based_suspension_recommendations(ml_results: Dict) -> Dict[str, List[str]]:
    """
    Generate suspension tuning suggestions based on ML-identified problems
    
    Args:
        ml_results: Output from run_ml_pipeline()
    
    Returns:
        Dict with suspension adjustment recommendations by component
    """
    df = ml_results['df']
    ml_scores = ml_results['ml_scores']
    ml_insights = ml_results['ml_insights']
    clusters = ml_results['clusters']
    
    recommendations = {
        'spring_stiffness': [],
        'damping': [],
        'anti_roll_bar': [],
        'alignment': [],
        'brake_bias': []
    }
    
    # Analyze patterns
    avg_stability = ml_scores['stability_score']
    avg_smoothness = ml_scores['smoothness_score']
    slip_severity = df['slip_severity'].mean()
    
    # Spring recommendations
    if avg_stability < 50:
        recommendations['spring_stiffness'].append('Increase front spring stiffness +8%')
        recommendations['spring_stiffness'].append('Consider rear spring +5% for balance')
    elif avg_stability > 70 and slip_severity > 2:
        recommendations['spring_stiffness'].append('Soften front springs -5% for compliance')
    
    # Damping recommendations
    if 'input_change' in df.columns and df['input_change'].std() > 0.4:
        recommendations['damping'].append('Increase bump stop damping +15%')
        recommendations['damping'].append('Increase rebound damping +10%')
    
    # ARB recommendations
    if slip_severity > 2.5:
        recommendations['anti_roll_bar'].append('Increase rear ARB +20%')
        recommendations['anti_roll_bar'].append('Consider front ARB +10%')
    elif avg_smoothness < 40:
        recommendations['anti_roll_bar'].append('Soften ARB -15% for smoother transitions')
    
    # Alignment
    if df['wheel_slip_ratio'].mean() > 1.3:
        recommendations['alignment'].append('Increase front toe-in +0.10° (understeer tendency)')
        recommendations['alignment'].append('Check front camber, consider -0.3° adjustment')
    elif df['wheel_slip_ratio'].mean() < 0.8:
        recommendations['alignment'].append('Reduce front toe-in -0.05° (oversteer tendency)')
    
    # Brake bias
    if df['brake_change'].mean() > 0.3:
        recommendations['brake_bias'].append('Adjust bias +0.5% toward front (smoother modulation)')
    
    return {k: v for k, v in recommendations.items() if v}


# ============================================================================
# PREDICTIVE ALERTS
# ============================================================================

def identify_critical_sections(df: pd.DataFrame, ml_results: Dict, threshold: float = 0.7) -> List[Dict]:
    """
    Identify critical sections where driver needs immediate attention
    
    Args:
        df: DataFrame with distance markers
        ml_results: ML pipeline output
        threshold: Anomaly severity threshold (0-1)
    
    Returns:
        List of critical sections with distance markers
    """
    anomalies = ml_results['anomalies']
    quality_preds = ml_results['quality_predictions']
    
    critical_sections = []
    
    # Find sustained quality dips
    quality_dips = quality_preds == 0
    if quality_dips.sum() > 0:
        # Group consecutive dips
        dip_groups = (quality_dips != quality_dips.shift()).cumsum()
        
        for group_id in dip_groups[quality_dips].unique():
            section = df[dip_groups == group_id]
            if len(section) > 2:  # Sustained issue
                start_dist = section['distance_traveled'].min() if 'distance_traveled' in section.columns else section.index.min()
                end_dist = section['distance_traveled'].max() if 'distance_traveled' in section.columns else section.index.max()
                
                severity = 1 - section['quality_pred'].mean()
                
                critical_sections.append({
                    'type': 'QUALITY_DIP',
                    'start_distance': start_dist,
                    'end_distance': end_dist,
                    'severity': severity,
                    'length': end_dist - start_dist,
                    'recommendation': 'Review line and inputs in this section'
                })
    
    # Anomaly zones
    anomaly_points = anomalies == -1
    if anomaly_points.sum() > 0:
        anomaly_groups = (anomaly_points != anomaly_points.shift()).cumsum()
        
        for group_id in anomaly_groups[anomaly_points].unique():
            section = df[anomaly_groups == group_id]
            if len(section) > 1:
                start_dist = section['distance_traveled'].min() if 'distance_traveled' in section.columns else section.index.min()
                end_dist = section['distance_traveled'].max() if 'distance_traveled' in section.columns else section.index.max()
                
                severity = section['stability_index'].max() / 100
                
                critical_sections.append({
                    'type': 'ANOMALY_ZONE',
                    'start_distance': start_dist,
                    'end_distance': end_dist,
                    'severity': severity,
                    'length': end_dist - start_dist,
                    'recommendation': 'Check suspension setup and tire condition'
                })
    
    return sorted(critical_sections, key=lambda x: x['severity'], reverse=True)[:5]


# ============================================================================
# COMPARISON: Current vs. Optimal Performance
# ============================================================================

def generate_improvement_roadmap(df: pd.DataFrame, ml_results: Dict) -> Dict:
    """
    Generate actionable improvement roadmap based on ML analysis
    
    Args:
        df: Full telemetry DataFrame
        ml_results: ML pipeline output
    
    Returns:
        Dict with prioritized improvements
    """
    ml_scores = ml_results['ml_scores']
    feature_importance = ml_results['feature_importance']
    ml_insights = ml_results['ml_insights']
    
    roadmap = {
        'current_performance': {
            'overall_score': ml_scores['ml_score'],
            'stability': ml_scores['stability_score'],
            'smoothness': ml_scores['smoothness_score'],
            'control': ml_scores['control_score']
        },
        'top_priorities': [],
        'medium_priorities': [],
        'long_term_goals': []
    }
    
    # Identify top issues from insights
    critical_issues = [i for i in ml_insights if i.get('type') == 'ANOMALY']
    quality_issues = [i for i in ml_insights if i.get('type') == 'QUALITY_DIP']
    
    # Priority 1: Fix major anomalies
    if critical_issues:
        roadmap['top_priorities'].append({
            'action': 'Diagnose and fix anomalies',
            'why': f'{len(critical_issues)} anomalies detected - review suspension/tires',
            'expected_gain': 10
        })
    
    # Priority 2: Improve smoothness if low
    if ml_scores['smoothness_score'] < 60:
        roadmap['top_priorities'].append({
            'action': 'Smooth input transitions',
            'why': 'Jerky pedal/steering inputs reducing control',
            'expected_gain': 8
        })
    
    # Priority 3: Stability improvements
    if ml_scores['stability_score'] < 60:
        roadmap['top_priorities'].append({
            'action': 'Increase vehicle balance',
            'why': 'Instability causing loss of control',
            'expected_gain': 12
        })
    
    # Medium term
    if len(quality_issues) > 0:
        roadmap['medium_priorities'].append({
            'action': 'Identify quality dip sections',
            'why': f'{len(quality_issues)} sections with poor performance',
            'expected_gain': 5
        })
    
    # Long term
    roadmap['long_term_goals'].append({
        'action': 'Target: 85+ ML score with <2% anomalies',
        'why': 'Achieve consistent, professional-level performance',
        'current_status': f"Current: {ml_scores['ml_score']:.0f}"
    })
    
    return roadmap
