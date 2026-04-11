"""
Advanced Track Features Module
Lap comparison, performance grids, export capabilities, and filtering tools
"""

import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from typing import Dict, List, Tuple, Optional
import streamlit as st


# ============================================================================
# LAP COMPARISON FEATURES
# ============================================================================

def create_lap_comparison_overlay(lap1: pd.DataFrame, lap2: pd.DataFrame, 
                                  metric: str = 'speed') -> go.Figure:
    """
    Create an interactive overlay comparison of two laps
    
    Parameters:
    -----------
    lap1 : pd.DataFrame
        First lap telemetry data
    lap2 : pd.DataFrame
        Second lap telemetry data
    metric : str
        Metric to compare ('speed', 'throttle', 'brake', 'steering', 'lateral_accel')
    
    Returns:
    --------
    go.Figure
        Interactive dual-lap comparison chart
    """
    
    metric_mapping = {
        'speed': ('speed', 'Speed (km/h)', '#1f77b4'),
        'throttle': ('throttle_input', 'Throttle Input (%)', '#2ca02c'),
        'brake': ('brake_input', 'Brake Input (%)', '#d62728'),
        'steering': ('steering_angle', 'Steering Angle (°)', '#ff7f0e'),
        'lateral_accel': ('lateral_accel', 'Lateral Acceleration (G)', '#e377c2'),
    }
    
    column, label, color1 = metric_mapping.get(metric, metric_mapping['speed'])
    
    fig = go.Figure()
    
    # Lap 1 trace
    if 'distance_traveled' in lap1.columns and column in lap1.columns:
        fig.add_trace(go.Scatter(
            x=lap1['distance_traveled'],
            y=lap1[column],
            mode='lines',
            name='Lap 1',
            line=dict(color=color1, width=3),
            hovertemplate='<b>Lap 1</b><br>Distance: %{x:.1f}m<br>' + label + ': %{y:.2f}<extra></extra>'
        ))
    
    # Lap 2 trace
    if 'distance_traveled' in lap2.columns and column in lap2.columns:
        fig.add_trace(go.Scatter(
            x=lap2['distance_traveled'],
            y=lap2[column],
            mode='lines',
            name='Lap 2',
            line=dict(color='#9467bd', width=3, dash='dash'),
            hovertemplate='<b>Lap 2</b><br>Distance: %{x:.1f}m<br>' + label + ': %{y:.2f}<extra></extra>'
        ))
    
    fig.update_layout(
        template='plotly_dark',
        title=f'📊 Lap Comparison: {label}',
        xaxis_title='Distance Traveled (m)',
        yaxis_title=label,
        height=600,
        hovermode='x unified',
        plot_bgcolor='rgba(20, 20, 30, 0.8)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        font=dict(color='#ffffff', size=12),
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.3)'),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor='rgba(100, 100, 100, 0.3)'),
    )
    
    return fig


def create_lap_delta_comparison(lap1: pd.DataFrame, lap2: pd.DataFrame) -> go.Figure:
    """
    Create a delta (difference) graph between two laps
    Shows which lap is faster at different points on track
    
    Parameters:
    -----------
    lap1 : pd.DataFrame
        Reference lap (typically the best lap)
    lap2 : pd.DataFrame
        Comparison lap
    
    Returns:
    --------
    go.Figure
        Delta chart showing time differences
    """
    
    if 'distance_traveled' not in lap1.columns or 'distance_traveled' not in lap2.columns:
        return go.Figure().add_annotation(text="Distance data required")
    
    # Interpolate to same distance points
    max_distance = min(lap1['distance_traveled'].max(), lap2['distance_traveled'].max())
    distance_points = np.linspace(0, max_distance, 100)
    
    # Interpolate speeds
    if 'speed' in lap1.columns and 'speed' in lap2.columns:
        speed1_interp = np.interp(distance_points, lap1['distance_traveled'], lap1['speed'])
        speed2_interp = np.interp(distance_points, lap2['distance_traveled'], lap2['speed'])
        delta = speed2_interp - speed1_interp
        
        fig = go.Figure()
        
        # Delta bar chart (positive = lap2 faster)
        colors = ['#2ca02c' if d > 0 else '#d62728' for d in delta]
        fig.add_trace(go.Bar(
            x=distance_points,
            y=delta,
            marker=dict(color=colors),
            name='Speed Delta',
            hovertemplate='Distance: %{x:.1f}m<br>Δ Speed: %{y:.2f} km/h<extra></extra>'
        ))
        
        fig.update_layout(
            template='plotly_dark',
            title='⚡ Lap Delta Analysis (Lap2 - Lap1)',
            xaxis_title='Distance Traveled (m)',
            yaxis_title='Speed Difference (km/h)',
            height=500,
            plot_bgcolor='rgba(20, 20, 30, 0.8)',
            paper_bgcolor='rgba(20, 20, 30, 1)',
            font=dict(color='#ffffff', size=12),
            showlegend=False,
        )
        
        return fig
    
    return go.Figure().add_annotation(text="Speed data required for delta analysis")


# ============================================================================
# PERFORMANCE GRID & HEAT MAPS
# ============================================================================

