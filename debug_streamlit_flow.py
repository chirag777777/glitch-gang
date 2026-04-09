#!/usr/bin/env python3
"""Test the complete Streamlit flow to find where metrics display 0"""

import pandas as pd
import sys
import os

sys.path.insert(0, 'c:/Users/Maha/Documents/telemetry')
import app

print("=" * 70)
print("🔍 DEBUG: COMPLETE STREAMLIT FLOW SIMULATION")
print("=" * 70)

# Simulate file upload
with open('sample_clean_telemetry.csv', 'rb') as f:
    file_bytes = f.read()

class FakeUpload:
    def __init__(self, name, data):
        self.name = name
        self._data = data
    def getvalue(self):
        return self._data

fake_file = FakeUpload('sample_clean_telemetry.csv', file_bytes)

print(f"\n1️⃣ FILE OBJECT CREATED")
print(f"   Name: {fake_file.name}")
print(f"   Size: {len(fake_file.getvalue())} bytes")

# STEP 1: Call analyze_uploaded_file (what render_overview-> render_summary_metrics would use)
print(f"\n2️⃣ CALLING analyze_uploaded_file()")
primary_bundle = app.analyze_uploaded_file(fake_file)

print(f"   ✅ Bundle created")
print(f"\n3️⃣ CHECKING BUNDLE PROPERTIES")
print(f"   primary_bundle.lap_time = {primary_bundle.lap_time}")
print(f"   primary_bundle.name = {primary_bundle.name}")
print(f"   primary_bundle.stats = {primary_bundle.stats}")
print(f"   primary_bundle.stats['lap_distance'] = {primary_bundle.stats.get('lap_distance', 0)}")

# STEP 2: Simulate render_summary_metrics
print(f"\n4️⃣ SIMULATING render_summary_metrics() OUTPUT")
print(f"   Would display:")
print(f"   - Lap Time: {primary_bundle.lap_time:.2f}s")
print(f"   - Total Distance: {primary_bundle.stats.get('lap_distance', 0):.0f}m")
print(f"   - Average Speed: {primary_bundle.stats['average_speed']:.1f} km/h")
print(f"   - Top Speed: {primary_bundle.stats['top_speed']:.1f} km/h")

# Check type of lap_time
print(f"\n5️⃣ TYPE CHECKING")
print(f"   type(primary_bundle.lap_time) = {type(primary_bundle.lap_time)}")
print(f"   isinstance(primary_bundle.lap_time, (int, float)) = {isinstance(primary_bundle.lap_time, (int, float))}")

# Check if it's NaN or None
import numpy as np
print(f"   np.isnan(primary_bundle.lap_time) = {np.isnan(primary_bundle.lap_time) if isinstance(primary_bundle.lap_time, float) else 'N/A'}")
print(f"   primary_bundle.lap_time is None = {primary_bundle.lap_time is None}")
print(f"   primary_bundle.lap_time == 0 = {primary_bundle.lap_time == 0}")

# Summary
print("\n" + "=" * 70)
if primary_bundle.lap_time > 0 and primary_bundle.stats.get('lap_distance', 0) > 0:
    print("✅ METRICS ARE CORRECT - Issue must be in Streamlit display")
    print("   Suggestion: Check if stats dictionary is being accessed correctly")
else:
    print("❌ METRICS ARE ZERO - Issue in processing pipeline")
print("=" * 70)
