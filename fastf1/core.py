"""
:mod:`fastf1.core` - Core module
================================

The Fast-F1 core is a collection of functions and data objects for accessing
and analyzing F1 timing and telemetry data.

Data Objects
------------

All data is provided through the following data objects:

    .. autosummary::
       :nosignatures:

       Weekend
       Session
       Laps
       Lap
       Telemetry
       Driver


The :class:`Weekend` object holds some generic information about the race
weekend. Furthermore, :class:`Session` objects for the various sessions of
a weekend can be created from a :class:`Weekend` object.

The :class:`Session` object is mainly used as an entry point for loading
timing data and telemetry data. The :class:`Session` can create a
:class:`Laps` object which contains all timing, track and session status
data for a whole session.

Usually you will be using :func:`get_session` to to get a :class:`Session`
or :class:`Weekend` object.

The :class:`Laps` object holds detailed information about multiples laps.

The :class:`Lap` object holds the same information as :class:`Laps` but only
for one single lap. When selecting a singel lap from a :class:`Laps` object,
an object of type :class:`Lap` will be returned.

Apart from only providing data, the :class:`Laps`, :class:`Lap` and
:class:`Telemetry` objects implement various methods for selecting and
analyzing specific parts of the data.


Functions
---------

.. autosummary::
   :nosignatures:

    get_session
    get_round

"""

from fastf1 import api, ergast
import fastf1
import pandas as pd
import numpy as np
import logging
from functools import cached_property

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', message="Using slow pure-python SequenceMatcher")
    # suppress that warning, it's confusing at best here, we don't need fast sequence matching
    # and the installation (on windows) some effort
    from fuzzywuzzy import fuzz

logging.basicConfig(level=logging.INFO, style='{', format="{module: <8} {levelname: >10} \t{message}")


TESTING_LOOKUP = {'2020': [['2020-02-19', '2020-02-20', '2020-02-21'],
                           ['2020-02-26', '2020-02-27', '2020-02-28']],
                  '2021': [['2021-03-12', '2021-03-13', '2021-03-14']]}

D_LOOKUP = [[44, 'HAM', 'Mercedes'], [77, 'BOT', 'Mercedes'],
            [55, 'SAI', 'Ferrari'], [16, 'LEC', 'Ferrari'],
            [33, 'VER', 'Red Bull'], [11, 'PER', 'Red Bull'],
            [3, 'RIC', 'McLaren'], [4, 'NOR', 'McLaren'],
            [5, 'VET', 'Aston Martin'], [18, 'STR', 'Aston Martin'],
            [14, 'ALO', 'Alpine'], [31, 'OCO', 'Alpine'],
            [22, 'TSU', 'AlphaTauri'], [10, 'GAS', 'AlphaTauri'],
            [47, 'MSC', 'Haas F1 Team'], [9, 'MAZ', 'Haas F1 Team'],
            [7, 'RAI', 'Alfa Romeo'], [99, 'GIO', 'Alfa Romeo'],
            [6, 'LAT', 'Williams'], [63, 'RUS', 'Williams']]