def create_performance_heat_grid(df: pd.DataFrame, grid_size: int = 10) -> go.Figure:
    """
    Create a 2D heat grid showing performance across track segments
    X-axis: Distance segments, Y-axis: Lap sectors or speed zones
    
    Parameters:
    -----------
    df : pd.DataFrame
        Telemetry data
    grid_size : int
        Number of segments to divide track into
    
    Returns:
    --------
    go.Figure
        2D heatmap of performance
    """
    
    if 'distance_traveled' not in df.columns or 'speed' not in df.columns:
        return go.Figure().add_annotation(text="Distance and speed data required")
    
    # Create distance bins
    max_distance = df['distance_traveled'].max()
    distance_bins = np.linspace(0, max_distance, grid_size + 1)
    
    # Calculate metrics per segment
    segments = []
    segment_metrics = []
    
    for i in range(len(distance_bins) - 1):
        mask = (df['distance_traveled'] >= distance_bins[i]) & (df['distance_traveled'] < distance_bins[i + 1])
        segment_data = df[mask]
        
        if len(segment_data) > 0:
            segments.append(f"Seg {i + 1}")
            
            # Combine multiple metrics into a performance score
            avg_speed = segment_data['speed'].mean()
            
            # Calculate smoothness (lower steering changes = smoother)
            steering_smoothness = 100 - (segment_data['steering_angle'].diff().abs().mean() * 10) \
                if 'steering_angle' in segment_data.columns else 50
            
            # Combine into performance score (0-100)
            speed_score = (avg_speed / df['speed'].max()) * 100 if df['speed'].max() > 0 else 0
            performance_score = (speed_score + steering_smoothness) / 2
            
            segment_metrics.append(performance_score)
    
    # Create simple line chart showing performance across segments
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=segments,
        y=segment_metrics,
        mode='lines+markers',
        name='Performance Score',
        line=dict(color='#00FF00', width=3),
        marker=dict(size=10, color=segment_metrics, colorscale='RdYlGn', 
                    showscale=True, colorbar=dict(title="Score")),
        hovertemplate='<b>%{x}</b><br>Performance: %{y:.1f}%<extra></extra>'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        title='🔥 Performance Heat Grid (by Distance Segment)',
        xaxis_title='Track Segment',
        yaxis_title='Performance Score (%)',
        height=500,
        plot_bgcolor='rgba(20, 20, 30, 0.8)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        font=dict(color='#ffffff', size=12),
    )
    
    return fig


def create_2d_performance_heatmap(df: pd.DataFrame, metric: str = 'speed') -> go.Figure:
    """
    Create a 2D heatmap with distance segments and speed zones
    
    Parameters:
    -----------
    df : pd.DataFrame
        Telemetry data
    metric : str
        Metric to analyze ('speed', 'steering', 'throttle', 'brake')
    
    Returns:
    --------
    go.Figure
        2D heatmap visualization
    """
    
    if 'distance_traveled' not in df.columns or metric not in df.columns:
        return go.Figure().add_annotation(text=f"Distance and {metric} data required")
    
    # Create 2D grid
    distance_bins = 15
    metric_bins = 8
    
    max_distance = df['distance_traveled'].max()
    max_metric = df[metric].max()
    
    heatmap_data = np.zeros((metric_bins, distance_bins))
    
    distance_edges = np.linspace(0, max_distance, distance_bins + 1)
    metric_edges = np.linspace(0, max_metric * 1.1, metric_bins + 1)
    
    # Populate heatmap with frequency count
    for i in range(len(distance_edges) - 1):
        for j in range(len(metric_edges) - 1):
            mask = ((df['distance_traveled'] >= distance_edges[i]) & 
                    (df['distance_traveled'] < distance_edges[i + 1]) &
                    (df[metric] >= metric_edges[j]) &
                    (df[metric] < metric_edges[j + 1]))
            heatmap_data[metric_bins - j - 1, i] = len(df[mask])
    
    fig = go.Figure(data=go.Heatmap(
        z=heatmap_data,
        x=[f"{int(distance_edges[i])}-{int(distance_edges[i+1])}m" for i in range(len(distance_edges)-1)],
        y=[f"{int(metric_edges[j])}-{int(metric_edges[j+1])}" for j in range(len(metric_edges)-1)],
        colorscale='YlGnBu',
        hovertemplate='Distance: %{x}<br>' + metric + ': %{y}<br>Count: %{z}<extra></extra>'
    ))
    
    fig.update_layout(
        template='plotly_dark',
        title=f'🔥 2D Performance Heatmap: {metric.title()}',
        xaxis_title='Distance Segment (m)',
        yaxis_title=f'{metric.title()} Value',
        height=500,
        plot_bgcolor='rgba(20, 20, 30, 0.8)',
        paper_bgcolor='rgba(20, 20, 30, 1)',
        font=dict(color='#ffffff', size=11),
    )
    
    return fig


# ============================================================================
# FILTERING & SEGMENTATION TOOLS
# ============================================================================

