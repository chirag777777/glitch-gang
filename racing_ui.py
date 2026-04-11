"""
Racing UI Module - Professional Dashboard with Graphics & Animations
Features: Track visualization, telemetry gauges, lap replays, driver ratings
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
import numpy as np
import pandas as pd
from dataclasses import dataclass
from typing import Dict, Tuple, Optional, List


# ============================================================================
# RACING DASHBOARD GAUGES
# ============================================================================

def create_speedometer(speed: float, max_speed: float = 300) -> go.Figure:
    """
    Create a spinning speedometer gauge (racing style)
    """
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=speed,
        title={'text': "Speed (km/h)", 'font': {'color': '#00FF00', 'size': 20}},
        delta={'reference': max_speed * 0.7, 'increasing': {'color': 'lightgreen'}},
        gauge={
            'axis': {'range': [0, max_speed], 'tickcolor': 'darkblue'},
            'bar': {'color': '#FF6B6B'},  # Racing red
            'steps': [
                {'range': [0, max_speed * 0.5], 'color': 'rgba(0, 255, 0, 0.3)'},  # Green (safe)
                {'range': [max_speed * 0.5, max_speed * 0.8], 'color': 'rgba(255, 200, 0, 0.3)'},  # Yellow (caution)
                {'range': [max_speed * 0.8, max_speed], 'color': 'rgba(255, 0, 0, 0.3)'},  # Red (danger)
            ],
            'threshold': {
                'line': {'color': 'red', 'width': 4},
                'thickness': 0.75,
                'value': max_speed * 0.95
            }
        },
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    
    fig.update_layout(
        font=dict(color='white', size=14, family='Arial Black'),
        plot_bgcolor='rgba(20, 20, 30, 1)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_rpm_gauge(rpm: float, max_rpm: float = 8000) -> go.Figure:
    """
    Create an RPM tachometer (racing style)
    """
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=rpm,
        title={'text': "RPM", 'font': {'color': '#00FFFF', 'size': 20}},
        gauge={
            'axis': {'range': [0, max_rpm], 'tickcolor': 'cyan'},
            'bar': {'color': '#00FFFF'},  # Cyan for racing tech
            'steps': [
                {'range': [0, max_rpm * 0.4], 'color': 'rgba(0, 255, 0, 0.2)'},
                {'range': [max_rpm * 0.4, max_rpm * 0.8], 'color': 'rgba(255, 200, 0, 0.2)'},
                {'range': [max_rpm * 0.8, max_rpm], 'color': 'rgba(255, 0, 0, 0.2)'},
            ]
        }
    ))
    
    fig.update_layout(
        font=dict(color='white', size=14, family='Arial Black'),
        plot_bgcolor='rgba(20, 20, 30, 1)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


def create_g_force_meter(g_force: float, max_g: float = 3.0) -> go.Figure:
    """
    Create a G-Force indicator (racing acceleration/cornering forces)
    """
    
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=abs(g_force),
        title={'text': "G-Force", 'font': {'color': '#FF00FF', 'size': 20}},
        gauge={
            'axis': {'range': [0, max_g], 'tickcolor': 'magenta'},
            'bar': {'color': '#FF00FF'},
            'steps': [
                {'range': [0, max_g * 0.5], 'color': 'rgba(0, 255, 255, 0.2)'},
                {'range': [max_g * 0.5, max_g * 0.8], 'color': 'rgba(255, 200, 0, 0.2)'},
                {'range': [max_g * 0.8, max_g], 'color': 'rgba(255, 0, 0, 0.2)'},
            ]
        }
    ))
    
    fig.update_layout(
        font=dict(color='white', size=14, family='Arial Black'),
        plot_bgcolor='rgba(20, 20, 30, 1)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        height=400,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


# ============================================================================
# TRACK VISUALIZATION
# ============================================================================

def create_track_map(df: pd.DataFrame, has_gps: bool = False) -> go.Figure:
    """
    Create an artistic track map with telemetry overlay
    """
    
    if has_gps and 'latitude' in df.columns and 'longitude' in df.columns:
        # GPS-based track
        fig = px.scatter_mapbox(
            df,
            lat='latitude',
            lon='longitude',
            color='speed',
            size='lateral_accel' if 'lateral_accel' in df.columns else None,
            hover_name='distance_traveled' if 'distance_traveled' in df.columns else None,
            color_continuous_scale='Viridis',
            title='🏁 Track Map (GPS)',
            zoom=15,
            mapbox_style='carto-positron'
        )
    else:
        # Distance-based track
        fig = go.Figure()
        
        # Create 2D track projection from distance
        df_sorted = df.sort_values('distance_traveled' if 'distance_traveled' in df.columns else 'time')
        distance = df_sorted['distance_traveled'].values if 'distance_traveled' in df.columns else df_sorted['time'].values
        
        # Create synthetic X-Y based on steering
        steering = df_sorted['steering_angle'].values if 'steering_angle' in df.columns else np.zeros(len(df_sorted))
        x_pos = np.cumsum(np.cos(np.radians(steering)) * 0.1)
        y_pos = np.cumsum(np.sin(np.radians(steering)) * 0.1)
        
        speed_color = df_sorted['speed'].values
        
        fig.add_trace(go.Scatter(
            x=x_pos,
            y=y_pos,
            mode='lines+markers',
            line=dict(color=speed_color, colorscale='Viridis', width=3),
            marker=dict(size=6, color=speed_color, colorscale='Viridis', showscale=True),
            hovertext=[f"Dist: {d:.1f}m<br>Speed: {s:.1f}km/h" for d, s in zip(distance, speed_color)],
            hoverinfo='text',
            name='Track'
        ))
    
    # Styling
    fig.update_layout(
        title={'text': '🏁 TRACK MAP', 'font': {'size': 24, 'color': '#FF6B6B', 'family': 'Arial Black'}},
        plot_bgcolor='rgba(20, 30, 45, 1)',
        paper_bgcolor='rgba(20, 30, 45, 1)',
        font=dict(color='white', size=12),
        height=500,
        hovermode='closest'
    )
    
    return fig


# ============================================================================
# DRIVER RATING SYSTEM
# ============================================================================

def create_driver_rating_card(df: pd.DataFrame) -> Tuple[str, str]:
    """
    Generate driver rating based on performance metrics
    Returns: (rating_class, colorful_display)
    """
    
    # Calculate metrics
    consistency = df['speed_consistency'].mean() if 'speed_consistency' in df.columns else 50
    smoothness = df['control_smoothness'].mean() if 'control_smoothness' in df.columns else 50
    efficiency = df['rpm_efficiency'].mean() if 'rpm_efficiency' in df.columns else 50
    
    avg_score = (consistency + smoothness + efficiency) / 3
    
    if avg_score >= 95:
        return "⭐⭐⭐⭐⭐", f"🏆 LEGENDARY DRIVER {avg_score:.1f}/100"
    elif avg_score >= 85:
        return "⭐⭐⭐⭐", f"🥇 PROFESSIONAL {avg_score:.1f}/100"
    elif avg_score >= 75:
        return "⭐⭐⭐", f"🥈 EXPERT {avg_score:.1f}/100"
    elif avg_score >= 65:
        return "⭐⭐", f"🥉 INTERMEDIATE {avg_score:.1f}/100"
    else:
        return "⭐", f"🎯 DEVELOPING {avg_score:.1f}/100"


# ============================================================================
# HEAT MAP VISUALIZATIONS
# ============================================================================

def create_corner_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Create intensity heat map for corners
    """
    
    if 'distance_traveled' not in df.columns:
        return go.Figure().add_annotation(text="No distance data")
    
    # Calculate corner intensity
    corners = df[df['steering_abs'] > 5] if 'steering_abs' in df.columns else df
    
    if len(corners) == 0:
        return go.Figure().add_annotation(text="No corners detected")
    
    fig = go.Figure(data=go.Heatmap(
        z=corners['steering_severity'].values if 'steering_severity' in corners else corners['steering_angle'].abs().values,
        x=corners['distance_traveled'].values if 'distance_traveled' in corners else corners.index,
        colorscale='Hot',
        colorbar=dict(title='Severity'),
        name='Corner Heat'
    ))
    
    fig.update_layout(
        title='🔥 CORNER HEAT MAP',
        xaxis_title='Distance (m)',
        yaxis_title='Severity Index',
        plot_bgcolor='rgba(20, 30, 45, 1)',
        paper_bgcolor='rgba(20, 30, 45, 1)',
        font=dict(color='white'),
        height=300
    )
    
    return fig


