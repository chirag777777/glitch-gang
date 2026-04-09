#!/usr/bin/env python3
"""DIAGNOSTIC: Show exact metric values for your sample data"""

import pandas as pd
import sys
import os

sys.path.insert(0, 'c:/Users/Maha/Documents/telemetry')
import app

print("\n" + "=" * 80)
print("🔧 DIAGNOSTIC: METRIC CALCULATION TEST")
print("=" * 80)

# Load sample data
df = pd.read_csv('sample_clean_telemetry.csv')
print(f"\n✅ Loaded CSV: 77 rows")
print(f"   Columns: {df.columns.tolist()}")

# Clean
cleaned = app.clean_telemetry_data(df)
print(f"\n✅ After cleaning: {len(cleaned)} rows")
print(f"   'time' column: {'✓' if 'time' in cleaned.columns else '✗'}")
print(f"   'distance_traveled' column: {'✗ (NOT YET)'}")

# Engineer features
featured = app.engineer_features(cleaned)
print(f"\n✅ After engineer_features: {len(featured)} rows")
print(f"   'distance_traveled' column: {'✓' if 'distance_traveled' in featured.columns else '✗'}")
if 'distance_traveled' in featured.columns:
    print(f"      - First value: {featured['distance_traveled'].iloc[0]:.2f}m")
    print(f"      - Last value: {featured['distance_traveled'].iloc[-1]:.2f}m")

# Full pipeline
thresholds = app.compute_thresholds(featured)
zoned = app.add_zone_columns(featured, thresholds)
events = app.detect_events(zoned, thresholds)
event_counts = {key: app.count_segments(mask) for key, mask in events.items()}
scores = app.compute_scores(zoned, events, thresholds)

# Call build_stats
print(f"\n✅ Calling build_stats():")
stats = app.build_stats(zoned)
print(f"   lap_time: {stats['lap_time']} seconds")
print(f"   lap_distance: {stats['lap_distance']} metres")
print(f"   average_speed: {stats['average_speed']} km/h")
print(f"   top_speed: {stats['top_speed']} km/h")

# Create bundle
print(f"\n✅ Creating AnalysisBundle:")
bundle = app.AnalysisBundle(
    name='sample_clean_telemetry.csv',
    data=zoned,
    thresholds=thresholds,
    events=events,
    event_counts=event_counts,
    scores=scores,
    grade=app.classify_grade(scores["consistency_score"]),
    insights=app.generate_insights(zoned, events, event_counts, scores, thresholds),
    turn_summary=app.build_turn_summary(zoned, events),
    sector_summary=app.build_sector_summary(zoned, events),
    lap_time=stats["lap_time"],
    stats=stats,
    ml_results=None,
)

print(f"   bundle.lap_time: {bundle.lap_time}")
print(f"   bundle.stats['lap_distance']: {bundle.stats['lap_distance']}")

# Simulate display
print(f"\n✅ METRIC VALUES THAT SHOULD DISPLAY:")
print(f"   Lap Time: {bundle.lap_time:.2f}s")
print(f"   Total Distance: {bundle.stats.get('lap_distance', 0):.0f}m")
print(f"   Average Speed: {bundle.stats['average_speed']:.1f} km/h")
print(f"   Top Speed: {bundle.stats['top_speed']:.1f} km/h")

print("\n" + "=" * 80)
if bundle.lap_time > 0 and bundle.stats['lap_distance'] > 0:
    print("✅ CORRECT: Metrics are calculating properly")
    print("\n⚠️  IF APP SHOWS 0:")
    print("   1. Close the Streamlit terminal window")
    print("   2. Delete folder: c:/Users/Maha/.streamlit/") 
    print("   3. Run: streamlit run app.py")
    print("   4. Upload CSV again")  
else:
    print("❌ ERROR: Metrics are 0 - issue in calculation")
print("=" * 80 + "\n")
