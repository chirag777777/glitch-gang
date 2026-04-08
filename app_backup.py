from __future__ import annotations

import io
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


REQUIRED_COLUMNS = [
    "time",
    "speed",
    "throttle_input",
    "brake_input",
    "steering_angle",
    "combined_slip_angle",
    "yaw_moment",
    "pitch",
    "rpm",
    "gear",
]
OPTIONAL_COLUMNS = ["latitude", "longitude"]

EVENT_STYLES = {
    "oversteer": {"label": "Oversteer", "color": "#d62728", "symbol": "x"},
    "understeer": {"label": "Understeer", "color": "#ff7f0e", "symbol": "diamond"},
    "harsh_braking": {"label": "Harsh Braking", "color": "#9467bd", "symbol": "triangle-down"},
    "late_braking": {"label": "Late Braking", "color": "#8c564b", "symbol": "triangle-left"},
    "early_braking": {"label": "Early Braking", "color": "#17becf", "symbol": "triangle-right"},
    "wheel_spin": {"label": "Wheel Spin", "color": "#e377c2", "symbol": "star"},
    "unstable": {"label": "Unstable", "color": "#7f7f7f", "symbol": "circle-open"},
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
    df["gear"] = (
        df["gear"]
        .round()
        .abs()
        .replace(0, np.nan)
        .ffill()
        .bfill()
        .fillna(1)
        .clip(lower=1)
        .astype(int)
    )

    df["relative_time"] = df["time"] - df["time"].iloc[0]
    time_delta = df["relative_time"].diff()
    default_dt = safe_quantile(time_delta[time_delta > 0], 0.5, 0.05)
    df["dt"] = time_delta.where(time_delta > 1e-6, default_dt).fillna(default_dt)
    return df.reset_index(drop=True)


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    data = df.copy()
    data["steering_abs"] = data["steering_angle"].abs()
    data["yaw_abs"] = data["yaw_moment"].abs()
    data["pitch_abs"] = data["pitch"].abs()
    data["acceleration"] = data["speed"].diff().fillna(0) / data["dt"].replace(0, np.nan)
    data["acceleration"] = data["acceleration"].replace([np.inf, -np.inf], 0).fillna(0)
    data["slip_severity"] = data["combined_slip_angle"].abs()
    data["input_change"] = (
        data["throttle_input"].diff().abs().fillna(0)
        + data["brake_input"].diff().abs().fillna(0)
    )
    data["stability_index"] = data["yaw_moment"] / (data["steering_abs"] + 0.01)
    data["yaw_response"] = data["yaw_abs"] / (data["steering_abs"] + 0.1)
    data["rpm_efficiency"] = data["rpm"] / data["gear"].replace(0, np.nan).fillna(1)
    
    # Distance traveled (cumulative, in meters)
    data["distance_traveled"] = (data["speed"] * data["dt"]).cumsum()
    
    # Lateral acceleration (derived from slip angle and speed)
    data["lateral_accel"] = (data["slip_severity"] * data["speed"] / 127).clip(0, 2.0)
    
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
        "pitch_high": float(max(1.0, safe_quantile(data["pitch_abs"], 0.80, 1.0))),
        "stability_high": float(max(0.20, safe_quantile(data["stability_index"].abs(), 0.90, 0.25))),
        "mid_speed": float(safe_quantile(data["speed"], 0.55, float(data["speed"].median()))),
        "high_speed": float(safe_quantile(data["speed"], 0.75, float(data["speed"].median()))),
        "rpm_low": float(max(3000, safe_quantile(data["rpm"], 0.25, 3500))),
        "rpm_high": float(max(6500, safe_quantile(data["rpm"], 0.85, 7000))),
        "max_gear": float(max(1, int(data["gear"].max()))),
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
        & (data["pitch_abs"] > thresholds["pitch_high"])
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
        & (data["gear"] > 1)
        & (data["speed"] < thresholds["high_speed"])
    )
    high_rpm_issue = (
        data["throttle_zone"]
        & (data["rpm"] > thresholds["rpm_high"])
        & (data["gear"] < thresholds["max_gear"])
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
    # Handling precision score: based on slip control and steering smoothness
    slip_metric = float(data["slip_severity"].mean())
    slip_score = inverse_score(slip_metric, 1.5, 8.0)
    
    steering_smoothness = float((data["steering_abs"].diff().abs()).mean())
    steering_score = inverse_score(steering_smoothness, 0.5, 5.0)
    
    handling_score = clip_0_100((slip_score * 0.6 + steering_score * 0.4))
    
    # Stability score: measure of predictable vehicle balance
    stability_metric = mask_ratio(events["oversteer"]) + mask_ratio(events["understeer"])
    stability_score = clip_0_100(100 - stability_metric * 300)
    
    # Braking precision: smooth pedal application without lock-up indicators
    braking_smoothness = float(data.loc[data["brake_input"] > 0.1, "input_change"].mean())
    braking_score = inverse_score(braking_smoothness, 0.03, 0.25)
    
    # Overall driving consistency (focuses on handling, not speed)
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
    """Returns (turn_id, distance_in_turn) of the dominant location."""
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


def generate_suspension_recommendations(
    data: pd.DataFrame, events: Dict[str, pd.Series], turn_id: int, segment: pd.DataFrame
) -> Dict[str, str]:
    """Generate suspension tuning recommendations for a specific turn based on handling issues."""
    recommendations: Dict[str, str] = {}
    
    segment_events = {key: events[key].loc[segment.index.min():segment.index.max()].any() for key in events}
    
    if segment_events["oversteer"]:
        avg_slip = float(segment["slip_severity"].mean())
        avg_speed = float(segment["speed"].mean())
        peak_yaw = float(segment["yaw_abs"].max())
        
        recommendations["issue"] = f"Oversteer in Turn {turn_id} (avg slip: {avg_slip:.1f}°, peak yaw: {peak_yaw:.3f})"
        recommendations["driver_technique"] = (\n            "1. Reduce entry speed by 2-3 km/h. 2. Delay throttle application until steering angle is reducing. "\n            "3. Maintain smoother steering inputs at turn-in to avoid abrupt load shifts."\n        )\n        recommendations["suspension_tuning"] = (\n            "• Increase rear ARB stiffness +15-20% to reduce rear slide tendency\\n"\n            "• Reduce front anti-roll bar stiffness -10% to improve front turn-in grip\\n"\n            "• Increase front damping +10-15% to reduce over-responsiveness\\n"\n            "• Increase rear spring rate +5% to reduce rear compliance\\n"\n            "• Reduce rear camber by 0.2-0.3° to improve rear edge grip\\n"\n            "• Consider toe-out reduction on rear axle by 0.05-0.1°\"\n        )\n    \n    elif segment_events[\"understeer\"]:\n        entry_speed = float(segment[\"speed"].iloc[0])\n        steering_demand = float(segment[\"steering_abs\"].mean())\n        yaw_response = float(segment[\"yaw_response\"].mean())\n        \n        recommendations[\"issue\"] = f\"Understeer in Turn {turn_id} (entry speed: {entry_speed:.1f}, steering: {steering_demand:.1f}°)\"\n        recommendations[\"driver_technique\"] = (\n            \"1. Release brake 1-2 car-lengths earlier (before turn-in). 2. Use progressive steering, not abrupt lock. "\n            \"3. Wait for the car to rotate before adding throttle. 4. Consider slightly later apex to reduce mid-corner steering demand.\"\n        )\n        recommendations[\"suspension_tuning\"] = (\n            \"• Reduce front ARB stiffness -15-20% to improve front turn-in response\\n"\n            "• Increase rear ARB stiffness +10% to help rotate the rear\\n"\n            "• Reduce front spring rate -5% for better compliance into the corner\\n"\n            "• Increase front camber (more negative) by 0.3-0.5° for additional edge grip\\n"\n            "• Add front toe-in by 0.05-0.1° for stability, but avoid excess understeer\\n"\n            "• Reduce front ride height by 5-10mm to improve aero-mechanical balance\"\n        )\n    \n    elif segment_events[\"harsh_braking\"]:\n        peak_pitch = float(segment[\"pitch_abs\"].max())\n        braking_level = float(segment[\"brake_input\"].max())\n        \n        recommendations[\"issue\"] = f\"Harsh braking event in Turn {turn_id} (pitch: {peak_pitch:.2f}°, brake: {braking_level*100:.0f}%)\"\n        recommendations[\"driver_technique\"] = (\n            \"1. Build pedal pressure gradually over 0.5-1.0 seconds instead of stabbing. 2. Modulate brake pressure through the corner. "\n            \"3. Begin brake release before the apex to balance the platform for turn-in. 4. Aim for smoother, earlier braking.\"\n        )\n        recommendations[\"suspension_tuning\"] = (\n            \"• Increase brake bias balance forward (if tunable) for more progressive pedal feel\\n"\n            "• Reduce front bump stop stiffness to absorb initial braking load\\n"\n            "• Increase front ride height by 5mm to reduce nose-dive behavior\\n"\n            "• Soften front springs by 5-10% for better brake balance absorption\\n"\n            "• Adjust front damping rebound -10% to reduce platform upset after lock-up fear\\n"\n            "• Consider adding brake cooling if overheating is a factor\"\n        )\n    \n    elif segment_events[\"wheel_spin\"]:\n        traction_slip = float(segment.loc[events[\"wheel_spin\"] & (segment.index >= segment.index.min()), \"slip_severity\"].max())\n        throttle_level = float(segment[\"throttle_input\"].max())\n        \n        recommendations[\"issue\"] = f\"Wheelspin on exit of Turn {turn_id} (slip: {traction_slip:.1f}°, throttle: {throttle_level*100:.0f}%)\"\n        recommendations[\"driver_technique\"] = (\n            \"1. Wait until steering angle is <5° before applying full throttle. 2. Squeeze throttle progressively over 0.5s. "\n            \"3. Reduce corner speed slightly so exit throttle is reached with straighter wheels. 4. Maintain throttle modulation even after power is on.\"\n        )\n        recommendations[\"suspension_tuning\"] = (\n            \"• Increase rear spring stiffness +10% to reduce rear compliance during exit loading\\n"\n            "• Increase rear ARB stiffness +15-20% to improve platform stability under acceleration\\n"\n            "• Reduce rear damping rebound by 5-10% for better traction out of corners\\n"\n            "• Increase rear ride height by 5-10mm to reduce squat and improve traction\\n"\n            "• Adjust differential lock setting (if available) to improve grip distribution\\n"\n            "• Consider rear wing angle adjustment for more downforce if available\"\n        )\n    \n    elif segment_events[\"late_braking\"] or segment_events[\"early_braking\"]:\n        min_speed = float(segment[\"speed\"].min())\n        recommendations[\"issue\"] = f\"Braking timing issue in Turn {turn_id} (min corner speed: {min_speed:.1f})\"\n        if segment_events[\"late_braking\"]:\n            recommendations[\"driver_technique\"] = (\n                \"1. Move initial brake application 0.5-1.0 second earlier (further up the braking zone). 2. Spread braking over longer distance. "\n                \"3. Begin brake release before corner entry, not inside the apex.\"\n            )\n        else:\n            recommendations[\"driver_technique\"] = (\n                \"1. Brake 0.3-0.5 seconds later (closer to the corner). 2. Use stronger braking intensity for shorter duration. "\n                \"3. Carry more speed into the corner; the car has capability.\"\n            )\n        recommendations[\"suspension_tuning\"] = (\n            \"• Adjust brake bias 1-2% forward to fine-tune pedal feel\\n"\n            "• Soften front bump significantly to reduce nose-dive if braking late\\n"\n            "• Stiffen rear spring +5% if braking late (reduces squat interference)\\n"\n            "• Fine-tune brake pad compound for consistency across temperature range\"\n        )\n    \n    return recommendations


def build_turn_summary(data: pd.DataFrame, events: Dict[str, pd.Series]) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []

    for turn_id in sorted(data["corner_id"].unique()):
        if turn_id <= 0:
            continue

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
            "unstable",
        ]:
            if events[key].loc[start_idx:end_idx].any():
                issues.append(EVENT_STYLES[key]["label"])

        rows.append(
            {
                "Turn": f"Turn {int(turn_id)}",
                "Entry Speed": round(float(segment["speed"].iloc[0]), 1),
                "Min Speed": round(float(segment["speed"].min()), 1),
                "Peak Slip": round(float(segment["slip_severity"].max()), 2),
                "Avg Throttle": round(float(segment["throttle_input"].mean() * 100), 1),
                "Key Issues": ", ".join(issues[:3]) if issues else "Clean",
            }
        )

    return pd.DataFrame(rows)


def generate_insights(
    data: pd.DataFrame,
    events: Dict[str, pd.Series],
    event_counts: Dict[str, int],
    scores: Dict[str, float],
    thresholds: Dict[str, float],
) -> List[str]:
    ranked_insights: List[Tuple[int, str]] = []

    def add(priority: int, text: str) -> None:
        ranked_insights.append((priority, text))

    if event_counts["oversteer"] > 0:
        location = dominant_location_label(data, events["oversteer"])
        peak_slip = float(data.loc[events["oversteer"], "slip_severity"].max())
        add(100, f"Oversteer detected in {location}. Slip severity peaks around {peak_slip:.1f}. Reduce entry speed slightly or delay throttle pickup until steering angle is falling.")

    if event_counts["understeer"] > 0:
        location = dominant_location_label(data, events["understeer"])
        add(95, f"Understeer is building in {location}. Steering demand is high without matching yaw response. Release the brake earlier and reduce steering lock at turn-in to recover front grip.")

    if event_counts["harsh_braking"] > 0:
        location = dominant_location_label(data, events["harsh_braking"])
        peak_pitch = float(data.loc[events["harsh_braking"], "pitch_abs"].max())
        add(92, f"Braking is too aggressive around {location}. Pitch spikes to about {peak_pitch:.2f}, upsetting platform balance. Build pedal pressure earlier and release it more progressively.")

    if event_counts["late_braking"] > 0:
        location = dominant_location_label(data, events["late_braking"])
        add(88, f"Late braking appears near {location}. Entry speed stays high until the corner. Move the initial brake hit a little earlier and spread the deceleration across a longer phase.")
    elif event_counts["early_braking"] > 0:
        location = dominant_location_label(data, events["early_braking"])
        add(82, f"Braking looks conservative near {location}. You are scrubbing speed earlier than necessary. Stay off the brake a fraction longer and carry a touch more minimum speed.")

    if event_counts["wheel_spin"] > 0:
        location = dominant_location_label(data, events["wheel_spin"])
        add(84, f"Throttle is being applied too early in {location}, causing wheel spin on exit. Let the car finish rotating first, then squeeze the throttle in as steering angle unwinds.")

    if event_counts["low_rpm_issue"] > 0:
        add(78, f"The engine is dropping below the efficient range in several acceleration zones. You are often under {thresholds['rpm_low']:.0f} RPM while asking for throttle, so downshift earlier or hold a lower gear longer.")

    if event_counts["high_rpm_issue"] > 0:
        add(76, f"Inefficient gear usage appears on the straights. RPM repeatedly climbs past {thresholds['rpm_high']:.0f}, so shifting a little earlier will keep the engine in a stronger power band.")

    high_speed_corner_mask = (
        data["corner_zone"]
        & (data["speed"] > thresholds["high_speed"])
        & (events["understeer"] | events["unstable"])
    )
    if count_segments(high_speed_corner_mask) > 0:
        location = dominant_location_label(data, high_speed_corner_mask)
        add(74, f"You are likely losing time in high-speed corners, with the biggest issue around {location}. Focus on one clean steering input and finish more of the brake release before peak lateral load.")

    unstable_ratio = mask_ratio(events["unstable"]) * 100
    if unstable_ratio > 8:
        location = dominant_location_label(data, events["unstable"])
        add(70, f"The car is unstable for about {unstable_ratio:.1f}% of the lap, especially around {location}. Smoother pedal transitions will calm yaw response and make the platform more predictable.")

    if scores["smoothness_score"] < 70:
        add(66, "Pedal transitions are busier than ideal. Reducing throttle and brake oscillation will lower load transfer spikes and make corner balance easier to repeat.")

    if scores["efficiency_score"] >= 80 and event_counts["high_rpm_issue"] == 0 and event_counts["low_rpm_issue"] == 0:
        add(48, "Gear selection is generally efficient. The next gains are more likely to come from corner entry discipline and exit timing than from shift strategy.")

    if not ranked_insights:
        add(40, "The telemetry trace is broadly tidy. The easiest next gain is to feed throttle in a little earlier on exits once steering is nearly straight, while keeping brake release smooth into the apex.")

    ranked_insights.sort(key=lambda item: item[0], reverse=True)
    unique_text: List[str] = []
    seen = set()
    for _, text in ranked_insights:
        if text not in seen:
            seen.add(text)
            unique_text.append(text)
        if len(unique_text) == 7:
            break
    return unique_text


def build_stats(data: pd.DataFrame) -> Dict[str, float]:
    return {
        "lap_time": float(data["relative_time"].iloc[-1]),
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
    grade = classify_grade(scores["final_score"])
    insights = generate_insights(zoned, events, event_counts, scores, thresholds)
    turn_summary = build_turn_summary(zoned, events)
    stats = build_stats(zoned)

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
        lap_time=stats["lap_time"],
        stats=stats,
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
            x=data["relative_time"],
            y=data["speed"],
            mode="lines",
            name="Speed",
            line=dict(color="#1f77b4", width=3),
            hovertemplate="Time %{x:.2f}s<br>Speed %{y:.2f}<extra></extra>",
        )
    )
    add_event_markers(fig, data, bundle.events, "relative_time", "speed", ["oversteer", "understeer", "unstable"])
    return style_figure(fig, "Speed vs Time", "Time (s)", "Speed")