# ============================================================================
# REAL-TIME TELEMETRY DISPLAY
# ============================================================================

def create_telemetry_dashboard(df: pd.DataFrame) -> go.Figure:
    """
    Create mini dashboard showing current telemetry values
    """
    
    current = df.iloc[-1] if len(df) > 0 else df.iloc[0]
    
    metrics_text = f"""
    <b style='color:#FF6B6B; font-size:18px'>⚡ LIVE TELEMETRY</b><br><br>
    
    <b style='color:#00FF00'>Speed:</b> {current.get('speed', 0):.1f} km/h<br>
    <b style='color:#00FFFF'>RPM:</b> {current.get('rpm', 0):.0f}<br>
    <b style='color:#FF00FF'>Steering:</b> {current.get('steering_angle', 0):.1f}°<br>
    <b style='color:#FFFF00'>Throttle:</b> {current.get('throttle_input', 0)*100:.0f}%<br>
    <b style='color:#FF6B6B'>Brake:</b> {current.get('brake_input', 0)*100:.0f}%<br>
    <b style='color:#00FF99'>G-Force:</b> {current.get('lateral_g_force', 0):.2f}G<br>
    """
    
    fig = go.Figure()
    fig.add_annotation(
        text=metrics_text,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        bgcolor="rgba(20, 20, 30, 0.9)",
        bordercolor="white",
        borderwidth=2,
        font=dict(family="Courier New", size=16, color="white")
    )
    
    fig.update_layout(
        title='📊 Current Telemetry',
        xaxis={'visible': False},
        yaxis={'visible': False},
        plot_bgcolor='rgba(20, 20, 30, 1)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        height=300,
        margin=dict(l=20, r=20, t=40, b=20)
    )
    
    return fig


