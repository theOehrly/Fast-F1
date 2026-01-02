
import pytest
import pandas as pd
import numpy as np
from fastf1.core import Session, Laps, Telemetry

class MockEvent:
    def __init__(self):
        self.year = 2023
        self.RoundNumber = 1
        self.EventName = 'Test Event'

    def get_session_date(self, name, utc=True):
        return pd.Timestamp('2023-01-01', tz='UTC' if utc else None)
    
    def __getitem__(self, item):
        if item == 'EventDate':
             return pd.Timestamp('2023-01-01')
        if item == 'EventName':
             return 'Test Event'
        return 'MockVal'

def test_impute_missing_speeds():
    mock_event = MockEvent()
    # Initialize Session correctly
    session = Session(event=mock_event, session_name='TestSession')
    
    # Mock Results for drivers list
    results_df = pd.DataFrame({'DriverNumber': ['1']})
    session._results = results_df 
    
    # 1. Mock Laps Data
    laps_data = pd.DataFrame({
        'DriverNumber': ['1', '1'],
        'LapNumber': [1, 2],
        'LapStartTime': [pd.Timedelta(seconds=0), pd.Timedelta(seconds=100)],
        'Time': [pd.Timedelta(seconds=90), pd.Timedelta(seconds=190)],
        'SpeedST': [300.0, np.nan], # Target column
        'SpeedFL': [np.nan, np.nan], 
        'SpeedI1': [np.nan, np.nan], 
        'SpeedI2': [np.nan, np.nan], 
    })
    session._laps = Laps(laps_data, session=session, _force_default_cols=True)
    
    # 2. Mock Car Data (Telemetry)
    # Lap 1: Speed 300 starts at 10s.
    # Dist calculation via add_distance() integrates Speed * Time.
    # Speed 300 km/h = 83.33 m/s.
    # 10s -> 0m.
    # 16s -> 6s * 83.33 = 500m.
    t1 = pd.timedelta_range(start='10s', periods=20, freq='1s') # 10s to 29s
    s1 = [300.0] * 20
    dates1 = pd.to_datetime('2023-01-01 12:00:00') + t1
    df1 = pd.DataFrame({
        'Date': dates1,
        'SessionTime': t1,
        'Speed': s1,
        'Source': 'car'
    })
    
    # Lap 2: Speed 150 starts at 112s (relative to lap start 100).
    # We want to match distance 500m.
    # Speed 150 km/h = 41.67 m/s.
    # If we want 500m from start of telemetry chunk?
    # No, we want 500m from START OF LAP.
    # My code adds distance to the CHUNK sliced by [LapStartTime, LapEndTime].
    # So Distance starts from 0 at LapStartTime?
    # IF the chunk starts at LapStartTime.
    
    # Lap 1: Chunk starts at 10s (because telemetry starts at 10s).
    # Lap start is 0s. 
    # Chunk: 10s to 90s.
    # chunk.add_distance() -> Distance at 10s is 0.
    # So "Distance" in my code means "Distance driven WITHIN the available telemetry for that lap".
    # Since telemetry might have gaps or start late, this is technically "Distance from first telemetry sample in lap".
    # Ideally should be distance from logic start, but for Speed Trap it's fine if consistent.
    # The Trap is at a physical location.
    
    # Lap 1: Telemetry starts at 10s. 
    # 300 km/h. At 16s (6s later), distance is 500m.
    # So Trap Distance = 500m relative to telemetry start.
    
    # Lap 2: Start 100s.
    # Telemetry should start at 100s? Or later?
    # If it starts at 100s, then we need 500m.
    # Speed 150 -> 12s -> 112s.
    
    # Let's start telemetry at 100s to be safe.
    t2 = pd.timedelta_range(start='100s', periods=20, freq='1s')
    s2 = [150.0] * 20
    # Adjust speeds slightly to ensure match isn't ambiguous or we hit exactly
    
    dates2 = pd.to_datetime('2023-01-01 12:00:00') + t2
    df2 = pd.DataFrame({
        'Date': dates2,
        'SessionTime': t2,
        'Speed': s2,
        'Source': 'car'
    })
    
    full_tel = pd.concat([df1, df2])
    full_tel['Time'] = full_tel['SessionTime'] 
    
    tel_obj = Telemetry(full_tel, session=session)
    session._car_data = {'1': tel_obj}
    
    # Run Imputation
    session._impute_missing_speeds()
    
    # Check Result
    filled_val = session._laps.loc[1, 'SpeedST']
    
    assert not pd.isna(filled_val), "Value not filled"
    assert 140.0 < filled_val < 160.0, f"Imputed value {filled_val} not close to 150.0"

    # Also verifying other columns remained NaN
    assert np.isnan(session._laps.loc[1, 'SpeedFL']), "SpeedFL shouldn't be filled"
    assert np.isnan(session._laps.loc[1, 'SpeedI1']), "SpeedI1 shouldn't be filled"

if __name__ == "__main__":
    test_impute_missing_speeds()
