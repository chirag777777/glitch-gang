"""
Quick-start examples for using ML modules in the telemetry app
Shows code snippets for integration into existing app.py
"""

import pandas as pd
import numpy as np
from ml_module import run_ml_pipeline, engineer_advanced_features
from ml_integration import (
    enrich_analysis_with_ml,
    analyze_turn_with_ml,
    generate_driver_profile,
    generate_ml_based_suspension_recommendations,
    identify_critical_sections,
    generate_improvement_roadmap
)


# ============================================================================
# EXAMPLE 1: Add ML to existing analysis bundle
# ============================================================================

def example_integrate_ml_with_existing_app(df: pd.DataFrame, existing_bundle: dict) -> dict:
    """
    How to integrate ML results into existing AnalysisBundle
    
    Usage in app.py:
        enhanced_bundle = example_integrate_ml_with_existing_app(df, bundle)
    """
    # Run ML pipeline on full dataset
    ml_results = run_ml_pipeline(df)
    
    # Merge with existing scores
    enhanced_bundle = existing_bundle.copy()
    enhanced_bundle['ml_scores'] = ml_results['ml_scores']
    enhanced_bundle['ml_df'] = ml_results['df']
    enhanced_bundle['ml_insights'] = ml_results['ml_insights']
    enhanced_bundle['ml_models'] = {
        'quality_model': ml_results['quality_model'],
        'kmeans_model': ml_results['kmeans_model']
    }
    enhanced_bundle['feature_importance'] = ml_results['feature_importance']
    enhanced_bundle['clusters'] = ml_results['clusters']
    enhanced_bundle['anomalies'] = ml_results['anomalies']
    
    return enhanced_bundle


# ============================================================================
# EXAMPLE 2: Display ML-Enhanced Metrics in Streamlit
# ============================================================================

def example_render_ml_metrics_dashboard(st_module, bundle: dict) -> None:
    """
    How to render ML metrics in Streamlit dashboard
    
    Usage in app.py:
        example_render_ml_metrics_dashboard(st, bundle)
    """
    import streamlit as st
    
    # ML Scores
    st.subheader("🤖 ML-Powered Analysis")
    
    ml_cols = st.columns(2)
    with ml_cols[0]:
        st.metric(
            "ML Framework Score",
            f"{bundle['ml_scores']['ml_score']:.1f}/100",
            delta="ML Model"
        )
        st.caption("Quality + Stability + Consistency (ML-weighted)")
    
    with ml_cols[1]:
        st.metric(
            "Anomaly-Free Performance",
            f"{bundle['ml_scores']['normal_ratio']:.1f}%",
            delta=f"{100 - bundle['ml_scores']['normal_ratio']:.1f}% anomalies"
        )
    
    # Feature importance
    with st.expander("📊 Feature Importance (What Matters Most)"):
        importance_df = pd.DataFrame(
            list(bundle['feature_importance'].items()),
            columns=['Feature', 'Importance']
        ).sort_values('Importance', ascending=True).tail(8)
        
        st.bar_chart(importance_df.set_index('Feature')['Importance'])
    
    # Driving style
    style_map = {v: k for k, v in enumerate(bundle['ml_scores'])}
    st.write(f"**Driving Style:** {bundle.get('dominant_style', 'Mixed')}")


# ============================================================================
# EXAMPLE 3: Enhanced Turn-by-turn Analysis with ML
# ============================================================================

def example_ml_enhanced_turn_analysis(df: pd.DataFrame, 
                                      turn_summary: pd.DataFrame,
                                      bundle: dict) -> pd.DataFrame:
    """
    Add ML insights to turn summary table
    
    Usage in app.py:
        enhanced_turn_summary = example_ml_enhanced_turn_analysis(df, bundle.turn_summary, bundle)
    """
    enhanced_summary = turn_summary.copy()
    
    ml_insights = []
    
    for idx, row in turn_summary.iterrows():
        turn_start = row['Distance start (m)']
        turn_end = row['Distance end (m)']
        
        # Get turn data
        turn_mask = (bundle['ml_df']['distance_traveled'] >= turn_start) & \
                    (bundle['ml_df']['distance_traveled'] <= turn_end)
        turn_data = bundle['ml_df'][turn_mask]
        
        if len(turn_data) > 0:
            # ML analysis
            quality_score = turn_data['quality_pred'].mean() * 100
            anomalies_in_turn = (turn_data['anomaly'] == -1).sum()
            
            # Generate insight
            if anomalies_in_turn > 0:
                insight = f"⚠️ {anomalies_in_turn} anomalies"
            elif quality_score < 50:
                insight = "🔴 Low quality"
            elif quality_score >= 80:
                insight = "✅ Good quality"
            else:
                insight = "⚡ Fair quality"
            
            ml_insights.append(insight)
        else:
            ml_insights.append("N/A")
    
    enhanced_summary['ML Insight'] = ml_insights
    return enhanced_summary