def build_controls_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data.copy()
    data["throttle_pct"] = data["throttle_input"] * 100
    data["brake_pct"] = data["brake_input"] * 100

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["relative_time"],
            y=data["throttle_pct"],
            mode="lines",
            name="Throttle",
            line=dict(color="#2ca02c", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=data["relative_time"],
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
        "relative_time",
        "brake_pct",
        ["harsh_braking", "late_braking", "early_braking"],
    )
    if bundle.events["wheel_spin"].any():
        subset = data.loc[bundle.events["wheel_spin"]]
        fig.add_trace(
            go.Scatter(
                x=subset["relative_time"],
                y=subset["throttle_pct"],
                mode="markers",
                name="Wheel Spin",
                marker=dict(color=EVENT_STYLES["wheel_spin"]["color"], symbol="star", size=9),
            )
        )
    return style_figure(fig, "Throttle and Brake vs Time", "Time (s)", "Pedal Input (%)")


def build_slip_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["relative_time"],
            y=data["combined_slip_angle"],
            mode="lines",
            name="Combined Slip Angle",
            line=dict(color="#ff7f0e", width=3),
        )
    )
    add_event_markers(fig, data, bundle.events, "relative_time", "combined_slip_angle", ["oversteer", "wheel_spin"])
    return style_figure(fig, "Slip Angle vs Time", "Time (s)", "Slip Angle")


