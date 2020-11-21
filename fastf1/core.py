"""
:mod:`fastf1.core` - Core module
================================

Contains the main classes and functions.
"""

from fastf1 import ergast
from fastf1 import api
from fastf1.utils import recursive_dict_get
import pandas as pd
import numpy as np
import logging
import scipy
import scipy.interpolate
import scipy.spatial
import scipy.signal
import scipy.optimize
import pickle
import json
import pathlib
import os
from functools import cached_property

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', message="Using slow pure-python SequenceMatcher")
    # suppress that warning, it's confusing at best here, we don't need fast sequence matching
    # and the installation (on windows) some effort
    from fuzzywuzzy import fuzz

logging.basicConfig(level=logging.INFO, style='{', format="{module: <8} {levelname: >10} \t{message}")


TESTING_LOOKUP = {'2020': [['2020-02-19', '2020-02-20', '2020-02-21'],
                           ['2020-02-26', '2020-02-27', '2020-02-28']]}

D_LOOKUP = [[44, 'HAM', 'Mercedes'], [77, 'BOT', 'Mercedes'],
            [5, 'VET', 'Ferrari'], [16, 'LEC', 'Ferrari'],
            [33, 'VER', 'Red Bull'], [23, 'ALB', 'Red Bull'],
            [55, 'SAI', 'McLaren'], [4, 'NOR', 'McLaren'],
            [11, 'PER', 'Racing Point'], [18, 'STR', 'Racing Point'],
            [3, 'RIC', 'Renault'], [31, 'OCO', 'Renault'],
            [26, 'KVY', 'Alpha Tauri'], [10, 'GAS', 'Alpha Tauri'],
            [8, 'GRO', 'Haas F1 Team'], [20, 'MAG', 'Haas F1 Team'],
            [7, 'RAI', 'Alfa Romeo'], [99, 'GIO', 'Alfa Romeo'],
            [6, 'LAT', 'Williams'], [63, 'RUS', 'Williams'],
            [88, 'KUB', 'Alfa Romeo']]

REFERENCE_LAP_RESOLUTION = 0.667
"""A distance in meters which indicates the resolution of the reference
lap. This reference is used to project car positions and calculate
things like distance between cars.
"""


def get_session(year, gp, event=None):
    """Main core function. It will take care of crafting an object
    corresponding to the requested session.
    If not specified, full weekend is returned.

    Args:
        year (number): Session year
        gp (number or string): Name or weekend number (1: Australia,
                               ..., 21: Abu Dhabi). If gp is a string,
                               a fuzzy match will be performed on the
                               season rounds and the most likely will be
                               selected.

                               Some examples that will be correctly
                               interpreted: 'bahrain', 'australia',
                               'abudabi', 'monza'.

                               Pass 'testing' to fetch Barcelona winter
                               tests.

        event (=None): may be 'FP1', 'FP2', 'FP3', 'Q' or 'R', if not 
                       specified you get the full :class:`Weekend`.
                       If gp is 'testing' event is the test day (1 to 6)

    Returns:
        :class:`Weekend` or :class:`Session`

    """
    if type(gp) is str and gp == 'testing':
        pre_season_week, event = _get_testing_week_event(year, event)
        print(pre_season_week, event)
        weekend = Weekend(year, pre_season_week)
        return Session(weekend, event)

    if type(gp) is str:
        gp = get_round(year, gp)
    weekend = Weekend(year, gp)
    if event == 'R':
        return Session(weekend, 'Race')
    if event == 'Q':
        return Session(weekend, 'Qualifying')
    if event == 'FP3':
        return Session(weekend, 'Practice 3')
    if event == 'FP2':
        return Session(weekend, 'Practice 2')
    if event == 'FP1':
        return Session(weekend, 'Practice 1')
    return weekend


def get_round(year, match):
    """From the year and a text to match, will try to find the most
    likely week number of the event.

    Args:
        year (int): Year of the event
        match (string): Name of the race or gp (e.g. 'Bahrain')

    Returns:
        The round number. (2019, 'Bahrain') -> 2

    """

    def build_string(d):
        r = len('https://en.wikipedia.org/wiki/')  # TODO what the hell is this
        c, l = d['Circuit'], d['Circuit']['Location']
        return (f"{d['url'][r:]} {d['raceName']} {c['circuitId']} "
                + f"{c['url'][r:]} {c['circuitName']} {l['locality']} "
                + f"{l['country']}")

    races = ergast.fetch_season(year)
    to_match = [build_string(block) for block in races]
    ratios = np.array([fuzz.partial_ratio(match, ref) for ref in to_match])

    return int(races[np.argmax(ratios)]['round'])


def _get_testing_week_event(year, day):
    """Get the correct weekend and event for testing from the
    year and day of the test. (where day is 1, 2, 3, ...)
    """
    try:
        day = int(day)
        week = 1 if day < 4 else 2  # TODO Probably will change from 2021
    except:
        msg = "Cannot fetch testing without correct event day."
        raise Exception(msg)
    week_day = ((day - 1) % 3) + 1  # TODO Probably will change from 2021
    pre_season_week = f'Pre-Season Test {week}'
    event = f'Practice {week_day}'

    return pre_season_week, event

# TODO update doc strings