# ============================================================================
# EXAMPLE 4: Driver Profile Report
# ============================================================================

def example_generate_driver_report(st_module, bundle: dict) -> None:
    """
    Generate comprehensive driver profile report
    
    Usage in app.py:
        example_generate_driver_report(st, bundle)
    """
    import streamlit as st
    
    profile = generate_driver_profile(bundle['ml_df'], {
        'clusters': bundle['clusters'],
        'cluster_names': bundle.get('cluster_names', {}),
        'quality_predictions': bundle['ml_df']['quality_pred'],
        'feature_importance': bundle['feature_importance'],
        'ml_scores': bundle['ml_scores']
    })
    
    st.header("👤 Driver Profile")
    
    # Summary
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Driving Style", profile['dominant_style'])
    col2.metric("Consistency", f"{profile['quality_consistency']:.0f}%")
    col3.metric("Stability", f"{profile['stability_rating']:.0f}/100")
    col4.metric("Smoothness", f"{profile['smoothness_rating']:.0f}/100")
    
    # Strengths
    st.subheader("💪 Strengths")
    for strength in profile['key_strengths']:
        st.write(f"✅ Strong **{strength}** management")
    
    # Areas for improvement
    st.subheader("🎯 Areas for Improvement")
    for weakness in profile['areas_for_improvement']:
        st.write(f"📈 Focus on **{weakness}**")


# ============================================================================
# EXAMPLE 5: Critical Sections Alert
# ============================================================================

def example_show_critical_sections(st_module, bundle: dict) -> None:
    """
    Display critical sections that need attention
    
    Usage in app.py:
        example_show_critical_sections(st, bundle)
    """
    import streamlit as st
    
    critical_sections = identify_critical_sections(
        bundle['ml_df'],
        {
            'anomalies': bundle['anomalies'],
            'quality_predictions': bundle['ml_df']['quality_pred']
        }
    )
    
    if critical_sections:
        st.warning("🚨 Critical Sections Detected")
        
        for i, section in enumerate(critical_sections, 1):
            col1, col2, col3 = st.columns([2, 1, 1])
            
            with col1:
                st.write(f"**{i}. {section['type']} ({section['start_distance']:.0f}-{section['end_distance']:.0f}m)**")
                st.caption(section['recommendation'])
            
            with col2:
                severity_pct = int(section['severity'] * 100)
                st.write(f"Severity: {severity_pct}%")
            
            with col3:
                st.write(f"Length: {section['length']:.0f}m")


# ============================================================================
# EXAMPLE 6: ML-Based Suspension Recommendations
# ============================================================================

def example_ml_suspension_recommendations(st_module, bundle: dict) -> None:
    """
    Display suspension recommendations derived from ML analysis
    
    Usage in app.py:
        example_ml_suspension_recommendations(st, bundle)
    """
    import streamlit as st
    
    recommendations = generate_ml_based_suspension_recommendations({
        'df': bundle['ml_df'],
        'ml_scores': bundle['ml_scores'],
        'ml_insights': bundle['ml_insights'],
        'clusters': bundle['clusters']
    })
    
    st.subheader("⚙️ ML-Derived Suspension Tuning")
    
    for component, changes in recommendations.items():
        with st.expander(f"🔧 {component.replace('_', ' ').title()}"):
            for change in changes:
                st.write(f"• {change}")


# ============================================================================
# EXAMPLE 7: Improvement Roadmap
# ============================================================================

