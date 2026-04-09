#!/usr/bin/env python3
"""Test data cleaning functionality"""
import pandas as pd
import app

# Load sample data
df = pd.read_csv('sample_clean_telemetry.csv')
print(f"Sample data loaded: {len(df)} rows")

# Test the enhanced cleaning function
cleaned_df, quality_report = app.clean_telemetry_data_enhanced(
    df, 
    remove_outliers=True, 
    filter_noise=True, 
    remove_duplicates=True
)

print(f"\n✅ Data Cleaning Results:")
print(f"   Original rows: {quality_report.original_rows}")
print(f"   Final rows: {quality_report.final_rows}")
print(f"   Duplicates removed: {quality_report.rows_removed_duplicates}")
print(f"   Outliers removed: {quality_report.rows_removed_outliers}")
print(f"   Invalid rows: {quality_report.rows_removed_invalid}")
print(f"   Data quality score: {quality_report.data_quality_score:.1f}/100")
print(f"   Avg sampling rate: {quality_report.avg_sampling_rate:.1f} Hz")
print(f"   Has gaps: {quality_report.has_gaps}")
print(f"   Max time gap: {quality_report.max_time_gap:.3f}s")
print(f"\n⚠️  Warnings:")
if quality_report.warnings:
    for w in quality_report.warnings:
        print(f"   - {w}")
else:
    print("   No warnings")
print(f"\nCleaning summary: {quality_report.cleaning_summary}")

# Verify the cleaned data has expected properties
print(f"\n📊 Cleaned Data Properties:")
print(f"   Shape: {cleaned_df.shape}")
print(f"   Columns: {list(cleaned_df.columns)[:5]}... ({len(cleaned_df.columns)} total)")
print(f"   Time range: {cleaned_df['time'].min():.2f}s to {cleaned_df['time'].max():.2f}s")
print(f"   Speed range: {cleaned_df['speed'].min():.1f} to {cleaned_df['speed'].max():.1f} km/h")
print(f"   Missing values: {cleaned_df.isna().sum().sum()} total")
