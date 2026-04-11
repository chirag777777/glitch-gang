"""
Enhanced Racing Telemetry Dashboard v3.0 - With Advanced ML, Racing UI, and Premium Features
"""

import streamlit as st
import pandas as pd
import numpy as np
from typing import Optional, Dict, List, Tuple
import sys
import os

# Add to path
sys.path.insert(0, os.path.dirname(__file__))

# Import all new modules
try:
    from ml_advanced_v2 import (
        engineer_advanced_features_v2,
        classify_driver_style,
        detect_anomalies_advanced,
        predict_upcoming_events,
        compute_realtime_metrics,
        cluster_performance_zones,
        benchmark_against_reference,
        generate_driver_embedding,
        compute_performance_index
    )
    ML_V2_AVAILABLE = True
except ImportError:
    ML_V2_AVAILABLE = False

try:
    from racing_ui import (
        create_speedometer,
        create_rpm_gauge,
        create_g_force_meter,
        create_track_map,
        create_driver_rating_card,
        create_corner_heatmap,
        create_telemetry_dashboard,
        create_lap_delta_graph,
        create_driver_style_radar,
        create_performance_timeline,
        create_antigravity_track_map,
        create_car_performance_track,
        create_g_force_map
    )
    RACING_UI_AVAILABLE = True
except ImportError:
    RACING_UI_AVAILABLE = False

try:
    from premium_features import (
        predict_lap_time,
        analyze_braking_points,
        analyze_acceleration_zones,
        analyze_consistency,
        analyze_sector_performance,
        benchmark_performance,
        generate_driver_profile,
        generate_recommendations,
        DriverProfile
    )
    PREMIUM_AVAILABLE = True
except ImportError:
    PREMIUM_AVAILABLE = False

# Import original modules
try:
    from app import (
        clean_telemetry_data,
        engineer_features,
        compute_thresholds,
        add_zone_columns,
        detect_events,
        build_stats,
        compute_scores,
        classify_grade,
        build_turn_summary,
        generate_insights,
        count_segments,
        AnalysisBundle
    )
    ORIGINAL_AVAILABLE = True
except ImportError:
    ORIGINAL_AVAILABLE = False


# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="🏎️ Racing Telemetry v3.0",
    page_icon="🏁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for racing theme
st.markdown("""
    <style>
        * {
            color: #ffffff;
            font-family: 'Arial', sans-serif;
        }
        
        .main {
            background-color: #0a0e27;
            color: #ffffff;
        }
        
        .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
            font-size: 1.2rem;
            color: #ff6b6b;
        }
        
        .metric-card {
            background: linear-gradient(135deg, #1a1f3a 0%, #2a2f4a 100%);
            border: 2px solid #ff6b6b;
            border-radius: 10px;
            padding: 20px;
            margin: 10px 0;
        }
        
        .dashboard-header {
            background: linear-gradient(90deg, #ff6b6b 0%, #4ecdc4 100%);
            color: #000;
            padding: 20px;
            border-radius: 10px;
            font-weight: bold;
            font-size: 2rem;
            text-align: center;
        }
    </style>
""", unsafe_allow_html=True)


# ============================================================================
# RACING DASHBOARD HEADER
# ============================================================================

