"""
Automated Motorsports Telemetry Analysis System (AMTAS)
Analyzes race telemetry data against DISTANCE (not time) for vehicle dynamics insights.
Provides corner-by-corner handling analysis with driver technique and suspension recommendations.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Set random seed for reproducible results across runs
np.random.seed(42)
pd.set_option('mode.copy_on_write', True)

# ML Module imports
try:
    from ml_module import run_ml_pipeline
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# Advanced Features imports
try:
    from advanced_features import (
        SessionHistory, AdvancedComparison, HeatmapGenerator,
        AlertSystem, PerformanceTracker, ExportManager, AdaptiveCoaching
    )
    ADVANCED_FEATURES_AVAILABLE = True
except ImportError:
    ADVANCED_FEATURES_AVAILABLE = False


REQUIRED_COLUMNS = [
    "time",
    "speed",
    "throttle_input",
    "brake_input",
    "steering_angle",
    "yaw_rate",
    "rpm",
]
OPTIONAL_COLUMNS = ["latitude", "longitude", "cornering_speed", "energy_efficient", "gps_sector", "sector_name"]

EVENT_STYLES = {
    "oversteer": {"label": "Oversteer", "color": "#d62728", "symbol": "x"},
    "understeer": {"label": "Understeer", "color": "#ff7f0e", "symbol": "diamond"},
    "harsh_braking": {"label": "Harsh Braking", "color": "#9467bd", "symbol": "triangle-down"},
    "late_braking": {"label": "Late Braking", "color": "#8c564b", "symbol": "triangle-left"},
    "early_braking": {"label": "Early Braking", "color": "#17becf", "symbol": "triangle-right"},
    "wheel_spin": {"label": "Longitudinal Wheel Slide", "color": "#e377c2", "symbol": "star"},
    "low_rpm_issue": {"label": "Low RPM", "color": "#2ca02c", "symbol": "square"},
    "high_rpm_issue": {"label": "High RPM", "color": "#bcbd22", "symbol": "hexagon"},
}


@dataclass
class AnalysisBundle:
    name: str
    data: pd.DataFrame
    thresholds: Dict[str, float]
    events: Dict[str, pd.Series]
    event_counts: Dict[str, int]
    scores: Dict[str, float]
    grade: str
    insights: List[str]
    turn_summary: pd.DataFrame
    lap_time: float
    stats: Dict[str, float]
    sector_summary: Optional[pd.DataFrame] = None  # Sector-based analysis (if sector data available)
    ml_results: Optional[Dict] = None  # ML pipeline results (if available)
    quality_report: Optional[object] = None  # Data quality report (if available)


def clip_0_100(value: float) -> float:
    return float(np.clip(value, 0, 100))


def scale_between(value: float, good: float, bad: float) -> float:
    if bad <= good:
        return 0.0
    return float(np.clip((value - good) / (bad - good), 0.0, 1.0))


def inverse_score(value: float, good: float, bad: float) -> float:
    return clip_0_100(100 * (1 - scale_between(value, good, bad)))


def mask_ratio(mask: pd.Series) -> float:
    return float(mask.fillna(False).mean())


def count_segments(mask: pd.Series) -> int:
    clean_mask = mask.fillna(False).astype(bool)
    return int((clean_mask & ~clean_mask.shift(fill_value=False)).sum())


def segment_ids_from_mask(mask: pd.Series) -> pd.Series:
    clean_mask = mask.fillna(False).astype(bool)
    starts = clean_mask & ~clean_mask.shift(fill_value=False)
    return starts.cumsum().where(clean_mask, 0).astype(int)


def has_gps(df: pd.DataFrame) -> bool:
    required = {"latitude", "longitude"}
    if not required.issubset(df.columns):
        return False
    return bool(df[["latitude", "longitude"]].dropna().shape[0] > 10)


def has_sector_data(df: pd.DataFrame) -> bool:
    """Check if sector information is available."""
    if "sector_name" in df.columns:
        return bool(df["sector_name"].notna().sum() > 0)
    if "gps_sector" in df.columns:
        return bool(df["gps_sector"].notna().sum() > 0)
    return False


def has_cornering_speed(df: pd.DataFrame) -> bool:
    """Check if cornering speed data is available."""
    if "cornering_speed" not in df.columns:
        return False
    return bool(df["cornering_speed"].notna().sum() > 0)


def has_energy_efficient(df: pd.DataFrame) -> bool:
    """Check if energy efficiency data is available."""
    if "energy_efficient" not in df.columns:
        return False
    return bool(df["energy_efficient"].notna().sum() > 0)


def safe_quantile(series: pd.Series, q: float, default: float) -> float:
    clean = series.replace([np.inf, -np.inf], np.nan).dropna()
    if clean.empty:
        return float(default)
    return float(clean.quantile(q))


def normalize_control_input(series: pd.Series) -> pd.Series:
    clean = series.copy()
    high = safe_quantile(clean.abs(), 0.99, 1.0)
    if high > 1.5 and high <= 100.5:
        clean = clean / 100.0
    elif high > 1.5:
        clean = clean / high
    return clean.clip(0, 1)


def parse_time_column(time_series: pd.Series) -> pd.Series:
    numeric = pd.to_numeric(time_series, errors="coerce")
    if numeric.notna().mean() >= 0.8:
        return numeric

    parsed = pd.to_datetime(time_series, errors="coerce")
    valid = parsed.dropna()
    if valid.empty:
        raise ValueError("The `time` column must be numeric seconds or a parseable datetime.")
    origin = valid.iloc[0]
    return (parsed - origin).dt.total_seconds()


@st.cache_data(show_spinner=False)
def read_csv_bytes(file_bytes: bytes) -> pd.DataFrame:
    return pd.read_csv(io.BytesIO(file_bytes))


def clean_telemetry_data(raw_df: pd.DataFrame) -> pd.DataFrame:
    if raw_df.empty:
        raise ValueError("The uploaded CSV is empty.")

    df = raw_df.copy()
    df.columns = [str(column).strip().lower() for column in df.columns]

    missing_columns = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns: {', '.join(missing_columns)}")

    df["time"] = parse_time_column(df["time"])

    numeric_columns = [column for column in REQUIRED_COLUMNS if column != "time"]
    numeric_columns += [column for column in OPTIONAL_COLUMNS if column in df.columns]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce")

    df = df.dropna(subset=["time"]).sort_values("time").reset_index(drop=True)
    if df.empty:
        raise ValueError("No valid telemetry rows remain after parsing the `time` column.")

    for column in numeric_columns:
        if df[column].notna().sum() == 0:
            raise ValueError(f"Column `{column}` does not contain usable numeric values.")

    df[numeric_columns] = df[numeric_columns].interpolate(method="linear", limit_direction="both")
    df[numeric_columns] = df[numeric_columns].ffill().bfill()

    df["throttle_input"] = normalize_control_input(df["throttle_input"])
    df["brake_input"] = normalize_control_input(df["brake_input"])
    df["speed"] = df["speed"].clip(lower=0)
    df["rpm"] = df["rpm"].clip(lower=0)

    df["relative_time"] = df["time"] - df["time"].iloc[0]
    time_delta = df["relative_time"].diff()
    default_dt = safe_quantile(time_delta[time_delta > 0], 0.5, 0.05)
    df["dt"] = time_delta.where(time_delta > 1e-6, default_dt).fillna(default_dt)
    return df.reset_index(drop=True)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["steering_abs"] = data["steering_angle"].abs()
    data["yaw_abs"] = data["yaw_rate"].abs()  # Fixed: was yaw_moment
    data["acceleration"] = data["speed"].diff().fillna(0) / data["dt"].replace(0, np.nan)
    data["acceleration"] = data["acceleration"].replace([np.inf, -np.inf], 0).fillna(0)
    # Slip angle estimation: Combines steering input and yaw rate to estimate vehicle slip angle
    # True slip angle = arctan(lateral_velocity / longitudinal_velocity) but we approximate using steering + yaw
    # This represents the angle between vehicle heading and direction of travel
    data["slip_severity"] = data["steering_abs"] + (data["yaw_abs"] * 0.5)  # Slip estimated from steering + yaw
    data["input_change"] = (
        data["throttle_input"].diff().fillna(0).abs()
        + data["brake_input"].diff().fillna(0).abs()
    )
    data["stability_index"] = data["yaw_rate"] / (data["steering_abs"] + 0.01)
    data["yaw_response"] = data["yaw_abs"] / (data["steering_abs"] + 0.1)
    data["rpm_efficiency"] = data["rpm"] / 5000  # Normalized to typical peak RPM
    
    # DISTANCE TRAVELED - cumulative distance in meters
    # Speed is in km/h, dt is in seconds. Convert: distance(m) = speed(km/h) * dt(s) / 3.6
    data["distance_traveled"] = (data["speed"] * data["dt"] / 3.6).cumsum()
    
    # Lateral acceleration for handling analysis
    data["lateral_accel"] = (data["slip_severity"] * data["speed"] / 127).clip(0, 2.5)
    
    # Preserve optional columns if present
    for col in OPTIONAL_COLUMNS:
        if col in df.columns:
            data[col] = df[col]
    
    return data


def compute_thresholds(data: pd.DataFrame) -> Dict[str, float]:
    # Adaptive corner threshold: if max steering is low, use lower threshold
    steering_max = float(data["steering_abs"].max())
    steering_mean = float(data["steering_abs"].mean())
    
    # More adaptive threshold based on steering distribution
    if steering_max < 0.5:
        # Extremely minimal steering - detect even tiny movements
        corner_threshold = float(max(0.2, safe_quantile(data["steering_abs"], 0.50, 0.3)))
    elif steering_max < 1.0:
        # Very minimal steering angles
        corner_threshold = float(max(0.3, safe_quantile(data["steering_abs"], 0.55, 0.5)))
    elif steering_max < 3.0:
        # Small steering angles
        corner_threshold = float(max(0.5, safe_quantile(data["steering_abs"], 0.60, 1.0)))
    elif steering_max < 10.0:
        # Moderate steering
        corner_threshold = float(max(2.0, safe_quantile(data["steering_abs"], 0.65, 3.0)))
    else:
        # Large steering angles
        corner_threshold = float(max(5.0, safe_quantile(data["steering_abs"], 0.70, 6.0)))
    
    return {
        "brake_threshold": float(np.clip(max(0.20, safe_quantile(data["brake_input"], 0.70, 0.25)), 0.20, 0.55)),
        "brake_high": float(np.clip(max(0.55, safe_quantile(data["brake_input"], 0.90, 0.75)), 0.55, 0.98)),
        "throttle_threshold": float(np.clip(max(0.35, safe_quantile(data["throttle_input"], 0.55, 0.40)), 0.35, 0.75)),
        "throttle_high": float(np.clip(max(0.65, safe_quantile(data["throttle_input"], 0.85, 0.70)), 0.65, 0.98)),
        "corner_threshold": corner_threshold,
        "slip_high": float(max(4.0, safe_quantile(data["slip_severity"], 0.85, 4.0))),
        "slip_medium": float(max(2.5, safe_quantile(data["slip_severity"], 0.65, 2.5))),
        "yaw_high": float(max(0.10, safe_quantile(data["yaw_abs"], 0.85, 0.10))),
        "yaw_response_low": float(max(0.015, safe_quantile(data["yaw_response"], 0.25, 0.03))),
        # pitch threshold removed
        "stability_high": float(max(0.20, safe_quantile(data["stability_index"].abs(), 0.90, 0.25))),
        "mid_speed": float(safe_quantile(data["speed"], 0.55, float(data["speed"].median()))),
        "high_speed": float(safe_quantile(data["speed"], 0.75, float(data["speed"].median()))),
        "rpm_low": float(max(3000, safe_quantile(data["rpm"], 0.25, 3500))),
        "rpm_high": float(max(6500, safe_quantile(data["rpm"], 0.85, 7000))),
        # max_gear removed
    }


def add_zone_columns(data: pd.DataFrame, thresholds: Dict[str, float]) -> pd.DataFrame:
    df = data.copy()
    df["braking_zone"] = df["brake_input"] > thresholds["brake_threshold"]
    df["throttle_zone"] = df["throttle_input"] > thresholds["throttle_threshold"]
    df["corner_zone"] = df["steering_abs"] > thresholds["corner_threshold"]
    df["corner_id"] = segment_ids_from_mask(df["corner_zone"])
    return df


def detect_corner_phases(data: pd.DataFrame) -> pd.Series:
    """
    Detect corner phases: ENTRY, APEX (MID), EXIT for each turn.
    Returns a Series with phase classification for each row.
    """
    phases = pd.Series("STRAIGHT", index=data.index)
    
    for turn_id in sorted(data[data["corner_id"] > 0]["corner_id"].unique()):
        turn_section = data[data["corner_id"] == turn_id]
        if turn_section.empty:
            continue
        
        turn_idx = turn_section.index
        start_idx = turn_idx.min()
        end_idx = turn_idx.max()
        turn_length = end_idx - start_idx + 1
        
        # Divide turn into three equal parts
        entry_end = start_idx + turn_length // 3
        exit_start = start_idx + 2 * (turn_length // 3)
        
        phases.iloc[start_idx:entry_end] = "ENTRY"
        phases.iloc[entry_end:exit_start] = "MID"
        phases.iloc[exit_start:end_idx+1] = "EXIT"
    
    return phases


def analyze_braking_timing(data: pd.DataFrame) -> Dict[str, pd.Series]:
    early_mask = pd.Series(False, index=data.index)
    late_mask = pd.Series(False, index=data.index)
    records: List[Dict[str, float]] = []

    dt = max(float(data["dt"].median()), 0.01)
    lookback_samples = max(5, int(round(3.0 / dt)))

    for turn_id in sorted(data["corner_id"].unique()):
        if turn_id <= 0:
            continue

        turn_section = data[data["corner_id"] == turn_id]
        turn_start_idx = int(turn_section.index.min())
        lookback_start = max(0, turn_start_idx - lookback_samples)
        approach = data.iloc[lookback_start : turn_start_idx + 1]

        brake_groups = segment_ids_from_mask(approach["braking_zone"])
        valid_groups = [group for group in brake_groups.unique() if group > 0]
        if not valid_groups:
            continue

        final_brake_zone = approach[brake_groups == int(valid_groups[-1])]
        brake_start_idx = int(final_brake_zone.index.min())

        records.append(
            {
                "turn_start_idx": float(turn_start_idx),
                "brake_start_idx": float(brake_start_idx),
                "approach_time": float(data.loc[turn_start_idx, "relative_time"] - data.loc[brake_start_idx, "relative_time"]),
                "entry_speed": float(data.loc[turn_start_idx, "speed"]),
                "speed_drop": float(data.loc[brake_start_idx, "speed"] - data.loc[turn_start_idx, "speed"]),
            }
        )

    if not records:
        return {"early_braking": early_mask, "late_braking": late_mask}

    braking_df = pd.DataFrame(records)
    median_approach = float(braking_df["approach_time"].median())
    median_entry_speed = float(braking_df["entry_speed"].median())
    median_speed_drop = float(braking_df["speed_drop"].median())

    if len(braking_df) >= 3:
        early_cutoff = float(braking_df["approach_time"].quantile(0.70))
        late_cutoff = float(braking_df["approach_time"].quantile(0.30))
    else:
        early_cutoff = max(1.8, median_approach * 1.20)
        late_cutoff = min(1.0, median_approach * 0.80 if median_approach > 0 else 1.0)

    for row in braking_df.itertuples(index=False):
        start_idx = int(row.brake_start_idx)
        end_idx = int(row.turn_start_idx)
        if row.approach_time >= early_cutoff and row.entry_speed <= median_entry_speed * 0.92:
            early_mask.loc[start_idx:end_idx] = True
        elif (
            row.approach_time <= late_cutoff
            and row.entry_speed >= median_entry_speed * 1.05
            and row.speed_drop >= median_speed_drop * 0.90
        ):
            late_mask.loc[start_idx:end_idx] = True

    return {"early_braking": early_mask, "late_braking": late_mask}


def detect_events(data: pd.DataFrame, thresholds: Dict[str, float]) -> Dict[str, pd.Series]:
    # Traction loss: when slip exceeds threshold in corners
    traction_loss = (
        data["corner_zone"]
        & (data["slip_severity"] > thresholds["slip_high"])
    )
    # Oversteer: SUBSET of traction loss with high yaw rate
    # Oversteer is when the rear slides more than the front
    oversteer = (
        traction_loss
        & (data["yaw_abs"] > thresholds["yaw_high"])
    )
    # Understeer: SUBSET of traction loss with low yaw response (MUTUALLY EXCLUSIVE from oversteer)
    # Understeer is when the front loses grip (insufficient yaw)
    # Important: understeer excludes oversteer to avoid dual reporting of same event
    understeer = (
        traction_loss
        & (data["yaw_response"] < thresholds["yaw_response_low"])
        & ~oversteer  # Explicitly exclude oversteer cases
    )
    # Note: These are explicit subsets. Some traction_loss events may be neither oversteer nor understeer.
    harsh_braking = (
        data["braking_zone"]
        & (data["brake_input"] > thresholds["brake_high"])
    )
    wheel_spin = (
        data["throttle_zone"]
        & (data["throttle_input"] > thresholds["throttle_high"])
        & (data["slip_severity"] > thresholds["slip_high"])
        & (data["speed"] < thresholds["high_speed"] * 1.10)
    )
    low_rpm_issue = (
        data["throttle_zone"]
        & (data["rpm"] < thresholds["rpm_low"])
        & (data["speed"] < thresholds["high_speed"])
    )
    high_rpm_issue = (
        data["throttle_zone"]
        & (data["rpm"] > thresholds["rpm_high"])
    )
    # Remove unstable parameter as requested - oversteer/understeer cover instability
    braking_timing = analyze_braking_timing(data)

    return {
        "oversteer": oversteer.fillna(False),
        "understeer": understeer.fillna(False),
        "traction_loss": traction_loss.fillna(False),
        "harsh_braking": harsh_braking.fillna(False),
        "late_braking": braking_timing["late_braking"].fillna(False),
        "early_braking": braking_timing["early_braking"].fillna(False),
        "wheel_spin": wheel_spin.fillna(False),
        "low_rpm_issue": low_rpm_issue.fillna(False),
        "high_rpm_issue": high_rpm_issue.fillna(False),
    }


def compute_scores(
    data: pd.DataFrame, events: Dict[str, pd.Series], thresholds: Dict[str, float]
) -> Dict[str, float]:
    # Handling precision: based on slip control and steering smoothness
    slip_metric = float(data["slip_severity"].mean())
    slip_score = inverse_score(slip_metric, 1.5, 8.0)
    
    steering_smoothness = float((data["steering_abs"].diff().abs()).mean())
    steering_score = inverse_score(steering_smoothness, 0.5, 5.0)
    
    handling_score = clip_0_100((slip_score * 0.6+ steering_score * 0.4))
    
    # Stability: measure of predictable vehicle balance - MINIMUM 70 AS PER REQUIREMENT
    stability_metric = mask_ratio(events["oversteer"]) + mask_ratio(events["understeer"])
    stability_score = clip_0_100(100 - stability_metric * 300)
    # Apply minimum stability floor of 70
    stability_score = max(70.0, stability_score)
    
    # Braking: smooth pedal application without upset
    braking_smoothness = float(data.loc[data["brake_input"] > 0.1, "input_change"].mean())
    braking_score = inverse_score(braking_smoothness, 0.03, 0.25)
    
    # Overall consistency focused on handling, not speed
    consistency_score = clip_0_100(
        handling_score * 0.40
        + stability_score * 0.35
        + braking_score * 0.25
    )

    return {
        "handling_score": round(handling_score, 1),
        "stability_score": round(stability_score, 1),
        "braking_score": round(braking_score, 1),
        "consistency_score": round(consistency_score, 1),
    }


def classify_grade(consistency_score: float) -> str:
    if consistency_score >= 85:
        return "Advanced Precision"
    if consistency_score >= 75:
        return "Good Control"
    if consistency_score >= 60:
        return "Room for Refinement"
    return "Developing Skills"


def dominant_location_label(data: pd.DataFrame, mask: pd.Series) -> Tuple[int, float]:
    """Returns (turn_id, distance_at_location)."""
    active_rows = data.loc[mask.fillna(False)]
    if active_rows.empty:
        return (0, 0.0)

    turn_counts = active_rows.loc[active_rows["corner_id"] > 0, "corner_id"].value_counts()
    if not turn_counts.empty:
        turn_id = int(turn_counts.index[0])
        turn_segment = data[data["corner_id"] == turn_id]
        distance = float(turn_segment["distance_traveled"].mean())
        return (turn_id, distance)

    first_index = int(active_rows.index[0])
    distance = float(data.loc[first_index, "distance_traveled"])
    return (0, distance)


def build_turn_summary(data: pd.DataFrame, events: Dict[str, pd.Series]) -> pd.DataFrame:
    """Build turn-by-turn summary with sector information if available."""
    rows: List[Dict[str, object]] = []
    
    # Determine if we have sector data
    has_sector = has_sector_data(data)
    sector_col = "sector_name" if "sector_name" in data.columns else "gps_sector" if "gps_sector" in data.columns else None

    corner_ids = [cid for cid in sorted(data["corner_id"].unique()) if cid > 0]
    
    # Handle case of no corners detected
    if not corner_ids:
        return pd.DataFrame([{
            "Turn": "No Corners",
            "Distance (m)": "—",
            "Entry Speed (km/h)": round(float(data["speed"].mean()), 1),
            "Min Speed (km/h)": round(float(data["speed"].min()), 1),
            "Peak Slip (°)": round(float(data["slip_severity"].max()), 1),
            "Max Lateral G": round(float(data["lateral_accel"].max()), 2),
            "Issues": "Insufficient steering activity detected",
        }])

    for turn_id in corner_ids:
        segment = data[data["corner_id"] == turn_id]
        start_idx = int(segment.index.min())
        end_idx = int(segment.index.max())
        issues = []

        for key in [
            "oversteer",
            "understeer",
            "harsh_braking",
            "late_braking",
            "early_braking",
            "wheel_spin",
        ]:
            if events[key].loc[start_idx:end_idx].any():
                issues.append(EVENT_STYLES[key]["label"])

        distance_start = float(segment["distance_traveled"].iloc[0])
        distance_end = float(segment["distance_traveled"].iloc[-1])
        turn_length = distance_end - distance_start
        distance_mid = (distance_start + distance_end) / 2
        
        row = {
            "Turn": f"T{int(turn_id)}",
            "Distance (m)": f"{distance_mid:.0f}",
            "Turn Length (m)": round(turn_length, 0),
            "Entry Speed (km/h)": round(float(segment["speed"].iloc[0]), 1),
            "Min Speed (km/h)": round(float(segment["speed"].min()), 1),
            "Peak Slip (°)": round(float(segment["slip_severity"].max()), 1),
            "Max Lateral G": round(float(segment["lateral_accel"].max()), 2),
            "Issues": ", ".join(issues[:2]) if issues else "✓ Clean",
        }
        
        # Add sector information if available
        if has_sector and sector_col:
            sector_vals = segment[sector_col].dropna().unique()
            if len(sector_vals) > 0:
                row["Sector"] = str(sector_vals[0])
        
        rows.append(row)

    return pd.DataFrame(rows)


def build_sector_summary(data: pd.DataFrame, events: Dict[str, pd.Series]) -> Optional[pd.DataFrame]:
    """Build sector-based analysis summary if sector data is available."""
    if not has_sector_data(data):
        return None
    
    # Determine which sector column to use
    sector_col = "sector_name" if "sector_name" in data.columns else "gps_sector"
    
    rows: List[Dict[str, object]] = []
    
    for sector_id in sorted(data[sector_col].dropna().unique()):
        segment = data[data[sector_col] == sector_id]
        start_idx = int(segment.index.min())
        end_idx = int(segment.index.max())
        issues = []
        
        for key in ["oversteer", "understeer", "harsh_braking", "late_braking", "early_braking"]:
            if events[key].loc[start_idx:end_idx].any():
                issues.append(EVENT_STYLES[key]["label"])
        
        # Calculate proper sector distance
        sector_start_dist = float(segment["distance_traveled"].min())
        sector_end_dist = float(segment["distance_traveled"].max())
        sector_dist = sector_end_dist - sector_start_dist
        
        row = {
            "Sector": str(sector_id),
            "Start (m)": f"{sector_start_dist:.0f}",
            "End (m)": f"{sector_end_dist:.0f}",
            "Length (m)": f"{sector_dist:.0f}",
            "Avg Speed": round(float(segment["speed"].mean()), 1),
            "Peak Slip (°)": round(float(segment["slip_severity"].max()), 1),
            "Max Lateral G": round(float(segment["lateral_accel"].max()), 2),
            "Issues": ", ".join(issues[:2]) if issues else "✓ Clean",
        }
        
        # Add cornering speed if available
        if "cornering_speed" in segment.columns:
            cornering_speeds = segment["cornering_speed"].dropna()
            if len(cornering_speeds) > 0:
                row["Avg Corner Speed"] = round(float(cornering_speeds.mean()), 1)
        
        # Add energy efficiency if available
        if "energy_efficient" in segment.columns:
            energy_scores = segment["energy_efficient"].dropna()
            if len(energy_scores) > 0:
                row["Energy Score"] = round(float(energy_scores.mean()), 1)
        
        rows.append(row)
    
    return pd.DataFrame(rows) if rows else None


def generate_insights(
    data: pd.DataFrame,
    events: Dict[str, pd.Series],
    event_counts: Dict[str, int],
    scores: Dict[str, float],
    thresholds: Dict[str, float],
) -> List[str]:
    """Generate handling-focused insights with driver & suspension recommendations."""
    ranked_insights: List[Tuple[int, str]] = []

    def add(priority: int, text: str) -> None:
        ranked_insights.append((priority, text))

    # OVERSTEER
    if event_counts["oversteer"] > 0:
        turn_id, distance = dominant_location_label(data, events["oversteer"])
        peak_slip = float(data.loc[events["oversteer"], "slip_severity"].max())
        location_str = f"T{turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(100, f"[OVERSTEER @{location_str}] Peak slip {peak_slip:.1f}°, rear traction loss. "
                f"Driver: reduce entry speed 2-3 km/h, delay throttle. "
                f"Setup: increase rear ARB +20%, soften front ARB -10%, increase front damping +15%.")

    # UNDERSTEER
    if event_counts["understeer"] > 0:
        turn_id, distance = dominant_location_label(data, events["understeer"])
        location_str = f"T{turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(95, f"[UNDERSTEER @{location_str}] Front insufficient grip mid-corner. "
                f"Driver: brake earlier before turn-in, use progressive steering. "
                f"Setup: reduce front ARB -20%, increase front camber -0.4°, lower front 5mm.")

    # HARSH BRAKING
    if event_counts["harsh_braking"] > 0:
        turn_id, distance = dominant_location_label(data, events["harsh_braking"])
        location_str = f"T{turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(92, f"[HARSH BRAKING @{location_str}] Sudden brake application detected. "
                f"Driver: build pedal pressure gradually 0.5-1.0s, modulate through corner. "
                f"Setup: soften front springs -8%, reduce front ride 5mm, adjust brake bias forward 1%.")

    # LATE BRAKING
    if event_counts["late_braking"] > 0:
        turn_id, distance = dominant_location_label(data, events["late_braking"])
        location_str = f"T{turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(88, f"[LATE BRAKING @{location_str}] Entry speed too high into corner. "
                f"Driver: brake 0.5-1.0s earlier, spread deceleration phase longer. "
                f"Setup: increase brake reactivity via bias adjustment forward 1-2%.")

    # EARLY BRAKING
    elif event_counts["early_braking"] > 0:
        turn_id, distance = dominant_location_label(data, events["early_braking"])
        location_str = f"T{turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(82, f"[EARLY BRAKING @{location_str}] Scrubbing speed unnecessarily early. "
                f"Driver: brake 0.3-0.5s later, use stronger pedal for shorter duration. "
                f"Setup: fine-tune brake bias for confidence and consistency.")

    # WHEEL SPIN
    if event_counts["wheel_spin"] > 0:
        turn_id, distance = dominant_location_label(data, events["wheel_spin"])
        location_str = f"T{turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(84, f"[LONGITUDINAL WHEEL SLIDE @{location_str}] Wheelspin on exit under acceleration. "
                f"Driver: wait for steering <5° before full throttle, squeeze progressively. "
                f"Setup: increase rear spring +10%, rear ARB +20%, reduce rear rebound damping -10%.")

    # INSTABILITY - REMOVED
    # Platform instability covered by oversteer/understeer events; over-reporting was causing confusion

    # RPM EFFICIENCY (secondary)
    if event_counts["high_rpm_issue"] > 0:
        add(65, f"[RPM EFFICIENCY] Frequent overshifting on straights (>{thresholds['rpm_high']:.0f} RPM). "
                f"Driver: shift 500 RPM earlier. Note: Higher RPM means increased fuel consumption.")

    if event_counts["low_rpm_issue"] > 0:
        add(63, f"[RPM EFFICIENCY] Engine below efficient band (>{thresholds['rpm_low']:.0f} RPM) during acceleration. "
                f"Driver: downshift earlier. Note: Lower RPM zones reduce fuel consumption but may sacrifice responsiveness.")

    # GENERAL HANDLING
    if scores.get("braking_score", 0) < 70:
        add(60, "[BRAKING TECHNIQUE] Pedal application lacks smoothness and progression. "
                "Gradual build-up with modulation will improve platform balance and confidence.")

    if scores.get("handling_score", 0) < 70:
        add(58, "[STEERING PRECISION] Inputs are wide or abrupt, reducing turn-in precision. "
                "Reduce steering wheel movements and practice single-input corners.")

    if not ranked_insights:
        add(40, "[SOLID LAP] Fundamentals are strong. Next improvements: "
                "(1) Feed throttle slightly earlier on exits when steering is unraveling, "
                "(2) Finish brake release smoother before apex, (3) Reduce mid-corner modulation.")

    ranked_insights.sort(key=lambda x: x[0], reverse=True)
    unique_text = []
    seen = set()
    for _, text in ranked_insights:
        if text not in seen:
            seen.add(text)
            unique_text.append(text)
        if len(unique_text) >= 8:
            break
    
    return unique_text


def build_stats(data: pd.DataFrame) -> Dict[str, float]:
    """Build statistics dictionary with comprehensive fallback handling."""
    # Check for required columns
    if data.empty:
        return {
            "lap_time": 0.0,
            "lap_distance": 0.0,
            "average_speed": 0.0,
            "top_speed": 0.0,
            "turns_detected": 0.0,
        }
    
    # Calculate lap time - prefer "time" column
    if "time" in data.columns and len(data["time"]) >= 2:
        try:
            lap_time = float(data["time"].iloc[-1] - data["time"].iloc[0])
        except:
            lap_time = float(data["relative_time"].iloc[-1]) if "relative_time" in data.columns else 0.0
    elif "relative_time" in data.columns:
        try:
            lap_time = float(data["relative_time"].iloc[-1])
        except:
            lap_time = 0.0
    else:
        lap_time = 0.0
    
    # Calculate total distance
    if "distance_traveled" in data.columns and len(data["distance_traveled"]) > 0:
        try:
            total_distance = float(data["distance_traveled"].iloc[-1])
        except:
            total_distance = 0.0
    else:
        total_distance = 0.0
    
    # Calculate average and top speed
    if "speed" in data.columns:
        try:
            average_speed = float(data["speed"].mean())
            top_speed = float(data["speed"].max())
        except:
            average_speed = 0.0
            top_speed = 0.0
    else:
        average_speed = 0.0
        top_speed = 0.0
    
    # Turns detected
    if "corner_id" in data.columns:
        try:
            turns_detected = float(int(data["corner_id"].max()))
        except:
            turns_detected = 0.0
    else:
        turns_detected = 0.0
    
    return {
        "lap_time": lap_time,
        "lap_distance": total_distance,
        "average_speed": average_speed,
        "top_speed": top_speed,
        "turns_detected": turns_detected,
    }


def analyze_uploaded_file(uploaded_file) -> AnalysisBundle:
    # Set random seed for reproducibility before any analysis
    np.random.seed(42)
    
    raw_df = read_csv_bytes(uploaded_file.getvalue())
    # Sort by time to ensure consistent ordering
    raw_df = raw_df.sort_values("time", ignore_index=True)
    
    cleaned = clean_telemetry_data(raw_df)
    featured = engineer_features(cleaned)
    thresholds = compute_thresholds(featured)
    zoned = add_zone_columns(featured, thresholds)
    # Add corner phase information (ENTRY, MID, EXIT)
    zoned["corner_phase"] = detect_corner_phases(zoned)
    events = detect_events(zoned, thresholds)
    event_counts = {key: count_segments(mask) for key, mask in events.items()}
    scores = compute_scores(zoned, events, thresholds)
    grade = classify_grade(scores["consistency_score"])
    insights = generate_insights(zoned, events, event_counts, scores, thresholds)
    turn_summary = build_turn_summary(zoned, events)
    sector_summary = build_sector_summary(zoned, events)  # Optional sector analysis
    stats = build_stats(zoned)
    
    # Run ML pipeline if available
    ml_results = None
    if ML_AVAILABLE:
        try:
            ml_results = run_ml_pipeline(zoned)
        except Exception as e:
            st.warning(f"⚠️ ML analysis skipped: {str(e)}")

    return AnalysisBundle(
        name=uploaded_file.name,
        data=zoned,
        thresholds=thresholds,
        events=events,
        event_counts=event_counts,
        scores=scores,
        grade=grade,
        insights=insights,
        turn_summary=turn_summary,
        sector_summary=sector_summary,
        lap_time=stats["lap_time"],
        stats=stats,
        ml_results=ml_results,
    )


def style_figure(fig: go.Figure, title: str, x_label: str, y_label: str, height: int = 380) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        title=dict(text=title, font=dict(size=18, color="#1a1a1a")),
        height=height,
        margin=dict(l=60, r=40, t=70, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        font=dict(size=12),
    )
    # Add 10-meter steps on distance X-axis with enhanced visibility
    if "Distance" in x_label:
        fig.update_xaxes(
            title=dict(text=x_label, font=dict(size=14, color="#000000"), standoff=20),
            showgrid=True,
            gridcolor="rgba(200, 200, 200, 0.4)",
            gridwidth=1,
            dtick=10,
            tickfont=dict(size=12, color="#333333"),
            tickangle=-45,
            rangeslider=dict(visible=False),
            type="linear",
            showline=True,
            linewidth=2,
            linecolor="rgb(100, 100, 100)",
            mirror=True
        )
    else:
        fig.update_xaxes(
            title=dict(text=x_label, font=dict(size=14, color="#000000"), standoff=20),
            showgrid=True,
            gridcolor="rgba(200, 200, 200, 0.4)",
            gridwidth=1,
            tickfont=dict(size=12, color="#333333"),
            showline=True,
            linewidth=2,
            linecolor="rgb(100, 100, 100)",
            mirror=True
        )
    fig.update_yaxes(
        title=dict(text=y_label, font=dict(size=14, color="#000000"), standoff=20),
        showgrid=True,
        gridcolor="rgba(200, 200, 200, 0.25)",
        gridwidth=1,
        tickfont=dict(size=12, color="#333333"),
        showline=True,
        linewidth=2,
        linecolor="rgb(100, 100, 100)",
        mirror=True
    )
    return fig


def add_event_markers(
    fig: go.Figure,
    data: pd.DataFrame,
    event_masks: Dict[str, pd.Series],
    x_column: str,
    y_column: str,
    keys: List[str],
) -> go.Figure:
    for key in keys:
        mask = event_masks[key]
        if not mask.any():
            continue
        style = EVENT_STYLES[key]
        subset = data.loc[mask]
        fig.add_trace(
            go.Scatter(
                x=subset[x_column],
                y=subset[y_column],
                mode="markers",
                name=style["label"],
                marker=dict(color=style["color"], symbol=style["symbol"], size=8, line=dict(width=0)),
                hovertemplate=f"{style['label']}<br>%{{x:.2f}}<br>%{{y:.2f}}<extra></extra>",
            )
        )
    return fig


def build_speed_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["speed"],
            mode="lines",
            name="Speed",
            line=dict(color="#1f77b4", width=3),
            hovertemplate="Distance: %{x:.1f}m<br>Speed: %{y:.1f} km/h<extra></extra>",
        )
    )
    
    # Add turn number markers on X-axis
    for turn_id in sorted(data[data["corner_id"] > 0]["corner_id"].unique()):
        turn_segment = data[data["corner_id"] == turn_id]
        turn_distance = float(turn_segment["distance_traveled"].mean())
        fig.add_vline(x=turn_distance, line_dash="dash", line_color="rgba(100,100,100,0.3)", annotation_text=f"T{int(turn_id)}", annotation_position="top")
    
    return style_figure(fig, "Speed vs Distance Traveled", "Distance (m)", "Speed (km/h)")


def build_controls_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data.copy()
    data["throttle_pct"] = data["throttle_input"] * 100
    data["brake_pct"] = data["brake_input"] * 100

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["throttle_pct"],
            mode="lines",
            name="Throttle",
            line=dict(color="#2ca02c", width=3),
            hovertemplate="Distance: %{x:.1f}m<br>Throttle: %{y:.1f}%<extra></extra>",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["brake_pct"],
            mode="lines",
            name="Brake",
            line=dict(color="#d62728", width=3),
            hovertemplate="Distance: %{x:.1f}m<br>Brake: %{y:.1f}%<extra></extra>",
        )
    )
    
    # Add turn number markers on X-axis
    for turn_id in sorted(data[data["corner_id"] > 0]["corner_id"].unique()):
        turn_segment = data[data["corner_id"] == turn_id]
        turn_distance = float(turn_segment["distance_traveled"].mean())
        fig.add_vline(x=turn_distance, line_dash="dash", line_color="rgba(100,100,100,0.3)", annotation_text=f"T{int(turn_id)}", annotation_position="top")
    
    return style_figure(fig, "Throttle & Brake vs Distance", "Distance (m)", "Pedal Input (%)")


def build_slip_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["slip_severity"],
            mode="lines",
            name="Slip Severity",
            line=dict(color="#ff7f0e", width=3),
            hovertemplate="Distance: %{x:.1f}m<br>Slip: %{y:.2f}°<extra></extra>",
        )
    )
    return style_figure(fig, "Slip Angle vs Distance", "Distance (m)", "Slip Angle (°)")


def build_lateral_accel_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["lateral_accel"],
            mode="lines",
            name="Lateral Acceleration",
            line=dict(color="#e377c2", width=3),
            hovertemplate="Distance: %{x:.1f}m<br>Lateral G: %{y:.2f}<extra></extra>",
        )
    )
    
    # Add turn number markers on X-axis
    for turn_id in sorted(data[data["corner_id"] > 0]["corner_id"].unique()):
        turn_segment = data[data["corner_id"] == turn_id]
        turn_distance = float(turn_segment["distance_traveled"].mean())
        fig.add_vline(x=turn_distance, line_dash="dash", line_color="rgba(100,100,100,0.3)", annotation_text=f"T{int(turn_id)}", annotation_position="top")
    
    return style_figure(fig, "Lateral Acceleration vs Distance", "Distance (m)", "Lateral G (m/s²)")


def build_steering_yaw_figure(bundle: AnalysisBundle) -> go.Figure:
    """Overlay steering angle and yaw rate vs distance on same graph."""
    data = bundle.data
    fig = go.Figure()
    
    # Add steering angle on left axis
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["steering_angle"],
            mode="lines",
            name="Steering Angle",
            line=dict(color="#1f77b4", width=3),
            yaxis="y1",
            hovertemplate="Distance: %{x:.1f}m<br>Steering: %{y:.2f}°<extra></extra>",
        )
    )
    
    # Add yaw rate on right axis
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["yaw_rate"],
            mode="lines",
            name="Yaw Rate",
            line=dict(color="#ff7f0e", width=3),
            yaxis="y2",
            hovertemplate="Distance: %{x:.1f}m<br>Yaw Rate: %{y:.3f}°/s<extra></extra>",
        )
    )
    
    fig.update_layout(
        template="plotly_white",
        title=dict(text="Steering Angle & Yaw Rate vs Distance", font=dict(size=18, color="#1a1a1a")),
        height=380,
        margin=dict(l=60, r=100, t=70, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified",
        font=dict(size=12),
        xaxis=dict(
            title=dict(text="Distance (m)", font=dict(size=14, color="#000000"), standoff=20),
            showgrid=True,
            gridcolor="rgba(200, 200, 200, 0.4)",
            gridwidth=1,
            dtick=10,
            tickfont=dict(size=12, color="#333333"),
            tickangle=-45,
            showline=True,
            linewidth=2,
            linecolor="rgb(100, 100, 100)",
            mirror=True
        ),
        yaxis=dict(
            title=dict(text="Steering Angle (°)", font=dict(size=14, color="#000000"), standoff=20),
            showgrid=True,
            gridcolor="rgba(200, 200, 200, 0.25)",
            gridwidth=1,
            tickfont=dict(size=12, color="#333333"),
            showline=True,
            linewidth=2,
            linecolor="rgb(100, 100, 100)",
            mirror=True
        ),
        yaxis2=dict(
            title=dict(text="Yaw Rate (°/s)", font=dict(size=14, color="#000000"), standoff=20),
            overlaying="y",
            side="right",
            showgrid=False,
            tickfont=dict(size=12, color="#333333"),
            showline=True,
            linewidth=2,
            linecolor="rgb(100, 100, 100)",
            mirror=True
        ),
    )
    
    # Add turn number markers on X-axis
    for turn_id in sorted(data[data["corner_id"] > 0]["corner_id"].unique()):
        turn_segment = data[data["corner_id"] == turn_id]
        turn_distance = float(turn_segment["distance_traveled"].mean())
        fig.add_vline(x=turn_distance, line_dash="dash", line_color="rgba(100,100,100,0.3)", annotation_text=f"T{int(turn_id)}", annotation_position="top")
    
    return fig


def build_rpm_evolution_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["rpm"],
            mode="lines",
            name="RPM",
            line=dict(color="#9467bd", width=3),
            hovertemplate="Distance: %{x:.1f}m<br>RPM: %{y:.0f}<extra></extra>",
        )
    )
    
    fig.add_hrect(
        y0=bundle.thresholds["rpm_low"],
        y1=bundle.thresholds["rpm_high"],
        fillcolor="rgba(46, 204, 113, 0.12)",
        line_width=0,
        annotation_text="Efficient RPM band",
        annotation_position="top left",
    )
    
    # Add turn number markers on X-axis
    for turn_id in sorted(data[data["corner_id"] > 0]["corner_id"].unique()):
        turn_segment = data[data["corner_id"] == turn_id]
        turn_distance = float(turn_segment["distance_traveled"].mean())
        fig.add_vline(x=turn_distance, line_dash="dash", line_color="rgba(100,100,100,0.3)", annotation_text=f"T{int(turn_id)}", annotation_position="top")
    
    fig = style_figure(fig, "RPM Evolution vs Distance", "Distance (m)", "RPM", height=380)
    return fig


def build_cornering_speed_figure(bundle: AnalysisBundle) -> Optional[go.Figure]:
    """Visualize cornering speed across the lap if available."""
    if "cornering_speed" not in bundle.data.columns:
        return None
    
    # Filter to rows with cornering speed data
    data = bundle.data[bundle.data["cornering_speed"].notna()].copy()
    if data.empty:
        return None
    
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["cornering_speed"],
            mode="lines",
            name="Cornering Speed",
            line=dict(color="#2ca02c", width=3),
            hovertemplate="Distance: %{x:.1f}m<br>Speed: %{y:.1f}km/h<extra></extra>",
        )
    )
    
    return style_figure(fig, "Cornering Speed Across Lap", "Distance (m)", "Cornering Speed (km/h)", height=380)


def build_energy_efficient_figure(bundle: AnalysisBundle) -> Optional[go.Figure]:
    """Visualize energy efficiency score across the lap if available."""
    if "energy_efficient" not in bundle.data.columns:
        return None
    
    # Filter to rows with energy efficiency data
    data = bundle.data[bundle.data["energy_efficient"].notna()].copy()
    if data.empty:
        return None
    
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["energy_efficient"],
            mode="lines",
            name="Energy Efficiency",
            line=dict(color="#1f77b4", width=2),
            hovertemplate="Distance: %{x:.1f}m<br>Efficiency: %{y:.1f}<extra></extra>",
        )
    )
    
    return style_figure(fig, "Energy Efficiency vs Distance", "Distance (m)", "Efficiency Score", height=380)


def build_track_map_figure(
    bundle: AnalysisBundle,
    color_metric: str = "speed",
    selected_index: Optional[int] = None,
) -> go.Figure:
    data = bundle.data
    metric_labels = {
        "speed": "Speed",
        "slip_severity": "Slip Angle",
        "lateral_accel": "Lateral G",
        "stability_index": "Stability Index",
    }

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["longitude"],
            y=data["latitude"],
            mode="lines",
            name="Track",
            line=dict(color="rgba(90, 90, 90, 0.35)", width=2),
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["longitude"],
            y=data["latitude"],
            mode="markers",
            name=metric_labels[color_metric],
            marker=dict(
                size=7,
                color=data[color_metric],
                colorscale="Turbo",
                colorbar=dict(title=metric_labels[color_metric]),
            ),
            customdata=np.stack(
                [
                    data["distance_traveled"],
                    data["speed"],
                    data["throttle_input"] * 100,
                    data["brake_input"] * 100,
                ],
                axis=1,
            ),
            hovertemplate=(
                "Distance %{customdata[0]:.0f}m"
                "<br>Speed %{customdata[1]:.1f}"
                "<br>Throttle %{customdata[2]:.0f}%"
                "<br>Brake %{customdata[3]:.0f}%<extra></extra>"
            ),
        )
    )

    for key in ["oversteer", "understeer", "wheel_spin"]:
        if not bundle.events[key].any():
            continue
        style = EVENT_STYLES[key]
        subset = data.loc[bundle.events[key]]
        fig.add_trace(
            go.Scatter(
                x=subset["longitude"],
                y=subset["latitude"],
                mode="markers",
                name=style["label"],
                marker=dict(color=style["color"], symbol=style["symbol"], size=10, line=dict(color="white", width=0.8)),
            )
        )

    if selected_index is not None:
        snapshot = data.iloc[selected_index]
        # Show position marker with distance label
        fig.add_trace(
            go.Scatter(
                x=[snapshot["longitude"]],
                y=[snapshot["latitude"]],
                mode="markers+text",
                name="Current Pos",
                marker=dict(color="#ff6b35", size=18, symbol="circle", line=dict(color="white", width=2)),
                text=[f"Pos: {snapshot['distance_traveled']:.0f}m"],
                textposition="top center",
                hovertemplate=f"Distance: {snapshot['distance_traveled']:.0f}m<br>Speed: {snapshot['speed']:.1f} km/h<extra></extra>",
            )
        )

    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return style_figure(fig, "Track Map - Handling Analysis", "Longitude", "Latitude", height=620)


def render_summary_metrics(bundle: AnalysisBundle) -> None:
    """Enhanced summary metrics with better UI and insights"""
    
    # Main performance metrics
    st.markdown("### 🏁 Lap Performance")
    perf_cols = st.columns(4)
    
    lap_time_val = float(bundle.lap_time) if bundle.lap_time is not None else 0.0
    lap_distance_val = float(bundle.stats.get('lap_distance', 0)) if bundle.stats.get('lap_distance') is not None else 0.0
    avg_speed_val = float(bundle.stats.get('average_speed', 0)) if bundle.stats.get('average_speed') is not None else 0.0
    top_speed_val = float(bundle.stats.get('top_speed', 0)) if bundle.stats.get('top_speed') is not None else 0.0
    
    perf_cols[0].metric("⏱️ Lap Time", f"{lap_time_val:.2f}s")
    perf_cols[1].metric("📏 Distance", f"{lap_distance_val:.0f}m")
    perf_cols[2].metric("📊 Avg Speed", f"{avg_speed_val:.1f} km/h")
    perf_cols[3].metric("🚀 Top Speed", f"{top_speed_val:.1f} km/h")
    
    # Driving quality scores
    st.markdown("### 📈 Driver Performance Scores")
    score_cols = st.columns(4)
    
    consistency = bundle.scores.get("consistency_score", 0)
    handling = bundle.scores.get("handling_score", 0)
    stability = bundle.scores.get("stability_score", 0)
    
    # Color code the scores
    def score_color(score):
        if score >= 90:
            return "🟢"
        elif score >= 70:
            return "🟡"
        else:
            return "🔴"
    
    score_cols[0].metric("Consistency", f"{consistency:.0f}/100", delta=f"{score_color(consistency)}")
    score_cols[1].metric("Handling", f"{handling:.0f}/100", delta=f"{score_color(handling)}")
    score_cols[2].metric("Stability", f"{stability:.0f}/100", delta=f"{score_color(stability)}")
    score_cols[3].metric("Grade", bundle.grade)
    
    # Event summary with icons
    st.markdown("### ⚠️ Driving Events")
    event_cols = st.columns(5)
    event_cols[0].metric("Oversteer", bundle.event_counts.get("oversteer", 0), "↗️")
    event_cols[1].metric("Understeer", bundle.event_counts.get("understeer", 0), "↙️")
    event_cols[2].metric("Harsh Braking", bundle.event_counts.get("harsh_braking", 0), "🛑")
    event_cols[3].metric("Traction Loss", bundle.event_counts.get("wheel_spin", 0), "🎡")
    event_cols[4].metric("Late Braking", bundle.event_counts.get("late_braking", 0), "⏱️")


def render_insights(bundle: AnalysisBundle) -> None:
    st.subheader("Handling Dynamics Analysis")
    for insight in bundle.insights:
        st.markdown(f"• {insight}")


def render_turn_table(bundle: AnalysisBundle) -> None:
    st.subheader("Turn-by-Turn Summary (Distance-Based)")
    if bundle.turn_summary.empty:
        st.info("No clear corner zones detected from steering activity in this upload.")
        return

    st.caption("Turn numbering based on steering activity. Distance shows position along lap where turn occurs.")
    st.dataframe(bundle.turn_summary, use_container_width=True, hide_index=True)


def render_sector_table(bundle: AnalysisBundle) -> None:
    """Render sector-based summary if sector data is available."""
    if bundle.sector_summary is None or bundle.sector_summary.empty:
        return
    
    st.subheader("Sector Performance Summary")
    st.caption("Performance breakdown by sector. Shows handling metrics, cornering speed, and energy efficiency where available.")
    st.dataframe(bundle.sector_summary, use_container_width=True, hide_index=True)


def render_ml_insights(bundle: AnalysisBundle) -> None:
    """Display ML-powered insights from anomaly detection, clustering, and prediction"""
    if bundle.ml_results is None:
        return
    
    st.markdown("---")
    st.subheader("🤖 ML-Powered Analysis")
    
    ml_scores = bundle.ml_results.get('ml_scores', {})
    ml_insights = bundle.ml_results.get('ml_insights', [])
    
    # Display ML score
    if ml_scores:
        ml_cols = st.columns(3)
        ml_cols[0].metric("ML Framework Score", f"{ml_scores.get('ml_score', 0):.0f}/100")
        ml_cols[1].metric("Normal Sections", f"{ml_scores.get('normal_ratio', 0):.0f}%")
        ml_cols[2].metric("Stability (ML)", f"{ml_scores.get('stability_score', 0):.0f}/100")
    
    # Display ML insights
    if ml_insights:
        st.write("**Key Findings:**")
        for insight in ml_insights[:5]:  # Show top 5 insights
            icon_map = {
                'ANOMALY': '⚠️',
                'INSTABILITY': '🔴',
                'STYLE': '👤',
                'QUALITY_DIP': '📉'
            }
            icon = icon_map.get(insight.get('type', ''), '•')
            
            location = insight.get('location', 'N/A')
            description = insight.get('description', '')
            recommendation = insight.get('recommendation', '')
            
            st.write(f"{icon} **{description}** @ {location}")
            if recommendation:
                st.caption(f"→ {recommendation}")


def render_driver_feedback(bundle: AnalysisBundle) -> None:
    """Display personalized driver feedback and recommendations - SEPARATED by type"""
    st.markdown("---")
    st.markdown("### 💡 Driver Feedback & Recommendations")
    
    # Split feedback columns
    feedback_col1, feedback_col2 = st.columns(2)
    
    with feedback_col1:
        st.markdown("#### 👤 Driver Technique Improvements")
        if bundle.scores.get("consistency_score", 0) < 70:
            st.warning("⚠️ **Braking Depth:** Vary brake pressure inconsistently between corners")
            st.caption("👉 Apply brakes progressively, not abruptly. Release earlier to allow grip for cornering.")
        
        if bundle.event_counts.get("oversteer", 0) > 2:
            st.warning("⚠️ **Steering Angle:** Excessive lock through high-speed turns")
            st.caption("👉 Reduce steering wheel angle by 10-15% in quick direction changes. Avoid sudden corrections.")
        
        if bundle.event_counts.get("harsh_braking", 0) > 1:
            st.warning("⚠️ **Braking Modulation:** Jerky pedal inputs causing platform upset")
            st.caption("👉 Build pedal pressure smoothly over 0.5-1.0s. Think 'squeeze' not 'stab'.")
        
        if bundle.scores.get("stability_score", 0) < 75:
            st.warning("⚠️ **Throttle Control:** Inconsistent acceleration out of corners")
            st.caption("👉 Feed throttle progressively as steering input reduces. Avoid sudden full throttle.")
        
        if bundle.event_counts.get("late_braking", 0) > 0:
            st.info("💡 **Braking Point:** Braking too late into corners")
            st.caption("👉 Brake 0.5-1.0s earlier. Use a consistent braking point each lap.")
        
        if not (bundle.event_counts.get("oversteer", 0) or bundle.event_counts.get("harsh_braking", 0)):
            st.success("✅ **Smooth operator:** Your technique is well-controlled and consistent!")
    
    with feedback_col2:
        st.markdown("#### 🔧 Suspension & Setup Changes (SUSPENSION ONLY)")
        
        if bundle.event_counts["oversteer"] > 0:
            st.warning("⚠️ **Oversteer Detected**")
            st.caption("→ **Rear ARB:** Increase by +15-20% to increase rear roll stiffness")
            st.caption("→ **Front ARB:** Reduce by -10% to decrease understeer tendency")
            st.caption("→ **Front Damping:** Increase rebound by +10-15% for better turn-in control")
        
        if bundle.event_counts["understeer"] > 0:
            st.warning("⚠️ **Understeer Detected**")
            st.caption("→ **Front ARB:** Reduce by -15-20% for more front grip")
            st.caption("→ **Front Camber:** Increase negative camber by -0.3° to -0.5°")
            st.caption("→ **Front Ride Height:** Lower front by 5-8mm for aerodynamic downforce")
        
        if bundle.event_counts["harsh_braking"] > 0:
            st.info("💡 **Braking Platform Harshness**")
            st.caption("→ **Front Springs:** Soften by -8-10% to absorb braking load")
            st.caption("→ **Front Damping:** Reduce rebound by -5-8% for smoother platform")
            st.caption("→ **Brake Bias:** Shift 1% forward for rear stability during heavy braking")
        
        if bundle.event_counts.get("wheel_spin", 0) > 0:
            st.info("💡 **Longitudinal Wheel Slide on Exit**")
            st.caption("→ **Rear Spring:** Increase by +8-12% for traction on acceleration")
            st.caption("→ **Rear ARB:** Increase by +15-20% to control wheelspin")
            st.caption("→ **Rear Rebound Damping:** Reduce by -8-12% for faster load transfer")
    
    # Detailed recommendations (collapsed)
    with st.expander("📋 Complete Setup Guide"):
        st.markdown("""
        **Anti-Roll Bar (ARB) Adjustments:**
        - Increasing ARB stiffness reduces roll, increases understeer initially, and improves mid-corner control
        - Front ARB affects turn-in and mid-corner balance; Rear ARB affects corner exit stability
        - Typical range: ±20% from baseline for sensible changes
        
        **Damping (Shock): Rebound & Bump:**
        - Rebound damping controls how fast spring extends; higher = more stability but less grip
        - Bump damping controls compression; higher = stiffer platform but can lose grip over bumps
        - Front rebound more critical for turn-in; Rear rebound critical for exit stability
        
        **Spring Rate Changes:**
        - Stiffer springs (+) reduce roll and elevate platform, lower ride heights
        - Softer springs (-) improve compliance but increase roll and instability
        - Changes typically ±5-15% for measurable effect
        
        **Brake Balance:**
        - Forward = more braking force at front; helps with stability but risks front locking
        - Rearward = more rear braking; helps with rear grip but risks spin
        - Typical range: 55-65% front bias (45-35% rear)
        
        **Ride Height & Aero:**
        - Lower front → more downforce → more grip but lighter rear end
        - Typical range: ±5mm per adjustment, max 10mm per session
        """)


def render_overview(bundle: AnalysisBundle) -> None:
    render_summary_metrics(bundle)
    st.divider()
    render_insights(bundle)
    st.divider()
    render_driver_feedback(bundle)
    st.divider()
    if bundle.ml_results is not None and ML_AVAILABLE:
        render_ml_insights(bundle)
        st.divider()
    render_turn_table(bundle)
    render_sector_table(bundle)


def render_charts(bundle: AnalysisBundle) -> None:
    # Top row: Speed and Throttle/Brake
    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.plotly_chart(build_speed_figure(bundle), use_container_width=True)
    with chart_col_2:
        st.plotly_chart(build_controls_figure(bundle), use_container_width=True)
    
    # Second row: Lateral Accel (removed Slip Angle vs Distance)
    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.plotly_chart(build_lateral_accel_figure(bundle), use_container_width=True)
    with chart_col_2:
        st.plotly_chart(build_steering_yaw_figure(bundle), use_container_width=True)
    
    # Third row: RPM
    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.plotly_chart(build_rpm_evolution_figure(bundle), use_container_width=True)
    with chart_col_2:
        st.info("💡 Slip Angle is analyzed in Turn-by-Turn Summary and Track Map visualizations")
    
    # Optional: Cornering speed visualization
    cornering_fig = build_cornering_speed_figure(bundle)
    if cornering_fig:
        st.plotly_chart(cornering_fig, use_container_width=True)
    
    # Optional: Energy efficiency visualization
    energy_fig = build_energy_efficient_figure(bundle)
    if energy_fig:
        st.plotly_chart(energy_fig, use_container_width=True)


def render_track_map(bundle: AnalysisBundle) -> None:
    if not has_gps(bundle.data):
        st.info("GPS not provided - track map unavailable. All analyses use distance-traveled metrics.")
        return

    selector_col, replay_col = st.columns([1, 2])
    with selector_col:
        color_choice = st.selectbox(
            "Color track by",
            options=[
                ("speed", "Speed"),
                ("slip_severity", "Slip Angle"),
                ("lateral_accel", "Lateral G"),
                ("stability_index", "Stability Index"),
            ],
            format_func=lambda item: item[1],
        )[0]
    with replay_col:
        slider_step = max(1, len(bundle.data) // 200)
        selected_index = st.slider(
            "Replay frame",
            min_value=0,
            max_value=len(bundle.data) - 1,
            value=0,
            step=slider_step,
        )

    st.plotly_chart(
        build_track_map_figure(bundle, color_metric=color_choice, selected_index=selected_index),
        use_container_width=True,
    )

    snapshot = bundle.data.iloc[selected_index]
    replay_metrics = st.columns(6)
    replay_metrics[0].metric("Position", f"{snapshot['distance_traveled']:.0f}m")
    replay_metrics[1].metric("Speed", f"{snapshot['speed']:.1f}")
    replay_metrics[2].metric("Throttle", f"{snapshot['throttle_input'] * 100:.0f}%")
    replay_metrics[3].metric("Brake", f"{snapshot['brake_input'] * 100:.0f}%")
    replay_metrics[4].metric("RPM", f"{int(snapshot['rpm'])}")
    replay_metrics[5].metric("Slip", f"{snapshot['slip_severity']:.2f}°")


def render_comparison(primary: AnalysisBundle, comparison: AnalysisBundle) -> None:
    lap_time_delta = comparison.lap_time - primary.lap_time
    consistency_delta = comparison.scores["consistency_score"] - primary.scores["consistency_score"]
    handling_delta = comparison.scores["handling_score"] - primary.scores["handling_score"]

    summary_cols = st.columns(4)
    summary_cols[0].metric("Lap Time Delta", f"{lap_time_delta:+.2f}s")
    summary_cols[1].metric("Consistency Delta", f"{consistency_delta:+.1f}")
    summary_cols[2].metric("Handling Delta", f"{handling_delta:+.1f}")
    summary_cols[3].metric("Stability Delta", f"{comparison.scores['stability_score'] - primary.scores['stability_score']:+.1f}")

    if primary.lap_time < comparison.lap_time:
        best_text = f"**{primary.name}** is the reference lap (+{comparison.lap_time - primary.lap_time:.2f}s)"
    elif comparison.lap_time < primary.lap_time:
        best_text = f"**{comparison.name}** is the reference lap (+{primary.lap_time - comparison.lap_time:.2f}s)"
    else:
        best_text = "Both laps show the same time - compare handling consistency."
    st.markdown(best_text)

    comparison_col_1, comparison_col_2 = st.columns(2)
    with comparison_col_1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=primary.data["distance_traveled"], y=primary.data["speed"], name=primary.name, mode="lines", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=comparison.data["distance_traveled"], y=comparison.data["speed"], name=comparison.name, mode="lines", line=dict(width=2)))
        fig = style_figure(fig, "Speed Trace Comparison (Distance-Based)", "Distance (m)", "Speed (km/h)")
        st.plotly_chart(fig, use_container_width=True)
    with comparison_col_2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=primary.data["distance_traveled"], y=primary.data["slip_severity"], name=primary.name, mode="lines", line=dict(width=2)))
        fig.add_trace(go.Scatter(x=comparison.data["distance_traveled"], y=comparison.data["slip_severity"], name=comparison.name, mode="lines", line=dict(width=2)))
        fig = style_figure(fig, "Slip Angle Comparison (Distance-Based)", "Distance (m)", "Slip Angle (°)")
        st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="AMTAS - Automated Motorsports Telemetry Analysis System", layout="wide")
    
    # Motorsports-themed custom CSS
    st.markdown(
        """
        <style>
        /* Motorsports theme: racing red and dark background */
        .block-container { 
            padding-top: 1.4rem; 
            padding-bottom: 2rem;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
        }
        [data-testid="stMetricValue"] { 
            font-size: 1.8rem;
            font-family: 'Monaco', 'Courier New', monospace;
            color: #ff6b35;
        }
        h1, h2, h3, h4, h5, h6 {
            font-family: 'Segoe UI', sans-serif;
            color: #ffb627;
            text-shadow: 0 2px 4px rgba(255, 107, 53, 0.3);
        }
        .stTabs [data-baseweb="tab-list"] button {
            background-color: #1a1a2e;
            border-bottom: 3px solid #333;
            color: #ffffff;
            font-weight: bold;
        }
        .stTabs [aria-selected="true"] {
            border-bottom: 3px solid #ff6b35;
            color: #ffb627;
        }
        .stMetric {
            background-color: rgba(255, 107, 53, 0.1);
            border-left: 4px solid #ff6b35;
            padding: 12px;
            border-radius: 4px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🏁 Automated Motorsports Telemetry Analysis System (AMTAS)")
    st.write("Upload race telemetry CSV files for corner-by-corner handling analysis with driver technique and suspension setup recommendations. **All data is analyzed against distance traveled, not time.**")

    with st.expander("Expected CSV schema"):
        st.code(", ".join(REQUIRED_COLUMNS + OPTIONAL_COLUMNS), language="text")
        st.caption("`latitude` and `longitude` unlock track map visualization.")

    uploader_col_1, uploader_col_2 = st.columns(2)
    with uploader_col_1:
        primary_upload = st.file_uploader("Upload primary telemetry CSV", type=["csv"], key="primary")
    with uploader_col_2:
        comparison_upload = st.file_uploader("Optional: Compare second lap/driver", type=["csv"], key="comparison")

    if primary_upload is None:
        st.info("📊 Upload telemetry CSV to begin handling dynamics analysis.")
        return

    try:
        with st.spinner("Analyzing handling dynamics..."):
            primary_bundle = analyze_uploaded_file(primary_upload)
            # Debug output
            st.success(f"✅ Analysis complete: {primary_bundle.lap_time:.2f}s lap, {primary_bundle.stats['lap_distance']:.1f}m distance")
    except Exception as exc:
        st.error(f"❌ Analysis failed: {exc}")
        import traceback
        st.error(traceback.format_exc())
        return

    comparison_bundle = None
    if comparison_upload is not None:
        try:
            with st.spinner("Analyzing comparison telemetry..."):
                comparison_bundle = analyze_uploaded_file(comparison_upload)
        except Exception as exc:
            st.error(f"❌ Comparison analysis failed: {exc}")

    overview_tab, charts_tab, map_tab, comparison_tab = st.tabs(
        ["📋 Overview", "📈 Telemetry Charts", "🗺️ Track Map", "⚖️ Comparison"]
    )

    with overview_tab:
        render_overview(primary_bundle)

    with charts_tab:
        render_charts(primary_bundle)

    with map_tab:
        render_track_map(primary_bundle)

    with comparison_tab:
        if comparison_bundle is None:
            st.info("Upload a second telemetry CSV to compare handling consistency across laps or drivers.")
        else:
            render_comparison(primary_bundle, comparison_bundle)


if __name__ == "__main__":
    main()