def build_yaw_vs_steering_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = px.scatter(
        data,
        x="steering_angle",
        y="yaw_moment",
        color="speed",
        color_continuous_scale="Turbo",
        labels={"steering_angle": "Steering Angle", "yaw_moment": "Yaw Moment", "speed": "Speed"},
        title="Yaw vs Steering",
    )

    for key in ["oversteer", "understeer"]:
        if not bundle.events[key].any():
            continue
        style = EVENT_STYLES[key]
        subset = data.loc[bundle.events[key]]
        fig.add_trace(
            go.Scatter(
                x=subset["steering_angle"],
                y=subset["yaw_moment"],
                mode="markers",
                name=style["label"],
                marker=dict(color=style["color"], symbol=style["symbol"], size=9, line=dict(color="white", width=0.8)),
            )
        )

    return style_figure(fig, "Yaw vs Steering", "Steering Angle", "Yaw Moment", height=420)


def build_rpm_gear_figure(bundle: AnalysisBundle) -> go.Figure:
    data = bundle.data
    fig = px.scatter(
        data,
        x="gear",
        y="rpm",
        color="throttle_input",
        color_continuous_scale="Viridis",
        labels={"gear": "Gear", "rpm": "RPM", "throttle_input": "Throttle"},
        title="RPM vs Gear",
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
                x=subset["gear"],
                y=subset["rpm"],
                mode="markers",
                name=style["label"],
                marker=dict(color=style["color"], symbol=style["symbol"], size=9, line=dict(width=0.8, color="white")),
            )
        )

    return style_figure(fig, "RPM vs Gear", "Gear", "RPM", height=420)


