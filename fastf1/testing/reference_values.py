"""Reference values that may be used in multiple tests"""
from fastf1.testing import PDStringDtype


def ensure_data_type(column_dtypes, df):
    for ch in column_dtypes.keys():
        if ch not in df.columns:
            continue
        if df.dtypes[ch] != column_dtypes[ch]:
            raise TypeError(f"Dtype {ch, df.dtypes[ch]} not equivalent to target dtype {column_dtypes[ch]}")


LAP_DTYPES = {'Time': '<m8[us]',
              'Driver': PDStringDtype,
              'DriverNumber': PDStringDtype,
              'LapTime': '<m8[us]',
              'LapNumber': 'float64',
              'Stint': 'float64',
              'PitOutTime': '<m8[us]',
              'PitInTime': '<m8[us]',
              'Sector1Time': '<m8[us]',
              'Sector2Time': '<m8[us]',
              'Sector3Time': '<m8[us]',
              'Sector1SessionTime': '<m8[us]',
              'Sector2SessionTime': '<m8[us]',
              'Sector3SessionTime': '<m8[us]',
              'SpeedI1': 'float64',
              'SpeedI2': 'float64',
              'SpeedFL': 'float64',
              'SpeedST': 'float64',
              'IsPersonalBest': 'bool',
              'Compound': PDStringDtype,
              'TyreLife': 'float64',
              'FreshTyre': 'bool',
              'Team': PDStringDtype,
              'LapStartTime': '<m8[us]',
              'LapStartDate': '<M8[us]',
              'TrackStatus': PDStringDtype,
              'Position': 'float64',
              # TODO: fix test
              # 'Deleted': 'O',
              'DeletedReason': PDStringDtype,
              'FastF1Generated': 'bool',
              'IsAccurate': 'bool',
              }

CAR_DATA_DTYPES = {'Brake': 'bool',
                   'nGear': 'int64',
                   'DRS': 'int64',
                   'Date': '<M8[us]',
                   'Throttle': 'float64',
                   'RPM': 'float64',
                   'Speed': 'float64',
                   'Source': PDStringDtype,
                   'Time': '<m8[us]',
                   'SessionTime': '<m8[us]'}

POS_DATA_DTYPES = {'Date': '<M8[us]',
                   'Status': PDStringDtype,
                   'X': 'float64',
                   'Y': 'float64',
                   'Z': 'float64',
                   'Source': PDStringDtype,
                   'Time': '<m8[us]',
                   'SessionTime': '<m8[us]'}
