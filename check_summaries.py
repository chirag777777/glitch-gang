#!/usr/bin/env python3
"""Check turn summary and sector summary distance values"""

import pandas as pd
import sys

sys.path.insert(0, 'c:/Users/Maha/Documents/telemetry')
import app

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

print("=" * 70)
print("📊 TURN SUMMARY DISTANCE VALUES")
print("=" * 70)
if not bundle.turn_summary.empty:
    print("\nTurn Summary DataFrame:")
    print(bundle.turn_summary.to_string())
    print(f"\nColumns: {bundle.turn_summary.columns.tolist()}")
else:
    print("❌ Turn summary is EMPTY")

print("\n" + "=" * 70)
print("📊 SECTOR SUMMARY DISTANCE VALUES")
print("=" * 70)
if bundle.sector_summary is not None and not bundle.sector_summary.empty:
    print("\nSector Summary DataFrame:")
    print(bundle.sector_summary.to_string())
    print(f"\nColumns: {bundle.sector_summary.columns.tolist()}")
else:
    print("⚠️  Sector summary is None or EMPTY (expected - no sector data in CSV)")

print("\n" + "=" * 70)
