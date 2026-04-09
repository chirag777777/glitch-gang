#!/usr/bin/env python3
"""Debug distance and lap time calculations"""
import pandas as pd
import numpy as np
import sys
sys.path.insert(0, 'c:/Users/Maha/Documents/telemetry')
import app

# Load sample data
df = pd.read_csv('sample_clean_telemetry.csv')
print(f"✅ Raw data loaded: {len(df)} rows\n")

# Step 1: Clean data
print("Step 1: Clean telemetry data")
cleaned = app.clean_telemetry_data(df)
print(f"  Rows: {len(cleaned)}")
print(f"  Time range: {cleaned['time'].min():.2f}s to {cleaned['time'].max():.2f}s")
print(f"  Time diff: {cleaned['time'].iloc[-1] - cleaned['time'].iloc[0]:.2f}s")
print(f"  dt values (first 5): {cleaned['dt'].head().values}")
print(f"  dt mean: {cleaned['dt'].mean():.4f}s")
print(f"  Speed range: {cleaned['speed'].min():.1f} to {cleaned['speed'].max():.1f} km/h\n")

# Step 2: Engineer features
print("Step 2: Engineer features")
featured = app.engineer_features(cleaned)
print(f"  Distance calc formula: (speed * dt / 3.6).cumsum()")
print(f"  First 5 distance values: {featured['distance_traveled'].head().values}")
print(f"  Last distance value: {featured['distance_traveled'].iloc[-1]:.1f}m")
print(f"  Distance cumsum test: Speed[0]={featured['speed'].iloc[0]:.1f} km/h, dt[0]={featured['dt'].iloc[0]:.4f}s")
dist_calc = (featured['speed'].iloc[0] * featured['dt'].iloc[0] / 3.6)
print(f"  Manual calc: {featured['speed'].iloc[0]:.1f} * {featured['dt'].iloc[0]:.4f} / 3.6 = {dist_calc:.4f}m\n")

# Step 3: Add zone columns
print("Step 3: Add zone columns")
thresholds = app.compute_thresholds(featured)
zoned = app.add_zone_columns(featured, thresholds)
print(f"  Corner_id added: {zoned['corner_id'].max():.0f} corners\n")

# Step 4: Build stats
print("Step 4: Build stats")
stats = app.build_stats(zoned)
print(f"  Lap time: {stats['lap_time']:.2f}s")
print(f"  Lap distance: {stats['lap_distance']:.1f}m")
print(f"  Avg speed: {stats['average_speed']:.1f} km/h")
print(f"  Top speed: {stats['top_speed']:.1f} km/h\n")

# Step 5: Check distance_traveled column
print("Step 5: Detailed distance analysis")
print(f"  distance_traveled min: {zoned['distance_traveled'].min():.1f}m")
print(f"  distance_traveled max: {zoned['distance_traveled'].max():.1f}m")
print(f"  distance_traveled sum: {zoned['distance_traveled'].sum():.1f}m")
print(f"  distance_traveled std: {zoned['distance_traveled'].std():.1f}m")

if zoned['distance_traveled'].iloc[-1] == 0:
    print("\n❌ ERROR: Distance is 0! Checking calculations...")
    print(f"  Speed values ok? {featured['speed'].sum() > 0}")
    print(f"  dt values ok? {featured['dt'].sum() > 0}")
    print(f"  Distance calculation: (speed * dt / 3.6)")
    test_dist = (featured['speed'] * featured['dt'] / 3.6)
    print(f"  Before cumsum - first 5: {test_dist.head().values}")
    print(f"  Before cumsum - sum: {test_dist.sum():.1f}m")
    print(f"  After cumsum - last: {test_dist.cumsum().iloc[-1]:.1f}m")
else:
    print(f"\n✅ Distance calculation correct: {zoned['distance_traveled'].iloc[-1]:.1f}m")