def filter_by_distance_range(df: pd.DataFrame, start_distance: float, 
                            end_distance: float) -> pd.DataFrame:
    """
    Filter telemetry data to a specific distance range
    Useful for analyzing specific corners or straights
    """
    if 'distance_traveled' not in df.columns:
        return df
    
    return df[(df['distance_traveled'] >= start_distance) & 
              (df['distance_traveled'] <= end_distance)].copy()


def filter_by_speed_range(df: pd.DataFrame, min_speed: float, 
                         max_speed: float) -> pd.DataFrame:
    """
    Filter telemetry data to a specific speed range
    Useful for analyzing high-speed corners vs braking zones
    """
    if 'speed' not in df.columns:
        return df
    
    return df[(df['speed'] >= min_speed) & 
              (df['speed'] <= max_speed)].copy()


def segment_by_corners(df: pd.DataFrame, steering_threshold: float = 15.0) -> Dict[str, pd.DataFrame]:
    """
    Automatically segment track into corners and straights
    
    Returns:
    --------
    Dict[str, pd.DataFrame]
        Dictionary with 'corners' and 'straights' segments
    """
    if 'steering_angle' not in df.columns:
        return {'full_track': df}
    
    corners = df[df['steering_angle'].abs() >= steering_threshold].copy()
    straights = df[df['steering_angle'].abs() < steering_threshold].copy()
    
    return {
        'corners': corners,
        'straights': straights,
        'full_track': df
    }


def segment_by_events(df: pd.DataFrame, event_column: str = 'zone') -> Dict[str, pd.DataFrame]:
    """
    Segment track by defined events/zones
    
    Returns:
    --------
    Dict[str, pd.DataFrame]
        Dictionary with segments for each unique event
    """
    if event_column not in df.columns:
        return {'full_track': df}
    
    segments = {}
    for event in df[event_column].unique():
        if pd.notna(event):
            segments[str(event)] = df[df[event_column] == event].copy()
    
    return segments


# ============================================================================
# EXPORT & ANALYTICS FEATURES
# ============================================================================

def generate_lap_summary_stats(df: pd.DataFrame) -> Dict[str, float]:
    """
    Generate comprehensive statistics for a lap
    """
    stats = {}
    
    if 'speed' in df.columns:
        stats['max_speed'] = df['speed'].max()
        stats['avg_speed'] = df['speed'].mean()
        stats['min_speed'] = df['speed'].min()
    
    if 'steering_angle' in df.columns:
        stats['max_steering'] = df['steering_angle'].max()
        stats['avg_steering'] = df['steering_angle'].mean()
    
    if 'lateral_accel' in df.columns:
        stats['max_lateral_g'] = df['lateral_accel'].max()
        stats['avg_lateral_g'] = df['lateral_accel'].mean()
    
    if 'throttle_input' in df.columns:
        stats['avg_throttle'] = (df['throttle_input'].mean() * 100)
    
    if 'brake_input' in df.columns:
        stats['avg_brake'] = (df['brake_input'].mean() * 100)
    
    if 'distance_traveled' in df.columns:
        stats['total_distance'] = df['distance_traveled'].max()
    
    return stats


def create_comparison_metrics_table(lap1: pd.DataFrame, lap2: pd.DataFrame) -> pd.DataFrame:
    """
    Create a comparison table of key metrics between two laps
    """
    stats1 = generate_lap_summary_stats(lap1)
    stats2 = generate_lap_summary_stats(lap2)
    
    comparison = []
    for metric in stats1.keys():
        val1 = stats1.get(metric, 0)
        val2 = stats2.get(metric, 0)
        delta = val2 - val1
        delta_pct = (delta / val1 * 100) if val1 != 0 else 0
        
        comparison.append({
            'Metric': metric.replace('_', ' ').title(),
            'Lap 1': f"{val1:.2f}",
            'Lap 2': f"{val2:.2f}",
            'Delta': f"{delta:.2f}",
            'Δ %': f"{delta_pct:.1f}%"
        })
    
    return pd.DataFrame(comparison)


def export_telemetry_csv(df: pd.DataFrame, filename: str = 'telemetry_export.csv') -> bytes:
    """
    Export telemetry data to CSV format
    """
    return df.to_csv(index=False).encode('utf-8')


def create_performance_report(df: pd.DataFrame, title: str = "Lap Analysis Report") -> str:
    """
    Generate a text-based performance report
    """
    stats = generate_lap_summary_stats(df)
    
    report = f"""
╔{'='*70}╗
║ {title.center(68)} ║
╚{'='*70}╝

📊 LAP STATISTICS:
├─ Max Speed: {stats.get('max_speed', 0):.1f} km/h
├─ Avg Speed: {stats.get('avg_speed', 0):.1f} km/h
├─ Total Distance: {stats.get('total_distance', 0):.1f} m
├─ Max Steering: {stats.get('max_steering', 0):.1f}°
├─ Max Lateral G: {stats.get('max_lateral_g', 0):.2f}G
├─ Avg Throttle: {stats.get('avg_throttle', 0):.1f}%
└─ Avg Brake: {stats.get('avg_brake', 0):.1f}%

{'='*72}
    """
    
    return report