def get_session(year, gp, event=None):
    """Create a :class:`Session` or :class:`Weekend` object based on year,
    event name and session name.
    This function will take care of crafting an object
    corresponding to the requested session.
    If no session is specified, the full weekend is returned.

    Examples:

        Get the second free practice of the first race of 2021::

            get_session(2021, 1, 'FP2')

        Get the qualifying of the 2020 Austrian Grand Prix::

            get_session(2020, 'Austria', 'Q')

        Get the second day of pre-season testing of 2021::

            get_session(2021, 'testing', 2)


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
    """Get event number by year and (partial) event name

    A fuzzy match is performed to find the most likely event for the provided name.

    Args:
        year (int): Year of the event
        match (string): Name of the race or gp (e.g. 'Bahrain')

    Returns:
        The round number. (2019, 'Bahrain') -> 2
    """

    def build_string(d):
        r = len('https://en.wikipedia.org/wiki/')  # TODO what the hell is this
        c, l = d['Circuit'], d['Circuit']['Location']  # noqa: E741 (for now...)
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
    if year == 2020:
        try:
            day = int(day)
            week = 1 if day < 4 else 2
        except:  # noqa: E722 TODO: improve
            raise InvalidSessionError
        week_day = ((day - 1) % 3) + 1
        pre_season_week = f'Pre-Season Test {week}'
        event = f'Practice {week_day}'
    elif year == 2021 and int(day) in (1, 2, 3):
        pre_season_week = 'Pre-Season Test'
        event = f'Practice {day}'
    else:
        raise InvalidSessionError

    return pre_season_week, event


class Telemetry(pd.DataFrame):
    """Multi-channel time series telemetry data

    The object can contain multiple telemetry channels. Multiple telemetry objects with different channels
    can be merged on time. Each telemetry channel is one dataframe column.
    Partial telemetry (e.g. for one lap only) can be obtained through various methods for slicing the data.
    Additionally, methods for adding common computed data channels are available.

    The following telemetry channels existed in the original API data:

        - **Car data**:
            - `Speed` (float): Car speed
            - `RPM` (int): Car RPM
            - `nGear` (int): Car gear number
            - `Throttle` (float): 0-100 Throttle pedal pressure
            - `Brake` (float): 0-100 Brake pedal pressure
            - `DRS` (int): DRS indicator

        - **Position data**:
            - `X` (float): X position
            - `Y` (float): Y position
            - `Z` (float): Z position
            - `Status` (string): Flag - OffTrack/OnTrack

        - **For both of the above**:
            - `Time` (timedelta): Time (0 is start of the data slice)
            - `SessionTime` (timedelta): Time elapsed since the start of the session
            - `Date` (datetime): The full date + time at which this sample was created
            - `Source` (str): Flag indicating how this sample was created:

                - 'car': sample from original api car data
                - 'pos': sample from original api position data
                - 'interpolated': this sample was artificially created; all values are computed/interpolated

                Example:
                    A sample's source is indicated as 'car'. It contains
                    values for speed, rpm and x, y, z coordinates.
                    Originally, this sample (with its timestamp) was received
                    when loading car data.
                    This means that the speed and rpm value are original
                    values as received from the api. The coordinates are
                    interpolated for this sample.

                    All methods of :class:`Telemetry` which resample or
                    interpolate data will preserve and adjust the source flag
                    correctly when modifying data.

        Through merging/slicing it is possible to obtain any combination of telemetry channels!
        The following additional computed data channels can be added:

            - Distance driven between two samples:
              :meth:`add_differential_distance`
            - Distance driven since the first sample:
              :meth:`add_distance`
            - Relative distance driven since the first sample:
              :meth:`add_relative_distance`
            - Distance to driver ahead and car number of said driver:
              :meth:`add_driver_ahead`

        .. note:: See the separate explanation concerning the various definitions of 'Time' for more information on the
          three date and time related channels: :ref:`time-explanation`

    Slicing this class will return :class:`Telemetry` again for slices containing multiple rows. Single rows will be
    returned as :class:`pandas.Series`.

    Args:
        *args (any): passed through to `pandas.DataFrame` superclass
        session (:class:`Session`): Instance of associated session object. Required for full functionality!
        driver (str): Driver number as string. Required for full functionality!
        **kwargs (any): passed through to `pandas.DataFrame` superclass
    """

    TELEMETRY_FREQUENCY = 'original'
    """Defines the frequency used when resampling the telemetry data. Either
    the string ``'original'`` or an integer to specify a frequency in Hz."""

    _CHANNELS = {
        'X': {'type': 'continuous', 'missing': 'quadratic'},
        'Y': {'type': 'continuous', 'missing': 'quadratic'},
        'Z': {'type': 'continuous', 'missing': 'quadratic'},
        'Status': {'type': 'discrete'},
        'Speed': {'type': 'continuous', 'missing': 'linear'},     # linear is often required as quadratic overshoots
        'RPM': {'type': 'continuous', 'missing': 'linear'},       # on sudden changes like sudden pedal application,
        'Throttle': {'type': 'continuous', 'missing': 'linear'},  # braking, ...)
        'Brake': {'type': 'continuous', 'missing': 'linear'},
        'DRS': {'type': 'discrete'},
        'nGear': {'type': 'discrete'},
        'Source': {'type': 'excluded'},  # special case, custom handling
        'Date': {'type': 'excluded'},  # special case, used as the index during resampling
        'Time': {'type': 'excluded'},  # special case, Time/SessionTime recalculated from 'Date'
        'SessionTime': {'type': 'excluded'},
        'Distance': {'type': 'continuous', 'missing': 'quadratic'},
        'RelativeDistance': {'type': 'continuous', 'missing': 'quadratic'},
        'DifferentialDistance': {'type': 'continuous', 'missing': 'quadratic'},
        'DriverAhead': {'type': 'discrete'},
        'DistanceToDriverAhead': {'type': 'continuous', 'missing': 'linear'}
    }
    """Known telemetry channels which are supported by default"""

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
        """For a nicer debugging experience; can view DataFrame through this property in various IDEs"""
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

    def merge(self, *args, **kwargs):
        """Wraps :mod:`pandas.DataFrame.merge` and adds metadata propagation.

        When calling `self.merge` metadata will be propagated from self to the merged dataframe.
        """
        meta = dict()
        for var in self._metadata:
            meta[var] = getattr(self, var)
        ret = super().merge(*args, **kwargs)
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

        .. note:: Self needs to contain a 'SessionTime' column.

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
            end_time = ref_laps['Time']
            start_time = ref_laps['LapStartTime']

        else:
            raise TypeError("Attribute 'ref_laps' needs to be an instance of `Lap` or `Laps`")

        return self.slice_by_time(start_time, end_time, pad, pad_side, interpolate_edges)

    def slice_by_time(self, start_time, end_time, pad=0, pad_side='both', interpolate_edges=False):
        """Slice self to only include data in a specific time frame.

        .. note:: Self needs to contain a 'SessionTime' column. Slicing by time use the 'SessionTime' as its reference.

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
            edges = Telemetry({'SessionTime': (start_time, end_time),
                               'Date': (start_time + self.session.t0_date, end_time + self.session.t0_date)},
                              session=self.session)
            d = self.merge_channels(edges)

        else:
            d = self.copy()  # TODO no copy?

        sel = ((d['SessionTime'] <= end_time) & (d['SessionTime'] >= start_time))
        if np.any(sel):
            data_slice = d.slice_by_mask(sel, pad, pad_side)

            if 'Time' in data_slice.columns:
                # shift time to 0 so laps can overlap
                data_slice.loc[:, 'Time'] = data_slice['SessionTime'] - start_time

            return data_slice
        return Telemetry()

    def merge_channels(self, other, frequency=None):
        """Merge telemetry objects containing different telemetry channels.

        The two objects don't need to have a common time base. The data will be merged, optionally resampled and
        missing values will be interpolated.

        :attr:`Telemetry.TELEMETRY_FREQUENCY` determines if and how the data is resampled. This can be overridden using
        the `frequency` keyword fo this method.

        Merging and resampling:

            If the frequency is 'original', data will not be resampled. The two objects will be merged and all
            timestamps of both objects are kept. Values will be interpolated so that all telemetry channels contain
            valid data for all timestamps. This is the default and recommended option.

            If the frequency is specified as an integer in Hz the data will be merged as before. After that, the merged
            time base will be resampled from the first value on at the specified frequency. Afterwards, the data will
            be interpolated to fit the new time base. This means that usually most if not all values of the data will
            be interpolated values. This is detrimental for overall accuracy.

        Interpolation:

            Missing values after merging will be interpolated for all known telemetry channels using
            :meth:`fill_missing`. Different interpolation methods are used depending on what kind of data the channel
            contains. For example, forward fill is used to interpolated 'nGear' while linear interpolation is used
            for 'RPM' interpolation.

        .. note :: Unknown telemetry channels will be merged but missing values will not be interpolated. This can
            either be done manually or a custom telemetry channel can be added using :meth:`register_new_channel`.

        .. note :: Do not resample data multiple times. Always resample based on the original data
            to preserve accuracy

        Args:
            other (:class:`Telemetry` or :class:`pandas.DataFrame`): Object to be merged with self
            frequency (str or int): Optional frequency to overwrite global preset. (Either string 'original' or integer
                for a frequency in Hz)

        Returns:
            :class:`Telemetry`
        """
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

        ref_date = merged.index[i]

        # data needs to be resampled/interpolated differently, depending on what kind of data it is
        # how to handle which column is defined in self._CHANNELS

        if frequency == 'original':
            # no resampling but still interpolation due to merging
            merged = merged.fill_missing()
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
                    res = merged.loc[:, ch].resample(frq, origin=ref_date).ffill().ffill().bfill()
                    # first ffill is a method of the resampler object and will ONLY ffill values created during
                    # resampling but not already existing NaN values. NaN values already existed because of merging,
                    # therefore call ffill a second time as a method of the returned series to fill these too
                    # only use bfill after ffill to fix first row

                else:
                    continue

                resampled_columns[ch] = res

            res_source = merged.loc[:, 'Source'].resample(frq, origin=ref_date).asfreq().fillna(value='interpolation')
            resampled_columns['Source'] = res_source

            # join resampled columns and make 'Date' a column again
            merged = Telemetry(resampled_columns, session=self.session).reset_index().rename(columns={'index': 'Date'})

            # recalculate the time columns
            merged['SessionTime'] = merged['Date'] - self.session.t0_date
            merged['Time'] = merged['SessionTime'] - merged['SessionTime'].iloc[0]

        # restore data types from before merging
        for col in dtype_map.keys():
            try:
                merged.loc[:, col] = merged.loc[:, col].astype(dtype_map[col])
            except ValueError:
                logging.warning(f"Failed to preserve data type for column '{col}' while merging telemetry.")

        return merged

    def resample_channels(self, rule=None, new_date_ref=None, **kwargs):
        """Resample telemetry data.

        Convenience method for frequency conversion and resampling. Up and down sampling of data is supported.
        'Date' and 'SessionTime' need to exist in the data. 'Date' is used as the main time reference.

        There are two ways to use this method:

            - Usage like :meth:`pandas.DataFrame.resample`: In this case you need to specify the 'rule' for resampling
              and any additional keywords will be passed on to :meth:`pandas.Series.resample` to create a new time
              reference. See the pandas method to see which options are available.

            - using the 'new_date_ref' keyword a :class:`pandas.Series` containing new values for date
              (dtype :class:`pandas.Timestamp`) can be provided. The existing data will be resampled onto this new
              time reference.

        Args:
            rule (optional, str): Resampling rule for :meth:`pandas.Series.resample`
            new_date_ref (optional, pandas.Series): New custom Series of reference dates
            **kwargs (optional, any): Only in combination with 'rule'; additional parameters for
                :meth:`pandas.Series.resample`
        """
        if rule is not None and new_date_ref is not None:
            raise ValueError("You can only specify one of 'rule' or 'new_index'")
        if rule is None and new_date_ref is None:
            raise ValueError("You need to specify either 'rule' or 'new_index'")

        if new_date_ref is None:
            st = pd.Series(index=pd.DatetimeIndex(self['Date']), dtype=int).resample(rule, **kwargs).asfreq()
            new_date_ref = pd.Series(st.index)

        new_tel = Telemetry(session=self.session, driver=self.driver, columns=self.columns)
        new_tel.loc[:, 'Date'] = new_date_ref

        combined_tel = self.merge_channels(Telemetry({'Date': new_date_ref}, session=self.session))
        mask = combined_tel['Date'].isin(new_date_ref)
        new_tel = combined_tel.loc[mask, :]

        return new_tel

    def fill_missing(self):
        """Calculate missing values in self.

        Only known telemetry channels will be interpolated. Unknown channels are skipped and returned unmodified.
        Interpolation will be done according to the default mapping and according to options specified for
        registered custom channels. For example:
        | Linear interpolation will be used for continuous values (Speed, RPM)
        | Forward-fill will be used for discrete values (Gear, DRS, ...)

        See :meth:`register_new_channel` for adding custom channels.
        """
        ret = self.copy()

        for ch in self._CHANNELS.keys():
            if ch not in self.columns:
                continue
            sig_type = self._CHANNELS[ch]['type']
            if sig_type == 'continuous':  # yes, this is necessary to prevent pandas from crashing
                if ret[ch].dtype == 'object':
                    warnings.warn("Interpolation not possible for telemetry "
                                  "channel because dtype is 'object'")
                missing = self._CHANNELS[ch]['missing']
                ret.loc[:, ch] = ret.loc[:, ch]\
                    .interpolate(method=missing, limit_direction='both', fill_value='extrapolate')

            elif sig_type == 'discrete':
                ret.loc[:, ch] = ret.loc[:, ch].ffill().ffill().bfill()
                # first ffill is a method of the resampler object and will ONLY ffill values created during
                # resampling but not already existing NaN values. NaN values already existed because of merging,
                # therefore call ffill a second time as a method of the returned series to fill these too
                # only use bfill after ffill to fix first row

        if 'Source' in ret.columns:
            ret.loc[:, 'Source'] = ret.loc[:, 'Source'].fillna(value='interpolation')

        if 'Date' in self.columns:
            ret['SessionTime'] = ret['Date'] - self.session.t0_date
        elif isinstance(ret.index, pd.DatetimeIndex):
            ret['SessionTime'] = ret.index - self.session.t0_date  # assume index is Date
        ret['Time'] = ret['SessionTime'] - ret['SessionTime'].iloc[0]

        return ret

    @classmethod
    def register_new_channel(cls, name, signal_type, interpolation_method=None):
        """Register a custom telemetry channel.

        Registered telemetry channels are automatically interpolated when merging or resampling data.

        Args:
            name (str): Telemetry channel/column name
            signal_type (str): One of three possible signal types:
                - 'continuous': Speed, RPM, Distance, ...
                - 'discrete': DRS, nGear, status values, ...
                - 'excluded': Data channel will be ignored during resampling
            interpolation_method (optional, str): The interpolation method
                which should be used. Can only be specified and is required
                in combination with ``signal_type='continuous'``. See
                :meth:`pandas.Series.interpolate` for possible interpolation
                methods.
        """
        if signal_type not in ('discrete', 'continuous', 'excluded'):
            raise ValueError(f"Unknown signal type {signal_type}.")
        if signal_type == 'continuous' and interpolation_method is None:
            raise ValueError("signal_type='continuous' requires interpolation_method to be specified.")

        cls._CHANNELS[name] = {'type': signal_type, 'missing': interpolation_method}

    def get_first_non_zero_time_index(self):
        """Return the first index at which the 'Time' value is not zero or NA/NaT"""
        # find first row where time is not zero; usually this is the first row but sometimes.....
        i_arr = np.where((self['Time'] != pd.Timedelta(0)) & ~pd.isna(self['Time']))[0]
        if i_arr.size != 0:
            return np.min(i_arr)
        return None

    def add_differential_distance(self, drop_existing=True):
        """Add column 'DifferentialDistance' to self.

        This column contains the distance driven between subsequent samples.

        Calls :meth:`calculate_differential_distance` and joins the result
        with self.

        Args:
            drop_existing (bool): Drop and recalculate column if it already exists
        Returns:
            :class:`Telemetry`: self joined with new column or self if column exists and `drop_existing` is False.
        """
        if ('DifferentialDistance' in self.columns) and not drop_existing:
            return self

        new_dif_dist = pd.DataFrame(
            {'DifferentialDistance': self.calculate_differential_distance()}
        )
        if 'DifferentialDistance' in self.columns:
            return self.drop(labels='DifferentialDistance', axis=1)\
                .join(new_dif_dist, how='outer')

        return self.join(new_dif_dist, how='outer')

    def add_distance(self, drop_existing=True):
        """Add column 'Distance' to self.

        This column contains the distance driven since the first sample of self in meters.

        The data is produced by integrating the differential distance between subsequent laps.
        You should not apply this function to telemetry of many laps simultaneously to reduce integration error.
        Instead apply it only to single laps or few laps at a time!

        Calls :meth:`integrate_distance` and joins the result with self.

        Args:
            drop_existing (bool): Drop and recalculate column if it already exists
        Returns:
            :class:`Telemetry`: self joined with new column or self if column exists and `drop_existing` is False.
        """
        if ('Distance' in self.columns) and not drop_existing:
            return self

        new_dist = pd.DataFrame({'Distance': self.integrate_distance()})
        if 'Distance' in self.columns:
            return self.drop(labels='Distance', axis=1).join(new_dist, how='outer')

        return self.join(new_dist, how='outer')

    def add_relative_distance(self, drop_existing=True):
        """Add column 'RelativeDistance' to self.

        This column contains the distance driven since the first sample as
        a floating point number where ``0.0`` is the first sample of self
        and ``1.0`` is the last sample.

        This is calculated the same way as 'Distance' (see: :meth:`add_distance`). The same warnings apply.

        Args:
            drop_existing (bool): Drop and recalculate column if it already exists
        Returns:
            :class:`Telemetry`: self joined with new column or self if column exists and `drop_existing` is False.
        """
        if 'RelativeDistance' in self.columns:
            if drop_existing:
                d = self.drop(labels='RelativeDistance', axis=1)
            else:
                return self
        else:
            d = self

        if 'Distance' in d.columns:
            rel_dist = d.loc[:, 'Distance'] / d.loc[:, 'Distance'].iloc[-1]
        else:
            dist = d.integrate_distance()
            rel_dist = dist / dist.iloc[-1]
        return d.join(pd.DataFrame({'RelativeDistance': rel_dist}), how='outer')

    def add_driver_ahead(self, drop_existing=True):
        """Add column 'DriverAhead' and 'DistanceToDriverAhead' to self.

        DriverAhead: Driver number of the driver ahead as string
        DistanceToDriverAhead: Distance to next car ahead in meters

        .. note:: Cars in the pit lane are currently not excluded from the data. They will show up when overtaken on
            pit straight even if they're not technically in front of the car. A fix for this is TBD with other
            improvements.

        This should only be applied to data of single laps or few laps at a time to reduce integration error.
        For longer time spans it should be applied per lap and the laps
        should be merged afterwards.
        If you absolutely need to apply it to a whole session, use the legacy implementation. Note that data of
        the legacy implementation will be considerably less smooth. (see :mod:`fastf1.legacy`)

        Calls :meth:`calculate_driver_ahead` and joins the result with self.

        Args:
            drop_existing (bool): Drop and recalculate column if it already exists
        Returns:
            :class:`Telemetry`: self joined with new column or self if column exists and `drop_existing` is False.
        """
        if 'DriverAhead' in self.columns and 'DistanceToDriverAhead' in self.columns:
            if drop_existing:
                d = self.drop(labels='DriverAhead', axis=1)\
                    .drop(labels='DistanceToDriverAhead', axis=1)
            else:
                return self
        else:
            d = self

        drv_ahead, dist = self.calculate_driver_ahead()
        return d.join(pd.DataFrame({'DriverAhead': drv_ahead,
                                    'DistanceToDriverAhead': dist},
                                   index=d.index), how='outer')

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

        Driver ahead: Driver number of the driver ahead as string
        Distance to driver ahead: Distance to the car ahead in meters

        .. note:: This gives a smoother/cleaner result than the legacy implementation but WILL introduce
            integration error when used over long distances (more than one or two laps may sometimes be considered
            a long distance). If in doubt, do sanity checks (against the legacy version or in another way).

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
            lap_n_after = drv_laps_after['LapNumber'].iloc[0] \
                if not drv_laps_after.empty \
                else max(drv_laps['LapNumber'])
            relevant_laps = drv_laps[(drv_laps['LapNumber'] >= lap_n_before) & (drv_laps['LapNumber'] <= lap_n_after)]

            if relevant_laps.empty:
                continue

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