def example_show_improvement_roadmap(st_module, bundle: dict) -> None:
    """
    Display personalized improvement roadmap
    
    Usage in app.py:
        example_show_improvement_roadmap(st, bundle)
    """
    import streamlit as st
    
    roadmap = generate_improvement_roadmap(bundle['ml_df'], {
        'ml_scores': bundle['ml_scores'],
        'feature_importance': bundle['feature_importance'],
        'ml_insights': bundle['ml_insights'],
        'anomalies': bundle['anomalies'],
        'clusters': bundle['clusters']
    })
    
    st.header("🗺️ Improvement Roadmap")
    
    # Current performance
    st.subheader("📊 Current Performance")
    perf_cols = st.columns(4)
    perf_cols[0].metric("Overall", f"{roadmap['current_performance']['overall_score']:.0f}")
    perf_cols[1].metric("Stability", f"{roadmap['current_performance']['stability']:.0f}")
    perf_cols[2].metric("Smoothness", f"{roadmap['current_performance']['smoothness']:.0f}")
    perf_cols[3].metric("Control", f"{roadmap['current_performance']['control']:.0f}")
    
    # Top priorities
    if roadmap['top_priorities']:
        st.subheader("🔴 Top Priorities")
        for i, priority in enumerate(roadmap['top_priorities'], 1):
            st.write(f"**{i}. {priority['action']}**")
            st.caption(f"{priority['why']} → +{priority['expected_gain']} pts")
    
    # Medium term
    if roadmap['medium_priorities']:
        st.subheader("🟡 Medium Term")
        for priority in roadmap['medium_priorities']:
            st.write(f"• {priority['action']}")
    
    # Long term
    st.subheader("🟢 Long Term Goal")
    for goal in roadmap['long_term_goals']:
        st.write(f"**{goal['action']}**")
        st.caption(goal['current_status'])


# ============================================================================
# EXAMPLE 8: Add ML features to AnalysisBundle creation
# ============================================================================

def example_enhanced_analysis_bundle_creation(df: pd.DataFrame) -> dict:
    """
    Complete example of creating bundle with ML integration
    
    Usage in app.py (in main function where AnalysisBundle would be created):
        bundle = example_enhanced_analysis_bundle_creation(df)
    """
    # Step 1: Engineer advanced features
    df_engineered = engineer_advanced_features(df)
    
    # Step 2: Run full ML pipeline
    ml_results = run_ml_pipeline(df_engineered)
    
    # Step 3: Create enhanced bundle
    bundle = {
        'df': df_engineered,
        'ml_results': ml_results,
        'ml_df': ml_results['df'],
        'ml_scores': ml_results['ml_scores'],
        'ml_insights': ml_results['ml_insights'],
        'anomalies': ml_results['anomalies'],
        'clusters': ml_results['clusters'],
        'cluster_names': ml_results['cluster_names'],
        'quality_model': ml_results['quality_model'],
        'feature_importance': ml_results['feature_importance'],
        'critical_sections': identify_critical_sections(ml_results['df'], ml_results),
        'improvement_roadmap': generate_improvement_roadmap(ml_results['df'], ml_results)
    }
    
    return bundle


# ============================================================================
# EXAMPLE 9: Minimal integration - Just add ML score to existing metrics
# ============================================================================

def example_minimal_ml_integration(scores: dict, ml_results: dict) -> dict:
    """
    Simplest approach: just add ML score to existing scores dict
    
    Usage in app.py (minimal change):
        scores = compute_scores(df)
        ml_results = run_ml_pipeline(df)
        scores = example_minimal_ml_integration(scores, ml_results)
    """
    scores['ml_score'] = ml_results['ml_scores']['ml_score']
    scores['anomaly_free_ratio'] = ml_results['ml_scores']['normal_ratio']
    scores['ml_stability'] = ml_results['ml_scores']['stability_score']
    
    # Update overall grade consideration
    if scores.get('consistency_score', 0) > 0:
        # Blend with ML score
        scores['combined_grade'] = (scores['consistency_score'] * 0.4 + scores['ml_score'] * 0.6)
    
    return scores


if __name__ == "__main__":
    print("ML Integration Examples - Ready to use in app.py")
    print("\nKey functions to integrate:")
    print("1. example_enhanced_analysis_bundle_creation() - Complete ML pipeline")
    print("2. example_render_ml_metrics_dashboard() - Display metrics")
    print("3. example_generate_driver_report() - Driver profile")
    print("4. example_show_critical_sections() - Alert system")
    print("5. example_ml_suspension_recommendations() - Tuning advice")
    print("6. example_show_improvement_roadmap() - Personalized roadmap")