def build_track_map_figure(
    bundle: AnalysisBundle,
    color_metric: str = "speed",
    selected_index: Optional[int] = None,
) -> go.Figure:
    data = bundle.data
    metric_labels = {
        "speed": "Speed",
        "slip_severity": "Slip Severity",
        "stability_index": "Stability Index",
    }

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data["longitude"],
            y=data["latitude"],
            mode="lines",
            name="Track Centerline",
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
                    data["relative_time"],
                    data["speed"],
                    data["throttle_input"] * 100,
                    data["brake_input"] * 100,
                ],
                axis=1,
            ),
            hovertemplate=(
                "Time %{customdata[0]:.2f}s"
                "<br>Speed %{customdata[1]:.2f}"
                "<br>Throttle %{customdata[2]:.1f}%"
                "<br>Brake %{customdata[3]:.1f}%<extra></extra>"
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
                name="Replay Position",
                marker=dict(color="#111111", size=16, symbol="star"),
            )
        )

    fig.update_yaxes(scaleanchor="x", scaleratio=1)
    return style_figure(fig, "Track Map", "Longitude", "Latitude", height=620)


def build_comparison_speed_figure(primary: AnalysisBundle, comparison: AnalysisBundle) -> go.Figure:
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=primary.data["relative_time"],
            y=primary.data["speed"],
            mode="lines",
            name=primary.name,
            line=dict(color="#1f77b4", width=3),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=comparison.data["relative_time"],
            y=comparison.data["speed"],
            mode="lines",
            name=comparison.name,
            line=dict(color="#d62728", width=3),
        )
    )
    return style_figure(fig, "Lap Comparison: Speed Trace", "Relative Time (s)", "Speed", height=420)


