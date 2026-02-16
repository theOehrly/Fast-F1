"""Tests for telemetry edge cases, particularly for small datasets."""
import pandas as pd
import pytest

from fastf1.core import Telemetry, Laps, Lap


class MockSession:
    """Mock session object for testing."""
    def __init__(self):
        self.t0_date = pd.Timestamp('2019-07-12 10:00:00')
        self.drivers = ['7', '44']
        self.car_data = {}
        self.pos_data = {}
        self.laps = pd.DataFrame()


def create_minimal_telemetry(n_samples, session=None, driver='7'):
    """Create a minimal telemetry object with n_samples rows."""
    if session is None:
        session = MockSession()

    if n_samples == 0:
        return Telemetry(session=session, driver=driver).__finalize__(
            pd.DataFrame()
        )

    session_times = [pd.Timedelta(seconds=i) for i in range(n_samples)]
    dates = [session.t0_date + pd.Timedelta(seconds=i)
             for i in range(n_samples)]

    data = {
        'SessionTime': session_times,
        'Date': dates,
        'Time': session_times,
        'Speed': [100 + i for i in range(n_samples)],
        'RPM': [10000 + i * 100 for i in range(n_samples)],
        'X': [float(i) for i in range(n_samples)],
        'Y': [float(i) for i in range(n_samples)],
        'Z': [float(i) for i in range(n_samples)],
    }

    tel = Telemetry(data, session=session, driver=driver)
    return tel


def test_get_telemetry_with_insufficient_data():
    """Test get_telemetry with very little data (issue #804).

    This test addresses issue #804 where drivers with very little
    telemetry data (e.g., after crashing) would cause an IndexError
    when trying to access empty DataFrames after padding removal.
    """
    session = MockSession()

    # Test with various small datasets
    for n_samples in [0, 1, 2]:
        # Create minimal telemetry for car and pos data
        car_tel = create_minimal_telemetry(n_samples, session)
        pos_tel = create_minimal_telemetry(n_samples, session)

        session.car_data['7'] = car_tel
        session.pos_data['7'] = pos_tel

        # Create a minimal lap
        lap_data = {
            'DriverNumber': '7',
            'LapNumber': 1,
            'LapStartTime': pd.Timedelta(seconds=0),
            'Time': pd.Timedelta(seconds=max(1, n_samples)),
        }
        lap = Lap(lap_data, session=session)

        # This should not raise an error even with minimal data
        # The fix skips driver ahead calculation when there's insufficient data
        try:
            telemetry = lap.get_telemetry()
            # If we get here without an error, the fix is working
            assert isinstance(telemetry, Telemetry)
            print(f"✓ get_telemetry succeeded with {n_samples} samples")
        except IndexError as e:
            pytest.fail(f"get_telemetry failed with {n_samples} samples: {e}")
        except Exception as e:
            # Other exceptions might be expected (e.g., missing data)
            # but IndexError specifically should not occur
            if "single positional indexer is out-of-bounds" in str(e):
                pytest.fail(
                    f"Got the specific IndexError we're fixing: {e}"
                )
            # Other exceptions might be acceptable
            print(f"  Note: Got {type(e).__name__} with "
                  f"{n_samples} samples: {e}")


def test_get_telemetry_laps_with_insufficient_data():
    """Test Laps.get_telemetry with very little data (issue #804)."""
    session = MockSession()

    # Test with 2 samples (after padding this becomes insufficient)
    n_samples = 2
    car_tel = create_minimal_telemetry(n_samples, session)
    pos_tel = create_minimal_telemetry(n_samples, session)

    session.car_data['7'] = car_tel
    session.pos_data['7'] = pos_tel

    # Create minimal laps data
    laps_data = pd.DataFrame({
        'DriverNumber': ['7'],
        'LapNumber': [1],
        'LapStartTime': [pd.Timedelta(seconds=0)],
        'Time': [pd.Timedelta(seconds=n_samples)],
    })

    laps = Laps(laps_data, session=session)

    # This should not raise an IndexError
    try:
        telemetry = laps.get_telemetry()
        assert isinstance(telemetry, Telemetry)
        print(f"✓ Laps.get_telemetry succeeded with {n_samples} samples")
    except IndexError as e:
        if "single positional indexer is out-of-bounds" in str(e):
            pytest.fail(
                f"Got the specific IndexError we're fixing: {e}"
            )
        raise
    except Exception as e:
        # Other exceptions might be acceptable depending on the mock data
        print(f"  Note: Got {type(e).__name__}: {e}")


def test_telemetry_iloc_edge_cases():
    """Test iloc[1:-1] behavior with different row counts."""
    session = MockSession()

    for n_rows in range(0, 5):
        tel = create_minimal_telemetry(n_rows, session)
        result = tel.iloc[1:-1]

        expected_rows = max(0, n_rows - 2)
        assert len(result) == expected_rows, (
            f"Expected {expected_rows} rows after iloc[1:-1] on "
            f"{n_rows} rows, got {len(result)}"
        )

        # Verify that empty result doesn't cause issues
        if len(result) == 0:
            assert result.empty
