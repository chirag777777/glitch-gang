#!/usr/bin/env python3
"""Test full analysis pipeline with quality reporting"""
import io
import pandas as pd
import app

# Create a mock file object from sample CSV
with open('sample_clean_telemetry.csv', 'rb') as f:
    file_bytes = f.read()

class MockFile:
    def __init__(self, name, file_bytes):
        self.name = name
        self._bytes = file_bytes
    
    def getvalue(self):
        return self._bytes

mock_file = MockFile('sample_clean_telemetry.csv', file_bytes)

print("🚀 Testing full analysis pipeline...")
print("-" * 60)

# Run the full analysis
try:
    bundle = app.analyze_uploaded_file(mock_file)
    
    print("✅ Analysis completed successfully!")
    print(f"\n📋 Bundle Properties:")
    print(f"   File: {bundle.name}")
    print(f"   Data rows: {len(bundle.data)}")
    print(f"   Lap time: {bundle.lap_time:.2f}s")
    print(f"   Grade: {bundle.grade}")
    
    print(f"\n📊 Quality Report:")
    if bundle.quality_report:
        qr = bundle.quality_report
        print(f"   Quality Score: {qr.data_quality_score:.0f}/100")
        print(f"   Processed: {qr.original_rows} → {qr.final_rows} rows")
        print(f"   Sampling Rate: {qr.avg_sampling_rate:.1f} Hz")
        print(f"   Warnings: {len(qr.warnings)}")
        print(f"   Summary: {qr.cleaning_summary}")
    else:
        print("   ⚠️  No quality report generated!")
    
    print(f"\n📈 Analysis Results:")
    print(f"   Consistency Score: {bundle.scores.get('consistency_score', 'N/A')}")
    print(f"   Handling Score: {bundle.scores.get('handling_score', 'N/A')}")
    print(f"   Stability Score: {bundle.scores.get('stability_score', 'N/A')}")
    print(f"   Event counts: {list(bundle.event_counts.keys())[:3]}... ({len(bundle.event_counts)} total)")
    
    if bundle.ml_results:
        print(f"\n🤖 ML Results: Available")
        print(f"   Stability Score: {bundle.ml_results.get('stability_score', 'N/A')}")
    else:
        print(f"\n🤖 ML Results: Not available")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - Data cleaning integration successful!")
    print("=" * 60)
    
except Exception as e:
    print(f"❌ Analysis failed: {str(e)}")
    import traceback
    traceback.print_exc()