class Weekend:
    """Object for accessing weekend specific data.

    If you want to handle multiple sessions from the same race event you can use a :class:Weekend instance.

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
            logging.warning("The Ergast API is not supported for testing")
            if year == 2020:
                date = TESTING_LOOKUP[str(year)][int(gp[-1]) - 1][-1]
            elif year == 2021:
                date = TESTING_LOOKUP[str(year)][0][-1]
            else:
                raise InvalidSessionError
            self.data = {'raceName': gp, 'date': date}
        else:
            try:
                self.data = ergast.fetch_weekend(self.year, self.gp)
            except Exception as exception:
                logging.critical("Failed to load critical data from Ergast!\n\n Cannot determine the date and name "
                                 "of the event. Cannot proceed!\n")  # TODO some backup strategy for this
                logging.critical(str(exception))
                logging.debug("", exc_info=exception)
                exit()

    def get_practice(self, number):
        """Return the specified practice session.
        Args:
            number: 1, 2 or 3 - Free practice session number
        Returns:
            :class:`Session` instance
        """
        return Session(self, f'Practice {number}')

    def get_quali(self):
        """Return the qualifying session.

        Returns:
            :class:`Session` instance
        """
        return Session(self, 'Qualifying')

    def get_race(self):
        """Return the race session.

        Returns:
            :class:`Session` instance
        """
        return Session(self, 'Race')

    def is_testing(self):
        """Indicates whether this 'weekend' is a testing event. (In which case is usually is not an actual weekend.)

        Returns:
            bool
        """
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
    """Object for accessing session specific data.

    The session class will usually be your starting point. This object will have various information about
    the session such as `name` and `date`. To get the session's laps use :meth:`Session.load_laps`.

    .. note:: For full functionality lap and telemetry data need to be loaded.
    """
    def __init__(self, weekend, session_name):
        self.weekend = weekend
        """:class:`.Weekend`: Reference to the associated weekend object."""
        self.name = session_name
        """str: Name of this session, for example 'Qualifying', 'Race', 'FP1', ..."""
        self.date = self._get_session_date()
        """pandas.Datetime: Date at which this session took place."""
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
                logging.warning("Ergast API lookup failed. The session is very recent and not yet available or does "
                                "not exist.")
                self._create_empty_ergast_result()
            except Exception as exception:
                logging.error("Failed to load data from Ergast API!")
                logging.exception(exception)
                self._create_empty_ergast_result()

        else:
            self._create_empty_ergast_result()

        self.laps = Laps(session=self)
        """Instance of :class:`Laps` containing all laps from all drivers
        in this session."""
        self.t0_date = None
        # can only be set when/if telemetry has been downloaded
        """pandas.Datetime: Date timestamp which marks the beginning of the
        data stream."""
        self.session_start_time = None
        """pandas.Timedelta: Session time at which the session was started."""

        self.car_data = dict()
        """Dictionary of car telemetry (Speed, RPM, etc.) as received from
        the api by car number (where car number is a string and the telemetry
        is an instance of :class:`Telemetry`)"""
        self.pos_data = dict()
        """Dictionary of car position data as received from the api by car
        number (where car number is a string and the telemetry
        is an instance of :class:`Telemetry`)"""
        self.weather_data = pd.DataFrame()
        """Dataframe containing weather data for this session as received
        from the api. See :func:`fastf1.api.weather_data` for available data
        channels. Each data channel is one row of the dataframe."""

        self.drivers = list()
        """List of all drivers that took part in this session; contains driver numbers as string. Drivers for which
        lap or telemetry data is missing completely are not listed!"""

    def _create_empty_ergast_result(self):
        """In case Ergast has no data, this function creates an empty result to emulate the structure."""
        self.results = []
        for driver in D_LOOKUP:
            self.results.append({
                'number': str(driver[0]),
                'Driver': {'code': driver[1]},
                'Constructor': {'name': driver[2]}})

    def _get_session_date(self):
        """Session date formatted as '%Y-%m-%d' (e.g. '2019-03-12')"""
        if self.weekend.is_testing():
            if (year := str(self.weekend.year)) == '2020':
                week_index = int(self.weekend.name[-1]) - 1
                day_index = int(self.name[-1]) - 1
                date = TESTING_LOOKUP[year][week_index][day_index]
            elif year == '2021':
                day_index = int(self.name[-1]) - 1
                date = TESTING_LOOKUP[year][0][day_index]

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

    def load_laps(self, with_telemetry=False, livedata=None):
        """Load lap timing information and telemetry data.

        This method creates a :class:`Laps` instance (:attr:`Session.laps`) which subclasses :class:`pandas.DataFrame`
        and contains information on a per lap basis. (The dataframe is additionally returned by this method.)

        The returned :class:`Laps` instance can be used just like a pandas DataFrame but offers some
        additional functionality.

        Downloading and parsing of the data takes a considerable amount of time. Therefore, it is highly recommended
        to enable caching so that most of the data processing needs to be done only once.

        .. note:: Absolute time is not super accurate. The moment a lap
            is logged is not always the same and there will be some
            jitter. At the moment lap time reference is synchronised
            on the sector time triggered with lowest latency.
            Expect an error of around ±10m when overlapping telemetry
            data of different laps.

        Args:
            with_telemetry (bool): Load telemetry data also.
                (Same as calling :meth:`Session.load_telemetry` manually)
            livedata (:class:`fastf1.livetiming.data.LiveTimingData`, optional) :
                instead of requesting the data from the api, locally saved
                livetiming data can be used as a data source

        Returns:
            instance of :class:`Laps`
        """
        logging.info(f"Loading laps for {self.weekend.name} - {self.name}"
                     f" [v{fastf1.__version__}]")

        """From `timing_data` and `timing_app_data` a summary table is
        built. Lap by lap, information on tyre, sectors and times are
        organised in an accessible pandas data frame.

        Returns:
            pandas dataframe

        """
        data, _ = api.timing_data(self.api_path, livedata=livedata)
        app_data = api.timing_app_data(self.api_path, livedata=livedata)
        # Now we do some manipulation to make it beautiful
        logging.info("Processing timing data...")

        # Matching data and app_data. Not super straightforward
        # Sometimes a car may enter the pit without changing tyres, so
        # new compound is associated with the help of logging time.
        useful = app_data[['Driver', 'Time', 'Compound', 'TotalLaps', 'New']]
        useful = useful[~useful['Compound'].isnull()]

        self.drivers = list(data['Driver'].unique())

        if not self.drivers:
            raise NoLapDataError

        # check when a session was started; for a race this indicates the start of the race
        session_status = api.session_status_data(self.api_path,
                                                 livedata=livedata)
        for i in range(len(session_status['Status'])):
            if session_status['Status'][i] == 'Started':
                self.session_start_time = session_status['Time'][i]
                break

        for i, driver in enumerate(self.drivers):
            d1 = data[data['Driver'] == driver]
            d2 = useful[useful['Driver'] == driver]

            if len(d2) == 0:
                continue  # no data for this driver; skip

            result = pd.merge_asof(d1, d2, on='Time', by='Driver')

            # calculate lap start time by setting it to the 'Time' of the previous lap
            laps_start_time = list(result['Time'])[:-1]
            if self.name == 'Race':
                # assumption that the first lap started when the session was started can only be made for the race
                laps_start_time.insert(0, self.session_start_time)
            else:
                laps_start_time.insert(0, pd.NaT)
            result.loc[:, 'LapStartTime'] = pd.Series(laps_start_time, dtype='timedelta64[ns]')

            for npit in result['NumberOfPitStops'].unique():
                sel = result['NumberOfPitStops'] == npit
                result.loc[sel, 'TotalLaps'] += np.arange(0, sel.sum()) + 1
            # check if df is defined already before concat (vars is a builtin function)
            df = result if 'df' not in vars() else pd.concat([df, result], sort=False)  # noqa: F821

        laps = df.reset_index(drop=True)  # noqa: F821
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
        # add track status data
        ts_data = api.track_status_data(self.api_path, livedata=livedata)
        laps['TrackStatus'] = '1'

        def applicator(new_status, current_status):
            if current_status == '1':
                return new_status
            elif new_status not in current_status:
                return current_status + new_status
            else:
                return current_status

        if len(ts_data['Time']) > 0:
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
            self.load_telemetry(livedata=livedata)

        # load weather data; this data is not crucial, just log a warning
        # in case of an error
        try:
            self._load_weather_data(livedata=livedata)
        except (api.SessionNotAvailableError, ValueError):
            logging.warning("Failed to load weather data!")

        logging.info(f"Loaded data for {len(self.drivers)} drivers: {self.drivers}")

        return self.laps

    def _check_lap_accuracy(self):
        """Accuracy validation; simples yes/no validation
        Currently only relies on provided information which can't catch all problems"""
        # TODO: check for outliers in lap start position
        # self.laps['IsAccurate'] = False  # default should be not accurate
        for drv in self.drivers:
            is_accurate = list()
            prev_lap = None
            integrity_errors = 0
            for _, lap in self.laps[self.laps['DriverNumber'] == drv].iterrows():
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

    def _load_weather_data(self, livedata=None):
        """Get weather data from the api and format it into a dataframe"""
        weather_data = api.weather_data(self.api_path, livedata=livedata)
        weather_df = pd.DataFrame(weather_data)
        self.weather_data = weather_df

    def load_telemetry(self, livedata=None):
        """Load telemetry data from the API.

        This method can only be called after :meth:`load_laps` has been
        called. You will usually just want to call :meth:`load_laps` with
        the optional ``with_telemetry=True`` argument instead of calling this
        method separately. The result will be the same.

        The raw data is divided into car data (Speed, RPM, ...) and position data (coordinates, on/off track). For each
        of the two types an instance of :class:`Telemetry` is created per driver. The properties
        :attr:`Session.car_data` and :attr:`Session.pos_data` are dictionaries which hold the the `Telemetry` objects
        keyed by driver number.

        The telemetry data can either be accessed through the above mentioned attributes or conveniently on a per
        lap basis through :class:`Lap` and :class:`Laps`. See :class:`Telemetry` on how to work with the telemetry
        data.

        Note that this method additionally calculates :attr:`Session.t0_date` and adds a `LapStartDate` column to
        :attr:`Session.laps`.

        Args:
            livedata (:class:`fastf1.livetiming.data.LiveTimingData`, optional) :
                instead of requesting the data from the api, locally saved
                livetiming data can be used as a data source
        """
        car_data = api.car_data(self.api_path, livedata=livedata)
        pos_data = api.position_data(self.api_path, livedata=livedata)

        self.drivers = list(set(self.drivers).intersection(set(car_data.keys())).intersection(set(pos_data.keys())))
        # self.drivers should only contain drivers which exist in all parts of the data

        self._calculate_t0_date(car_data, pos_data)

        for drv in self.drivers:
            # drop and recalculate time stamps based on 'Date', because 'Date' has a higher resolution
            drv_car = Telemetry(car_data[drv].drop(labels='Time', axis=1),
                                session=self, driver=drv)
            drv_pos = Telemetry(pos_data[drv].drop(labels='Time', axis=1),
                                session=self, driver=drv)

            drv_car['Date'] = drv_car['Date'].round('ms')
            drv_pos['Date'] = drv_pos['Date'].round('ms')

            drv_car['Time'] = drv_car['Date'] - self.t0_date  # create proper continuous timestamps
            drv_pos['Time'] = drv_pos['Date'] - self.t0_date
            drv_car['SessionTime'] = drv_car['Time']
            drv_pos['SessionTime'] = drv_pos['Time']

            self.car_data[drv] = drv_car
            self.pos_data[drv] = drv_pos

        self.laps['LapStartDate'] = self.laps['LapStartTime'] + self.t0_date

    def get_driver(self, identifier):
        """
        Get a driver object which contains additional information about a driver.

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

    def _calculate_t0_date(self, car_data, pos_data):
        """Calculate the date timestamp at which data for this session is starting.

        This does not mark the start of a race (or other sessions). This marks the start of the data which is sometimes
        far before.

        This function sets :attr:`self.t0_date` which is an internally required offset for some calculations.

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

        self.t0_date = date_offset.round('ms')