def build_score_comparison_figure(primary: AnalysisBundle, comparison: AnalysisBundle) -> go.Figure:
    score_rows = pd.DataFrame(
        [
            {"Metric": "Driver Score", primary.name: primary.scores["final_score"], comparison.name: comparison.scores["final_score"]},
            {"Metric": "Smoothness", primary.name: primary.scores["smoothness_score"], comparison.name: comparison.scores["smoothness_score"]},
            {"Metric": "Control", primary.name: primary.scores["control_score"], comparison.name: comparison.scores["control_score"]},
            {"Metric": "Efficiency", primary.name: primary.scores["efficiency_score"], comparison.name: comparison.scores["efficiency_score"]},
            {"Metric": "Aggression", primary.name: primary.scores["aggression_score"], comparison.name: comparison.scores["aggression_score"]},
        ]
    )
    melted = score_rows.melt(id_vars="Metric", var_name="Lap", value_name="Score")
    fig = px.bar(
        melted,
        x="Metric",
        y="Score",
        color="Lap",
        barmode="group",
        text_auto=".1f",
        title="Score Comparison",
    )
    return style_figure(fig, "Score Comparison", "Metric", "Score", height=420)


def render_metric_cards(bundle: AnalysisBundle) -> None:
    score_columns = st.columns(6)
    score_columns[0].metric("Driver Score", f"{bundle.scores['final_score']:.1f}/100")
    score_columns[1].metric("Grade", bundle.grade)
    score_columns[2].metric("Smoothness", f"{bundle.scores['smoothness_score']:.1f}")
    score_columns[3].metric("Control", f"{bundle.scores['control_score']:.1f}")
    score_columns[4].metric("Efficiency", f"{bundle.scores['efficiency_score']:.1f}")
    score_columns[5].metric("Aggression", f"{bundle.scores['aggression_score']:.1f}")
    st.caption("Aggression is an intensity score. The final driver score rewards balanced aggression, not maximum aggression.")


