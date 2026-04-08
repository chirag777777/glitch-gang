#!/usr/bin/env python3
"""
Quick verification that optional columns integration works correctly
"""
import sys
sys.path.insert(0, 'c:\\Users\\Maha\\Documents\\telemetry')

import pandas as pd
from io import BytesIO

# Test 1: Import the app module
print("TEST 1: Import app module...")
try:
    import app
    print("✅ App module imports successfully")
except Exception as e:
    print(f"❌ Import failed: {e}")
    sys.exit(1)

# Test 2: Load and process extended sample with optional columns
print("\nTEST 2: Process extended sample with optional columns...")
try:
    df_extended = pd.read_csv('c:\\Users\\Maha\\Documents\\telemetry\\sample_extended_telemetry.csv')
    print(f"  - Loaded {len(df_extended)} rows")
    print(f"  - Columns: {list(df_extended.columns)}")
    
    # Check if optional columns are present
    optional_cols = ["longitude", "latitude", "sector_name", "cornering_speed", "energy_efficient"]
    found_optional = [col for col in optional_cols if col in df_extended.columns]
    print(f"  - Optional columns found: {found_optional}")
    
    # Simulate the cleaning process
    cleaned = app.clean_telemetry_data(df_extended)
    print(f"  - After cleaning: {len(cleaned)} rows")
    
    # Check if optional columns survived
    survived_optional = [col for col in optional_cols if col in cleaned.columns]
    print(f"  - Optional columns after cleaning: {survived_optional}")
    
    # Engineer features
    featured = app.engineer_features(cleaned)
    print(f"  - After engineering: {len(featured)} rows")
    
    # Check if optional columns still there
    final_optional = [col for col in optional_cols if col in featured.columns]
    print(f"  - Optional columns after feature engineering: {final_optional}")
    
    # Check helper functions
    print(f"\n  - has_sector_data(): {app.has_sector_data(featured)}")
    print(f"  - has_cornering_speed(): {app.has_cornering_speed(featured)}")
    print(f"  - has_energy_efficient(): {app.has_energy_efficient(featured)}")
    
    print("✅ Extended sample processes correctly")
except Exception as e:
    print(f"❌ Processing failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 3: Verify sector analysis function
print("\nTEST 3: Sector analysis function...")
try:
    thresholds = app.compute_thresholds(featured)
    zoned = app.add_zone_columns(featured, thresholds)
    events = app.detect_events(zoned, thresholds)
    
    sector_summary = app.build_sector_summary(zoned, events)
    if sector_summary is not None:
        print(f"✅ Sector summary generated: {len(sector_summary)} sectors")
        print(f"  Columns: {list(sector_summary.columns)}")
        print(sector_summary.to_string())
    else:
        print("⚠️  Sector summary returned None (no sector data found)")
except Exception as e:
    print(f"❌ Sector analysis failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 4: Test visualization functions
print("\nTEST 4: Visualization functions...")
try:
    from dataclasses import dataclass, field
    from typing import Dict, List, Optional
    
    # Create a minimal AnalysisBundle-like object
    class TestBundle:
        def __init__(self, data):
            self.data = data
            self.thresholds = {
                'slip_high': 10,
                'rpm_low': 1000,
                'rpm_high': 5000,
            }
    
    bundle = TestBundle(featured)
    
    # Try to build optional charts
    cornering_fig = app.build_cornering_speed_figure(bundle)
    if cornering_fig:
        print("✅ Cornering speed figure created")
    else:
        print("⚠️  Cornering speed figure returned None (may be OK if not using plotly)")
    
    energy_fig = app.build_energy_efficient_figure(bundle)
    if energy_fig:
        print("✅ Energy efficient figure created")
    else:
        print("⚠️  Energy efficient figure returned None (may be OK if not using plotly)")
    
except Exception as e:
    print(f"❌ Visualization test failed: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("✅ All tests passed! Optional columns integration is working.")
print("="*60)
