"""
Timing and Telemetry Data - :mod:`fastf1.core`
==============================================

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
       SessionResults
       DriverResult


The :class:`Session` object is mainly used as an entry point for loading
timing data and telemetry data. The :class:`Session` can create a
:class:`Laps` object which contains all timing, track and session status
data for a whole session.

Usually you will be using :func:`get_session` to get a :class:`Session`
object.

The :class:`Laps` object holds detailed information about multiples laps.

The :class:`Lap` object holds the same information as :class:`Laps` but only
for one single lap. When selecting a single lap from a :class:`Laps` object,
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
import collections
from functools import cached_property
import logging
import warnings

import numpy as np
import pandas as pd

import fastf1
from fastf1 import api, ergast
from fastf1.utils import recursive_dict_get, to_timedelta

logging.basicConfig(level=logging.INFO, style='{',
                    format="{module: <8} {levelname: >10} \t{message}")


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


def get_session(*args, **kwargs):
    """
    .. deprecated:: 2.2
        replaced by :func:`fastf1.get_session`
    """
    # TODO remove
    warnings.warn("`fastf1.core.get_session` has been deprecated and will be"
                  "removed in a future version.\n"
                  "Use `fastf1.get_session` instead.", FutureWarning)
    from fastf1 import events
    return events.get_session(*args, **kwargs)


def get_round(year, match):
    """
    .. deprecated:: 2.2
        will be removed without replacement;
        Use :func:`fastf1.get_event` instead to get an
        :class:`~fastf1.events.Event` object which provides
        information including the round number for the event.
    """
    # TODO remove
    warnings.warn("_func:`fastf1.core.get_round` has been deprecated and will "
                  "be removed without replacement in a future version.\n"
                  "Use :func:`fastf1.get_event` instead to get an "
                  ":class:`~fastf1.events.Event` object which provides "
                  "information including the round number for the event.",
                  FutureWarning)
    from fastf1 import events
    event = events.get_event(year, match)
    return event.RoundNumber


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
            - `DRS` (int): DRS indicator (See :meth:`car_data` for more info)

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
        'Speed': {'type': 'continuous', 'missing': 'linear'},  # linear is often required as quadratic overshoots
        'RPM': {'type': 'continuous', 'missing': 'linear'},  # on sudden changes like sudden pedal application)
        'Throttle': {'type': 'continuous', 'missing': 'linear'},
        'Brake': {'type': 'discrete'},
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

    def __init__(self, *args, session=None, driver=None,
                 drop_unknown_channels=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = session
        self.driver = driver

        if drop_unknown_channels:
            unknown = set(self.columns).difference(self._CHANNELS.keys())
            super().drop(columns=unknown, inplace=True)
            if unknown:
                logging.warning(
                    f"The following unknown telemetry channels have "
                    f"been dropped when creating a Telemetry object: "
                    f"{unknown} (driver: {self.driver})"
                )

    @property
    def _constructor(self):
        def _new(*args, **kwargs):
            return Telemetry(*args, **kwargs).__finalize__(self)

        return _new

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

            end_time = ref_laps['Time'].max()
            start_time = ref_laps['LapStartTime'].min()

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
                ret.loc[:, ch] = ret.loc[:, ch] \
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
            return self.drop(labels='DifferentialDistance', axis=1) \
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
                d = self.drop(labels='DriverAhead', axis=1) \
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
            if drv not in self.session.car_data:
                continue
            # find correct first relevant lap; very important for correct zero point in distance
            drv_laps = self.session.laps[self.session.laps['DriverNumber'] == drv]
            if drv_laps.empty:  # Only include drivers who participated in this session
                continue
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
    """
    .. deprecated:: 2.2
        Use :class:`fastf1.events.Event` instead
    """
    def __new__(cls, year, gp):
        warnings.warn("`fastf1.core.Weekend` has been deprecated and will be"
                      "removed in a future version.\n"
                      "Use `fastf1.events.Event` instead.", FutureWarning)
        from fastf1 import events
        return events.get_event(year, gp)


class Session:
    """Object for accessing session specific data.

    The session class will usually be your starting point. This object will
    have various information about the session.

    .. note:: Most of the data is only available after calling
        :func:`Session.load`
    """

    def __init__(self, event, session_name, f1_api_support=False):
        # TODO: load drivers immediately
        # TODO: load driver list for older seasons through ergast
        self.event = event
        """:class:`~fastf1.events.Event`: Reference to the associated event
        object."""
        self.name = session_name
        """str: Name of this session, for example 'Qualifying', 'Race', 'FP1', ..."""
        self.f1_api_support = f1_api_support
        """bool: The official F1 API supports this event and lap timing data and
        telemetry data are available."""
        self.date = self.event.get_session_date(session_name)
        """pandas.Datetime: Date at which this session took place."""
        self.api_path = api.make_path(
            self.event['EventName'],
            self.event['EventDate'].strftime('%Y-%m-%d'),
            self.name, self.date.strftime('%Y-%m-%d')
        )
        """str: API base path for this session"""

        self._session_status = dict()
        self._race_control_messages = dict()

        self._laps: Laps
        self._t0_date: pd.Timestamp

        self._session_start_time: pd.Timedelta

        self._car_data = dict()
        self._pos_data = dict()

        self._weather_data: pd.DataFrame
        self._results: SessionResults

    def _get_property_warn_not_loaded(self, name):
        d = getattr(self, name, None)
        if d is None:
            raise DataNotLoadedError("The data you are trying to access has not "
                                     "been loaded yet. See `Session.load`")
        return d

    @property
    def weekend(self):
        """Deprecated: use :attr:`Session.event` instead"""
        warnings.warn("The property `Session.weekend` has been renamed to "
                      "`Session.event`.\n The old property will be removed in"
                      "a future version.", FutureWarning)
        return self.event

    @property
    def drivers(self):
        """:class:`list`: List of all drivers that took part in this
        session; contains driver numbers as string.

        Data is available after calling `Session.load`
        """
        return list(self.results['DriverNumber'].unique())

    @property
    def results(self):
        """:class:`SessionResults`: Session result with driver information.

        Data is available after calling `Session.load`
        """
        return self._get_property_warn_not_loaded('_results')

    @property
    def laps(self):
        """:class:`Laps`: All laps from all drivers driven in this session.

        Data is available after calling `Session.load` with ``laps=True``
        """
        return self._get_property_warn_not_loaded('_laps')

    @property
    def weather_data(self):
        """Dataframe containing weather data for this session as received
        from the api. See :func:`fastf1.api.weather_data` for available data
        channels. Each data channel is one row of the dataframe.

        Data is available after calling `Session.load` with ``weather=True``
        """
        return self._get_property_warn_not_loaded('_weather_data')

    @property
    def car_data(self):
        """Dictionary of car telemetry (Speed, RPM, etc.) as received from
        the api by car number (where car number is a string and the telemetry
        is an instance of :class:`Telemetry`)

        Data is available after calling `Session.load` with ``telemetry=True``
        """
        return self._get_property_warn_not_loaded('_car_data')

    @property
    def pos_data(self):
        """Dictionary of car position data as received from the api by car
        number (where car number is a string and the telemetry
        is an instance of :class:`Telemetry`)

        Data is available after calling `Session.load` with ``telemetry=True``
        """
        return self._get_property_warn_not_loaded('_pos_data')

    @property
    def session_status(self):
        """:class:`pandas.Dataframe`: Session status data as returned by
        :func:`fastf1.api.session_status_data`

        Data is available after calling `Session.load` with ``laps=True``
        """
        return self._get_property_warn_not_loaded('_session_status')

    @property
    def race_control_messages(self):
        """:class:`pandas.Dataframe`: Race Control messages as returned by
        :func:`fastf1.api.race_control_messages`

        Data is available after calling `Session.load` with ``messages=True``
        """
        return self._get_property_warn_not_loaded('_race_control_messages')

    @property
    def session_start_time(self):
        """:class:`pandas.Timedelta`: Session time at which the session was
        started according to the session status data. This is not the
        time at which the session is scheduled to be started!

        Data is available after calling `Session.load` with ``laps=True``
        """
        return self._get_property_warn_not_loaded('_session_start_time')

    @property
    def t0_date(self):
        """:class:`pandas.Datetime`: Date timestamp which marks the beginning
        of the data stream (the moment at which the session time is zero).

        Data is available after calling `Session.load` with ``telemetry=True``
        """
        return self._get_property_warn_not_loaded('_t0_date')

    def load(self, *, laps=True, telemetry=True, weather=True, messages=True,
             livedata=None):
        """Load session data from the supported APIs.

        This method allows to flexibly load some or all data that FastF1 can
        give you access to. Without specifying any further options, all data
        is loaded by default.

        Downloading and parsing of the data takes a considerable amount of
        time. Therefore, it is highly recommended to enable caching so that
        most of the data processing needs to be done only once.

        .. note:: **Lap data: drivers crashing and retiring**

            *During a session:*
            An additional last lap is added for a driver if the last timed
            lap of a driver is not an inlap and the session is aborted next.
            The `Time` for when this lap was "set" will be set to the time at
            which the session was aborted.

            *First lap in a race:*
            A single lap with minimal information will be added in race
            sessions if a driver does not complete at least one timed lap.
            The `LapStartTime` for this lap will be set to the start time
            of the session as with all other laps in a race. The `Time` at
            which this lap was "set" will be set to the time at which the
            first driver completes their first lap.


        .. note:: Absolute time is not super accurate. The moment a lap
            is logged is not always the same and there will be some
            jitter. At the moment lap time reference is synchronised
            on the sector time triggered with lowest latency.
            Expect an error of around ±10m when overlapping telemetry
            data of different laps.

        Args:
            laps (bool): Load laps and session status data.
            telemetry (bool): Load telemetry data.
            weather (bool): Load weather data.
            messages (bool): Load race control messages for the session
            livedata (:class:`fastf1.livetiming.data.LiveTimingData`, optional):
                instead of requesting the data from the api, locally saved
                livetiming data can be used as a data source
        """
        logging.info(f"Loading data for "
                     f"{self.event['EventName']} - {self.name}"
                     f" [v{fastf1.__version__}]")

        self._load_drivers_results(livedata=livedata)

        if self.f1_api_support:
            if laps:
                # try:
                self._load_laps_data(livedata)
                # except Exception as exc:
                #     logging.warning("Failed to load lap data!")
                #     logging.debug("Lap data failure traceback:", exc_info=exc)

            if telemetry:
                try:
                    self._load_telemetry(livedata=livedata)
                except Exception as exc:
                    logging.warning("Failed to load telemetry data!")
                    logging.debug("Telemetry data failure traceback:", exc_info=exc)

            if weather:
                try:
                    self._load_weather_data(livedata=livedata)
                except Exception as exc:
                    logging.warning("Failed to load weather data!")
                    logging.debug("Weather data failure traceback:", exc_info=exc)

            if messages:
                try:
                    self._load_race_control_messages(livedata=livedata)
                except Exception as exc:
                    logging.warning("Failed to load Race Control message "
                                    "data!")
                    logging.debug("RC message data failure traceback:",
                                  exc_info=exc)

        else:
            if any((laps, telemetry, weather, messages)):
                logging.warning(
                    "Cannot load laps, telemetry, weather, and message data "
                    "because the relevant API is not supported for this "
                    "session."
                )

        logging.info(f"Finished loading data for {len(self.drivers)} "
                     f"drivers: {self.drivers}")

    def load_laps(self, with_telemetry=False, livedata=None):
        """
        .. deprecated:: 2.2
            use :func:`Session.load` instead
        """
        # TODO: remove in v2.3
        warnings.warn("`Session.load_laps` is deprecated and will be"
                      "removed in a future version.\n"
                      "Use `Session.load` instead.", FutureWarning)
        self.load(telemetry=with_telemetry, livedata=livedata)
        return self.laps

    def load_telemetry(self, livedata=None):
        """
        .. deprecated:: 2.2
            use :func:`Session.load` instead
        """
        # TODO: remove in v2.3
        warnings.warn("`Session.load_laps` is deprecated and will be"
                      "removed in a future version.\n"
                      "Use `Session.load` instead.", FutureWarning)
        self._load_telemetry(livedata=livedata)

    def _load_laps_data(self, livedata):
        data, _ = api.timing_data(self.api_path, livedata=livedata)
        app_data = api.timing_app_data(self.api_path, livedata=livedata)
        logging.info("Processing timing data...")
        # Matching data and app_data. Not super straightforward
        # Sometimes a car may enter the pit without changing tyres, so
        # new compound is associated with the help of logging time.
        useful = app_data[['Driver', 'Time', 'Compound', 'TotalLaps', 'New']]
        useful = useful[~useful['Compound'].isnull()]
        # check when a session was started; for a race this indicates the
        # start of the race
        session_status = api.session_status_data(self.api_path,
                                                 livedata=livedata)
        for i in range(len(session_status['Status'])):
            if session_status['Status'][i] == 'Started':
                self._session_start_time = session_status['Time'][i]
                break
        self._session_status = pd.DataFrame(session_status)
        df = None

        track_status = api.track_status_data(self.api_path, livedata=livedata)

        drivers = self.drivers
        if not drivers:
            # no driver list, generate from lap data
            drivers = set(data['Driver'].unique())\
                .intersection(set(useful['Driver'].unique()))

            _nums_df = pd.DataFrame({'DriverNumber': list(drivers)},
                                    index=list(drivers))
            _info_df = pd.DataFrame(fastf1._DRIVER_TEAM_MAPPING).T

            self._results = SessionResults(_nums_df.join(_info_df),
                                           force_default_cols=True)

            logging.warning("Generating minimal driver "
                            "list from timing data.")

        for i, driver in enumerate(drivers):
            d1 = data[data['Driver'] == driver]
            d2 = useful[useful['Driver'] == driver]
            only_one_lap = False

            if not len(d1):
                if ((self.name in ('Race', 'Sprint', 'Sprint Qualifying'))
                        and len(d2)):
                    # add data for drivers who crashed on the very first lap
                    # as a downside, this potentially adds a nonexistent lap
                    # for drivers who could not start the race
                    only_one_lap = True
                    result = d1.copy()
                    result['Driver'] = [driver, ]
                    result['NumberOfLaps'] = 0
                    result['NumberOfPitStops'] = 0
                    result['Time'] = data['Time'].min()
                    result['IsPersonalBest'] = False
                    result['Compound'] = d2['Compound'].iloc[0]
                    result['TotalLaps'] = d2['TotalLaps'].iloc[0]
                    result['New'] = d2['New'].iloc[0]
                else:
                    logging.warning(f"No lap data for driver {driver}")
                    continue  # no data for this driver; skip

            elif not len(d2):
                result = d1.copy()
                result['Compound'] = str()
                result['TotalLaps'] = np.nan
                result['New'] = False
                logging.warning(f"No tyre data for driver {driver}")

            else:
                result = pd.merge_asof(d1, d2, on='Time', by='Driver')

            # calculate lap start time by setting it to the 'Time' of the
            # previous lap
            laps_start_time = list(result['Time'])[:-1]
            if self.name in ('Race', 'Sprint', 'Sprint Qualifying'):
                # assumption that the first lap started when the session was
                # started can only be made for the race
                laps_start_time.insert(0, self.session_start_time)
            else:
                laps_start_time.insert(0, pd.NaT)
            laps_start_time = pd.Series(laps_start_time)

            # don't set lap start times after red flag restart to the time
            # at which the previous lap was set
            # only run this correction if the session was ever aborted
            if (self.session_status['Status'] == 'Aborted').any():
                _is_aborted = False
                # first, find the point at which the session was aborted, then
                # the following restart and the lap that starts immediately
                # after; correct its pit out time
                for _, row in self.session_status.iterrows():
                    if _is_aborted and row['Status'] == 'Started':  # restart
                        _is_aborted = False
                        try:
                            restart_index = result.loc[
                                result['PitOutTime'] > row['Time'],
                                'PitOutTime'
                            ].index[0]
                        except IndexError:
                            continue  # no pit out, car did not restart
                        if self.name in ('Sprint Qualifying', 'Sprint',
                                         'Race'):
                            # if this is a race-like session, we can assume the
                            # session restart time as lap start time
                            laps_start_time[restart_index] = row['Time']
                        else:
                            # for other sessions, we cannot make this
                            # assumption set to NaT here, it will be set to
                            # PitOutTime later if possible
                            laps_start_time[restart_index] = pd.NaT
                    elif row['Status'] == 'Aborted':  # red flag
                        _is_aborted = True

            result.loc[:, 'LapStartTime'] = pd.Series(
                laps_start_time, dtype='timedelta64[ns]'
            )

            # set missing lap start times to pit out time where possible
            mask = pd.isna(result['LapStartTime']) & (~pd.isna(result['PitOutTime']))
            result.loc[mask, 'LapStartTime'] = result.loc[mask, 'PitOutTime']

            # create total laps counter
            for npit in result['NumberOfPitStops'].unique():
                sel = result['NumberOfPitStops'] == npit
                result.loc[sel, 'TotalLaps'] += np.arange(0, sel.sum()) + 1

            # check if there is another lap during which the session was aborted
            # but which is not in the data
            # if yes, add as much data as possible for it
            # set the time of abort as lap end time given that there is no
            # accurate time available
            # this block of code has no tests; testing would require to mock
            # the data as the actual data may be updated on the server after
            # some time and the problem no longer occurs
            if pd.isna(result['PitInTime'].iloc[-1]) and not only_one_lap:
                if not pd.isna(result['Time'].iloc[-1]):
                    next_statuses = self.session_status[
                        self.session_status['Time'] > result['Time'].iloc[-1]
                        ]
                else:
                    next_statuses = self.session_status[
                        self.session_status['Time']
                        > result['LapStartTime'].iloc[-1]
                        ]

                aborted = False
                if not next_statuses.empty:
                    next_status = next_statuses.iloc[0]
                    aborted = (next_status['Status'] == 'Aborted')

                if aborted:
                    new_last = pd.DataFrame({
                        'LapStartTime': [result['Time'].iloc[-1]],
                        'Time': [next_status['Time']],
                        'Driver': [result['Driver'].iloc[-1]],
                        'NumberOfLaps': [result['NumberOfLaps'].iloc[-1] + 1],
                        'NumberOfPitStops':
                            [result['NumberOfPitStops'].iloc[-1]],
                        # 'IsPersonalBest': False,
                        'Compound': [result['Compound'].iloc[-1]],
                        'TotalLaps': [result['TotalLaps'].iloc[-1] + 1],
                        'New': [result['New'].iloc[-1]],
                    })
                    if not only_one_lap:
                        result = result.append(new_last).reset_index(drop=True)
                    else:
                        result = new_last

            df = pd.concat([df, result], sort=False)
        if df is None:
            raise NoLapDataError
        laps = df.reset_index(drop=True)  # noqa: F821
        laps.rename(columns={'TotalLaps': 'TyreLife',
                             'NumberOfPitStops': 'Stint',
                             'Driver': 'DriverNumber',
                             'NumberOfLaps': 'LapNumber',
                             'New': 'FreshTyre'}, inplace=True)
        laps['Stint'] += 1  # counting stints from 1
        t_map = {r['DriverNumber']: r['TeamName']
                 for _, r in self.results.iterrows()}
        laps['Team'] = laps['DriverNumber'].map(t_map)
        d_map = {r['DriverNumber']: r['Abbreviation']
                 for _, r in self.results.iterrows()}
        laps['Driver'] = laps['DriverNumber'].map(d_map)

        # add track status data
        laps['TrackStatus'] = '1'

        def applicator(new_status, current_status):
            if current_status == '1':
                return new_status
            elif new_status not in current_status:
                return current_status + new_status
            else:
                return current_status

        if len(track_status['Time']) > 0:
            t = track_status['Time'][0]
            status = track_status['Status'][0]
            for next_t, next_status in zip(track_status['Time'][1:], track_status['Status'][1:]):
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
        self._laps = Laps(laps, session=self)
        self._check_lap_accuracy()

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
                self._laps.loc[self.laps['DriverNumber'] == drv, 'IsAccurate'] = is_accurate

            if integrity_errors > 0:
                logging.warning(f"Driver {drv: >2}: Lap timing integrity check failed for {integrity_errors} lap(s)")

    def _load_drivers_results(self, *, livedata=None):
        # get list of drivers
        driver_info = None
        if self.f1_api_support:
            # load driver info from f1 api
            driver_info = self._drivers_from_f1_api(livedata=livedata)

        if not driver_info:
            if not self.event.is_testing():
                # load driver info and results from ergast
                # (season 2017 and older or fallback from f1 api)
                driver_info = self._drivers_results_from_ergast(
                    load_drivers=True, load_results=True
                )
                self._results = SessionResults(
                    driver_info, index=driver_info['DriverNumber'],
                    force_default_cols=True
                )
            else:
                logging.warning("Failed to load driver list and "
                                "session results!")
                self._results = SessionResults(force_default_cols=True)

        else:
            # extend existing driver info (f1 api) with results from ergast
            drivers = pd.DataFrame(driver_info,
                                   index=driver_info['DriverNumber'])
            if not self.event.is_testing():
                r = self._drivers_results_from_ergast(load_results=True)
            else:
                r = None

            if r:
                # join driver info and session results
                results = pd.DataFrame(r).set_index('DriverNumber')
                self._results = SessionResults(drivers.join(results),
                                               force_default_cols=True)
            else:
                # return driver info without session results
                self._results = SessionResults(drivers,
                                               force_default_cols=True)

        if (dupl_mask := self._results.index.duplicated()).any():
            dupl_drv = list(self._results.index[dupl_mask])
            logging.warning("Session results contain duplicate entries for "
                            f"driver(s) {dupl_drv}")

        if 'Position' in self._results:
            self._results = self._results.sort_values('Position')

    def _drivers_from_f1_api(self, *, livedata=None):
        try:
            f1di = api.driver_info(self.api_path, livedata=livedata)
        except Exception as exc:
            logging.warning("Failed to load extended driver information!")
            logging.debug("Exception while loading driver list", exc_info=exc)
            driver_info = {}
        else:
            driver_info = collections.defaultdict(list)
            for key1, key2 in {
                'RacingNumber': 'DriverNumber',
                'BroadcastName': 'BroadcastName',
                'Tla': 'Abbreviation', 'TeamName': 'TeamName',
                'TeamColour': 'TeamColor', 'FirstName': 'FirstName',
                'LastName': 'LastName'
            }.items():
                for entry in f1di.values():
                    driver_info[key2].append(entry.get(key1))
            if 'FirstName' in driver_info and 'LastName' in driver_info:
                for first, last in zip(driver_info['FirstName'],
                                       driver_info['LastName']):
                    driver_info['FullName'].append(f"{first} {last}")
        return driver_info

    def _drivers_results_from_ergast(self, *, load_drivers=False,
                                     load_results=False):
        if self.name in ('Qualifying', 'Sprint Qualifying', 'Sprint', 'Race'):
            session_name = self.name
        else:
            # this is a practice session, use drivers from race session but
            # don't load results
            session_name = 'Race'
            load_results = False

        d = collections.defaultdict(list)
        try:
            data = ergast.fetch_results(
                self.event.year, self.event['RoundNumber'], session_name
            )
        except Exception as exc:
            logging.warning("Failed to load data from Ergast API! "
                            "(This is expected for recent sessions)")
            logging.debug("Ergast failure traceback:", exc_info=exc)
            return d

        time0 = None
        for r in data:
            d['DriverNumber'].append(r.get('number'))
            if load_drivers:
                d['Abbreviation'].append(
                    recursive_dict_get(r, 'Driver', 'code',
                                       default_none=True))
                first_name = recursive_dict_get(r, 'Driver', 'givenName',
                                                default_none=True)
                last_name = recursive_dict_get(r, 'Driver', 'familyName',
                                               default_none=True)
                d['FirstName'].append(first_name)
                d['LastName'].append(last_name)
                d['FullName'].append(f"{first_name} {last_name}")
                d['TeamName'].append(
                    recursive_dict_get(r, 'Constructor', 'name',
                                       default_none=True))
            if load_results:
                d['Position'].append(r.get('position'))
                d['GridPosition'].append(r.get('grid'))
                d['Q1'].append(to_timedelta(r.get('Q1')))
                d['Q2'].append(to_timedelta(r.get('Q2')))
                d['Q3'].append(to_timedelta(r.get('Q3')))
                if time0 is None:
                    ts = recursive_dict_get(r, 'Time', 'time',
                                            default_none=True)
                    if ts:
                        time0 = to_timedelta(ts)
                    else:
                        time0 = pd.NaT
                    d['Time'].append(time0)
                else:
                    ts = recursive_dict_get(r, 'Time', 'time',
                                            default_none=True)
                    if ts:
                        dt = to_timedelta(ts)
                    else:
                        dt = pd.NaT
                    d['Time'].append(time0 + dt)
                d['Status'].append(r.get('status'))
                d['Points'].append(r.get('points'))

        return d

    def _load_weather_data(self, livedata=None):
        weather_data = api.weather_data(self.api_path, livedata=livedata)
        weather_df = pd.DataFrame(weather_data)
        self._weather_data = weather_df

    def _load_race_control_messages(self, livedata=None):
        race_control_messages = api.race_control_messages(self.api_path,
                                                          livedata=livedata)
        race_control_df = pd.DataFrame(race_control_messages)
        self._race_control_messages = race_control_df

    def _load_telemetry(self, livedata=None):
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

        self._calculate_t0_date(car_data, pos_data)

        for drv in self.drivers:
            try:
                # drop and recalculate time stamps based on 'Date', because 'Date' has a higher resolution
                drv_car = Telemetry(car_data[drv].drop(labels='Time', axis=1),
                                    session=self, driver=drv,
                                    drop_unknown_channels=True)
                drv_pos = Telemetry(pos_data[drv].drop(labels='Time', axis=1),
                                    session=self, driver=drv,
                                    drop_unknown_channels=True)
            except KeyError:
                # not pos data or car data exists for this driver
                continue

            drv_car['Date'] = drv_car['Date'].round('ms')
            drv_pos['Date'] = drv_pos['Date'].round('ms')

            drv_car['Time'] = drv_car['Date'] - self.t0_date  # create proper continuous timestamps
            drv_pos['Time'] = drv_pos['Date'] - self.t0_date
            drv_car['SessionTime'] = drv_car['Time']
            drv_pos['SessionTime'] = drv_pos['Time']

            self._car_data[drv] = drv_car
            self._pos_data[drv] = drv_pos

        self._laps['LapStartDate'] = self._laps['LapStartTime'] + self.t0_date

    def get_driver(self, identifier):
        """
        Get a driver object which contains additional information about a driver.

        Args:
            identifier (str): driver's three letter identifier (for
                example 'VER') or driver number as string

        Returns:
            instance of :class:`Driver`
        """
        mask = ((self.results['Abbreviation'] == identifier)
                | (self.results['DriverNumber'] == identifier))
        if not mask.any():
            raise ValueError(f"Invalid driver identifier '{identifier}'")
        return self.results[mask].iloc[0]

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

        self._t0_date = date_offset.round('ms')


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

        import fastf1

        session = fastf1.get_session(2019, 'Bahrain', 'Q')
        session.load()
        best_bottas = session.laps.pick_driver('BOT').pick_fastest()

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
        - **IsPersonalBest** (bool): Flag that indicates whether this lap is
            the official personal best lap of a driver. If any lap of a driver
            is quicker than their respective personal best lap, this means that
            the quicker lap is invalid and not counted. This can happen it the
            track limits were execeeded, for example.
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
        def _new(*args, **kwargs):
            return Laps(*args, **kwargs).__finalize__(self)

        return _new

    @property
    def _constructor_sliced(self):
        def _new(*args, **kwargs):
            return Lap(*args, **kwargs).__finalize__(self)

        return _new

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

        .. doctest::

            >>> session = fastf1.get_session(2019, 'Monza', 'Q')
            >>> session.load(telemetry=False)
            >>> weather_data = session.laps.get_weather_data()
            >>> print(weather_data)
                                 Time AirTemp Humidity  ... TrackTemp WindDirection WindSpeed
            20 0 days 00:20:14.613000    22.5     52.0  ...      35.8           212       2.0
            21 0 days 00:21:15.001000    22.5     52.2  ...      36.1           207       2.7
            23 0 days 00:23:14.854000    22.7     52.5  ...      37.4           210       2.3
            24 0 days 00:24:14.430000    23.2     51.5  ...      37.4           207       3.2
            26 0 days 00:26:14.315000    23.6     50.2  ...      37.2           238       1.8
            ..                    ...     ...      ...  ...       ...           ...       ...
            36 0 days 00:36:14.426000    23.0     51.1  ...      38.3           192       0.9
            37 0 days 00:37:14.391000    23.3     50.0  ...      38.7           213       0.9
            28 0 days 00:28:14.324000    23.5     49.9  ...      37.5           183       1.3
            34 0 days 00:34:14.385000    23.0     51.7  ...      37.7           272       0.8
            35 0 days 00:35:14.460000    23.2     50.3  ...      38.0           339       1.1
            <BLANKLINE>
            [275 rows x 8 columns]

        Joining weather data with lap timing data:

        .. doctest::

            >>> import pandas as pd  # needed additionally to fastf1

            # prepare the data for joining
            >>> laps = session.laps
            >>> laps = laps.reset_index(drop=True)
            >>> weather_data = weather_data.reset_index(drop=True)

            # exclude the 'Time' column from weather data when joining
            >>> joined = pd.concat([laps, weather_data.loc[:, ~(weather_data.columns == 'Time')]], axis=1)
            >>> print(joined)
                                  Time DriverNumber  ... WindDirection  WindSpeed
            0   0 days 00:21:01.358000           16  ...           212        2.0
            1   0 days 00:22:21.775000           16  ...           207        2.7
            2   0 days 00:24:03.991000           16  ...           210        2.3
            3   0 days 00:25:24.117000           16  ...           207        3.2
            4   0 days 00:27:09.461000           16  ...           238        1.8
            ..                     ...          ...  ...           ...        ...
            270 0 days 00:36:38.150000           88  ...           192        0.9
            271 0 days 00:38:37.508000           88  ...           213        0.9
            272 0 days 00:33:27.227000           33  ...           183        1.3
            273 0 days 00:35:05.865000           33  ...           272        0.8
            274 0 days 00:36:47.787000           33  ...           339        1.1
            <BLANKLINE>
            [275 rows x 33 columns]
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

    def pick_fastest(self, only_by_time=False):
        """Return the lap with the fastest lap time.

        This method will by default return the quickest lap out of self, that
        is also marked as personal best lap of a driver.

        If the quickest lap by lap time is not marked as personal best, this
        means that it was not counted. This can be the case for example, if
        the driver exceeded track limits and the lap time was deleted.

        If no lap is marked as personal best lap or self contains no laps,
        an empty Lap object will be returned.

        The check for personal best lap can be disabled, so that any quickest
        lap will be returned.

        Args:
            only_by_time (bool): Ignore whether any laps are marked as
                personal best laps and simply return the lap that has the
                lowest lap time.

        Returns:
            instance of :class:`Lap`
        """
        if only_by_time:
            laps = self  # all laps
        else:
            # select only laps marked as personal fastest
            laps = self.loc[self['IsPersonalBest'] == True]  # noqa: E712 comparison with True

        if not laps.size:
            return Lap(index=self.columns)

        lap = laps.loc[laps['LapTime'].idxmin()]
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
        def _new(*args, **kwargs):
            return Lap(*args, **kwargs).__finalize__(self)

        return _new

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

        .. doctest::

            >>> session = fastf1.get_session(2019, 'Monza', 'Q')
            >>> session.load(telemetry=False)
            >>> lap = session.laps.pick_fastest()
            >>> lap['LapStartTime']
            Timedelta('0 days 01:09:55.561000')
            >>> lap.get_weather_data()
            Time             0 days 01:10:15.292000
            AirTemp                            23.0
            Humidity                           51.9
            Pressure                          992.4
            Rainfall                          False
            TrackTemp                          37.8
            WindDirection                       166
            WindSpeed                           0.8
            Name: 70, dtype: object
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


class SessionResults(pd.DataFrame):
    """This class provides driver and result information for all drivers that
    participated in a session.

    This class subclasses a :class:`pandas.DataFrame` and the usual methods
    provided by pandas can be used to work with the data.

    **All dataframe columns will always exist even if they are not relevant
    for the current session!**

    The following information is provided for each driver as a column of the
    dataframe:

        - ``DriverNumber`` | :class:`str` |
          The number associated with this driver in this session (usually the
          drivers permanent number)

        - ``BroadcastName`` | :class:`str` |
          First letter of the drivers first name plus the drivers full last name
          in all capital letters. (e.g. 'P GASLY')

        - ``FullName`` | :class:`str` |
          The drivers full name (e.g. "Pierre Gasly")

        - ``Abbreviation`` | :class:`str` |
          The drivers three letter abbreviation (e.g. "GAS")

        - ``TeamName`` | :class:`str` |
          The team name (short version without title sponsors)

        - ``TeamColor`` | :class:`str` |
          The color commonly associated with this team (hex value)

        - ``FirstName`` | :class:`str` |
          The drivers first name

        - ``LastName`` | :class:`str` |
          The drivers last name

        - ``Position`` | :class:`float` |
          The drivers finishing position (values only given if session is
          'Race', 'Qualifying' or 'Sprint Qualifying')

        - ``GridPosition`` | :class:`float` |
          The drivers starting position (values only given if session is
          'Race' or 'Sprint Qualifying')

        - ``Q1`` | :class:`pd.Timedelta` |
          The drivers best Q1 time (values only given if session is
          'Qualifying')

        - ``Q2`` | :class:`pd.Timedelta` |
          The drivers best Q2 time (values only given if session is
          'Qualifying')

        - ``Q3`` | :class:`pd.Timedelta` |
          The drivers best Q3 time (values only given if session is
          'Qualifying')

        - ``Time`` | :class:`pd.Timedelta` |
          The drivers total race time (values only given if session is
          'Race' or 'Sprint Qualifying' and the driver was not more than one
          lap behind the leader)

        - ``Status`` | :class:`str` |
          A status message to indicate if and how the driver finished the race
          or to indicate the cause of a DNF. Possible values include but are
          not limited to 'Finished', '+ 1 Lap', 'Crash', 'Gearbox', ...
          (values only given if session is 'Race' or 'Sprint Qualifying')

        - ``Status`` | :class:`float` |
          The number of points received by each driver for their finishing
          result.

    By default, the session results are indexed by driver number and sorted by
    finishing position.

    .. note:: This class is usually not instantiated directly. You should
        create a session and access the session result through the
        :attr:`Session.results` property.

    Args:
        *args: passed on to :class:`pandas.DataFrame` superclass
        force_default_cols (bool): Enforce that all default columns and only
            the default columns exist
        **kwargs: passed on to :class:`pandas.DataFrame` superclass
            (except 'columns' which is unsupported for this object)

    .. versionadded:: 2.2
    """

    _COL_TYPES = {
        'DriverNumber': str,
        'BroadcastName': str,
        'Abbreviation': str,
        'TeamName': str,
        'TeamColor': str,
        'FirstName': str,
        'LastName': str,
        'FullName': str,
        'Position': float,
        'GridPosition': float,
        'Q1': 'timedelta64[ns]',
        'Q2': 'timedelta64[ns]',
        'Q3': 'timedelta64[ns]',
        'Time': 'timedelta64[ns]',
        'Status': str,
        'Points': float
    }

    _internal_names = ['base_class_view']

    def __init__(self, *args, force_default_cols=False, **kwargs):
        if force_default_cols:
            kwargs['columns'] = list(self._COL_TYPES.keys())
        super().__init__(*args, **kwargs)

        # apply column specific dtypes
        for col, _type in self._COL_TYPES.items():
            if col not in self.columns:
                continue
            if self[col].isna().all():
                if _type == 'timedelta64[ns]':
                    self[col] = pd.Series(dtype='timedelta64[ns]')
                else:
                    self[col] = _type()

            self[col] = self[col].astype(_type)

    def __repr__(self):
        return self.base_class_view.__repr__()

    @property
    def _constructor(self):
        def _new(*args, **kwargs):
            return SessionResults(*args, **kwargs).__finalize__(self)

        return _new

    @property
    def _constructor_sliced(self):
        def _new(*args, **kwargs):
            return DriverResult(*args, **kwargs).__finalize__(self)

        return _new

    @property
    def base_class_view(self):
        """For a nicer debugging experience; can view DataFrame through
        this property in various IDEs"""
        return pd.DataFrame(self)


class DriverResult(pd.Series):
    """This class provides driver and result information for a single driver.

    This class subclasses a :class:`pandas.Series` and the usual methods
    provided by pandas can be used to work with the data.

    For information on which data is available, see :class:`SessionResult`.

    .. note:: This class is usually not instantiated directly. You should
        create a session and access the driver result through
        :func:`Session.get_driver` or by slicing the session result.

    Args:
        *args: passed on to :class:`pandas.Series` superclass
        **kwargs: passed on to :class:`pandas.Series` superclass

    .. versionadded:: 2.2
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._getattr_override = True  # TODO: remove in v2.3

    @property
    def _constructor(self):
        def _new(*args, **kwargs):
            return DriverResult(*args, **kwargs).__finalize__(self)

        return _new

    def __getattribute__(self, name):
        # TODO: remove in v2.3
        if name == 'name' and getattr(self, '_getattr_override', False):
            if 'FirstName' in self:
                warnings.warn(
                    "The `Driver.name` property is deprecated and will be"
                    "removed in a future version.\n"
                    "Use `Driver['FirstName']` or `Driver.FirstName` instead.",
                    FutureWarning
                )
                # name may be accessed by pandas internals to, when data
                # does not exist yet
                return self['FirstName']

        return super().__getattribute__(name)

    def __repr__(self):
        # don't show .name deprecation message when .name is accessed internally
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore',
                                    message=r".*property is deprecated.*")
            return super().__repr__()

    @property
    def dnf(self):
        """True if driver did not finish"""
        return not (self.Status[3:6] == 'Lap' or self.Status == 'Finished')

    @property
    def grid(self):
        """Grid position

        .. deprecated:: 2.2
            Use ``Driver['GridPosition']`` instead
        """
        # TODO: remove in v2.3
        warnings.warn("The `Driver.grid` property is deprecated and will be"
                      "removed in a future version.\n"
                      "Use `Driver['GridPosition']` or `Driver.GridPosition` "
                      "instead.", FutureWarning)
        return self['GridPosition']

    @property
    def position(self):
        """Finishing position

        .. deprecated:: 2.2
            Use ``Driver['Position']`` instead
        """
        # TODO: remove in v2.3
        warnings.warn("The `Driver.position` property is deprecated and will be"
                      "removed in a future version.\n"
                      "Use `Driver['Position']` or `Driver.Position` "
                      "instead.", FutureWarning)
        return self['Position']

    @property
    def familyname(self):
        """Driver family name

        .. deprecated:: 2.2
            Use ``Driver['LastName']`` instead
        """
        # TODO: remove in v2.3
        warnings.warn("The `Driver.position` property is deprecated and will be"
                      "removed in a future version.\n"
                      "Use `Driver['LastName']` or `Driver.LastName` "
                      "instead.", FutureWarning)
        return self['LastName']

    @property
    def team(self):
        """Team name

        .. deprecated:: 2.2
            Use ``Driver['TeamName']`` instead
        """
        # TODO: remove in v2.3
        warnings.warn("The `Driver.team` property is deprecated and will be"
                      "removed in a future version.\n"
                      "Use `Driver['TeamName']` or `Driver.TeamName` "
                      "instead.", FutureWarning)
        return self['TeamName']


class Driver:
    """
    .. deprecated:: 2.2
        Use :class:`fastf1.core.DriverResult` instead
    """
    def __new__(cls, *args, **kwargs):
        warnings.warn("`fastf1.core.Driver` has been deprecated and will be"
                      "removed in a future version.\n"
                      "Use `fastf1.core.DriverResult` instead.",
                      FutureWarning)
        return DriverResult()


class DataNotLoadedError(Exception):
    """Raised if an attempt is made to access data that has not been loaded
    yet."""
    pass


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