class Telemetry(pd.DataFrame):
    # explain columns
    # Some (Dist, RelDist only available by default for single laps

    TELEMETRY_FREQUENCY = 'original'

    _CHANNELS = {
        'X': {'type': 'continuous', 'missing': 'quadratic'},
        'Y': {'type': 'continuous', 'missing': 'quadratic'},
        'Z': {'type': 'continuous', 'missing': 'quadratic'},
        'Status': {'type': 'discrete', 'missing': 'fill'},
        'Speed': {'type': 'continuous', 'missing': 'linear'},     # linear is often required as quadratic overshoots
        'RPM': {'type': 'continuous', 'missing': 'linear'},       # on sudden changes like sudden pedal application,
        'Throttle': {'type': 'continuous', 'missing': 'linear'},  # braking, ...)
        'Brake': {'type': 'continuous', 'missing': 'linear'},
        'DRS': {'type': 'discrete', 'missing': 'fill'},
        'nGear': {'type': 'discrete', 'missing': 'fill'},
        'Source': {'type': 'excluded'},  # special case, custom handling
        'Date': {'type': 'excluded'},  # special case, used as the index during resampling
        'Time': {'type': 'excluded'},  # special case, Time/SessionTime recalculated from 'Date'
        'SessionTime': {'type': 'excluded'},
        'Distance': {'type': 'continuous', 'missing': 'quadratic'},
        'RelativeDistance': {'type': 'continuous', 'missing': 'quadratic'},
        'DifferentialDistance': {'type': 'continuous', 'missing': 'quadratic'},
        'DriverAhead': {'type': 'discrete', 'missing': 'fill'},
        'DistanceToDriverAhead': {'type': 'continuous', 'missing': 'linear'}
    }

    _metadata = ['session', 'driver']

    def __init__(self, *args, session=None, driver=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.driver = driver

    @property
    def _constructor(self):
        return Telemetry

    @property
    def base_class_view(self):
        # for a nicer debugging experience; can now select base_class_view -> show as dataframe in IDE
        return pd.DataFrame(self)

    def join(self, *args, **kwargs):
        """Wraps :mod:`pandas.DataFrame.join` and adds metadata propagation.

        When calling `self.join` metadata will be propagated from self to the joined dataframe.
        """
        meta = dict()
        for var in self._metadata:
            meta[var] = getattr(self, var)
        ret = super().join(*args, **kwargs)
        for var, val in meta.items():
            setattr(ret, var, val)
        return ret

    def slice_by_mask(self, mask, pad=0, pad_side='both'):
        """Slice self using a boolean array as a mask.

        Args:
            mask (array-like): Array of boolean values with the same length as self
            pad (int): Number of samples used for padding the sliced data
            pad_side (str): Where to pad the data; possible options: 'both', 'before', 'after'

        Returns:
            :class:`Telemetry`
        """
        if pad:
            if pad_side in ('both', 'before'):
                i_left_pad = max(0, np.min(np.where(mask)) - pad)
            else:
                i_left_pad = np.min(np.where(mask))

            if pad_side in ('both', 'after'):
                i_right_pad = min(len(mask), np.max(np.where(mask)) + pad)
            else:
                i_right_pad = np.max(np.where(mask))
            mask[i_left_pad: i_right_pad + 1] = True

        data_slice = self.loc[mask].copy()

        return data_slice

    def slice_by_lap(self, ref_laps, pad=0, pad_side='both', interpolate_edges=False):
        """Slice self to only include data from the provided lap or laps.

        .. note:: Self needs to have a 'SessionTime' column for slicing by time.

        .. note:: When slicing with an instance of :class:`Laps` as a reference, the data will be sliced by first and
            last lap. Missing laps in between will not be considered and data for these will still be included in
            the sliced result.

        Args:
            ref_laps (Lap or Laps): The lap/laps by which to slice self
            pad (int): Number of samples used for padding the sliced data
            pad_side (str): Where to pad the data; possible options: 'both', 'before', 'after
            interpolate_edges (bool): Add an interpolated sample at the beginning and end to exactly
                match the provided time window.

        Returns:
            :class:`Telemetry`
        """
        if isinstance(ref_laps, Laps) and len(ref_laps) > 1:
            if 'DriverNumber' not in ref_laps.columns:
                ValueError("Laps is missing 'DriverNumber'. Cannot return telemetry for unknown driver.")
            if not len(ref_laps['DriverNumber'].unique()) <= 1:
                raise ValueError("Cannot create telemetry for multiple drivers at once!")

            end_time = max(ref_laps['Time'])
            start_time = min(ref_laps['LapStartTime'])

        elif isinstance(ref_laps, (Lap, Laps)):
            if isinstance(ref_laps, Laps):  # one lap in Laps
                ref_laps = ref_laps.iloc[0]  # needs to be handled as a single lap
            if 'DriverNumber' not in ref_laps.index:
                ValueError("Lap is missing 'DriverNumber'. Cannot return telemetry for unknown driver.")
            end_time, duration = ref_laps['Time'], ref_laps['LapTime']
            start_time = end_time - duration

        else:
            raise TypeError("Attribute 'ref_laps' needs to be an instance of `Lap` or `Laps`")

        return self.slice_by_time(start_time, end_time, pad, pad_side, interpolate_edges)

    def slice_by_time(self, start_time, end_time, pad=0, pad_side='both', interpolate_edges=False):
        """requires session time to be present
        Slice self to only include data in a specific time frame.

        .. note:: Self needs to have a 'SessionTime' column for slicing by time.

        Args:
            start_time (Timedelta): Start of the section
            end_time (Timedelta): End of the section
            pad (int): Number of samples used for padding the sliced data
            pad_side (str): Where to pad the data; possible options: 'both', 'before', 'after
            interpolate_edges (bool): Add an interpolated sample at the beginning and end to exactly
                match the provided time window.

        Returns:
            :class:`Telemetry`
        """
        if interpolate_edges:
            edges = pd.DataFrame({'SessionTime': (start_time, end_time)})
            d = self.merge(edges, how='outer').sort_values(by='SessionTime').reset_index(drop=True)

            # cannot simply use fill_missing() because it expects 'Date' without missing values; calculate 'Date' first
            i = d.get_first_non_zero_time_index()
            time_offset = d['Date'].iloc[i] - d['SessionTime'].iloc[i]
            d.loc[:, 'Date'] = d['SessionTime'] + time_offset

            d = d.fill_missing()  # now fill in the other missing values

        else:
            d = self.copy()  # TODO no copy?

        sel = ((d['SessionTime'] <= end_time) & (d['SessionTime'] >= start_time))
        if np.any(sel):
            data_slice = d.slice_by_mask(sel, pad, pad_side)

            if 'Time' in data_slice.columns:
                data_slice.loc[:, 'Time'] -= start_time  # shift time to 0 so laps can overlap

            if 'Distance' in data_slice.columns:  # offset Distance so that it starts at zero on the first sample
                distance_zero = data_slice['Distance'].iloc[0]  # TODO and others?
                data_slice.loc[:, 'Distance'] = data_slice.loc[:, 'Distance'] - distance_zero

            return data_slice
        return Telemetry()

    def merge_channels(self, other, frequency=None):
        # unknown channels will be skipped
        """`car_data` is aligned with main time reference (time used in
        summary). For constant frequency a resampling to 10Hz is applied.

        `car_data` (telemetry) has a 'Date' entry which is the actual time
        the sample was taken (I guess), but anyway, is unique. So from
        the time step before resampling is taken from this column and
        Time is aligned on Date.

        One time sample may carry more than one Date sample. Single time
        entries at the beginning are often messed up, so the last time
        of a consecutive stike is chosen as alignment point.

        Time = [t1, t2, t3, t3, t3, t4, t4, ... ]
        Date = [d1, d2, d3, d4, d5, d6, d7, ... ]
                                ^
                                Start of alignment

        So in this example t3 is kept as reference for start time and
        the incrementals from Date are added to have a correctly spaced
        time column. d5 will be used for the `offset_date` which is then
        used to find the lap start time.

        Now data can be resampled on Time.

        .. note :: Do not resample data multiple times. Always resample based on the original data
            to preserve accuracy
        """  # TODO update docstring
        # TODO: this should be capable of handling custom columns!
        # merge the data and interpolate missing; 'Date' needs to be the index
        data = self.set_index('Date')
        other = other.set_index('Date')

        # save dtypes before merging so they can be restored after merging
        # necessary for example because merging produces NaN values which would cause an int column to become float
        # but it can be converted back to int after interpolating missing values
        dtype_map = dict()
        for df in data, other:
            for col in df.columns:
                if col not in dtype_map.keys():
                    dtype_map[col] = df[col].dtype

        # Exclude columns existing on both dataframes from one dataframe before merging (cannot merge with duplicates)
        on_both_columns = set(other.columns).intersection(set(data.columns))
        merged = other.merge(data[data.columns.difference(on_both_columns, sort=False)],
                             how='outer', left_index=True, right_index=True, sort=True)
        # now use the previously excluded columns to update the missing values in the merged dataframe
        for col in on_both_columns:
            merged[col].update(data[col])

        if 'Driver' in merged.columns and len(merged['Driver'].unique()) > 1:
            raise ValueError("Cannot merge multiple drivers")

        if not frequency:
            frequency = data.TELEMETRY_FREQUENCY

        i = data.get_first_non_zero_time_index()
        if i is None:
            raise ValueError("No valid 'Time' data. Cannot resample!")

        time_offset = merged.index[i] - merged['Time'].iloc[i]  # offsets are valid for this slice only
        if 'SessionTime' in merged.columns:
            session_time_offset = merged.index[i] - merged['SessionTime'].iloc[i]
        else:
            session_time_offset = None
        ref_date = merged.index[i]

        # data needs to be resampled/interpolated differently, depending on what kind of data it is
        # how to handle which column is defined in self._CHANNELS

        if frequency == 'original':
            # no resampling but still interpolation due to merging
            # 'Source' column not mentioned here because no changes are necessary
            for ch in self._CHANNELS.keys():
                if ch not in merged.columns:
                    continue
                sig_type = self._CHANNELS[ch]['type']

                if sig_type == 'continuous':  # yes, this is necessary to prevent pandas from crashing
                    missing = self._CHANNELS[ch]['missing']
                    merged.loc[:, ch] = merged.loc[:, ch] \
                        .interpolate(method=missing, limit_direction='both', fill_value='extrapolate')

                elif sig_type == 'discrete':
                    merged.loc[:, ch] = merged.loc[:, ch]\
                        .fillna(method='ffill').fillna(method='bfill')  # only use bfill after ffill to fix first row

            # restore data types from before merging
            for col in dtype_map.keys():
                try:
                    merged.loc[:, col] = merged.loc[:, col].astype(dtype_map[col])
                except ValueError:
                    logging.warning(f"Failed to preserve data type for column '{col}' while merging telemetry.")

            merged = merged.reset_index().rename(columns={'index': 'Date'})  # make 'Date' a column again

        else:
            frq = f'{1 / frequency}S'

            resampled_columns = dict()

            for ch in self._CHANNELS.keys():
                if ch not in merged.columns:
                    continue
                sig_type = self._CHANNELS[ch]['type']

                if sig_type == 'continuous':
                    missing = self._CHANNELS[ch]['missing']
                    res = merged.loc[:, ch] \
                        .resample(frq, origin=ref_date).mean().interpolate(method=missing, fill_value='extrapolate')

                elif sig_type == 'discrete':
                    res = merged.loc[:, ch].resample(frq, origin=ref_date).fillna(method='ffill').fillna(method='bfill')
                    # only use bfill after ffill to fix first row

                else:
                    continue

                resampled_columns[ch] = res

            res_source = merged.loc[:, 'Source'].resample(frq, origin=ref_date).asfreq().fillna(value='interpolation')
            resampled_columns['Source'] = res_source

            # join resampled columns and make 'Date' a column again
            merged = Telemetry(resampled_columns).reset_index().rename(columns={'index': 'Date'})

        # recalculate the time columns
        if session_time_offset is not None:
            merged['SessionTime'] = merged['Date'] - session_time_offset
        merged['Time'] = merged['Date'] - time_offset

        return merged

    def fill_missing(self):
        """Calculate missing values in self.

        Interpolation will be used for continuous values (Speed, RPM).
        Forward-fill will be used for discrete values (Gear, DRS, ...)

        Only default columns and registered columns will be processed. Missing data in other columns will be ignored.
        See :func:`register_new_channel` for adding custom channels.
        """
        ret = self.copy()

        i = ret.get_first_non_zero_time_index()
        time_offset = ret['Date'].iloc[i] - ret['Time'].iloc[i]  # offsets are valid for this slice only
        if 'SessionTime' in ret.columns:
            session_time_offset = ret['Date'].iloc[i] - ret['SessionTime'].iloc[i]
        else:
            session_time_offset = None

        for ch in self._CHANNELS.keys():
            if ch not in self.columns:
                continue
            sig_type = self._CHANNELS[ch]['type']

            if sig_type == 'continuous':  # yes, this is necessary to prevent pandas from crashing
                missing = self._CHANNELS[ch]['missing']
                ret.loc[:, ch] = ret.loc[:, ch]\
                    .interpolate(method=missing, limit_direction='both', fill_value='extrapolate')

            elif sig_type == 'discrete':
                ret.loc[:, ch] = ret.loc[:, ch] \
                    .fillna(method='ffill').fillna(method='bfill')  # only use bfill after ffill to fix first row

        if 'Source' in ret.columns:
            ret.loc[:, 'Source'] = ret.loc[:, 'Source'].fillna(value='interpolation')

        if session_time_offset is not None:
            ret.loc[:, 'SessionTime'] = ret['Date'] - session_time_offset
        ret.loc[:, 'Time'] = ret['Date'] - time_offset

        return ret

    def register_new_channel(self, name, signal_type, interpolation_method):
        pass  # TODO TBD

    def get_first_non_zero_time_index(self):
        """Return the first index at which the 'Time' value is not zero or NA/NaT"""
        # find first row where time is not zero; usually this is the first row but sometimes.....
        i_arr = np.where((self['Time'] != pd.Timedelta(0)) & ~pd.isna(self['Time']))[0]
        if i_arr.size != 0:
            return np.min(i_arr)
        return None

    def add_differential_distance(self, drop_existing=True):
        """A column 'DifferentialDistance' to self.

        This column contains the distance driven between subsequent samples.

        Args:
            drop_existing (bool): Drop and recalculate column if it already exists
        """
        if 'Distance' in self.columns:
            if drop_existing:
                return self.drop('DifferentialDistance', 1)\
                    .join(pd.DataFrame({'DifferentialDistance': self.calculate_differential_distance()}), how='outer')
            return self
        return self.join(pd.DataFrame({'DifferentialDistance': self.calculate_differential_distance()}), how='outer')

    def add_distance(self, drop_existing=True):
        """Add column 'Distance' to self.

        This column contains the distance driven since the first sample of self in meters.

        The data is produced by integrating the differential distance between subsequent laps.
        You should not apply this function to telemetry of many laps simultaneously to reduce integration error.
        Instead apply it only to single laps or few laps at a time!

        Args:
            drop_existing (bool): Drop and recalculate column if it already exists
        """
        if 'Distance' in self.columns:
            if drop_existing:
                return self.drop('Distance', 1).join(pd.DataFrame({'Distance': self.integrate_distance()}), how='outer')
            return self
        return self.join(pd.DataFrame({'Distance': self.integrate_distance()}), how='outer')

    def add_relative_distance(self, drop_existing=True):
        """Add column 'RelativeDistance' to self.

        This column contains the distance driven since the first sample as a floating point number in the range
        from 0.0 to 1.0.

        This the same way as 'Distance' (see: :func:`add_distance`). The same warnings apply.

        Args:
            drop_existing (bool): Drop and recalculate column if it already exists
        """
        if 'RelativeDistance' in self.columns:
            if drop_existing:
                d = self.drop('RelativeDistance', 1)
            else:
                return self
        else:
            d = self

        if 'Distance' in d.columns:
            rel_dist = d.loc[:, 'Distance'] / d.loc[:, 'Distance'].iloc[-1]
        else:
            dist = d.integrate_distance()
            rel_dist = dist / dist.iloc[0]
        return d.join(pd.DataFrame({'RelativeDistance': rel_dist}), how='outer')

    def add_driver_ahead(self, drop_existing=True):
        """Add column 'DriverAhead' and 'DistanceToDriverAhead' to self.

        DriverAhead: Three letter abbreviation of the drivers name
        DistanceToDriverAhead: Distance to next car ahead in meters

        .. note:: Cars in the pit lane are currently not excluded from the data. They will show up when overtaken on
            pit straight even if they're not technically in front of the car. A fix for this is TBD with other
            improvements.

        This should only be apply to data of single laps or few laps at a time to reduce integration error.
        If you absolutely need to apply it to a whole session, used the legacy implementation. Note that data of
        the legacy implementation will be considerably less smooth.

        Args:
            drop_existing (bool): Drop and recalculate column if it already exists
        """
        if 'DriverAhead' in self.columns and 'DistanceToDriverAhead' in self.columns:
            if drop_existing:
                d = self.drop('DriverAhead', 1).drop('DistanceToDriverAhead', 1)
            else:
                return self
        else:
            d = self

        drv_ahead, dist = self.calculate_driver_ahead()
        return d.join(pd.DataFrame({'DriverAhead': drv_ahead, 'DistanceToDriverAhead': dist}), how='outer')

    def calculate_differential_distance(self):
        """Calculate the distance between subsequent samples of self.

        Distance is in meters

        Returns:
            :class:`pandas.Series`
        """
        if not all([col in self.columns for col in ('Speed', 'Time')]):
            raise ValueError("Telemetry does not contain required channels 'Time' and 'Speed'.")
        if self.size != 0:
            dt = self['Time'].dt.total_seconds().diff()
            dt.iloc[0] = self['Time'].iloc[0].total_seconds()
            ds = self['Speed'] / 3.6 * dt
            return ds
        else:
            return pd.Series()

    def integrate_distance(self):
        """Return the distance driven since the first sample of self.

        Distance is in meters. The data is produce by integration. Integration error will stack up when used for
        long slices of data. This should therefore only be used for data of single laps or few laps at a time.

        Returns:
            :class:`pd.Series`
        """
        ds = self.calculate_differential_distance()
        if not ds.empty:
            return ds.cumsum()
        else:
            return pd.Series()

    def calculate_driver_ahead(self):
        """Calculate driver ahead and distance to driver ahead.

        Driver ahead: three letter abbreviation of the drivers name
        Distance to driver ahead: distance to the car ahead in meters

        .. note:: This gives a smoother/cleaner result than the legacy implementation but WILL introduce
            integration error when used over long distances (more than one or two laps may sometimes be considered
            a long distance). If in doubt, do sanity checks against the legacy version.

        Returns:
            driver ahead (numpy.array), distance to driver ahead (numpy.array)
        """
        t_start = self['SessionTime'].iloc[0]
        t_end = self['SessionTime'].iloc[-1]

        combined_distance = pd.DataFrame()

        # Assume the following lap profile as a catch all for all drivers
        #
        # |------ Lap before ------|------ n Laps between ------|------ Lap after ------|
        #        ^                                                   ^
        #        t_start                                             t_end
        # Integration of the distance needs to start at the finish line so that there exists a common zero point
        # Therefore find the "lap before" which is the lap during which the telemetry slice starts and the "lap after"
        # where the telemetry slice ends
        # Integrate distance over all relevant laps and slice by t_start and t_end after to get the interesting
        # part only
        own_laps = self.session.laps[self.session.laps['DriverNumber'] == self.driver]
        first_lap_number = (own_laps[own_laps['LapStartTime'] <= t_start])['LapNumber'].iloc[-1]

        for drv in self.session.drivers:
            # find correct first relevant lap; very important for correct zero point in distance
            drv_laps = self.session.laps[self.session.laps['DriverNumber'] == drv]
            drv_laps_before = drv_laps[(drv_laps['LapStartTime'] <= t_start)]
            if not drv_laps_before.empty:
                lap_n_before = drv_laps_before['LapNumber'].iloc[-1]
                if lap_n_before < first_lap_number:
                    # driver is behind on track an therefore will cross the finish line AFTER self
                    # therefore above check for LapStartTime <= t_start is wrong
                    # the first relevant lap is the first lap with LapStartTime > t_start which is lap_n_before += 1
                    lap_n_before += 1
            else:
                lap_n_before = min(drv_laps['LapNumber'])

            # find last relevant lap so as to no do too much unnecessary calculation later
            drv_laps_after = drv_laps[drv_laps['Time'] >= t_end]
            lap_n_after = drv_laps_after['LapNumber'].iloc[0] if not drv_laps_after.empty else max(drv_laps['LapNumber'])
            relevant_laps = drv_laps[(drv_laps['LapNumber'] >= lap_n_before) & (drv_laps['LapNumber'] <= lap_n_after)]

            # first slice by lap and calculate distance, so that distance is zero at finish line
            drv_tel = self.session.car_data[drv].slice_by_lap(relevant_laps).add_distance() \
                .loc[:, ('SessionTime', 'Distance')].rename(columns={'Distance': drv})

            # now slice again by time to only get the relevant time frame
            drv_tel = drv_tel.slice_by_time(t_start, t_end)
            if drv_tel.empty:
                continue
            drv_tel = drv_tel.set_index('SessionTime')
            combined_distance = combined_distance.join(drv_tel, how='outer')

        # create driver map for array
        drv_map = combined_distance.loc[:, combined_distance.columns != self.driver].columns.to_numpy()
        for drv_number, drv_abb, team in D_LOOKUP:  # change driver number into abbreviation
            drv_map[drv_map == str(drv_number)] = drv_abb

        own_dst = combined_distance.loc[:, self.driver].to_numpy()
        other_dst = combined_distance.loc[:, combined_distance.columns != self.driver].to_numpy()
        # replace distance with nan if it does not change
        # prepend first row before diff so that array size stays the same; but missing first sample because of that
        other_dst[np.diff(other_dst, n=1, axis=0, prepend=other_dst[0, :].reshape((1, -1))) == 0] = np.nan

        # resize own_dst to match shape of other_dst for easy subtraction
        own_dst = np.repeat(own_dst.reshape((-1, 1)), other_dst.shape[1], axis=1)

        delta_dst = other_dst - own_dst
        delta_dst[np.isnan(delta_dst)] = np.inf  # substitute nan with inf, else nan is returned as min
        delta_dst[delta_dst < 0] = np.inf  # remove cars behind so that neg numbers are not returned as min

        index_ahead = np.argmin(delta_dst, axis=1)

        drv_ahead = np.array([drv_map[i] for i in index_ahead])
        drv_ahead[np.all(delta_dst == np.inf, axis=1)] = ''  # remove driver from all inf rows

        dist_to_drv_ahead = np.array([delta_dst[i, index_ahead[i]] for i in range(len(index_ahead))])
        dist_to_drv_ahead[np.all(delta_dst == np.inf, axis=1)] = np.nan  # remove value from all inf rows

        return drv_ahead, dist_to_drv_ahead

    def _make_trajectory(self, ref_lap, working_data):
        """Create telemetry Distance
        """
        # get data slices; pad before to make interpolation work properly
        # merge_channels will cut off data which is too early
        # car_data, pos_data = self.slice_by_lap((self.car_data[ref_lap['DriverNumber']],
        #                                         self.pos_data[ref_lap['DriverNumber']]),
        #                                        ref_lap)

        # telemetry = self.merge_channels(car_data, pos_data, frequency='original')
        telemetry = self.slice_by_lap(working_data[ref_lap['DriverNumber']], ref_lap)

        if telemetry.size != 0:
            x = telemetry['X'].values
            y = telemetry['Y'].values
            z = telemetry['Z'].values
            s = telemetry['Distance'].values

            # Assuming constant speed in the last tenth
            dt0_ = (ref_lap['LapTime'] - telemetry['Time'].iloc[-1]).total_seconds()
            ds0_ = (telemetry['Speed'].iloc[-1] / 3.6) * dt0_
            total_s = s[-1] + ds0_

            # To prolong start and finish and have a correct linear interpolation
            full_s = np.concatenate([s - total_s, s, s + total_s])
            full_x = np.concatenate([x, x, x])
            full_y = np.concatenate([y, y, y])
            full_z = np.concatenate([z, z, z])

            reference_s = np.arange(0, total_s, REFERENCE_LAP_RESOLUTION)

            reference_x = np.interp(reference_s, full_s, full_x)
            reference_y = np.interp(reference_s, full_s, full_y)
            reference_z = np.interp(reference_s, full_s, full_z)

            ssize = len(reference_s)

            """Build track map and project driver position to one trajectory
            """

            def fix_suzuka(projection_index, _s):
                """Yes, suzuka is bad
                """

                # For tracks like suzuka (therefore only suzuka) we have
                # a beautiful crossing point. So, FOR F**K SAKE, sometimes
                # shortest distance may fall below the bridge or viceversa
                # gotta do some monotony sort of check. Not the cleanest
                # solution.
                def moving_average(a, n=3):
                    ret = np.cumsum(a, dtype=float)
                    ret[n:] = ret[n:] - ret[:-n]
                    ma = ret[n - 1:] / n

                    return np.concatenate([ma[0:n // 2], ma, ma[-n // 2:-1]])

                ma_projection = moving_average(_s[projection_index], n=3)
                spikes = np.absolute(_s[projection_index] - ma_projection)
                # 1000 and 3000, very suzuka specific. Damn magic numbers
                sel_bridge = np.logical_and(spikes > 1000, spikes < 3000)
                unexpected = np.where(sel_bridge)[0]
                max_length = _s[-1]

                for p in unexpected:
                    # Just assuming linearity for this 2 or 3 samples
                    last_value = _s[projection_index[p - 1]]
                    last_step = last_value - _s[projection_index[p - 2]]

                    if (last_value + last_step) > max_length:
                        # Over the finish line
                        corrected_distance = -max_length + last_step + last_value
                    else:
                        corrected_distance = last_value + last_step

                    corrected_index = np.argmin(np.abs(_s - corrected_distance))
                    projection_index[p] = corrected_index

                return projection_index

            track = np.empty((ssize, 3))
            track[:, 0] = reference_x
            track[:, 1] = reference_y
            track[:, 2] = reference_z

            track_tree = scipy.spatial.cKDTree(track)
            drivers_list = np.array(list(self.drivers))
            stream_length = len(working_data[drivers_list[0]])
            dmap = np.empty((stream_length, len(drivers_list)), dtype=int)

            fast_query = {'n_jobs': 2, 'distance_upper_bound': 500}
            # fast_query < Increases speed
            for index, drv in enumerate(drivers_list):
                if drv not in working_data.keys():
                    logging.warning(f"No position data for driver {drv}. (_make_trajectory)")
                    continue
                trajectory = working_data[drv][['X', 'Y', 'Z']].values
                projection_index = track_tree.query(trajectory, **fast_query)[1]
                # When tree cannot solve super far points means there is some
                # pit shit shutdown. We can replace these index with 0
                projection_index[projection_index == len(reference_s)] = 0
                dmap[:, index] = fix_suzuka(projection_index.copy(), reference_s)

            """Create transform matrix to change distance point of reference
            """
            t_matrix = np.empty((ssize, ssize))
            for index in range(ssize):
                rref = reference_s - reference_s[index]
                rref[rref <= 0] = total_s + rref[rref <= 0]
                t_matrix[index, :] = rref

            """Create mask to remove distance elements when car is on track
            """
            time = working_data[drivers_list[0]]['Time']
            pit_mask = np.zeros((stream_length, len(drivers_list)), dtype=bool)
            for driver_index, driver_number in enumerate(drivers_list):
                laps = self.laps.pick_driver(driver_number)
                in_pit = True
                times = [[], []]
                for lap_index in laps.index:
                    lap = laps.loc[lap_index]
                    if not pd.isnull(lap['PitInTime']) and not in_pit:
                        times[1].append(lap['PitInTime'])
                        in_pit = True
                    if not pd.isnull(lap['PitOutTime']) and in_pit:
                        times[0].append(lap['PitOutTime'])
                        in_pit = False

                if not in_pit:
                    # Car crashed, we put a time and 'Status' will take care
                    times[1].append(lap['Time'])
                times = np.transpose(np.array(times))
                for inout in times:
                    out_of_pit = np.logical_and(time >= inout[0], time < inout[1])
                    pit_mask[:, driver_index] |= out_of_pit
                on_track = (working_data[driver_number]['Status'] == 'OnTrack')
                pit_mask[:, driver_index] &= on_track.values

            """Calculate relative distances using transform matrix
            """
            driver_ahead = {}
            stream_axis = np.arange(stream_length)
            for my_di, my_d in enumerate(drivers_list):
                rel_distance = np.empty(np.shape(dmap))

                for his_di, his_d in enumerate(drivers_list):
                    my_pos_i = dmap[:, my_di]
                    his_pos_i = dmap[:, his_di]
                    rel_distance[:, his_di] = t_matrix[my_pos_i, his_pos_i]

                his_in_pit = ~pit_mask.copy()
                his_in_pit[:, my_di] = False
                my_in_pit = ~pit_mask[:, drivers_list == my_d][:, 0]
                rel_distance[his_in_pit] = np.nan

                closest_index = np.nanargmin(rel_distance, axis=1)
                closest_distance = rel_distance[stream_axis, closest_index]
                closest_driver = drivers_list[closest_index].astype(object)
                closest_distance[my_in_pit] = np.nan
                closest_driver[my_in_pit] = None

                data = {'DistanceToDriverAhead': closest_distance,
                        'DriverAhead': closest_driver}
                driver_ahead[my_d] = pd.DataFrame(data)

        else:
            # no data to base calculations on; create empty results
            driver_ahead = dict()
            for drv in self.drivers:
                data = {'DistanceToDriverAhead': (), 'DriverAhead': ()}
                driver_ahead[drv] = pd.DataFrame(data)

        return driver_ahead

    def _inject_driver_ahead(self, working_data):
        """Add 'DistanceToDriverAhead' and 'DriverAhead' column to self.

        .. note:: You should usually not need to use this function. It is called once from :func:`load_telemetry`.
            Everything else is highly inefficient.
        """

        ref_lap = self._get_reference_lap(working_data)

        if ref_lap is not None:
            driver_ahead = self._make_trajectory(ref_lap, working_data)

        else:
            logging.warning("Telemetry data is missing! No valid car data has been found for any lap!"
                            "Cannot compute 'DistanceToDriverAhead' or 'DriverAhead'")

            driver_ahead = dict()  # create empty data
            for drv in self.drivers:
                empty_drv = (None,) * len(self.pos_data[drv])
                empty_dist = (np.nan,) * len(self.pos_data[drv])
                driver_ahead[drv] = pd.DataFrame({'DistanceToDriverAhead': empty_dist, 'DriverAhead': empty_drv})

        return driver_ahead


class Weekend:
    """If you want to handle multiple sessions from the same race event
    you can use a :class:Weekend instance.

    For example you could do the following::

        import fastf1 as ff1

        weekend = ff1.get_session(2019, 'Monza')
        quali = weekend.get_quali() # Q Session
        race = weekend.get_race() # R Session

    """
    def __init__(self, year, gp):
        self.year = year
        self.gp = gp
        if self.is_testing():
            logging.warning("Ergast api not supported for testing.")
            self.data = {'raceName': gp,
                         'date': TESTING_LOOKUP[str(year)][int(gp[-1]) - 1][-1]}
        else:
            try:
                self.data = ergast.fetch_weekend(self.year, self.gp)
            except Exception as exception:
                logging.critical("Failed to load critical data from Ergast!\n\n Cannot determine the date and name "
                                 "of the weekend. Cannot proceed!\n")  # TODO some backup strategy for this
                logging.critical(str(exception))
                logging.debug("", exc_info=exception)
                exit()

    def get_practice(self, number):
        """
        Args:
            number: 1, 2 or 3 Free practice session number
        Returns:
            :class:`Session` instance
        """
        return Session(self, f'Practice {number}')

    def get_quali(self):
        """
        Returns:
            :class:`Session` instance
        """
        return Session(self, 'Qualifying')

    def get_race(self):
        """
        Returns:
            :class:`Session` instance
        """
        return Session(self, 'Race')

    def is_testing(self):
        if type(self.gp) is str:
            return 'Test' in self.gp
        else:
            return False

    @property
    def name(self):
        """Weekend name, e.g. "British Grand Prix"
        """
        return self.data['raceName']

    @property
    def date(self):
        """Weekend race date (YYYY-MM-DD)
        """
        return self.data['date']


class Session:
    """The session class usually will be your starting point. This
    object will have various information about the event such as `name` and
    `date`. To get the sessions laps use :meth:`Session.load_laps`.
    """

    def __init__(self, weekend, session_name):
        self.weekend = weekend
        self.name = session_name
        self.date = self._get_session_date()
        self.api_path = api.make_path(self.weekend.name,
                                      self.weekend.date,
                                      self.name, self.date)
        if not self.weekend.is_testing():
            # The Ergast API can provide some general information about weekends, drivers, ...
            # See ergast.com
            try:
                self.results = ergast.load(self.weekend.year,
                                           self.weekend.gp,
                                           self.name)
            except IndexError:
                # Ergast will take some time after a session until the data is available
                # while the data is not yet available, an error will be raised
                logging.warning("Ergast  API lookup failed. The session is very recent and not yet available or does "
                                "not exist.")
                self._create_empty_ergast_result()
            except Exception as exception:
                logging.error("Failed to load data from Ergast!")
                logging.exception(exception)
                self._create_empty_ergast_result()

        else:
            self._create_empty_ergast_result()

        self.laps = Laps(session=self)
        """Instance of :class:`Laps` containing all laps from all drivers in this session."""
        self.session_start_date = None  # can only be set when/if telemetry has been downloaded

        self.car_data = dict()
        """Car telemetry (Speed, RPM, etc.) as received from the api."""
        self.pos_data = dict()
        """Car position data as received from the api."""

        self.telemetry = dict()
        """Merged and possibly resampled telemetry and position data."""

        self.track = None

        self.drivers = list()
        """List of all that took part in this session; contains driver numbers as string. Drivers for which lap or
         telemetry data is missing completely are not listed!"""

    @property
    def driver_numbers(self):
        if self.laps:
            return list(self.laps['DriversNum'].unique())
        return None

    def _create_empty_ergast_result(self):
        """In case Ergast has no data, this function creates an empty result
        to emulate the structure."""
        self.results = []
        for driver in D_LOOKUP:
            self.results.append({
                'number': str(driver[0]),
                'Driver': {'code': driver[1]},
                'Constructor': {'name': driver[2]}})

    def _get_session_date(self):
        """Session date formatted as '%Y-%m-%d' (e.g. '2019-03-12')"""
        if self.weekend.is_testing():
            year = str(self.weekend.year)
            week_index = int(self.weekend.name[-1]) - 1
            day_index = int(self.name[-1]) - 1
            date = TESTING_LOOKUP[year][week_index][day_index]
        elif self.name in ('Qualifying', 'Practice 3'):
            # Assuming that quali was one day before race which is not always correct
            # TODO Should check if also formula1 makes this assumption
            offset_date = pd.to_datetime(self.weekend.date) + pd.DateOffset(-1)
            date = offset_date.strftime('%Y-%m-%d')
        elif self.name in ('Practice 1', 'Practice 2'):
            # Again, assuming that practice 1/2 are the day before quali (except Monaco)
            _ = -3 if self.weekend.name == 'Monaco Grand Prix' else -2
            offset_date = pd.to_datetime(self.weekend.date) + pd.DateOffset(_)
            date = offset_date.strftime('%Y-%m-%d')
        else:  # Race
            date = self.weekend.date

        return date

    def load_laps(self, with_telemetry=True):
        """ TODO Columns
        TODO explain track status handling
        With load laps all the timing information is merged into a
        single pandas dataframe. The first time you run this method on
        a session it may take a while to load. Multiple megabytes of
        data have to be downloaded and processed. After that, laps will
        be stored locally and execution will be much faster.

        The returned :class:`Laps` instance can be used just like a
        pandas DataFrame with some additional enhancements.

        The dataframe columns, therefore, each lap, has the following
        properties:

            - **Time** (pandas.Timedelta): Time when the lap time was set (end of lap)
            - **Driver** (string): Three letters driver identifier
            - **LapTime** (pandas.Timedelta): Recorded lap time
            - **LapNumber** (int): Recorded lap number
            - **PitOutTime** (pandas.Timedelta): Time when car exited the pit
            - **PitInTime** (pandas.Timedelta): Time when car entered the pit
            - **Sector1Time** (pandas.Timedelta): Sector 1 recorded time
            - **Sector2Time** (pandas.Timedelta): Sector 2 recorded time
            - **Sector3Time** (pandas.Timedelta): Sector 3 recorded time
            - **Sector1Time** (pandas.Timedelta): Sector 1 timestamp (end of sector)
            - **Sector2Time** (pandas.Timedelta): Sector 2 timestamp (end of sector)
            - **Sector3Time** (pandas.Timedelta): Sector 3 timestamp (end of sector)
            - **SpeedI1** (float): Speedtrap sector 1
            - **SpeedI2** (float): Speedtrap sector 2
            - **SpeedFL** (float): Speedtrap at finish line
            - **SpeedST** (float): Speedtrap on longest straight (Not sure)
            - **Stint** (int): Indicates the stint number
            - **Compound** (str): Tyre compound name: SOFT, MEDIUM ..
            - **TyreLife** (int): Laps spent on that compound
            - **FreshTyre** (bool): Tyre had TyreLife=0 at stint start
            - **DriverNumber** (str): Car number
            - **Team** (str): Team name
            - **LapStartDate** (pandas.Timestamp): Timestamp (Date+Time) for the start of the lap
            - **telemetry** (pandas.DataFrame): Telemetry with the following channels:

                - `Time` (timedelta): Time axis (0 is start of lap)
                - `Distance` (float): Distance in meters (from speed and time)
                - `Speed` (float): Car speed
                - `RPM` (int): Car RPM
                - `nGear` (int): Car gear number
                - `Throttle` (float): 0-100 Throttle pedal pressure
                - `Brake` (float): 0-100 Brake pedal pressure
                - `DRS` (int): DRS indicator
                - `X` (float): GPS X position (normalized)
                - `Y` (float): GPS X position (normalized)
                - `Z` (float): GPS Z position (normalized)
                - `Status` (string): flags OffTrack/OnTrack for GPS 
                - `SessionTime` (timedelta): time elapsed from session start
                - `DistanceToDriverAhead` (string): distance to next car in m
                - `DriverAhead` (string): the car ahead

        .. note:: Absolute time is not super accurate. The moment a lap
            is logged is not always the same and there will be some
            jitter. At the moment lap time reference is synchronised
            on the sector time triggered with lowest latency.
            Expect an error of around ±10m when overlapping telemetry
            data of different laps.

        Returns:
            :class:`Laps`

        """
        logging.info(f"Loading {self.weekend.name} {self.name}")

        """From `timing_data` and `timing_app_data` a summary table is
        built. Lap by lap, information on tyre, sectors and times are 
        organised in an accessible pandas data frame.

        Returns:
            pandas dataframe

        """
        logging.info("Getting summary...")
        data, _ = api.timing_data(self.api_path)
        app_data = api.timing_app_data(self.api_path)
        # Now we do some manipulation to make it beautiful
        logging.info("Formatting summary...")

        # Matching data and app_data. Not super straightforward
        # Sometimes a car may enter the pit without changing tyres, so
        # new compound is associated with the help of logging time.
        useful = app_data[['Driver', 'Time', 'Compound', 'TotalLaps', 'New']]
        useful = useful[~useful['Compound'].isnull()]

        self.drivers = list(data['Driver'].unique())

        if not self.drivers:
            raise NoLapDataError

        for i, driver in enumerate(self.drivers):
            d1 = data[data['Driver'] == driver]
            d2 = useful[useful['Driver'] == driver]

            if len(d2) == 0:
                continue  # no data for this driver; skip

            result = pd.merge_asof(d1, d2, on='Time', by='Driver')

            for npit in result['NumberOfPitStops'].unique():
                sel = result['NumberOfPitStops'] == npit
                result.loc[sel, 'TotalLaps'] += np.arange(0, sel.sum()) + 1
            # check if df is defined already before concat (vars is a builtin function)
            df = result if 'df' not in vars() else pd.concat([df, result], sort=False)

        laps = df.reset_index(drop=True)
        laps.rename(columns={'TotalLaps': 'TyreLife',
                             'NumberOfPitStops': 'Stint',
                             'Driver': 'DriverNumber',
                             'NumberOfLaps': 'LapNumber',
                             'New': 'FreshTyre'}, inplace=True)
        laps['Stint'] += 1  # counting stints from 1
        t_map = {r['number']: r['Constructor']['name'] for r in self.results}
        laps['Team'] = laps['DriverNumber'].map(t_map)
        d_map = {r['number']: r['Driver']['code'] for r in self.results}
        laps['Driver'] = laps['DriverNumber'].map(d_map)
        laps['LapStartTime'] = laps['Time'] - laps['LapTime']

        # add track status data
        ts_data = api.track_status_data(self.api_path)
        laps['TrackStatus'] = '1'

        def applicator(new_status, current_status):
            if current_status == '1':
                return new_status
            elif new_status not in current_status:
                return current_status + new_status
            else:
                return current_status

        if len(ts_data) > 0:
            t = ts_data['Time'][0]
            status = ts_data['Status'][0]
            for next_t, next_status in zip(ts_data['Time'][1:], ts_data['Status'][1:]):
                if status != '1':
                    # status change partially in lap partially outside
                    sel = (((next_t >= laps['LapStartTime']) & (laps['LapStartTime'] >= t)) |
                           ((t <= laps['Time']) & (laps['Time'] <= next_t)))
                    laps.loc[sel, 'TrackStatus'] = laps.loc[sel, 'TrackStatus'].apply(
                        lambda curr: applicator(status, curr)
                    )

                    # status change two times in one lap (e.g. short yellow flag)
                    sel = ((laps['LapStartTime'] <= t) & (laps['Time'] >= next_t))
                    laps.loc[sel, 'TrackStatus'] = laps.loc[sel, 'TrackStatus'].apply(
                        lambda curr: applicator(status, curr)
                    )

                t = next_t
                status = next_status

            sel = laps['LapStartTime'] >= t
            laps.loc[sel, 'TrackStatus'] = laps.loc[sel, 'TrackStatus'].apply(
                lambda curr: applicator(status, curr)
            )

        else:
            logging.warning("Could not load any valid session status information!")

        self.laps = Laps(laps, session=self)

        self._check_lap_accuracy()

        if with_telemetry:
            self.load_telemetry()

        logging.info(f"Loaded data for {len(self.drivers)} drivers: {self.drivers}")
        logging.info(f"Laps loaded and saved!")

        return self.laps

    def _check_lap_accuracy(self):
        # accuracy validation; simples yes/no validation
        # currently only relies on provided information which can't quite catch all problems
        # TODO: check for outliers in lap start position
        # self.laps['IsAccurate'] = False  # default should be not accurate
        for drv in self.drivers:
            is_accurate = list()
            prev_lap = None
            integrity_errors = 0
            for _, lap in self.laps[self.laps['DriverNumber'] == drv].iterrows():
                a = True

                # require existence, non-existence and specific values for some variables
                check_1 = (pd.isnull(lap['PitInTime'])
                           & pd.isnull(lap['PitOutTime'])
                           & (lap['TrackStatus'] in ('1', '2'))  # slightly paranoid, allow only green and yellow flag
                           & (not pd.isnull(lap['LapTime']))
                           & (not pd.isnull(lap['Sector1Time']))
                           & (not pd.isnull(lap['Sector2Time']))
                           & (not pd.isnull(lap['Sector3Time'])))

                if check_1:  # only do check 2 if all necessary values for this check are even available
                    # sum of sector times should be almost equal to lap time (tolerance 3ms)
                    check_2 = np.allclose(np.sum((lap['Sector1Time'], lap['Sector2Time'],
                                                  lap['Sector3Time'])).total_seconds(),
                                          lap['LapTime'].total_seconds(),
                                          atol=0.003, rtol=0, equal_nan=False)
                    if not check_2:
                        integrity_errors += 1
                else:
                    check_2 = False  # data not available means fail

                if prev_lap is not None:
                    # first lap after safety car often has timing issues (as do all laps under safety car)
                    check_3 = (prev_lap['TrackStatus'] != '4')
                else:
                    check_3 = True  # no previous lap, no SC error

                result = check_1 and check_2 and check_3
                is_accurate.append(result)
                prev_lap = lap

            if len(is_accurate) > 0:
                self.laps.loc[self.laps['DriverNumber'] == drv, 'IsAccurate'] = is_accurate

            if integrity_errors > 0:
                logging.warning(f"Driver {drv: >2}: Lap timing integrity check failed for {integrity_errors} lap(s)")

    def load_telemetry(self):
        """Load telemetry data.

        Also does some further calculations to add LapStartDate, LapStartTime which can only be done precisely with
        timing information from the telemetry data.
        """
        logging.info("Getting telemetry data...")
        car_data = api.car_data(self.api_path)
        logging.info("Getting position data...")
        pos_data = api.position_data(self.api_path)

        self.drivers = list(set(self.drivers).intersection(set(car_data.keys())).intersection(set(pos_data.keys())))
        # self.drivers should only contain drivers which exist in all parts of the data

        self._calculate_session_start_date(car_data, pos_data)

        for drv in self.drivers:
            # drop and recalculate time stamps based on 'Date', because 'Date' has a higher resolution
            drv_car = Telemetry(car_data[drv].drop('Time', 1), session=self, driver=drv)
            drv_pos = Telemetry(pos_data[drv].drop('Time', 1), session=self, driver=drv)

            drv_car['Date'] = drv_car['Date'].round('ms')
            drv_pos['Date'] = drv_pos['Date'].round('ms')

            drv_car['Time'] = drv_car['Date'] - self.session_start_date  # create proper continuous timestamps
            drv_pos['Time'] = drv_pos['Date'] - self.session_start_date
            drv_car['SessionTime'] = drv_car['Time']
            drv_pos['SessionTime'] = drv_pos['Time']

            self.car_data[drv] = drv_car
            self.pos_data[drv] = drv_pos

        self.laps['LapStartDate'] = self.laps['LapStartTime'] + self.session_start_date

        # for drv in self.drivers:
        #     self.car_data[drv] = self.car_data[drv].drop('Distance', 1)
        #     # TODO if somehow preventable, do not merge here! All calculations should be done without resampling
        #     self.telemetry[drv] = self.merge_channels(self.car_data[drv], self.pos_data[drv], frequency='original')
        #     self.telemetry[drv] = self.inject_distance(self.telemetry[drv])
        #
        # driver_ahead = self._inject_driver_ahead(self.telemetry)  # this is done here because the full data set is required for this operation
        # for drv in self.drivers:
        #     self.telemetry[drv] = self.telemetry[drv].join(driver_ahead[drv])

    def get_driver(self, identifier):
        """
        Args:
            identifier (str): driver's three letter identifier (for example 'VER')

        Returns:
            instance of :class:`Driver`
        """
        if type(identifier) is str:
            for info in self.results:
                if info['Driver']['code'] == identifier:
                    return Driver(self, info)

        return None

    def _calculate_session_start_date(self, car_data, pos_data):
        """Calculate the timestamp at which the session was started.

        This function sets :py:attr:`self.start_date`

        The current assumption is that the latest date which can be calculated is correct. (Based on the timestamp with
        the least delay.)
        
        Args:
            car_data: Car telemetry; should contain all samples and only original ones
            pos_data: Car position data; should contain all samples and only original ones
        """
        date_offset = None

        for data in (car_data, pos_data):
            for drv in data.keys():
                new_offset = max(data[drv]['Date'] - data[drv]['Time'])
                if date_offset is None or new_offset > date_offset:
                    date_offset = new_offset

        self.session_start_date = date_offset

    def _get_reference_lap(self, working_data):
        times = self.laps['LapTime'].copy()
        times = times.sort_values()

        for i in range(len(self.laps)):
            lap = self.laps.loc[times.index[i]]
            car_data = working_data[lap['DriverNumber']].slice_by_lap(lap)  # TODO interpolate_edges ?
            if np.all(car_data['Speed'] > 0):  # check for valid telemetry
                break
        else:
            return None

        return lap


class Laps(pd.DataFrame):
    """This class wraps :attr:`Session.laps` which is a classic pandas
    DataFrame with the addition of a few 'pick' methods to simplify lap
    selection and filtering.

    If for example you want to get the fastest lap of Bottas you can
    narrow it down like this::

        import fastf1 as ff1

        laps = ff1.get_session(2019, 'Bahrain', 'Q').load_laps()
        best_bottas = laps.pick_driver('BOT').pick_fastest()

        print(best_bottas['LapTime'])
        # Timedelta('0 days 00:01:28.256000')

    Pick methods will return :class:`Laps` or pandas Series if only 1
    entry is left.
    """

    _metadata = ['session']

    QUICKLAP_THRESHOLD = 1.07

    def __init__(self, *args, session=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session

    @property
    def _constructor(self):
        return Laps

    @property
    def _constructor_sliced(self):
        # this is effectively 'return Lap' but I need to pass a reference to the session instance too
        # what this actually does is to dynamically subclass Lap with the new class being called Lap again,
        # additionally the class variable session is added
        return type('Lap', (Lap,), {'session': self.session})

    @property
    def base_class_view(self):
        # for a nicer debugging experience; can now select base_class_view -> show as dataframe in IDE
        return pd.DataFrame(self)

    @cached_property
    def telemetry(self):
        return self.get_telemetry()

    def get_telemetry(self):
        pos_data = self.get_pos_data(pad=1, pad_side='both')
        car_data = self.get_car_data(pad=1, pad_side='both')
        merged = pos_data.merge_channels(car_data)
        return merged.slice_by_lap(self, interpolate_edges=True)

    def get_car_data(self, **kwargs):
        drv_num = self['DriverNumber'].unique()
        if len(drv_num) != 1:
            raise ValueError("Cannot slice telemetry for when self contains Laps of multiple drivers!")
        drv_num = drv_num[0]
        car_data = self.session.car_data[drv_num].slice_by_lap(self, **kwargs).reset_index(drop=True)
        car_data = car_data.add_distance().add_relative_distance().add_driver_ahead()
        return car_data

    def get_pos_data(self, **kwargs):
        drv_num = self['DriverNumber'].unique()
        if len(drv_num) != 1:
            raise ValueError("Cannot slice telemetry for when self contains Laps of multiple drivers!")
        drv_num = drv_num[0]
        pos_data = self.session.pos_data[self['DriverNumber']].slice_by_lap(self, **kwargs).reset_index(drop=True)
        return pos_data

    def pick_driver(self, identifier):
        """Select driver given his three letters identifier or its car
        number::

            perez_laps = ff1.pick_driver('PER')
            bottas_laps = ff1.pick_driver(77)
            kimi_laps = ff1.pick_driver('RAI')

        """
        identifier = str(identifier)
        if identifier.isdigit():
            return self[self['DriverNumber'] == identifier]
        else:
            return self[self['Driver'] == identifier]

    def pick_drivers(self, identifiers):
        """Select drivers given a list of their identifiers. Same as
        :meth:`Laps.pick_driver` but for lists::

            some_drivers_laps = ff1.pick_drivers([5, 'BOT', 7])

        """
        names = [n for n in identifiers if not str(n).isdigit()]
        numbers = [str(n) for n in identifiers if str(n).isdigit()]
        drv, num = self['Driver'], self['DriverNumber']

        return self[(drv.isin(names) | num.isin(numbers))]

    def pick_team(self, name):
        """Select team given its name::

            mercedes = ff1.pick_team('Mercedes')
            alfa_romeo = ff1.pick_team('Alfa Romeo')

        Have a look to :attr:`fastf1.plotting.TEAM_COLORS` for a quick
        reference on team names.
        """
        return self[self['Team'] == name]

    def pick_teams(self, names):
        """Same as :meth:`Laps.pick_team` but for a list of teams.
        """
        return self[self['Team'].isin(names)]

    def pick_fastest(self):
        """Get lap with best `LapTime`.
        """
        lap = self.loc[self['LapTime'].idxmin()]
        if isinstance(lap, pd.DataFrame):
            # More laps, same time
            lap = lap.iloc[0]  # take first clocked

        return lap

    def pick_quicklaps(self, threshold=None):
        """Select laps with `LapTime` faster than a certain limit.
        By default 107% of the best `LapTime` of the given laps set.

        Args:
            threshold (optional, float): custom threshold coefficent
                (e.g. 1.05 for 105%)

        """
        if threshold is None:
            threshold = Laps.QUICKLAP_THRESHOLD
        time_threshold = self['LapTime'].min() * threshold

        return self[self['LapTime'] < time_threshold]

    def pick_tyre(self, compound):
        """Get laps done on a specific compound.

        Args:
            compound (string): may be "SOFT", "MEDIUM" or "HARD"

        """
        return self[self['Compound'] == compound]

    def pick_track_status(self, status, how='equals'):
        """Get laps set under a specific track status.

        Args:
            status (str): The track status as a string, e.g. '1'
            how (str): one of 'equals'/'contains'
                For example, if how='equals', status='2' will only match '2'.
                If how='contains', status='2' will also match '267' and similar
        Returns:
            A sliced instance of Laps
        """
        if how == 'equals':
            return self[self['TrackStatus'] == status]
        elif how == 'contains':
            return self[self['TrackStatus'].str.contains(status, regex=False)]
        else:
            raise ValueError(f"Invalid value '{how}' for kwarg 'how'")

    def pick_wo_box(self):
        """Get laps which are NOT in or out laps.

        Returns:
            A sliced instance of Laps
        """
        return self[pd.isnull(self['PitInTime']) & pd.isnull(self['PitOutTime'])]

    def pick_accurate(self):
        """Get laps which passed the accuracy validation check (lap['IsAccurate'] is True).

        Returns:
            A sliced instance of Laps
        """
        return self[self['IsAccurate']]

    def iterlaps(self, require=()):
        # TODO doc
        for index, lap in self.iterrows():
            if require:
                # make sure that all required values even exist in the index
                if any(val not in lap.index.values for val in require):
                    continue
                require = set(require).intersection(set(lap.index.values))
                if any(pd.isnull(val) for val in lap.loc[require]):
                    continue
            yield index, lap


class Lap(pd.Series):
    """This class provides data for a single lap.
    It subclasses pandas.Series and provides some additional data which is computed on the fly
    when accessed."""
    # TODO docstring with explanation of columns

    _metadata = ['session']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _constructor(self):
        return Lap

    @cached_property
    def telemetry(self):
        pos_data = self.get_pos_data(pad=1, pad_side='both')
        car_data = self.get_car_data(pad=1, pad_side='both')
        merged = pos_data.merge_channels(car_data)
        return merged.slice_by_lap(self, interpolate_edges=True)

    def get_car_data(self, **kwargs):
        car_data = self.session.car_data[self['DriverNumber']].slice_by_lap(self, **kwargs).reset_index(drop=True)
        car_data = car_data.add_distance().add_relative_distance().add_driver_ahead()
        return car_data

    def get_pos_data(self, **kwargs):
        pos_data = self.session.pos_data[self['DriverNumber']].slice_by_lap(self, **kwargs).reset_index(drop=True)
        return pos_data


class Driver:
    """Driver class that provides some information on drivers and their finishing results.

    see also :func:`Session.get_driver`

    .. note:: Driver data is only available if the Ergast api lookup did not fail.

    """
    def __init__(self, session, info):
        self.session = session
        self.info = info
        """`Driver.info` contains some more info from the Ergast api"""
        self.identifier = info['Driver']['code']
        self.number = info['number']

    @property
    def dnf(self):
        """True if driver did not finish"""
        s = self.info['status']
        return not (s[3:6] == 'Lap' or s == 'Finished')

    @property
    def grid(self):
        """Grid position"""
        return int(self.info['grid'])

    @property
    def position(self):
        """Finishing position"""
        return int(self.info['position'])

    @property
    def name(self):
        """Driver first name"""
        return self.info['Driver']['givenName']

    @property
    def familyname(self):
        """Driver family name"""
        return self.info['Driver']['familyName']

    @property
    def team(self):
        """Team name"""
        return self.info['Constructor']['name']


def _map_objects(df):
    """Map column values of dataframes to integers if they are a non-numeric type.

    For example map the 'Status' column values 'OnTrack' and 'OffTrack' to 0 and 1.
    This can be useful when doing interpolation and allows for interpolating columns that can not be interpolated
    with their native data type.

    Args:
        df (pd.DataFrame): pandas dataframe

    Returns:
        pd.DataFrame: the original dataframe with it's column values mapped to integers where necessary
        func: a function that takes the mapped dataframe as single argument, maps the original values back and
            returns the dataframe again
    """
    nnummap = {}
    for column in df.columns:
        if df[column].dtype == object:
            backward = dict(enumerate(df[column].unique()))
            forward = {v: k for k, v in backward.items()}
            df[column] = df[column].map(forward)
            nnummap[column] = backward

    def unmap(res):
        for column in nnummap:
            res[column] = res[column].round().map(nnummap[column])
        return res

    return df, unmap


def _log_progress(i, length, c=30):
    """Simple progress bar for console logging.

    Args:
        i (int): current value
        length (int): maximum value
        c (int, optional): number of steps when displaying the progress bar
    """
    if length < c:
        c = length
    if logging.root.level >= logging.INFO and i % int(length / (c - 1)) == 0:
        p = round((i / length) * c)
        is_last = (p * (c + 1) / c) > c
        print(f"\r[{'+' * p}{'-' * (c - p)}] ({length if is_last else i}/{length})",
              end="\n" if is_last else '')


class NoLapDataError(Exception):
    """Raised if the API request does not fail but there is no usable data after processing the result."""
    def __init__(self, *args):
        super(NoLapDataError, self).__init__("Failed to load session because the API did not provide any usable data.")