# ============================================================================
# LAP TIME COMPARISON
# ============================================================================

def create_lap_delta_graph(df1: pd.DataFrame, df2: pd.DataFrame) -> go.Figure:
    """
    Create delta graph comparing two laps (lap1 - lap2)
    """
    
    # Normalize to distance
    distance1 = df1['distance_traveled'].values if 'distance_traveled' in df1.columns else df1.index.values
    distance2 = df2['distance_traveled'].values if 'distance_traveled' in df2.columns else df2.index.values
    
    # Linear interpolation to common distance grid
    common_dist = np.linspace(max(distance1.min(), distance2.min()), 
                              min(distance1.max(), distance2.max()), 100)
    
    speed1_interp = np.interp(common_dist, distance1, df1['speed'].values)
    speed2_interp = np.interp(common_dist, distance2, df2['speed'].values)
    
    delta = speed1_interp - speed2_interp
    
    colors = ['red' if x < 0 else 'green' for x in delta]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=common_dist,
        y=delta,
        marker=dict(color=colors),
        name='Speed Delta',
        hovertemplate='<b>Distance:</b> %{x:.1f}m<br><b>Delta:</b> %{y:+.2f} km/h<extra></extra>'
    ))
    
    fig.update_layout(
        title='⚡ LAP COMPARISON DELTA',
        xaxis_title='Distance (m)',
        yaxis_title='Speed Difference (km/h)',
        plot_bgcolor='rgba(20, 30, 45, 1)',
        paper_bgcolor='rgba(20, 30, 45, 1)',
        font=dict(color='white'),
        height=400,
        hovermode='x unified'
    )
    
    return fig


# ============================================================================
# DRIVER STYLE INDICATOR
# ============================================================================

def create_driver_style_radar(driver_style: Dict[str, float]) -> go.Figure:
    """
    Create radar chart showing driver style profile
    """
    
    fig = go.Figure(data=go.Scatterpolar(
        r=list(driver_style.values()),
        theta=list(driver_style.keys()),
        fill='toself',
        name='Driver Profile',
        line=dict(color='#FF6B6B'),
        fillcolor='rgba(255, 107, 107, 0.3)'
    ))
    
    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                tickcolor='white'
            ),
            bgcolor='rgba(20, 30, 45, 0.5)'
        ),
        title='🎯 DRIVER STYLE PROFILE',
        font=dict(color='white', size=12),
        plot_bgcolor='rgba(20, 20, 30, 1)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        height=400
    )
    
    return fig


# ============================================================================
# PERFORMANCE TIMELINE
# ============================================================================

def create_performance_timeline(df: pd.DataFrame) -> go.Figure:
    """
    Create animated timeline of performance metrics
    """
    
    distance = df['distance_traveled'].values if 'distance_traveled' in df.columns else df.index.values
    
    fig = go.Figure()
    
    # Speed trace
    if 'speed' in df.columns:
        fig.add_trace(go.Scatter(
            x=distance, y=df['speed'],
            mode='lines',
            name='Speed',
            line=dict(color='#00FF00', width=3)
        ))
    
    # Consistency trace
    if 'speed_consistency' in df.columns:
        fig.add_trace(go.Scatter(
            x=distance, y=df['speed_consistency'],
            mode='lines',
            name='Consistency',
            line=dict(color='#00FFFF', width=2),
            yaxis='y2'
        ))
    
    fig.update_layout(
        title='📈 PERFORMANCE PROGRESSION',
        xaxis_title='Distance (m)',
        yaxis_title='Speed (km/h)',
        yaxis2=dict(title='Consistency Score', overlaying='y', side='right'),
        plot_bgcolor='rgba(20, 30, 45, 1)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        font=dict(color='white'),
        height=400,
        hovermode='x unified'
    )
    
    return fig
