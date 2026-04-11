"""
Advanced Features Module - Session History, Trending, and Export Functionality
Extends the base telemetry analysis with additional analysis capabilities
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

class SessionHistory:
    """Track session history and identify trends over time"""
    
    def __init__(self, history_file: str = "session_history.json"):
        self.history_file = history_file
        self.sessions = self.load_history()
    
    def load_history(self) -> List[Dict]:
        """Load session history from JSON"""
        try:
            with open(self.history_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return []
    
    def save_history(self):
        """Save session history to JSON"""
        with open(self.history_file, 'w') as f:
            json.dump(self.sessions, f, indent=2)
    
    def add_session(self, filename: str, lap_time: float, lap_distance: float, 
                   consistency: float, handling: float, stability: float) -> None:
        """Add new session to history"""
        session = {
            "timestamp": datetime.now().isoformat(),
            "filename": filename,
            "lap_time": lap_time,
            "lap_distance": lap_distance,
            "consistency": consistency,
            "handling": handling,
            "stability": stability,
        }
        self.sessions.append(session)
        self.save_history()
    
    def get_trending(self) -> Dict:
        """Calculate trending metrics"""
        if len(self.sessions) < 2:
            return {}
        
        df = pd.DataFrame(self.sessions)
        
        trends = {
            "lap_time_trend": float(df.iloc[-1]["lap_time"] - df.iloc[0]["lap_time"]),
            "consistency_trend": float(df.iloc[-1]["consistency"] - df.iloc[0]["consistency"]),
            "handling_trend": float(df.iloc[-1]["handling"] - df.iloc[0]["handling"]),
            "stability_trend": float(df.iloc[-1]["stability"] - df.iloc[0]["stability"]),
            "improvement_rate": float((df.iloc[-1]["consistency"] - df.iloc[0]["consistency"]) / len(df)),
        }
        
        return trends
    
    def get_personal_best(self) -> Optional[Dict]:
        """Get personal best lap"""
        if not self.sessions:
            return None
        
        df = pd.DataFrame(self.sessions)
        best_idx = df["lap_time"].idxmin()
        return df.iloc[best_idx].to_dict()
    
    def get_session_count(self) -> int:
        """Get total number of sessions"""
        return len(self.sessions)


class AdvancedComparison:
    """Advanced comparison metrics between laps"""
    
    @staticmethod
    def corner_by_corner_delta(primary_data: pd.DataFrame, comparison_data: pd.DataFrame,
                               primary_corners: int, comparison_corners: int) -> pd.DataFrame:
        """Compare corner-by-corner performance"""
        deltas = []
        
        max_corners = min(primary_corners, comparison_corners)
        
        for corner_id in range(1, max_corners + 1):
            primary_corner = primary_data[primary_data["corner_id"] == corner_id]
            comparison_corner = comparison_data[comparison_data["corner_id"] == corner_id]
            
            if len(primary_corner) == 0 or len(comparison_corner) == 0:
                continue
            
            delta = {
                "corner": f"T{corner_id}",
                "time_delta": (comparison_corner["relative_time"].iloc[-1] - 
                             comparison_corner["relative_time"].iloc[0]) - \
                            (primary_corner["relative_time"].iloc[-1] - 
                             primary_corner["relative_time"].iloc[0]),
                "speed_delta": comparison_corner["speed"].mean() - primary_corner["speed"].mean(),
                "slip_delta": comparison_corner["slip_severity"].max() - primary_corner["slip_severity"].max(),
                "throttle_delta": comparison_corner["throttle_input"].mean() - primary_corner["throttle_input"].mean(),
            }
            deltas.append(delta)
        
        return pd.DataFrame(deltas)


class HeatmapGenerator:
    """Generate heatmaps for telemetry data visualization"""
    
    @staticmethod
    def braking_heatmap(data: pd.DataFrame) -> Dict:
        """Identify intense braking zones"""
        aggressive_threshold = data["brake_input"].quantile(0.75)
        braking_zones = data[data["brake_input"] > aggressive_threshold]
        
        return {
            "count": len(braking_zones),
            "avg_intensity": float(braking_zones["brake_input"].mean()),
            "peak_intensity": float(braking_zones["brake_input"].max()),
            "locations": braking_zones["distance_traveled"].tolist(),
        }
    
    @staticmethod
    def acceleration_heatmap(data: pd.DataFrame) -> Dict:
        """Identify intense acceleration zones"""
        aggressive_threshold = data["throttle_input"].quantile(0.75)
        accel_zones = data[data["throttle_input"] > aggressive_threshold]
        
        return {
            "count": len(accel_zones),
            "avg_intensity": float(accel_zones["throttle_input"].mean()),
            "peak_intensity": float(accel_zones["throttle_input"].max()),
            "locations": accel_zones["distance_traveled"].tolist(),
        }
    
    @staticmethod
    def slip_heatmap(data: pd.DataFrame) -> Dict:
        """Identify high-slip zones"""
        high_slip_threshold = data["slip_severity"].quantile(0.85)
        slip_zones = data[data["slip_severity"] > high_slip_threshold]
        
        return {
            "count": len(slip_zones),
            "avg_slip": float(slip_zones["slip_severity"].mean()),
            "peak_slip": float(slip_zones["slip_severity"].max()),
            "locations": slip_zones["distance_traveled"].tolist(),
        }


class AlertSystem:
    """Generate real-time alerts and warnings"""
    
    @staticmethod
    def generate_alerts(bundle) -> List[Dict]:
        """Generate contextual alerts"""
        alerts = []
        
        # High oversteer
        if bundle.event_counts.get("oversteer", 0) > 2:
            alerts.append({
                "level": "warning",
                "icon": "⚠️",
                "title": "Multiple Oversteer Events",
                "message": f"{bundle.event_counts['oversteer']} oversteer incidents detected",
                "action": "Reduce entry speed or rear wing angle",
            })
        
        # Low consistency
        if bundle.scores.get("consistency_score", 0) < 70:
            alerts.append({
                "level": "caution",
                "icon": "📉",
                "title": "Low Consistency Score",
                "message": f"Consistency at {bundle.scores['consistency_score']:.0f}/100",
                "action": "Focus on repeating brake points and throttle inputs",
            })
        
        # High instability
        if bundle.scores.get("stability_score", 0) < 75:
            alerts.append({
                "level": "warning",
                "icon": "🔄",
                "title": "Stability Concerns",
                "message": f"Stability score {bundle.scores['stability_score']:.0f}/100",
                "action": "Smooth throttle application and steering inputs",
            })
        
        # Excessive harsh braking
        if bundle.event_counts.get("harsh_braking", 0) > 2:
            alerts.append({
                "level": "info",
                "icon": "🛑",
                "title": "Harsh Braking Detected",
                "message": f"{bundle.event_counts['harsh_braking']} harsh braking events",
                "action": "Build brake pressure gradually over 0.5-1.0 seconds",
            })
        
        return alerts


class PerformanceTracker:
    """Track driver performance improvements"""
    
    @staticmethod
    def identify_weak_sectors(sessions: List[Dict]) -> Dict:
        """Identify sectors that need improvement"""
        if len(sessions) < 2:
            return {}
        
        latest = sessions[-1]
        previous = sessions[-2]
        
        sectors = {
            "consistency": latest["consistency"] - previous["consistency"],
            "handling": latest["handling"] - previous["handling"],
            "stability": latest["stability"] - previous["stability"],
        }
        
        weak = {k: v for k, v in sectors.items() if v < 0}
        return weak
    
    @staticmethod
    def estimate_improvement(sessions: List[Dict], metric: str = "consistency") -> float:
        """Estimate improvement rate per session"""
        if len(sessions) < 2:
            return 0.0
        
        df = pd.DataFrame(sessions)
        if metric not in df.columns:
            return 0.0
        
        values = df[metric].values
        improvement = values[-1] - values[0]
        sessions_count = len(values)
        
        return float(improvement / sessions_count)


class ExportManager:
    """Export analysis data in various formats"""
    
    @staticmethod
    def prepare_export_data(bundle) -> Dict:
        """Prepare data for export in multiple formats"""
        export_data = {
            "session_info": {
                "file": bundle.name,
                "timestamp": datetime.now().isoformat(),
                "lap_time": bundle.lap_time,
                "lap_distance": bundle.stats.get("lap_distance", 0),
            },
            "performance_scores": {
                "consistency": bundle.scores.get("consistency_score", 0),
                "handling": bundle.scores.get("handling_score", 0),
                "stability": bundle.scores.get("stability_score", 0),
                "overall_grade": bundle.grade,
            },
            "events": bundle.event_counts,
            "insights": bundle.insights,
            "turn_summary": bundle.turn_summary.to_dict("records") if not bundle.turn_summary.empty else [],
        }
        return export_data
    
    @staticmethod
    def export_csv(bundle, filename: str = "telemetry_export.csv") -> str:
        """Export turn-by-turn summary as CSV"""
        if bundle.turn_summary.empty:
            return "No turn data to export"
        
        bundle.turn_summary.to_csv(filename, index=False)
        return f"Exported to {filename}"
    
    @staticmethod
    def export_json(bundle, filename: str = "telemetry_export.json") -> str:
        """Export full analysis as JSON"""
        export_data = ExportManager.prepare_export_data(bundle)
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        return f"Exported to {filename}"


class AdaptiveCoaching:
    """Adaptive coaching based on performance patterns"""
    
    @staticmethod
    def get_personalized_tips(bundle) -> List[str]:
        """Generate personalized tips based on performance"""
        tips = []
        
        # Based on consistency
        consistency = bundle.scores.get("consistency_score", 0)
        if consistency < 60:
            tips.append("🎯 **Consistency Priority:** Record and reference a 'ideal' lap to replicate braking points exactly")
        elif consistency < 75:
            tips.append("📍 **Improve Consistency:** Brake 0.1-0.2s earlier each session for 5 sessions - measure improvement")
        
        # Based on handling
        handling = bundle.scores.get("handling_score", 0)
        if handling < 70:
            tips.append("🎮 **Smooth Inputs:** Practice smooth steering wheel movements - avoid sudden corrections")
        
        # Based on oversteer
        oversteer = bundle.event_counts.get("oversteer", 0)
        if oversteer > 2:
            tips.append("↗️ **Oversteer Control:** Try -0.5° less steering angle in corners, apply throttle 0.3s later")
        
        # Based on understeer
        understeer = bundle.event_counts.get("understeer", 0)
        if understeer > 2:
            tips.append("↙️ **Front Grip:** Brake 0.2s earlier before corners, use progressive steering input")
        
        # Based on braking
        braking = bundle.event_counts.get("harsh_braking", 0)
        if braking > 3:
            tips.append("🛑 **Brake Modulation:** Progressive braking saves 0.2-0.3s per lap - practice on straights first")
        
        # Based on stability
        stability = bundle.scores.get("stability_score", 0)
        if stability < 80:
            tips.append("⚖️ **Stability:** Reduce throttle aggressiveness on corner exits by 20% for 3 laps")
        
        return tips if tips else ["✨ **Great job!** Maintain current technique and focus on consistency"]