class Laps(pd.DataFrame):
    """Object for accessing lap (timing) data of multiple laps.

    Args:
        *args (any): passed through to :class:`pandas.DataFrame` super class
        session (:class:`Session`): instance of session class; required for
          full functionality
        **kwargs (any): passed through to :class:`pandas.DataFrame`
          super class

    This class allows for easily picking specific laps from all laps in a session. It implements some additional
    functionality on top off the usual `pandas.DataFrame` functionality. Among others, the laps' associated telemetry
    data can be accessed.

    If for example you want to get the fastest lap of Bottas you can narrow it down like this::

        import fastf1 as ff1

        laps = ff1.get_session(2019, 'Bahrain', 'Q').load_laps()
        best_bottas = laps.pick_driver('BOT').pick_fastest()

        print(best_bottas['LapTime'])
        # Timedelta('0 days 00:01:28.256000')

    Slicing this class will return :class:`Laps` again for slices containing multiple rows. Single rows will be
    returned as :class:`Lap`.

    The following information is available per lap (one DataFrame column for each):
        - **Time** (pandas.Timedelta): Session time when the lap time was set (end of lap)
        - **Driver** (string): Three letter driver identifier
        - **DriverNumber** (str): Driver number
        - **LapTime** (pandas.Timedelta): Recorded lap time.
          Officially deleted lap times will *not* be deleted here.
          Deleting laps is currently not supported.
        - **LapNumber** (int): Recorded lap number
        - **Stint** (int): Stint number
        - **PitOutTime** (pandas.Timedelta): Session time when car exited the pit
        - **PitInTime** (pandas.Timedelta): Session time when car entered the pit
        - **Sector1Time** (pandas.Timedelta): Sector 1 recorded time
        - **Sector2Time** (pandas.Timedelta): Sector 2 recorded time
        - **Sector3Time** (pandas.Timedelta): Sector 3 recorded time
        - **Sector1SessionTime** (pandas.Timedelta): Session time when the Sector 1 time was set
        - **Sector2SessionTime** (pandas.Timedelta): Session time when the Sector 2 time was set
        - **Sector3SessionTime** (pandas.Timedelta): Session time when the Sector 3 time was set
        - **SpeedI1** (float): Speedtrap sector 1
        - **SpeedI2** (float): Speedtrap sector 2
        - **SpeedFL** (float): Speedtrap at finish line
        - **SpeedST** (float): Speedtrap on longest straight (Not sure)
        - **Compound** (str): Tyre compound name: SOFT, MEDIUM ..
        - **TyreLife** (float): Laps driven on this tire (includes laps in other sessions for used sets of tires)
        - **FreshTyre** (bool): Tyre had TyreLife=0 at stint start, i.e. was a new tire
        - **Team** (str): Team name
        - **LapStartTime** (pandas.Timedelta): Session time at the start of the lap
        - **LapStartDate** (pandas.Timestamp): Timestamp at the start of the lap
        - **TrackStatus** (str): A string that contains track status numbers for all track status that occurred
          during this lap. The meaning of the track status numbers is explained in
          :func:`fastf1.api.track_status_data`. (Currently, track status data is only implemented per lap.
          If a finer resolution is desired, you need to directly use the data returned by
          :func:`fastf1.api.track_status_data`)  # TODO updated when implemented
        - **IsAccurate** (bool): If True, the lap has passed a basic accuracy check for timing data.
          This does not guarantee accuracy but laps marked as inaccurate need to be handled with
          caution. They might contain errors which can not be spotted easily.
          Laps need to satisfy the following criteria to be marked
          as accurate:

            - not an inlap or outlap
            - set under green or yellow flag (the api sometimes has issues
              with data from SC/VSC laps)
            - is not the first lap after a safety car period
              (issues with SC/VSC might still apear on the first lap
              after it has ended)
            - has a value for lap time and all sector times
            - the sum of the sector times matches the lap time
              (will be additionally logged as integrity error if not)
    """

    _metadata = ['session']

    QUICKLAP_THRESHOLD = 1.07
    """Used to determine 'quick' laps. Defaults to the 107% rule."""

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
        """For a nicer debugging experience; can now view as
        dataframe in various IDEs"""
        return pd.DataFrame(self)

    @cached_property
    def telemetry(self):
        """Telemetry data for all laps in `self`

        This is a cached (!) property for :meth:`get_telemetry`. It will return the same value as `get_telemetry`
        but cache the result so that the involved processing is only done once.

        This is mainly provided for convenience and backwards compatibility.

        See :meth:`get_telemetry` for more information.

        .. note:: Telemetry can only be returned if `self` contains laps of one driver only.

        Returns:
            instance of :class:`Telemetry`"""
        return self.get_telemetry()

    def get_telemetry(self):
        """Telemetry data for all laps in `self`

        Telemetry data is the result of merging the returned data from :meth:`get_car_data` and :meth:`get_pos_data`.
        This means that telemetry data at least partially contains interpolated values! Telemetry data additionally
        already has computed channels added (e.g. Distance).

        This method is provided for convenience and compatibility reasons. But using it does usually not produce
        the most accurate possible result.
        It is recommended to use :meth:`get_car_data` or :meth:`get_pos_data` when possible. This is also faster if
        merging of car and position data is not necessary and if not all computed channels are needed.

        Resampling during merging is done according to the frequency set by :attr:`TELEMETRY_FREQUENCY`.

        .. note:: Telemetry can only be returned if `self` contains laps of one driver only.

        Returns:
            instance of :class:`Telemetry`
        """
        pos_data = self.get_pos_data(pad=1, pad_side='both')
        car_data = self.get_car_data(pad=1, pad_side='both')

        # calculate driver ahead from from data without padding to
        # prevent out of bounds errors
        drv_ahead = car_data.iloc[1:-1].add_driver_ahead() \
            .loc[:, ('DriverAhead', 'DistanceToDriverAhead',
                     'Date', 'Time', 'SessionTime')]

        car_data = car_data.add_distance().add_relative_distance()
        car_data = car_data.merge_channels(drv_ahead)
        merged = pos_data.merge_channels(car_data)
        return merged.slice_by_lap(self, interpolate_edges=True)

    def get_car_data(self, **kwargs):
        """Car data for all laps in `self`

        Slices the car data in :attr:`Session.car_data` using this set of laps and returns the result.

        The data returned by this method does not contain computed telemetry channels. The can be added by calling the
        appropriate `add_*()` method on the returned telemetry object..

        .. note:: Car data can only be returned if `self` contains laps of one driver only.

        Args:
            **kwargs: Keyword arguments are passed to :meth:`Telemetry.slice_by_lap`

        Returns:
            instance of :class:`Telemetry`
        """
        drv_num = self['DriverNumber'].unique()
        if len(drv_num) == 0:
            raise ValueError("Cannot slice telemetry because self contains no driver number!")
        if len(drv_num) > 1:
            raise ValueError("Cannot slice telemetry because self contains Laps of multiple drivers!")
        drv_num = drv_num[0]
        car_data = self.session.car_data[drv_num].slice_by_lap(self, **kwargs).reset_index(drop=True)
        return car_data

    def get_pos_data(self, **kwargs):
        """Pos data for all laps in `self`

        Slices the position data in :attr:`Session.pos_data` using this set of laps and returns the result.

        .. note:: Position data can only be returned if `self` contains laps of one driver only.

        Args:
            **kwargs: Keyword arguments are passed to :meth:`Telemetry.slice_by_lap`

        Returns:
            instance of :class:`Telemetry`
        """
        drv_num = self['DriverNumber'].unique()
        if len(drv_num) == 0:
            raise ValueError("Cannot slice telemetry because self contains no driver number!")
        if len(drv_num) > 1:
            raise ValueError("Cannot slice telemetry because self contains Laps of multiple drivers!")
        drv_num = drv_num[0]
        pos_data = self.session.pos_data[drv_num].slice_by_lap(self, **kwargs).reset_index(drop=True)
        return pos_data

    def get_weather_data(self):
        """Return weather data for each lap in self.

        Weather data is updated once per minute. This means that there are
        usually one or two data points per lap. This function will always
        return only one data point per lap:

           - The first value within the duration of a lap

        or

            - the last known value before the end of the lap if there are
              no values within the duration of a lap

        See :func:`fastf1.api.weather_data` for available data
        channels.

        If you wish to have more control over the data, you can access the
        weather data directly in :attr:`Session.weather_data`.

        Returns:
            pandas.DataFrame

        Example::

            >>> weather_data = laps.get_weather_data()
            >>> print(weather_data)
                                 Time AirTemp Humidity  ... TrackTemp WindDirection WindSpeed
            16 0 days 00:16:20.305000    21.9     55.8  ...      35.5           119       0.2
            17 0 days 00:17:20.301000    22.0     54.6  ...      35.9           113       0.1
            ..                    ...     ...      ...  ...       ...           ...       ...
            75 0 days 01:15:20.525000    22.3     53.5  ...      36.9            76       0.6
            76 0 days 01:16:20.534000    22.2     53.1  ...      37.1            81       0.6
            [453 rows x 25 columns]

        Joining weather data with lap timing data::

            >>> # prepare the data for joining
            >>> laps = laps.reset_index(drop=True)
            >>> weather_data = weather_data.reset_index(drop=True)

            >>> # exclude the 'Time' column from weather data when joining
            >>> joined = pandas.concat([laps, weather_data.loc[:, ~(weather_data.columns == 'Time')]], axis=1)
            >>> print(joined)
                                  Time DriverNumber  ... WindDirection  WindSpeed
            0   0 days 00:16:58.221000            3  ...           119        0.2
            1   0 days 00:19:32.354000            3  ...           113        0.1
            ..                     ...          ...  ...           ...        ...
            451 0 days 01:16:01.722000           99  ...            76        0.6
            452 0 days 01:17:35.072000           99  ...            81        0.6
            [453 rows x 32 columns]
        """
        wd = [lap.get_weather_data() for _, lap in self.iterrows()]
        if wd:
            return pd.concat(wd, axis=1).T
        else:
            return pd.DataFrame(columns=self.session.weather_data.columns)

    def pick_driver(self, identifier):
        """Return all laps of a specific driver in self based on the driver's
        three letters identifier or based on the driver number ::

            perez_laps = ff1.pick_driver('PER')
            bottas_laps = ff1.pick_driver(77)
            kimi_laps = ff1.pick_driver('RAI')

        Args:
            identifier (str or int): Driver abbreviation or number

        Returns:
            instance of :class:`Laps`
        """
        identifier = str(identifier)
        if identifier.isdigit():
            return self[self['DriverNumber'] == identifier]
        else:
            return self[self['Driver'] == identifier]

    def pick_drivers(self, identifiers):
        """Return all laps of the specified drivers in self based on the
        drivers' three letters identifier or based on the driver number. This
        is the same as :meth:`Laps.pick_driver` but for multiple drivers
        at once. ::

            some_drivers_laps = ff1.pick_drivers([5, 'BOT', 7])

        Args:
            identifiers (iterable): Multiple driver abbreviations or driver numbers (can be mixed)

        Returns:
            instance of :class:`Laps`
        """
        names = [n for n in identifiers if not str(n).isdigit()]
        numbers = [str(n) for n in identifiers if str(n).isdigit()]
        drv, num = self['Driver'], self['DriverNumber']

        return self[(drv.isin(names) | num.isin(numbers))]

    def pick_team(self, name):
        """Return all laps of a specific team in self based on the
        team's name ::

            mercedes = ff1.pick_team('Mercedes')
            alfa_romeo = ff1.pick_team('Alfa Romeo')

        Have a look to :attr:`fastf1.plotting.TEAM_COLORS` for a quick reference on team names.

        Args:
            name (str): Team name

        Returns:
            instance of :class:`Laps`
        """
        return self[self['Team'] == name]

    def pick_teams(self, names):
        """Return all laps of the specified teams in self based on the teams'
        name. This is the same as :meth:`Laps.pick_team` but for multiple
        teams at once. ::

            some_drivers_laps = ff1.pick_teams(['Mercedes', 'Williams'])

        Args:
            names (iterable): Multiple team names

        Returns:
            instance of :class:`Laps`
        """
        return self[self['Team'].isin(names)]

    def pick_fastest(self):
        """Return the lap with the fastest lap time.

        .. note:: Officially deleted laps (e.g. driver was outside of
          the track limits) will still show up as normal laps here.
          The fastest lap returned by this method can therefore be one
          that was officially deleted after it was set. You need to manually
          ensure that this is not the case by comparing lap times with a
          session's official results or some other source of data.

        Returns:
            instance of :class:`Lap`
        """
        lap = self.loc[self['LapTime'].idxmin()]
        if isinstance(lap, pd.DataFrame):
            # More laps, same time
            lap = lap.iloc[0]  # take first clocked

        return lap

    def pick_quicklaps(self, threshold=None):
        """Return all laps with `LapTime` faster than a certain limit. By
        default the threshold is 107% of the best `LapTime` of all laps
        in self.

        Args:
            threshold (optional, float): custom threshold coefficent
                (e.g. 1.05 for 105%)

        Returns:
            instance of :class:`Laps`
        """
        if threshold is None:
            threshold = Laps.QUICKLAP_THRESHOLD
        time_threshold = self['LapTime'].min() * threshold

        return self[self['LapTime'] < time_threshold]

    def pick_tyre(self, compound):
        """Return all laps in self which were done on a specific compound.

        Args:
            compound (string): may be "SOFT", "MEDIUM", "HARD", "INTERMEDIATE" or "WET"

        Returns:
            instance of :class:`Laps`
        """
        return self[self['Compound'] == compound]

    def pick_track_status(self, status, how='equals'):
        """Return all laps set under a specific track status.

        Args:
            status (str): The track status as a string, e.g. '1'
            how (str): one of 'equals'/'contains'
                For example, if how='equals', status='2' will only match '2'.
                If how='contains', status='2' will also match '267' and similar
        Returns:
            instance of :class:`Laps`
        """
        if how == 'equals':
            return self[self['TrackStatus'] == status]
        elif how == 'contains':
            return self[self['TrackStatus'].str.contains(status, regex=False)]
        else:
            raise ValueError(f"Invalid value '{how}' for kwarg 'how'")

    def pick_wo_box(self):
        """Return all laps which are NOT in laps or out laps.

        Returns:
            instance of :class:`Laps`
        """
        return self[pd.isnull(self['PitInTime']) & pd.isnull(self['PitOutTime'])]

    def pick_accurate(self):
        """Return all laps which pass the accuracy validation check
        (lap['IsAccurate'] is True).

        Returns:
            instance of :class:`Laps`
        """
        return self[self['IsAccurate']]

    def iterlaps(self, require=()):
        """Iterator for iterating over all laps in self.

        This method wraps :meth:`pandas.DataFrame.iterrows`.
        It additionally provides the `require` keyword argument.

        Args:
             require (optional, iterable): Require is a list of column/telemetry channel names. All names listed in
               `require` must exist in the data and have a non-null value (tested with :func:`pandas.is_null`). The
               iterator only yields laps for which this is true. If require is left empty, the iterator will yield
               all laps.
        Yields:
            (index, instance of :class:`Lap`)
        """
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
    """Object for accessing lap (timing) data of a single lap.

    This class wraps :class:`pandas.Series`. It provides extra functionality for accessing a lap's associated
    telemetry data.
    """
    _metadata = ['session']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _constructor(self):
        return Lap

    @cached_property
    def telemetry(self):
        """Telemetry data for this lap

        This is a cached (!) property for :meth:`get_telemetry`. It will return the same value as `get_telemetry`
        but cache the result so that the involved processing is only done once.

        This is mainly provided for convenience and backwards compatibility.

        See :meth:`get_telemetry` for more information.

        Returns:
            instance of :class:`Telemetry`"""
        return self.get_telemetry()

    def get_telemetry(self):
        """Telemetry data for this lap

        Telemetry data is the result of merging the returned data from :meth:`get_car_data` and :meth:`get_pos_data`.
        This means that telemetry data at least partially contains interpolated values! Telemetry data additionally
        already has computed channels added (e.g. Distance).

        This method is provided for convenience and compatibility reasons. But using it does usually not produce
        the most accurate possible result.
        It is recommended to use :meth:`get_car_data` or :meth:`get_pos_data` when possible. This is also faster if
        merging of car and position data is not necessary and if not all computed channels are needed.

        Resampling during merging is done according to the frequency set by :attr:`TELEMETRY_FREQUENCY`.

        Returns:
            instance of :class:`Telemetry`
        """
        pos_data = self.get_pos_data(pad=1, pad_side='both')
        car_data = self.get_car_data(pad=1, pad_side='both')

        # calculate driver ahead from from data without padding to
        # prevent out of bounds errors
        drv_ahead = car_data.iloc[1:-1].add_driver_ahead() \
            .loc[:, ('DriverAhead', 'DistanceToDriverAhead',
                     'Date', 'Time', 'SessionTime')]

        car_data = car_data.add_distance().add_relative_distance()
        car_data = car_data.merge_channels(drv_ahead)
        merged = pos_data.merge_channels(car_data)
        return merged.slice_by_lap(self, interpolate_edges=True)

    def get_car_data(self, **kwargs):
        """Car data for this lap

        Slices the car data in :attr:`Session.car_data` using this lap and returns the result.

        The data returned by this method does not contain computed telemetry channels. The can be added by calling the
        appropriate `add_*()` method on the returned telemetry object.

        Args:
            **kwargs: Keyword arguments are passed to :meth:`Telemetry.slice_by_lap`

        Returns:
            instance of :class:`Telemetry`
        """
        car_data = self.session.car_data[self['DriverNumber']].slice_by_lap(self, **kwargs).reset_index(drop=True)
        return car_data

    def get_pos_data(self, **kwargs):
        """Pos data for all laps in `self`

        Slices the position data in :attr:`Session.pos_data` using this lap and returns the result.

        Args:
            **kwargs: Keyword arguments are passed to :meth:`Telemetry.slice_by_lap`

        Returns:
            instance of :class:`Telemetry`
        """
        pos_data = self.session.pos_data[self['DriverNumber']].slice_by_lap(self, **kwargs).reset_index(drop=True)
        return pos_data

    def get_weather_data(self):
        """Return weather data for this lap.

        Weather data is updated once per minute. This means that there are
        usually one or two data points per lap. This function will always
        return only one data point:

            - The first value within the duration of a lap

        or

            - the last known value before the end of the lap if there are
              no values within the duration of a lap

        See :func:`fastf1.api.weather_data` for available data
        channels.

        If you wish to have more control over the data, you can access the
        weather data directly in :attr:`Session.weather_data`.

        Returns:
            pandas.Series

        Example::

            >>> lap = laps.pick_fastest()
            >>> lap['LapStartTime']
            Timedelta('0 days 01:10:29.730000')
            >>> lap.get_weather_data()
            Time             0 days 01:11:20.525000
            AirTemp                            22.1
            Humidity                           53.5
            Pressure                         1003.5
            Rainfall                           True
            TrackTemp                          36.9
            WindDirection                        76
            WindSpeed                           0.6
            Name: 71, dtype: object
        """
        # get first value within the duration of the lap
        mask = ((self.session.weather_data['Time'] >= self['LapStartTime']) &
                (self.session.weather_data['Time'] <= self['Time']))
        samples = self.session.weather_data[mask]
        if not samples.empty:
            return samples.iloc[0]

        # fallback: get last value before the lap ended
        mask = self.session.weather_data['Time'] <= self['Time']
        samples = self.session.weather_data[mask]
        if not samples.empty:
            return samples.iloc[-1]

        # no data: return an empty Series with the correct index names
        return pd.Series(index=self.session.weather_data.columns)


class Driver:
    """Driver class that provides some information on drivers and their finishing results.

    see also :meth:`Session.get_driver`

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


class NoLapDataError(Exception):
    """Raised if the API request does not fail but there is no usable data after processing the result."""
    def __init__(self, *args):
        super(NoLapDataError, self).__init__("Failed to load session because the API did not provide any usable data.")


class InvalidSessionError(Exception):
    """Raised if no session for the specified event name, type and year
    can be found."""

    def __init__(self, *args):
        super(InvalidSessionError, self).__init__(
            "No matching session can be found."
        )
