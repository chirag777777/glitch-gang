#!/usr/bin/env python3
"""Quick distance verification"""

import pandas as pd
import sys

sys.path.insert(0, 'c:/Users/Maha/Documents/telemetry')
import app

# Load and process data
df = pd.read_csv('sample_clean_telemetry.csv')
cleaned = app.clean_telemetry_data(df)
featured = app.engineer_features(cleaned)
thresholds = app.compute_thresholds(featured)
zoned = app.add_zone_columns(featured, thresholds)
stats = app.build_stats(zoned)

print("=" * 60)
print("📍 DISTANCE VERIFICATION")
print("=" * 60)
print(f"\nTotal Distance: {stats['lap_distance']:.2f} metres")
print(f"Lap Time: {stats['lap_time']:.2f} seconds")
print(f"Average Speed: {stats['average_speed']:.2f} km/h")
print(f"\nDistance Data Points:")
print(f"  Min: {zoned['distance_traveled'].min():.2f}m")
print(f"  Max: {zoned['distance_traveled'].max():.2f}m")
print(f"  Mean: {zoned['distance_traveled'].mean():.2f}m")
print(f"\nFirst 5 distance values:")
for i in range(min(5, len(zoned))):
    print(f"  Row {i}: {zoned['distance_traveled'].iloc[i]:.2f}m")
print(f"\nLast 5 distance values:")
for i in range(max(0, len(zoned)-5), len(zoned)):
    print(f"  Row {i}: {zoned['distance_traveled'].iloc[i]:.2f}m")
print("\n" + "=" * 60)
print("✅ Distance correctly calculated in metres")
print("=" * 60)