def render_summary_metrics(bundle: AnalysisBundle) -> None:
    stats_columns = st.columns(4)
    stats_columns[0].metric("Lap Time", f"{bundle.lap_time:.2f}s")
    stats_columns[1].metric("Average Speed", f"{bundle.stats['average_speed']:.1f}")
    stats_columns[2].metric("Top Speed", f"{bundle.stats['top_speed']:.1f}")
    stats_columns[3].metric("Turns Detected", f"{int(bundle.stats['turns_detected'])}")

    event_columns = st.columns(5)
    event_columns[0].metric("Oversteer Zones", bundle.event_counts["oversteer"])
    event_columns[1].metric("Understeer Zones", bundle.event_counts["understeer"])
    event_columns[2].metric("Harsh Brakes", bundle.event_counts["harsh_braking"])
    event_columns[3].metric("Wheel Spin Zones", bundle.event_counts["wheel_spin"])
    event_columns[4].metric("Unstable Segments", bundle.event_counts["unstable"])


def render_insights(bundle: AnalysisBundle) -> None:
    st.subheader("Actionable Insights")
    st.markdown("\n".join(f"- {insight}" for insight in bundle.insights))


def render_turn_table(bundle: AnalysisBundle) -> None:
    st.subheader("Turn-by-Turn Summary")
    if bundle.turn_summary.empty:
        st.info("No clear corner zones were detected from steering activity in this upload.")
        return

    st.caption("Turn numbering is inferred from steering activity and represents corner order within the uploaded file.")
    st.dataframe(bundle.turn_summary, use_container_width=True, hide_index=True)


