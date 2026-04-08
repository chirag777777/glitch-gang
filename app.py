"""
Driver Telemetry Analysis System - Handling Dynamics Focus
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

# ML Module imports
try:
    from ml_module import run_ml_pipeline
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False


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
    "wheel_spin": {"label": "Traction Loss", "color": "#e377c2", "symbol": "star"},
    "unstable": {"label": "Platform Instability", "color": "#7f7f7f", "symbol": "circle-open"},
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
    data["slip_severity"] = data["steering_abs"] + (data["yaw_abs"] * 0.5)  # Slip estimated from steering + yaw
    data["input_change"] = (
        data["throttle_input"].diff().fillna(0).abs()
        + data["brake_input"].diff().fillna(0).abs()
    )
    data["stability_index"] = data["yaw_rate"] / (data["steering_abs"] + 0.01)
    data["yaw_response"] = data["yaw_abs"] / (data["steering_abs"] + 0.1)
    data["rpm_efficiency"] = data["rpm"] / 5000  # Normalized to typical peak RPM
    
    # DISTANCE TRAVELED - cumulative distance in meters
    data["distance_traveled"] = (data["speed"] * data["dt"]).cumsum()
    
    # Lateral acceleration for handling analysis
    data["lateral_accel"] = (data["slip_severity"] * data["speed"] / 127).clip(0, 2.5)
    
    # Preserve optional columns if present
    for col in OPTIONAL_COLUMNS:
        if col in df.columns:
            data[col] = df[col]
    
    return data


def compute_thresholds(data: pd.DataFrame) -> Dict[str, float]:
    return {
        "brake_threshold": float(np.clip(max(0.20, safe_quantile(data["brake_input"], 0.70, 0.25)), 0.20, 0.55)),
        "brake_high": float(np.clip(max(0.55, safe_quantile(data["brake_input"], 0.90, 0.75)), 0.55, 0.98)),
        "throttle_threshold": float(np.clip(max(0.35, safe_quantile(data["throttle_input"], 0.55, 0.40)), 0.35, 0.75)),
        "throttle_high": float(np.clip(max(0.65, safe_quantile(data["throttle_input"], 0.85, 0.70)), 0.65, 0.98)),
        "corner_threshold": float(max(5.0, safe_quantile(data["steering_abs"], 0.65, 6.0))),
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
    oversteer = (
        data["corner_zone"]
        & (data["slip_severity"] > thresholds["slip_high"])
        & (data["yaw_abs"] > thresholds["yaw_high"])
    )
    understeer = (
        data["corner_zone"]
        & (data["steering_abs"] > thresholds["corner_threshold"] * 1.15)
        & (data["yaw_response"] < thresholds["yaw_response_low"])
        & (data["speed"] > thresholds["mid_speed"])
    )
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
    unstable = (
        (data["stability_index"].abs() > thresholds["stability_high"])
        | oversteer
        | understeer
        | harsh_braking
        | (
            data["corner_zone"]
            & (data["input_change"] > safe_quantile(data["input_change"], 0.90, 0.20))
            & (data["slip_severity"] > thresholds["slip_medium"])
        )
    )
    braking_timing = analyze_braking_timing(data)

    return {
        "oversteer": oversteer.fillna(False),
        "understeer": understeer.fillna(False),
        "harsh_braking": harsh_braking.fillna(False),
        "late_braking": braking_timing["late_braking"].fillna(False),
        "early_braking": braking_timing["early_braking"].fillna(False),
        "wheel_spin": wheel_spin.fillna(False),
        "unstable": unstable.fillna(False),
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
    
    # Stability: measure of predictable vehicle balance
    stability_metric = mask_ratio(events["oversteer"]) + mask_ratio(events["understeer"])
    stability_score = clip_0_100(100 - stability_metric * 300)
    
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
    rows: List[Dict[str, object]] = []

    for turn_id in sorted(data["corner_id"].unique()):
        if turn_id <= 0:
            continue

        segment = data[data["corner_id"] ==turn_id]
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
            "unstable",
        ]:
            if events[key].loc[start_idx:end_idx].any():
                issues.append(EVENT_STYLES[key]["label"])

        distance_start = float(segment["distance_traveled"].iloc[0])
        distance_end = float(segment["distance_traveled"].iloc[-1])
        turn_length = distance_end - distance_start
        
        rows.append(
            {
                "Turn": f"T{int(turn_id)}",
                "Distance": f"{distance_start:.0f}-{distance_end:.0f}m",
                "Length (m)": round(turn_length, 0),
                "Entry Speed": round(float(segment["speed"].iloc[0]), 1),
                "Min Speed": round(float(segment["speed"].min()), 1),
                "Peak Slip (°)": round(float(segment["slip_severity"].max()), 1),
                "Max Lateral G": round(float(segment["lateral_accel"].max()), 2),
                "Issues": ", ".join(issues[:2]) if issues else "✓ Clean",
            }
        )

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
        
        sector_dist = float(segment["distance_traveled"].iloc[-1] - segment["distance_traveled"].iloc[0])
        
        row = {
            "Sector": str(sector_id),
            "Distance (m)": f"{segment['distance_traveled'].iloc[0]:.0f}-{segment['distance_traveled'].iloc[-1]:.0f}",
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
        add(84, f"[TRACTION LOSS @{location_str}] Wheelspin on exit under acceleration. "
                f"Driver: wait for steering <5° before full throttle, squeeze progressively. "
                f"Setup: increase rear spring +10%, rear ARB +20%, reduce rear rebound damping -10%.")

    # INSTABILITY
    unstable_ratio = mask_ratio(events["unstable"]) * 100
    if unstable_ratio > 8:
        turn_id, distance = dominant_location_label(data, events["unstable"])
        location_str = f"T{turn_id} (~{distance:.0f}m)" if turn_id > 0 else f"~{distance:.0f}m"
        add(70, f"[PLATFORM INSTABILITY @{location_str}] Vehicle unstable {unstable_ratio:.0f}% of lap. "
                f"Driver: smooth all pedal transitions, single steering input per corner. "
                f"Setup: increase damping +10-15% overall, rebalance front/rear springs.")

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
    total_distance = float(data["distance_traveled"].iloc[-1])
    return {
        "lap_time": float(data["relative_time"].iloc[-1]),
        "lap_distance": total_distance,
        "average_speed": float(data["speed"].mean()),
        "top_speed": float(data["speed"].max()),
        "turns_detected": float(int(data["corner_id"].max())),
    }


def analyze_uploaded_file(uploaded_file) -> AnalysisBundle:
    raw_df = read_csv_bytes(uploaded_file.getvalue())
    cleaned = clean_telemetry_data(raw_df)
    featured = engineer_features(cleaned)
    thresholds = compute_thresholds(featured)
    zoned = add_zone_columns(featured, thresholds)
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
        title=title,
        height=height,
        margin=dict(l=20, r=20, t=55, b=20),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    fig.update_xaxes(title=x_label, showgrid=True, gridcolor="rgba(200, 200, 200, 0.25)")
    fig.update_yaxes(title=y_label, showgrid=True, gridcolor="rgba(200, 200, 200, 0.25)")
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
            hovertemplate="Distance %{x:.0f}m<br>Speed %{y:.1f} km/h<extra></extra>",
        )
    )
    add_event_markers(fig, data, bundle.events, "distance_traveled", "speed", ["oversteer", "understeer", "unstable"])
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
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["distance_traveled"],
            y=data["brake_pct"],
            mode="lines",
            name="Brake",
            line=dict(color="#d62728", width=3),
        )
    )
    add_event_markers(
        fig,
        data,
        bundle.events,
        "distance_traveled",
        "brake_pct",
        ["harsh_braking", "late_braking", "early_braking"],
    )
    if bundle.events["wheel_spin"].any():
        subset = data.loc[bundle.events["wheel_spin"]]
        fig.add_trace(
            go.Scatter(
                x=subset["distance_traveled"],
                y=subset["throttle_pct"],
                mode="markers",
                name="Traction Loss",
                marker=dict(color=EVENT_STYLES["wheel_spin"]["color"], symbol="star", size=9),
            )
        )
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
        )
    )
    add_event_markers(fig, data, bundle.events, "distance_traveled", "slip_severity", ["oversteer", "wheel_spin"])
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
            line=dict(color="#e377c2", width=2),
            fill="tozeroy",
            fillcolor="rgba(227, 119, 194, 0.2)",
        )
    )
    add_event_markers(fig, data, bundle.events, "distance_traveled", "lateral_accel", ["oversteer", "understeer"])
    corner_max = data["lateral_accel"].max()
    fig.add_hline(y=corner_max * 0.8, line_dash="dash", line_color="rgba(100,100,100,0.5)", 
                  annotation_text="High G-Load Reference")
    return style_figure(fig, "Lateral Acceleration vs Distance", "Distance (m)", "Lateral G (m/s²)")


def build_yaw_vs_steering_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = px.scatter(
        data,
        x="steering_angle",
        y="yaw_rate",
        color="distance_traveled",
        color_continuous_scale="Viridis",
        labels={"steering_angle": "Steering Angle (°)", "yaw_rate": "Yaw Rate (°/s)", "distance_traveled": "Distance (m)"},
        title="Yaw Response vs Steering Input",
    )

    for key in ["oversteer", "understeer"]:
        if not bundle.events[key].any():
            continue
        style = EVENT_STYLES[key]
        subset = data.loc[bundle.events[key]]
        fig.add_trace(
            go.Scatter(
                x=subset["steering_angle"],
                y=subset["yaw_rate"],
                mode="markers",
                name=style["label"],
                marker=dict(color=style["color"], symbol=style["symbol"], size=9, line=dict(color="white", width=0.8)),
            )
        )

    return style_figure(fig, "Yaw Response vs Steering - Distance Colored", "Steering Angle (°)", "Yaw Moment", height=420)


def build_rpm_evolution_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = px.scatter(
        data,
        x="distance_traveled",
        y="rpm",
        color="distance_traveled",
        color_continuous_scale="Plasma",
        labels={"rpm": "RPM", "distance_traveled": "Distance (m)"},
        title="RPM Evolution Across Lap",
    )
    fig.add_hrect(
        y0=bundle.thresholds["rpm_low"],
        y1=bundle.thresholds["rpm_high"],
        fillcolor="rgba(46, 204, 113, 0.12)",
        line_width=0,
        annotation_text="Efficient RPM band",
        annotation_position="top left",
    )

    for key in ["low_rpm_issue", "high_rpm_issue"]:
        if not bundle.events[key].any():
            continue
        style = EVENT_STYLES[key]
        subset = data.loc[bundle.events[key]]
        fig.add_trace(
            go.Scatter(
                x=subset["distance_traveled"],
                y=subset["rpm"],
                mode="markers",
                name=style["label"],
                marker=dict(color=style["color"], symbol=style["symbol"], size=9, line=dict(width=0.8, color="white")),
            )
        )

    return style_figure(fig, "RPM Evolution - Distance Colored", "Distance (m)", "RPM", height=420)


def build_cornering_speed_figure(bundle: AnalysisBundle) -> Optional[go.Figure]:
    """Visualize cornering speed across the lap if available."""
    if "cornering_speed" not in bundle.data.columns:
        return None
    
    # Filter to rows with cornering speed data
    data = bundle.data[bundle.data["cornering_speed"].notna()].copy()
    if data.empty:
        return None
    
    fig = px.scatter(
        data,
        x="distance_traveled",
        y="cornering_speed",
        color="cornering_speed",
        color_continuous_scale="Viridis",
        labels={"cornering_speed": "Speed (km/h)", "distance_traveled": "Distance (m)"},
        title="Cornering Speed Profile",
    )
    
    return style_figure(fig, "Cornering Speed Across Lap", "Distance (m)", "Cornering Speed", height=380)


def build_energy_efficient_figure(bundle: AnalysisBundle) -> Optional[go.Figure]:
    """Visualize energy efficiency score across the lap if available."""
    if "energy_efficient" not in bundle.data.columns:
        return None
    
    # Filter to rows with energy efficiency data
    data = bundle.data[bundle.data["energy_efficient"].notna()].copy()
    if data.empty:
        return None
    
    fig = px.bar(
        data.reset_index(drop=True),
        x="distance_traveled",
        y="energy_efficient",
        color="energy_efficient",
        color_continuous_scale="RdYlGn",
        labels={"energy_efficient": "Efficiency Score", "distance_traveled": "Distance (m)"},
        title="Energy Efficiency Timeline",
    )
    fig.update_traces(marker_line_width=0)
    
    return style_figure(fig, "Energy Efficiency - Distance Based", "Distance (m)", "Efficiency Score", height=380)


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

    for key in ["oversteer", "understeer", "wheel_spin", "unstable"]:
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
        fig.add_trace(
            go.Scatter(
                x=[snapshot["longitude"]],
                y=[snapshot["latitude"]],
                mode="markers",
                name="Position",
                marker=dict(color="#111111", size=16, symbol="star"),
            )
        )

    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return style_figure(fig, "Track Map - Handling Analysis", "Longitude", "Latitude", height=620)


def render_summary_metrics(bundle: AnalysisBundle) -> None:
    stats_columns = st.columns(4)
    stats_columns[0].metric("Lap Time", f"{bundle.lap_time:.2f}s")
    stats_columns[1].metric("Total Distance", f"{bundle.stats.get('lap_distance', 0):.0f}m")
    stats_columns[2].metric("Average Speed", f"{bundle.stats['average_speed']:.1f} km/h")
    stats_columns[3].metric("Top Speed", f"{bundle.stats['top_speed']:.1f} km/h")

    event_columns = st.columns(5)
    event_columns[0].metric("Oversteer", bundle.event_counts["oversteer"])
    event_columns[1].metric("Understeer", bundle.event_counts["understeer"])
    event_columns[2].metric("Harsh Braking", bundle.event_counts["harsh_braking"])
    event_columns[3].metric("Traction Loss", bundle.event_counts["wheel_spin"])
    event_columns[4].metric("Instability", bundle.event_counts["unstable"])


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



def render_overview(bundle: AnalysisBundle) -> None:
    render_summary_metrics(bundle)
    render_insights(bundle)
    if bundle.ml_results is not None and ML_AVAILABLE:
        render_ml_insights(bundle)
    render_turn_table(bundle)
    render_sector_table(bundle)


def render_charts(bundle: AnalysisBundle) -> None:
    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.plotly_chart(build_speed_figure(bundle), use_container_width=True)
        st.plotly_chart(build_slip_figure(bundle), use_container_width=True)
    with chart_col_2:
        st.plotly_chart(build_controls_figure(bundle), use_container_width=True)
        st.plotly_chart(build_lateral_accel_figure(bundle), use_container_width=True)

    st.plotly_chart(build_yaw_vs_steering_figure(bundle), use_container_width=True)
    st.plotly_chart(build_rpm_evolution_figure(bundle), use_container_width=True)
    
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
        fig.add_trace(go.Scatter(x=primary.data["distance_traveled"], y=primary.data["speed"], name=primary.name))
        fig.add_trace(go.Scatter(x=comparison.data["distance_traveled"], y=comparison.data["speed"], name=comparison.name))
        fig = style_figure(fig, "Speed Trace Comparison (Distance-Based)", "Distance (m)", "Speed (km/h)")
        st.plotly_chart(fig, use_container_width=True)
    with comparison_col_2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=primary.data["distance_traveled"], y=primary.data["slip_severity"], name=primary.name))
        fig.add_trace(go.Scatter(x=comparison.data["distance_traveled"], y=comparison.data["slip_severity"], name=comparison.name))
        fig = style_figure(fig, "Slip Angle Comparison (Distance-Based)", "Distance (m)", "Slip Angle (°)")
        st.plotly_chart(fig, use_container_width=True)


def main() -> None:
    st.set_page_config(page_title="Handling Dynamics Analysis System", layout="wide")
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
        [data-testid="stMetricValue"] { font-size: 1.8rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("🏎️ Handling Dynamics Analysis System")
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
    except Exception as exc:
        st.error(f"❌ Analysis failed: {exc}")
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
