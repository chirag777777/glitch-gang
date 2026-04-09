#!/usr/bin/env python3
"""Debug script to trace metrics calculation through the pipeline"""

import pandas as pd
import sys

sys.path.insert(0, 'c:/Users/Maha/Documents/telemetry')
import app

# Load sample data
print("=" * 70)
print("🔍 DEBUGGING METRICS CALCULATION")
print("=" * 70)

df = pd.read_csv('sample_clean_telemetry.csv')
print(f"\n1️⃣  RAW CSV LOAD: {len(df)} rows")
print(f"   Columns: {df.columns.tolist()}")

# Step through the pipeline
cleaned = app.clean_telemetry_data(df)
print(f"\n2️⃣  AFTER CLEAN: {len(cleaned)} rows")
print(f"   Has 'time': {'time' in cleaned.columns}")
print(f"   Has 'dt': {'dt' in cleaned.columns}")
print(f"   Has 'speed': {'speed' in cleaned.columns}")
if 'time' in cleaned.columns:
    print(f"   Time range: {cleaned['time'].min():.4f}s to {cleaned['time'].max():.4f}s")
if 'dt' in cleaned.columns:
    print(f"   dt min/max: {cleaned['dt'].min():.6f}s / {cleaned['dt'].max():.6f}s")
    print(f"   dt mean: {cleaned['dt'].mean():.6f}s")

featured = app.engineer_features(cleaned)
print(f"\n3️⃣  AFTER ENGINEER_FEATURES: {len(featured)} rows")
print(f"   Has 'distance_traveled': {'distance_traveled' in featured.columns}")
if 'distance_traveled' in featured.columns:
    print(f"   Distance range: {featured['distance_traveled'].min():.2f}m to {featured['distance_traveled'].max():.2f}m")
    print(f"   Final distance (last row): {featured['distance_traveled'].iloc[-1]:.2f}m")

thresholds = app.compute_thresholds(featured)
zoned = app.add_zone_columns(featured, thresholds)
print(f"\n4️⃣  AFTER ZONE PROCESSING: {len(zoned)} rows")
print(f"   Has 'distance_traveled': {'distance_traveled' in zoned.columns}")
if 'distance_traveled' in zoned.columns:
    print(f"   Final distance (last row): {zoned['distance_traveled'].iloc[-1]:.2f}m")

# Test build_stats
stats = app.build_stats(zoned)
print(f"\n5️⃣  STATS FROM build_stats():")
print(f"   lap_time: {stats['lap_time']:.2f}s")
print(f"   lap_distance: {stats['lap_distance']:.2f}m")
print(f"   average_speed: {stats['average_speed']:.2f} km/h")
print(f"   top_speed: {stats['top_speed']:.2f} km/h")

# Check raw calculation
print(f"\n6️⃣  MANUAL VERIFICATION:")
manual_lap_time = zoned["time"].iloc[-1] - zoned["time"].iloc[0]
manual_distance = zoned["distance_traveled"].iloc[-1]
print(f"   Manual lap_time: {manual_lap_time:.2f}s")
print(f"   Manual distance: {manual_distance:.2f}m")

print("\n" + "=" * 70)
if abs(stats['lap_time'] - manual_lap_time) < 0.01 and abs(stats['lap_distance'] - manual_distance) < 0.01:
    print("✅ METRICS CORRECTLY CALCULATED")
else:
    print("❌ METRICS MISMATCH - ISSUE FOUND")
print("=" * 70)