def render_header():
    """Render racing-themed header"""
    st.markdown("""
        <div class='dashboard-header'>
            🏎️ RACING TELEMETRY ANALYSIS SYSTEM v3.0 🏁
            <br>
            <span style='font-size: 0.8rem;'>Advanced ML • Racing UI • Premium Features</span>
        </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.info(f"🤖 ML V2: {'✓ Available' if ML_V2_AVAILABLE else '✗ Unavailable'}")
    with col2:
        st.info(f"🎨 Racing UI: {'✓ Available' if RACING_UI_AVAILABLE else '✗ Unavailable'}")
    with col3:
        st.info(f"⭐ Premium: {'✓ Available' if PREMIUM_AVAILABLE else '✗ Unavailable'}")


# ============================================================================
# MAIN DASHBOARD
# ============================================================================

def render_real_time_dashboard(df: pd.DataFrame):
    """Render real-time telemetry dashboard with gauges"""
    
    if not RACING_UI_AVAILABLE:
        st.warning("Racing UI module not available")
        return
    
    st.markdown("### ⚡ REAL-TIME TELEMETRY")
    
    current = df.iloc[-1] if len(df) > 0 else df.iloc[0]
    
    col1, col2, col3 = st.columns(3)
    
    # Speedometer
    with col1:
        speed = float(current.get('speed', 0))
        max_speed = float(df['speed'].max() * 1.2)
        st.plotly_chart(
            create_speedometer(speed, max_speed),
            use_container_width=True
        )
    
    # RPM Gauge
    with col2:
        rpm = float(current.get('rpm', 0))
        st.plotly_chart(
            create_rpm_gauge(rpm, 8000),
            use_container_width=True
        )
    
    # G-Force Meter
    with col3:
        g_force = float(current.get('lateral_g_force', 0))
        st.plotly_chart(
            create_g_force_meter(g_force, 3.0),
            use_container_width=True
        )


def render_driver_rating(df: pd.DataFrame):
    """Render driver rating card"""
    
    if not RACING_UI_AVAILABLE:
        return
    
    rating, display_text = create_driver_rating_card(df)
    
    st.markdown(f"""
        <div style='
            background: linear-gradient(135deg, #ff6b6b 0%, #ffd93d 100%);
            border-radius: 15px;
            padding: 30px;
            text-align: center;
            color: #000;
            font-weight: bold;
            font-size: 1.5rem;
        '>
            {rating}<br>{display_text}
        </div>
    """, unsafe_allow_html=True)


def render_track_visualization(df: pd.DataFrame):
    """Render various track visualization modes"""
    
    if not RACING_UI_AVAILABLE:
        st.warning("Racing UI unavailable")
        return
    
    st.markdown("### 🗺️ Track Visualization Modes")
    
    # Create tabs for different visualization types
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏁 Standard Track", 
        "🚀 Anti-Gravity 3D",
        "🏎️ Racing Performance",
        "⚡ G-Force Intensity",
        "🔥 Corner Heatmap"
    ])
    
    with tab1:
        st.markdown("**Standard Distance-Based Track Map**")
        st.plotly_chart(
            create_track_map(df, has_gps='latitude' in df.columns),
            use_container_width=True
        )
    
    with tab2:
        st.markdown("**Anti-Gravity 3D Visualization**")
        st.info("🚀 3D track with G-forces shown as elevation. Grab and rotate to explore!")
        st.plotly_chart(
            create_antigravity_track_map(df),
            use_container_width=True
        )
    
    with tab3:
        st.markdown("**Racing Performance Track**")
        st.info("🏎️ Shows acceleration (green ▲), braking (red ▼), and cornering (magenta ◆) zones")
        st.plotly_chart(
            create_car_performance_track(df),
            use_container_width=True
        )
    
    with tab4:
        st.markdown("**G-Force Intensity Map**")
        st.info("⚡ Red intensity shows G-forces, yellow circles mark extreme zones (>2.0G)")
        st.plotly_chart(
            create_g_force_map(df),
            use_container_width=True
        )
    
    with tab5:
        st.markdown("**Corner Intensity Heatmap**")
        st.plotly_chart(
            create_corner_heatmap(df),
            use_container_width=True
        )


def render_driver_style_profile(df: pd.DataFrame):
    """Render driver style radar chart"""
    
    if not ML_V2_AVAILABLE or not RACING_UI_AVAILABLE:
        return
    
    driver_style = classify_driver_style(df)
    
    st.markdown("### 🎯 Driver Style Profile")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_driver_style_radar(driver_style),
            use_container_width=True
        )
    
    with col2:
        st.markdown("### Driver Characteristics:")
        stats_text = f"""
        - **Aggressive Score:** {driver_style.get('aggressive', 0):.1f}/100
        - **Smooth Score:** {driver_style.get('smooth', 0):.1f}/100
        - **Consistent Score:** {driver_style.get('consistent', 0):.1f}/100
        - **Defensive Score:** {driver_style.get('defensive', 0):.1f}/100
        """
        
        # Determine dominant style
        dominated_style = max(driver_style.items(), key=lambda x: x[1])[0]
        st.success(f"**Dominant Style:** {dominated_style.upper()}")
        st.markdown(stats_text)


def render_ml_v2_analysis(df: pd.DataFrame):
    """Render advanced ML analysis"""
    
    if not ML_V2_AVAILABLE:
        st.warning("Advanced ML module not available")
        return
    
    st.markdown("### 🤖 Advanced ML Analysis")
    
    # Anomaly Detection
    anomaly_scores, anomaly_proba = detect_anomalies_advanced(df)
    anomaly_pct = (anomaly_scores == -1).sum() / len(anomaly_scores) * 100
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.metric("🔍 Anomaly Detection", f"{anomaly_pct:.1f}%", "Low anomalies is good")
    
    with col2:
        st.metric("📊 Performance Index", f"{compute_performance_index(df):.1f}/100", "Overall score")
    
    # Upcoming Events Prediction
    upcoming = predict_upcoming_events(df)
    if upcoming:
        st.warning(f"🚨 Predicted Events: {', '.join([e.replace('_', ' ').title() for e in upcoming])}")
    else:
        st.success("✓ No anomalies or risky events predicted")
    
    # Real-time Metrics
    realtime = compute_realtime_metrics(df)
    
    metric_cols = st.columns(4)
    for i, (key, val) in enumerate(list(realtime.items())[:4]):
        with metric_cols[i % 4]:
            st.metric(key.replace('_', ' ').title(), f"{val:.1f}", "Live")


def render_premium_features(primary_df: pd.DataFrame, secondary_df: Optional[pd.DataFrame] = None):
    """Render premium features"""
    
    if not PREMIUM_AVAILABLE:
        st.warning("Premium features not available")
        return
    
    st.markdown("### ⭐ Premium Features")
    
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🏁 Lap Prediction", "🛑 Braking", "⚡ Acceleration", 
        "🎯 Consistency", "📊 Sectors"
    ])
    
    # Lap Prediction
    with tab1:
        if 'time' in primary_df.columns and 'distance_traveled' in primary_df.columns:
            predicted_time, confidence = predict_lap_time(primary_df)
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("🎯 Predicted Lap Time", f"{predicted_time:.2f}s", "Estimated")
            with col2:
                st.metric("📈 Confidence", f"{confidence*100:.1f}%", "Higher is accurate")
    
    # Braking Analysis
    with tab2:
        braking_points = analyze_braking_points(primary_df)
        if braking_points:
            st.dataframe(
                pd.DataFrame(braking_points).head(5),
                use_container_width=True
            )
            st.info(f"Found {len(braking_points)} braking zones")
    
    # Acceleration Analysis
    with tab3:
        accel_zones = analyze_acceleration_zones(primary_df)
        if accel_zones:
            st.dataframe(
                pd.DataFrame(accel_zones).head(5),
                use_container_width=True
            )
            st.info(f"Found {len(accel_zones)} acceleration zones")
    
    # Consistency
    with tab4:
        consistency = analyze_consistency(primary_df)
        
        for metric, value in consistency.items():
            st.progress(value / 100, text=f"{metric.replace('_', ' ').title()}: {value:.1f}")
    
    # Sector Analysis
    with tab5:
        sector_perf = analyze_sector_performance(primary_df, n_sectors=3)
        
        if sector_perf:
            selected_sector = st.selectbox(
                "Select Sector",
                list(sector_perf.keys())
            )
            
            sector_info = sector_perf[selected_sector]
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Avg Speed", f"{sector_info['avg_speed']:.1f} km/h")
            with col2:
                st.metric("Max Speed", f"{sector_info['max_speed']:.1f} km/h")
            with col3:
                st.metric("Time", f"{sector_info['time_in_sector']:.2f}s")


# ============================================================================
# MAIN APP LOGIC
# ============================================================================

def main():
    """Main application"""
    
    render_header()
    
    # Sidebar
    st.sidebar.markdown("## 📁 Upload Data")
    
    primary_file = st.sidebar.file_uploader(
        "Upload Primary Telemetry (CSV)",
        type=['csv'],
        key='primary'
    )
    
    secondary_file = st.sidebar.file_uploader(
        "Upload Secondary Telemetry (Compare)",
        type=['csv'],
        key='secondary'
    )
    
    # Process main data
    if primary_file:
        st.sidebar.success("✓ Primary file loaded")
        
        # Load data
        df = pd.read_csv(primary_file)
        
        # Tab interface
        tabs = st.tabs([
            "📊 Dashboard",
            "🎨 Track & Style", 
            "🤖 ML Analysis",
            "⭐ Premium",
            "📈 Comparison" if secondary_file else "ℹ️ Info"
        ])
        
        with tabs[0]:
            st.markdown("## 📊 Real-Time Telemetry Dashboard")
            render_real_time_dashboard(df)
            st.divider()
            render_driver_rating(df)
        
        with tabs[1]:
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("## 🏁 Track Visualization")
                render_track_visualization(df)
            with col2:
                st.markdown("")
                st.markdown("")
                render_driver_style_profile(df)
        
        with tabs[2]:
            render_ml_v2_analysis(df)
        
        with tabs[3]:
            secondary_df = None
            if secondary_file:
                secondary_df = pd.read_csv(secondary_file)
            render_premium_features(df, secondary_df)
        
        with tabs[4]:
            if secondary_file:
                secondary_df = pd.read_csv(secondary_file)
                
                st.markdown("## ⚡ Lap Comparison")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("Primary Lap Time", f"{df['time'].max():.2f}s")
                with col2:
                    st.metric("Secondary Lap Time", f"{secondary_df['time'].max():.2f}s")
                
                # Benchmark
                benchmarks = benchmark_performance(df, secondary_df)
                
                st.markdown("### Benchmark Results:")
                for result in benchmarks:
                    status_icon = "🟢" if result.status == "ahead" else "🔴"
                    st.metric(
                        f"{status_icon} {result.metric.replace('_', ' ').title()}",
                        f"{result.current_value:.2f}",
                        f"{result.percentage_diff:+.1f}%"
                    )
                
                # Delta graph
                st.plotly_chart(
                    create_lap_delta_graph(df, secondary_df),
                    use_container_width=True
                )
            else:
                st.info("Upload a second file to compare laps")
    
    else:
        st.info("👈 Upload a telemetry CSV file to begin")


if __name__ == "__main__":
    main()
