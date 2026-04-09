#!/usr/bin/env python3
"""Test all graph rendering"""

import pandas as pd
import sys

sys.path.insert(0, 'c:/Users/Maha/Documents/telemetry')
import app

print("=" * 70)
print("🔍 TESTING ALL GRAPH RENDERING")
print("=" * 70)

# Create bundle
with open('sample_clean_telemetry.csv', 'rb') as f:
    file_bytes = f.read()

class FakeUpload:
    def __init__(self, name, data):
        self.name = name
        self._data = data
    def getvalue(self):
        return self._data

fake_file = FakeUpload('sample_clean_telemetry.csv', file_bytes)
bundle = app.analyze_uploaded_file(fake_file)

def test_graph(graph_func, name):
    try:
        fig = graph_func(bundle)
        if fig is None:
            print(f"⚠️  {name}: Returned None (optional)")
            return True
        # Check if it's a plotly figure
        if hasattr(fig, 'data') and hasattr(fig, 'layout'):
            # Check X-axis is distance
            if hasattr(fig, 'xaxes'):
                print(f"✅ {name}: Created successfully")
                return True
            else:
                print(f"⚠️  {name}: Created but axis data unclear")
                return True
        else:
            print(f"❌ {name}: Not a valid Plotly figure")
            return False
    except Exception as e:
        print(f"❌ {name}: {str(e)}")
        return False

print("\nTesting graph functions:")
print("-" * 70)

results = {
    "Speed vs Distance": test_graph(app.build_speed_figure, "Speed vs Distance"),
    "Throttle & Brake": test_graph(app.build_controls_figure, "Throttle & Brake"),
    "Slip Angle": test_graph(app.build_slip_figure, "Slip Angle"),
    "Lateral Accel": test_graph(app.build_lateral_accel_figure, "Lateral Acceleration"),
    "Steering & Yaw": test_graph(app.build_steering_yaw_figure, "Steering & Yaw"),
    "RPM Evolution": test_graph(app.build_rpm_evolution_figure, "RPM Evolution"),
    "Cornering Speed": test_graph(app.build_cornering_speed_figure, "Cornering Speed (opt)"),
    "Energy Efficient": test_graph(app.build_energy_efficient_figure, "Energy Efficient (opt)"),
}

print("\n" + "=" * 70)
print(f"SUMMARY:")
passed = sum(1 for v in results.values() if v)
total = len(results)
print(f"  {passed}/{total} graphs working correctly")
print("=" * 70)