def render_overview(bundle: AnalysisBundle) -> None:
    render_metric_cards(bundle)
    render_summary_metrics(bundle)
    render_insights(bundle)
    render_turn_table(bundle)

    with st.expander("Auto-detected thresholds"):
        threshold_frame = pd.DataFrame(
            {
                "Metric": [
                    "Brake zone threshold",
                    "Throttle zone threshold",
                    "Corner zone threshold",
                    "High slip threshold",
                    "High RPM threshold",
                    "Low RPM threshold",
                ],
                "Value": [
                    round(bundle.thresholds["brake_threshold"], 3),
                    round(bundle.thresholds["throttle_threshold"], 3),
                    round(bundle.thresholds["corner_threshold"], 3),
                    round(bundle.thresholds["slip_high"], 3),
                    round(bundle.thresholds["rpm_high"], 1),
                    round(bundle.thresholds["rpm_low"], 1),
                ],
            }
        )
        st.dataframe(threshold_frame, use_container_width=True, hide_index=True)


def render_charts(bundle: AnalysisBundle) -> None:
    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.plotly_chart(build_speed_figure(bundle), use_container_width=True)
        st.plotly_chart(build_slip_figure(bundle), use_container_width=True)
    with chart_col_2:
        st.plotly_chart(build_controls_figure(bundle), use_container_width=True)
        st.plotly_chart(build_yaw_vs_steering_figure(bundle), use_container_width=True)

    st.plotly_chart(build_rpm_gear_figure(bundle), use_container_width=True)


