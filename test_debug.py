import pandas as pd
from app import analyze_uploaded_file

# Test file object simulation
class MockFile:
    def __init__(self, df):
        self.data = df
        self.name = 'sample_test.csv'
    def getvalue(self):
        return self.data.to_csv(index=False).encode()

# Load and test
df = pd.read_csv('sample_clean_telemetry.csv')
mock_file = MockFile(df)

try:
    print('Testing analysis pipeline...')
    bundle = analyze_uploaded_file(mock_file)
    print('[OK] Analysis successful')
    print(f'  Lap time: {bundle.lap_time:.2f}s')
    print(f'  Distance: {bundle.stats["lap_distance"]:.1f}m')
    print(f'  Oversteer events: {bundle.event_counts["oversteer"]}')
    print(f'  Understeer events: {bundle.event_counts["understeer"]}')
    dual = (bundle.events["oversteer"] & bundle.events["understeer"]).sum()
    print(f'  Dual reports (should be 0): {dual}')
    print(f'  Corner phases: {list(bundle.data["corner_phase"].unique())}')
    print('[OK] All core features working')
except Exception as e:
    print(f'[ERROR] Error: {e}')
    import traceback
    traceback.print_exc()
