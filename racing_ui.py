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
        # Distance-based synthetic track generation
        fig = go.Figure()
        
        df_sorted = df.sort_values('distance_traveled' if 'distance_traveled' in df.columns else 'time')
        distance = df_sorted['distance_traveled'].values if 'distance_traveled' in df.columns else df_sorted['time'].values
        
        # Multi-signal synthetic track projection (better than simple steering)
        steering = df_sorted['steering_angle'].values if 'steering_angle' in df.columns else np.zeros(len(df_sorted))
        throttle = df_sorted['throttle_input'].values if 'throttle_input' in df.columns else np.zeros(len(df_sorted))
        brake = df_sorted['brake_input'].values if 'brake_input' in df.columns else np.zeros(len(df_sorted))
        speed = df_sorted['speed'].values if 'speed' in df.columns else np.ones(len(df_sorted)) * 100
        
        # Create more realistic track using steering, throttle, brake inputs
        x_pos = np.zeros(len(df_sorted))
        y_pos = np.zeros(len(df_sorted))
        angle = 0
        
        for i in range(1, len(df_sorted)):
            # Steering input curves the track
            angle += steering.iloc[i] if hasattr(steering, 'iloc') else steering[i]
            angle = angle % 360
            
            # Speed affects segment length
            segment_length = (speed.iloc[i] if hasattr(speed, 'iloc') else speed[i]) / 100 * 0.2
            
            # Add acceleration/braking depth
            depth_factor = 1 + (throttle.iloc[i] if hasattr(throttle, 'iloc') else throttle[i]) * 0.3
            
            x_pos[i] = x_pos[i-1] + np.cos(np.radians(angle)) * segment_length * depth_factor
            y_pos[i] = y_pos[i-1] + np.sin(np.radians(angle)) * segment_length * depth_factor
        
        speed_color = speed
        
        # Track line
        fig.add_trace(go.Scatter(
            x=x_pos,
            y=y_pos,
            mode='lines',
            line=dict(color=speed_color, colorscale='Plasma', width=6, 
                     colorbar=dict(title='Speed (km/h)', thickness=15, len=0.7)),
            hovertext=[f"Dist: {d:.1f}m<br>Speed: {s:.1f}km/h<br>Steering: {st:.1f}°" 
                      for d, s, st in zip(distance, speed_color, steering)],
            hoverinfo='text',
            name='Track Line'
        ))
        
        # Add cornering points
        corner_mask = (np.abs(steering) > 10)
        if corner_mask.any():
            fig.add_trace(go.Scatter(
                x=x_pos[corner_mask],
                y=y_pos[corner_mask],
                mode='markers',
                marker=dict(size=8, color='#FF00FF', symbol='diamond', 
                           line=dict(color='white', width=2)),
                name='Corners',
                hovertext='🔄 Corner Zone',
                hoverinfo='text'
            ))
        
        # Add straights
        straight_mask = (np.abs(steering) <= 5)
        if straight_mask.any():
            fig.add_trace(go.Scatter(
                x=x_pos[straight_mask],
                y=y_pos[straight_mask],
                mode='markers',
                marker=dict(size=4, color='#00FF00', symbol='circle', opacity=0.6),
                name='Straights',
                hovertext='➡️ Straight Zone',
                hoverinfo='text'
            ))
        
        # Start point
        fig.add_trace(go.Scatter(
            x=[x_pos[0]], y=[y_pos[0]],
            mode='markers+text',
            marker=dict(size=15, color='#00FF00', symbol='star'),
            text=['START'],
            textposition='top center',
            name='Start',
            hovertext='🏁 Start/Finish',
            hoverinfo='text'
        ))
        
        # End point
        fig.add_trace(go.Scatter(
            x=[x_pos[-1]], y=[y_pos[-1]],
            mode='markers+text',
            marker=dict(size=15, color='#FF0000', symbol='star'),
            text=['END'],
            textposition='top center',
            name='Finish',
            hovertext='🏁 Finish',
            hoverinfo='text'
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
# ANTI-GRAVITY VISUALIZATION
# ============================================================================

def create_antigravity_track_map(df: pd.DataFrame) -> go.Figure:
    """
    Create an anti-gravity style visualization with 3D-like effects
    Shows acceleration, braking, and cornering forces as vertical displacement
    """
    
    df_sorted = df.sort_values('distance_traveled' if 'distance_traveled' in df.columns else 'time')
    distance = df_sorted['distance_traveled'].values if 'distance_traveled' in df.columns else df_sorted['time'].values
    
    # Generate base track
    steering = df_sorted['steering_angle'].values if 'steering_angle' in df_sorted.columns else np.zeros(len(df_sorted))
    speed = df_sorted['speed'].values if 'speed' in df_sorted.columns else np.ones(len(df_sorted)) * 100
    
    x_pos = np.zeros(len(df_sorted))
    y_pos = np.zeros(len(df_sorted))
    angle = 0
    
    for i in range(1, len(df_sorted)):
        angle += steering[i]
        angle = angle % 360
        segment_length = (speed[i] / 100) * 0.2
        x_pos[i] = x_pos[i-1] + np.cos(np.radians(angle)) * segment_length
        y_pos[i] = y_pos[i-1] + np.sin(np.radians(angle)) * segment_length
    
    # Calculate G-forces for vertical displacement (anti-gravity effect)
    if 'lateral_g_force' in df_sorted.columns:
        g_force = np.abs(df_sorted['lateral_g_force'].values)
    else:
        # Estimate from steering and speed
        g_force = (np.abs(steering) / 45) * (speed / 200) * 3
    
    # Normalize for visualization
    z_pos = (g_force - g_force.min()) / (g_force.max() - g_force.min() + 0.001) * 100
    
    fig = go.Figure()
    
    # Anti-gravity track surface
    fig.add_trace(go.Scatter3d(
        x=x_pos,
        y=y_pos,
        z=z_pos,
        mode='lines+markers',
        line=dict(
            color=speed,
            colorscale='Hot',
            width=8,
            colorbar=dict(title='Speed', x=0.85, len=0.7)
        ),
        marker=dict(
            size=5,
            color=g_force,
            colorscale='Plasma',
            showscale=False
        ),
        hovertext=[f"<b>Distance:</b> {d:.0f}m<br><b>Speed:</b> {s:.1f}km/h<br><b>G-Force:</b> {g:.2f}G" 
                  for d, s, g in zip(distance, speed, g_force)],
        hoverinfo='text',
        name='Anti-Gravity Track'
    ))
    
    # Start point
    fig.add_trace(go.Scatter3d(
        x=[x_pos[0]], y=[y_pos[0]], z=[z_pos[0]],
        mode='markers+text',
        marker=dict(size=12, color='lime', symbol='star'),
        text=['START'],
        name='Start',
        hovertext='🏁 START'
    ))
    
    # End point  
    fig.add_trace(go.Scatter3d(
        x=[x_pos[-1]], y=[y_pos[-1]], z=[z_pos[-1]],
        mode='markers+text',
        marker=dict(size=12, color='red', symbol='star'),
        text=['FINISH'],
        name='Finish',
        hovertext='🏁 FINISH'
    ))
    
    fig.update_layout(
        title='🚀 ANTI-GRAVITY TRACK MAP (3D)',
        scene=dict(
            xaxis=dict(title='X Position', backgroundcolor='rgb(20, 20, 30)', gridcolor='rgb(50, 50, 80)'),
            yaxis=dict(title='Y Position', backgroundcolor='rgb(20, 20, 30)', gridcolor='rgb(50, 50, 80)'),
            zaxis=dict(title='G-Force Level', backgroundcolor='rgb(20, 20, 30)', gridcolor='rgb(50, 50, 80)'),
            bgcolor='rgba(20, 20, 30, 0.95)'
        ),
        font=dict(color='white', family='Arial Black', size=12),
        paper_bgcolor='rgba(20, 20, 30, 1)',
        height=600,
        hovermode='closest'
    )
    
    return fig


# ============================================================================
# CAR RACING VISUALIZATION
# ============================================================================

def create_car_performance_track(df: pd.DataFrame) -> go.Figure:
    """
    Create a racing visualization with car position and performance metrics
    """
    
    df_sorted = df.sort_values('distance_traveled' if 'distance_traveled' in df.columns else 'time')
    distance = df_sorted['distance_traveled'].values if 'distance_traveled' in df_sorted.columns else df_sorted['time'].values
    
    # Generate track
    steering = df_sorted['steering_angle'].values if 'steering_angle' in df_sorted.columns else np.zeros(len(df_sorted))
    speed = df_sorted['speed'].values if 'speed' in df_sorted.columns else np.ones(len(df_sorted)) * 100
    throttle = df_sorted['throttle_input'].values if 'throttle_input' in df_sorted.columns else np.zeros(len(df_sorted))
    brake = df_sorted['brake_input'].values if 'brake_input' in df_sorted.columns else np.zeros(len(df_sorted))
    
    x_pos = np.zeros(len(df_sorted))
    y_pos = np.zeros(len(df_sorted))
    angle = 0
    
    for i in range(1, len(df_sorted)):
        angle += steering[i]
        angle = angle % 360
        segment_length = (speed[i] / 100) * 0.2
        x_pos[i] = x_pos[i-1] + np.cos(np.radians(angle)) * segment_length
        y_pos[i] = y_pos[i-1] + np.sin(np.radians(angle)) * segment_length
    
    fig = go.Figure()
    
    # Main track line with speed coloring
    fig.add_trace(go.Scatter(
        x=x_pos,
        y=y_pos,
        mode='lines',
        line=dict(
            color=speed,
            colorscale='Turbo',
            width=5,
            colorbar=dict(title='Speed km/h', thickness=15)
        ),
        hovertext=[f"Speed: {s:.1f}km/h<br>Throttle: {t*100:.0f}%<br>Brake: {b*100:.0f}%<br>Distance: {d:.0f}m" 
                  for s, t, b, d in zip(speed, throttle, brake, distance)],
        hoverinfo='text',
        name='Racing Line'
    ))
    
    # Acceleration zones (high throttle)
    accel_mask = throttle > 0.7
    if accel_mask.any():
        fig.add_trace(go.Scatter(
            x=x_pos[accel_mask],
            y=y_pos[accel_mask],
            mode='markers',
            marker=dict(size=8, color='lime', symbol='triangle-up', opacity=0.7),
            name='🚀 Acceleration',
            hovertext='Accelerating'
        ))
    
    # Braking zones (high brake)
    brake_mask = brake > 0.7
    if brake_mask.any():
        fig.add_trace(go.Scatter(
            x=x_pos[brake_mask],
            y=y_pos[brake_mask],
            mode='markers',
            marker=dict(size=8, color='red', symbol='triangle-down', opacity=0.7),
            name='🔴 Braking',
            hovertext='Braking Hard'
        ))
    
    # Cornering zones (high steering)
    corner_mask = np.abs(steering) > 15
    if corner_mask.any():
        fig.add_trace(go.Scatter(
            x=x_pos[corner_mask],
            y=y_pos[corner_mask],
            mode='markers',
            marker=dict(size=8, color='#FF00FF', symbol='diamond', opacity=0.7, 
                       line=dict(color='white', width=1)),
            name='🔄 Cornering',
            hovertext='Hard Corner'
        ))
    
    # Car position markers at key points (every 100 distance units)
    sample_rate = max(1, len(df_sorted) // 20)
    sample_indices = np.arange(0, len(df_sorted), sample_rate)
    
    fig.add_trace(go.Scatter(
        x=x_pos[sample_indices],
        y=y_pos[sample_indices],
        mode='markers',
        marker=dict(
            size=10,
            color=speed[sample_indices],
            colorscale='Plasma',
            symbol='circle',
            line=dict(color='yellow', width=2)
        ),
        name='🏎️ Car Positions',
        hovertext=[f"Distance: {distance[i]:.0f}m<br>Speed: {speed[i]:.1f}km/h" 
                  for i in sample_indices],
        hoverinfo='text'
    ))
    
    # Start/Finish
    fig.add_trace(go.Scatter(
        x=[x_pos[0]], y=[y_pos[0]],
        mode='markers', marker=dict(size=20, color='lime', symbol='star'),
        name='🏁 START'
    ))
    
    fig.add_trace(go.Scatter(
        x=[x_pos[-1]], y=[y_pos[-1]],
        mode='markers', marker=dict(size=20, color='red', symbol='star'),
        name='🏁 FINISH'
    ))
    
    fig.update_layout(
        title='🏎️ RACING PERFORMANCE MAP',
        xaxis_title='Track X Position',
        yaxis_title='Track Y Position',
        plot_bgcolor='rgba(20, 30, 45, 1)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        font=dict(color='white', size=12),
        height=600,
        hovermode='closest',
        showlegend=True
    )
    
    fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 150, 0.2)')
    fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 150, 0.2)')
    
    return fig


# ============================================================================
# FORCE VISUALIZATION (G-FORCES IN 2D)
# ============================================================================

def create_g_force_map(df: pd.DataFrame) -> go.Figure:
    """
    Create a 2D map showing G-forces at each point on track
    """
    
    df_sorted = df.sort_values('distance_traveled' if 'distance_traveled' in df.columns else 'time')
    distance = df_sorted['distance_traveled'].values if 'distance_traveled' in df_sorted.columns else df_sorted['time'].values
    
    # Generate track
    steering = df_sorted['steering_angle'].values if 'steering_angle' in df_sorted.columns else np.zeros(len(df_sorted))
    speed = df_sorted['speed'].values if 'speed' in df_sorted.columns else np.ones(len(df_sorted)) * 100
    
    x_pos = np.zeros(len(df_sorted))
    y_pos = np.zeros(len(df_sorted))
    angle = 0
    
    for i in range(1, len(df_sorted)):
        angle += steering[i]
        angle = angle % 360
        segment_length = (speed[i] / 100) * 0.2
        x_pos[i] = x_pos[i-1] + np.cos(np.radians(angle)) * segment_length
        y_pos[i] = y_pos[i-1] + np.sin(np.radians(angle)) * segment_length
    
    # Calculate G-forces
    if 'lateral_g_force' in df_sorted.columns:
        lateral_g = df_sorted['lateral_g_force'].values
    else:
        lateral_g = (np.abs(steering) / 45) * (speed / 200) * 3
    
    if 'longitudinal_g_force' in df_sorted.columns:
        long_g = df_sorted['longitudinal_g_force'].values
    else:
        long_g = np.zeros(len(df_sorted))
    
    total_g = np.sqrt(lateral_g**2 + long_g**2)
    
    fig = go.Figure()
    
    # Track with G-force coloring
    fig.add_trace(go.Scatter(
        x=x_pos,
        y=y_pos,
        mode='lines+markers',
        line=dict(
            color=total_g,
            colorscale='Reds',
            width=6,
            colorbar=dict(title='Total G-Force', thickness=15)
        ),
        marker=dict(
            size=5,
            color=total_g,
            colorscale='Reds',
            showscale=False
        ),
        hovertext=[f"<b>G-Force:</b> {g:.2f}G<br><b>Lateral:</b> {lg:.2f}G<br><b>Speed:</b> {s:.1f}km/h<br><b>Distance:</b> {d:.0f}m" 
                  for g, lg, s, d in zip(total_g, lateral_g, speed, distance)],
        hoverinfo='text',
        name='G-Force Map'
    ))
    
    # High G-force warning zones (>2G)
    high_g_mask = total_g > 2.0
    if high_g_mask.any():
        fig.add_trace(go.Scatter(
            x=x_pos[high_g_mask],
            y=y_pos[high_g_mask],
            mode='markers',
            marker=dict(size=10, color='yellow', symbol='circle', 
                       line=dict(color='red', width=3), opacity=0.8),
            name='⚡ High G-Force Zone (>2.0G)',
            hovertext='⚠️ Extreme G-Forces'
        ))
    
    fig.update_layout(
        title='⚡ G-FORCE INTENSITY MAP',
        xaxis_title='Track X Position',
        yaxis_title='Track Y Position',
        plot_bgcolor='rgba(20, 30, 45, 1)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        font=dict(color='white', size=12),
        height=600
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