def render_track_map(bundle: AnalysisBundle) -> None:
    if not has_gps(bundle.data):
        st.info("GPS columns were not provided, so the track map and replay view are unavailable for this upload.")
        return

    selector_col, replay_col = st.columns([1, 2])
    with selector_col:
        color_choice = st.selectbox(
            "Color track by",
            options=[
                ("speed", "Speed"),
                ("slip_severity", "Slip Severity"),
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
    replay_metrics[0].metric("Replay Time", f"{snapshot['relative_time']:.2f}s")
    replay_metrics[1].metric("Speed", f"{snapshot['speed']:.1f}")
    replay_metrics[2].metric("Throttle", f"{snapshot['throttle_input'] * 100:.1f}%")
    replay_metrics[3].metric("Brake", f"{snapshot['brake_input'] * 100:.1f}%")
    replay_metrics[4].metric("Gear", f"{int(snapshot['gear'])}")
    replay_metrics[5].metric("Slip", f"{snapshot['slip_severity']:.2f}")


def render_comparison(primary: AnalysisBundle, comparison: AnalysisBundle) -> None:
    lap_time_delta = comparison.lap_time - primary.lap_time
    score_delta = comparison.scores["final_score"] - primary.scores["final_score"]
    avg_speed_delta = comparison.stats["average_speed"] - primary.stats["average_speed"]
    control_delta = comparison.scores["control_score"] - primary.scores["control_score"]

    summary_cols = st.columns(4)
    summary_cols[0].metric("Lap Time Delta", f"{lap_time_delta:+.2f}s")
    summary_cols[1].metric("Driver Score Delta", f"{score_delta:+.1f}")
    summary_cols[2].metric("Average Speed Delta", f"{avg_speed_delta:+.1f}")
    summary_cols[3].metric("Control Delta", f"{control_delta:+.1f}")

    if primary.lap_time < comparison.lap_time:
        best_text = f"{primary.name} is currently the quicker lap by {comparison.lap_time - primary.lap_time:.2f}s."
    elif comparison.lap_time < primary.lap_time:
        best_text = f"{comparison.name} is currently the quicker lap by {primary.lap_time - comparison.lap_time:.2f}s."
    else:
        best_text = "Both uploads show the same lap time, so the score breakdown is the better differentiator."
    st.markdown(best_text)
    st.caption("Lap time delta is meaningful when both uploads represent comparable full laps or driver runs.")

    comparison_col_1, comparison_col_2 = st.columns(2)
    with comparison_col_1:
        st.plotly_chart(build_comparison_speed_figure(primary, comparison), use_container_width=True)
    with comparison_col_2:
        st.plotly_chart(build_score_comparison_figure(primary, comparison), use_container_width=True)

    insight_col_1, insight_col_2 = st.columns(2)
    with insight_col_1:
        st.subheader(primary.name)
        st.markdown("\n".join(f"- {insight}" for insight in primary.insights[:4]))
    with insight_col_2:
        st.subheader(comparison.name)
        st.markdown("\n".join(f"- {insight}" for insight in comparison.insights[:4]))


def main() -> None:
    st.set_page_config(page_title="Driver Telemetry Analysis System", layout="wide")
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1.4rem;
            padding-bottom: 2rem;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.8rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.title("Driver Telemetry Analysis System")
    st.write("Upload race telemetry CSV files to convert driver inputs and vehicle dynamics into coaching insights, performance scoring, and interactive visuals.")

    with st.expander("Expected CSV schema"):
        st.code(", ".join(REQUIRED_COLUMNS + OPTIONAL_COLUMNS), language="text")
        st.caption("`latitude` and `longitude` are optional, but they unlock the track map and replay view.")

    uploader_col_1, uploader_col_2 = st.columns(2)
    with uploader_col_1:
        primary_upload = st.file_uploader("Upload telemetry CSV", type=["csv"], key="primary")
    with uploader_col_2:
        comparison_upload = st.file_uploader("Optional: compare another lap or driver", type=["csv"], key="comparison")

    if primary_upload is None:
        st.info("Upload a telemetry CSV to start the analysis dashboard.")
        return

    try:
        with st.spinner("Analyzing primary telemetry..."):
            primary_bundle = analyze_uploaded_file(primary_upload)
    except Exception as exc:
        st.error(f"Could not analyze the uploaded file: {exc}")
        return

    comparison_bundle = None
    if comparison_upload is not None:
        try:
            with st.spinner("Analyzing comparison telemetry..."):
                comparison_bundle = analyze_uploaded_file(comparison_upload)
        except Exception as exc:
            st.error(f"Comparison file could not be analyzed: {exc}")

    overview_tab, charts_tab, map_tab, comparison_tab = st.tabs(
        ["Overview", "Telemetry Charts", "Track Map", "Comparison"]
    )

    with overview_tab:
        render_overview(primary_bundle)

    with charts_tab:
        render_charts(primary_bundle)

    with map_tab:
        render_track_map(primary_bundle)

    with comparison_tab:
        if comparison_bundle is None:
            st.info("Upload a second telemetry CSV to compare laps or drivers.")
        else:
            render_comparison(primary_bundle, comparison_bundle)


if __name__ == "__main__":
    main()
