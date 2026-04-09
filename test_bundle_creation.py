#!/usr/bin/env python3
"""Test what analyze_uploaded_file returns"""

import pandas as pd
import io
import sys

sys.path.insert(0, 'c:/Users/Maha/Documents/telemetry')
import app

print("=" * 70)
print("🔍 TESTING FULL analyze_uploaded_file FUNCTION")
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

try:
    bundle = app.analyze_uploaded_file(fake_file)
    
    print(f"\n✅ Bundle created successfully")
    print(f"\nBundle Properties:")
    print(f"  name: {bundle.name}")
    print(f"  lap_time: {bundle.lap_time:.2f}s")
    print(f"  stats['lap_distance']: {bundle.stats.get('lap_distance', 0):.2f}m")
    print(f"  data rows: {len(bundle.data)}")
    print(f"  event_counts: {bundle.event_counts}")
    print(f"  scores: {bundle.scores}")
    
    # Check if metrics would display as 0
    if bundle.lap_time == 0:
        print(f"\n❌ ISSUE FOUND: lap_time is 0!")
    if bundle.stats.get('lap_distance', 0) == 0:
        print(f"❌ ISSUE FOUND: lap_distance is 0!")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 70)
