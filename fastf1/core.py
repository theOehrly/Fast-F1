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

Usually you will be using :func:`fastf1.get_session` to get a :class:`Session`
object.

The :class:`Laps` object holds detailed information about multiple laps.

The :class:`Lap` object holds the same information as :class:`Laps` but only
for one single lap. When selecting a single lap from a :class:`Laps` object,
an object of type :class:`Lap` will be returned.

Apart from only providing data, the :class:`Laps`, :class:`Lap` and
:class:`Telemetry` objects implement various methods for selecting and
analyzing specific parts of the data.
"""
import collections
import re
import typing
import warnings
from functools import cached_property
from typing import (
    Any,
    Callable,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    Union
)

import numpy as np
import pandas as pd

import fastf1
from fastf1 import _api as api
from fastf1 import ergast
from fastf1.internals.pandas_base import (
    BaseDataFrame,
    BaseSeries
)
from fastf1.livetiming.data import LiveTimingData
from fastf1.logger import (
    get_logger,
    soft_exceptions
)
from fastf1.mvapi import (
    CircuitInfo,
    get_circuit_info
)
from fastf1.utils import to_timedelta


_logger = get_logger(__name__)

D_LOOKUP: List[List] = \
    [[44, 'HAM', 'Mercedes'], [77, 'BOT', 'Mercedes'],
     [55, 'SAI', 'Ferrari'], [16, 'LEC', 'Ferrari'],
     [33, 'VER', 'Red Bull'], [11, 'PER', 'Red Bull'],
     [3, 'RIC', 'McLaren'], [4, 'NOR', 'McLaren'],
     [5, 'VET', 'Aston Martin'], [18, 'STR', 'Aston Martin'],
     [14, 'ALO', 'Alpine'], [31, 'OCO', 'Alpine'],
     [22, 'TSU', 'AlphaTauri'], [10, 'GAS', 'AlphaTauri'],
     [47, 'MSC', 'Haas F1 Team'], [9, 'MAZ', 'Haas F1 Team'],
     [7, 'RAI', 'Alfa Romeo'], [99, 'GIO', 'Alfa Romeo'],
     [6, 'LAT', 'Williams'], [63, 'RUS', 'Williams']]


class Telemetry(pd.DataFrame):
    """Multi-channel time series telemetry data

    The object can contain multiple telemetry channels. Multiple telemetry
    objects with different channels can be merged on time. Each telemetry
    channel is one dataframe column. Partial telemetry (e.g. for one lap only)
    can be obtained through various methods for slicing the data. Additionally,
    methods for adding common computed data channels are available.

    The following telemetry channels existed in the original API data:

        - **Car data**:
            - `Speed` (float): Car speed [km/h]
            - `RPM` (int): Car RPM
            - `nGear` (int): Car gear number
            - `Throttle` (float): 0-100 Throttle pedal pressure [%]
            - `Brake` (bool): Brakes are applied or not.
            - `DRS` (int): DRS indicator (See :func:`fastf1.api.car_data`
              for more info)

        - **Position data**:
            - `X` (float): X position [1/10 m]
            - `Y` (float): Y position [1/10 m]
            - `Z` (float): Z position [1/10 m]
            - `Status` (string): Flag - OffTrack/OnTrack

        - **For both of the above**:
            - `Time` (timedelta): Time (0 is start of the data slice)
            - `SessionTime` (timedelta): Time elapsed since the start of the
              session
            - `Date` (datetime): The full date + time at which this sample
              was created
            - `Source` (str): Flag indicating how this sample was created:

                - 'car': sample from original api car data
                - 'pos': sample from original api position data
                - 'interpolated': this sample was artificially created; all
                  values are computed/interpolated

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

        Through merging/slicing it is possible to obtain any combination of
        telemetry channels!
        The following additional computed data channels can be added:

            - Distance driven between two samples:
              :meth:`add_differential_distance`
            - Distance driven since the first sample:
              :meth:`add_distance`
            - Relative distance driven since the first sample:
              :meth:`add_relative_distance`
            - Distance to driver ahead and car number of said driver:
              :meth:`add_driver_ahead`

        .. note:: See the separate explanation concerning the various
          definitions of 'Time' for more information on the three date and
          time related channels: :ref:`time-explanation`

    Slicing this class will return :class:`Telemetry` again for slices
    containing multiple rows. Single rows will be returned as
    :class:`pandas.Series`.

    Args:
        *args: passed through to `pandas.DataFrame` superclass
        session: Instance of associated session object.
            Required for full functionality!
        driver: Driver number as string. Required for full functionality!
        drop_unknown_channels: Remove all unknown data channels (i.e. columns)
            on initialization.
        **kwargs: passed through to `pandas.DataFrame` superclass
    """

    TELEMETRY_FREQUENCY = 'original'
    """Defines the frequency used when resampling the telemetry data. Either
    the string ``'original'`` or an integer to specify a frequency in Hz."""

    _CHANNELS = {
        'X': {'type': 'continuous', 'method': 'quadratic'},
        'Y': {'type': 'continuous', 'method': 'quadratic'},
        'Z': {'type': 'continuous', 'method': 'quadratic'},
        'Status': {'type': 'discrete'},
        'Speed': {'type': 'continuous', 'method': 'linear'},
        'RPM': {'type': 'continuous', 'method': 'linear'},
        'Throttle': {'type': 'continuous', 'method': 'linear'},
        # linear is often required as quadratic overshoots on sudden changes
        'Brake': {'type': 'discrete'},
        'DRS': {'type': 'discrete'},
        'nGear': {'type': 'discrete'},
        'Source': {'type': 'excluded'},  # special, custom handling
        'Date': {'type': 'excluded'},  # special, used as index when resampling
        'Time': {'type': 'excluded'},  # special, recalculated from 'Date'
        'SessionTime': {'type': 'excluded'},
        'Distance': {'type': 'continuous', 'method': 'quadratic'},
        'RelativeDistance': {'type': 'continuous', 'method': 'quadratic'},
        'DifferentialDistance': {'type': 'continuous', 'method': 'quadratic'},
        'DriverAhead': {'type': 'discrete'},
        'DistanceToDriverAhead': {'type': 'continuous', 'method': 'linear'}
    }
    """Known telemetry channels which are supported by default"""

    _metadata = ['session', 'driver']
    _internal_names = pd.DataFrame._internal_names + ['base_class_view']
    _internal_names_set = set(_internal_names)

    def __init__(self,
                 *args,
                 session: "Session" = None,
                 driver: str = None,
                 drop_unknown_channels: bool = False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.session: Optional[Session] = session
        self.driver = driver

        if drop_unknown_channels:
            unknown = set(self.columns).difference(self._CHANNELS.keys())
            super().drop(columns=unknown, inplace=True)
            if unknown:
                _logger.warning(
                    f"The following unknown telemetry channels have "
                    f"been dropped when creating a Telemetry object: "
                    f"{unknown} (driver: {self.driver})"
                )

    @property
    def _constructor(self):
        return Telemetry

    @property
    def base_class_view(self):
        """For a nicer debugging experience; can view DataFrame through this
        property in various IDEs"""
        return pd.DataFrame(self)

    def join(self, *args, **kwargs):
        """Wraps :meth:`pandas.DataFrame.join` and adds metadata propagation.

        When calling ``self.join`` metadata will be propagated from self to the
        joined dataframe.
        """
        meta = dict()
        for var in self._metadata:
            meta[var] = getattr(self, var)
        ret = super().join(*args, **kwargs)
        for var, val in meta.items():
            setattr(ret, var, val)
        return ret

    def merge(self, *args, **kwargs):
        """Wraps :meth:`pandas.DataFrame.merge` and adds metadata propagation.

        When calling ``self.merge`` metadata will be propagated from self to
        the merged dataframe.
        """
        meta = dict()
        for var in self._metadata:
            meta[var] = getattr(self, var)
        ret = super().merge(*args, **kwargs)
        for var, val in meta.items():
            setattr(ret, var, val)
        return ret

    def slice_by_mask(
            self,
            mask: Union[list, pd.Series, np.ndarray],
            pad: int = 0,
            pad_side: str = 'both'
    ) -> "Telemetry":
        """Slice self using a boolean array as a mask.

        Args:
            mask: Array of boolean values with the same length as self
            pad: Number of samples used for padding the sliced data
            pad_side: Where to pad the data; possible options: 'both',
            'before', 'after'
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

    def slice_by_lap(
            self,
            ref_laps: Union["Lap", "Laps"],
            pad: int = 0,
            pad_side: str = 'both',
            interpolate_edges: bool = False
    ) -> "Telemetry":
        """Slice self to only include data from the provided lap or laps.

        .. note:: Self needs to contain a 'SessionTime' column.

        .. note:: When slicing with an instance of :class:`Laps` as a
            reference, the data will be sliced by first and last lap. Missing
            laps in between will not be considered and data for these will
            still be included in the sliced result.

        Args:
            ref_laps: The lap/laps by which to slice self
            pad: Number of samples used for padding the sliced data
            pad_side: Where to pad the data; possible options:
                'both', 'before', 'after
            interpolate_edges: Add an interpolated sample at the beginning
                and end to exactly match the provided time window.
        """
        if isinstance(ref_laps, Laps) and len(ref_laps) > 1:
            if 'DriverNumber' not in ref_laps.columns:
                ValueError("Laps is missing 'DriverNumber'. Cannot return "
                           "telemetry for unknown driver.")
            if not len(ref_laps['DriverNumber'].unique()) <= 1:
                raise ValueError("Cannot create telemetry for multiple "
                                 "drivers at once!")

            end_time = ref_laps['Time'].max()
            start_time = ref_laps['LapStartTime'].min()

        elif isinstance(ref_laps, (Lap, Laps)):
            if isinstance(ref_laps, Laps):  # one lap in Laps
                ref_laps = ref_laps.iloc[0]  # handle as a single lap
            if 'DriverNumber' not in ref_laps.index:
                ValueError("Lap is missing 'DriverNumber'. Cannot return "
                           "telemetry for unknown driver.")
            end_time = ref_laps['Time']
            start_time = ref_laps['LapStartTime']

        else:
            raise TypeError("Attribute 'ref_laps' needs to be an instance of "
                            "`Lap` or `Laps`")

        return self.slice_by_time(start_time, end_time, pad, pad_side,
                                  interpolate_edges)

    def slice_by_time(
            self,
            start_time: pd.Timedelta,
            end_time: pd.Timedelta,
            pad: int = 0,
            pad_side: str = 'both',
            interpolate_edges: bool = False
    ) -> "Telemetry":
        """Slice self to only include data in a specific time frame.

        .. note:: Self needs to contain a 'SessionTime' column. Slicing by
            time use the 'SessionTime' as its reference.

        Args:
            start_time: Start of the section
            end_time: End of the section
            pad: Number of samples used for padding the sliced data
            pad_side: Where to pad the data; possible options:
                'both', 'before', 'after
            interpolate_edges: Add an interpolated sample at the beginning
                and end to exactly match the provided time window.

        Returns:
            :class:`Telemetry`
        """
        if interpolate_edges:
            edges = Telemetry({'SessionTime': (start_time, end_time),
                               'Date': (start_time + self.session.t0_date,
                                        end_time + self.session.t0_date)
                               },
                              session=self.session).__finalize__(self)
            d = self.merge_channels(edges, frequency='original')

        else:
            d = self.copy()  # TODO no copy?

        sel = ((d['SessionTime'] <= end_time)
               & (d['SessionTime'] >= start_time))
        if np.any(sel):
            data_slice = d.slice_by_mask(sel, pad, pad_side)

            if 'Time' in data_slice.columns:
                # shift time to 0 so laps can overlap
                data_slice.loc[:, 'Time'] \
                    = data_slice['SessionTime'] - start_time

            return data_slice
        return Telemetry().__finalize__(self)

    def merge_channels(
            self,
            other: Union["Telemetry", pd.DataFrame],
            frequency: Union[int, Literal['original'], None] = None
    ):
        """Merge telemetry objects containing different telemetry channels.

        The two objects don't need to have a common time base. The data will
        be merged, optionally resampled and missing values will be
        interpolated.

        :attr:`Telemetry.TELEMETRY_FREQUENCY` determines if and how the data
        is resampled. This can be overridden using the `frequency` keyword for
        this method.

        Merging and resampling:

            If the frequency is 'original', data will not be resampled. The
            two objects will be merged and all timestamps of both objects are
            kept. Values will be interpolated so that all telemetry channels
            contain valid data for all timestamps. This is the default and
            recommended option.

            If the frequency is specified as an integer in Hz the data will be
            merged as before. After that, the merged time base will be
            resampled from the first value on at the specified frequency.
            Afterward, the data will be interpolated to fit the new time base.
            This means that usually most if not all values of the data will be
            interpolated values. This is detrimental for overall accuracy.

        Interpolation:

            Missing values after merging will be interpolated for all known
            telemetry channels using :meth:`fill_missing`. Different
            interpolation methods are used depending on what kind of data the
            channel contains. For example, forward fill is used to
            interpolated 'nGear' while linear interpolation is used for 'RPM'
            interpolation.

        .. note :: Unknown telemetry channels will be merged but missing
            values will not be interpolated. This can either be done manually
            or a custom telemetry channel can be added using
            :meth:`register_new_channel`.

        .. note :: Do not resample data multiple times. Always resample based
            on the original data to preserve accuracy

        Args:
            other: Object to be merged with self
            frequency: Optional frequency to overwrite the default value set by
                :attr:`~Telemetry.TELEMETRY_FREQUENCY`.
                (Either string 'original' or integer for a frequency in Hz)
        """
        # merge the data and interpolate missing; 'Date' needs to be the index
        data = self.set_index('Date')
        other = other.set_index('Date')

        # save dtypes before merging, so they can be restored after merging
        # necessary for example because merging produces NaN values which
        # would cause an int column to become float, but it can be converted
        # back to int after interpolating missing values
        dtype_map = dict()
        for df in data, other:
            for col in df.columns:
                if col not in dtype_map.keys():
                    dtype_map[col] = df[col].dtype

        # Exclude columns existing on both dataframes from one dataframe
        # before merging (cannot merge with duplicates)
        on_both_columns = set(other.columns).intersection(set(data.columns))
        merged = other.merge(
            data[data.columns.difference(on_both_columns, sort=False)],
            how='outer', left_index=True, right_index=True, sort=True
        )
        # now use the previously excluded columns to update the missing values
        # in the merged dataframe
        for col in on_both_columns:
            merged.update({col: data[col]})

        if 'Driver' in merged.columns and len(merged['Driver'].unique()) > 1:
            raise ValueError("Cannot merge multiple drivers")

        if not frequency:
            frequency = data.TELEMETRY_FREQUENCY

        i = data.get_first_non_zero_time_index()
        if i is None:
            raise ValueError("No valid 'Time' data. Cannot resample!")

        ref_date = merged.index[i]

        # data needs to be resampled/interpolated differently, depending on
        # what kind of data it is how to handle which column is defined in
        # self._CHANNELS

        if frequency == 'original':
            # no resampling but still interpolation due to merging
            merged = merged.fill_missing()
            # make 'Date' a column again
            merged = merged.reset_index().rename(columns={'index': 'Date'})

        else:
            frq = pd.Timedelta(seconds=1/frequency)

            resampled_columns = dict()

            for ch in self._CHANNELS.keys():
                if ch not in merged.columns:
                    continue
                sig_type = self._CHANNELS[ch]['type']

                if sig_type == 'continuous':
                    method = self._CHANNELS[ch]['method']
                    if method in ('nearest', 'zero', 'slinear', 'quadratic',
                                  'cubic', 'barycentric', 'polynomial'):
                        # interpolation done using scipy.interpolate.interp1d
                        interp_kwargs = {'fill_value': 'extrapolate'}
                    elif method in ('pad', 'backfill', 'ffill', 'bfill'):
                        interp_kwargs = {}
                    else:
                        interp_kwargs = {'limit_direction': 'both'}

                    res = merged.loc[:, ch] \
                        .resample(frq, origin=ref_date).mean() \
                        .interpolate(method=method, **interp_kwargs)

                elif sig_type == 'discrete':
                    with warnings.catch_warnings():
                        # deprecated since pandas 2.2.0; don't opt in to new
                        # behaviour as that would silently change behaviour for
                        # user code; irrelevant here, therefore just filter
                        warnings.filterwarnings(
                            "ignore",
                            "Downcasting object dtype arrays on .fillna, "
                            ".ffill, .bfill is deprecated",
                            FutureWarning
                        )
                        res = merged.loc[:, ch] \
                            .resample(frq, origin=ref_date) \
                            .ffill().ffill().bfill()
                    # first ffill is a method of the resampler object and will
                    # ONLY ffill values created during resampling but not
                    # already existing NaN values. NaN values already existed
                    # because of merging, therefore call ffill a second time as
                    # a method of the returned series to fill these too only
                    # use bfill after ffill to fix first row

                else:
                    continue

                resampled_columns[ch] = res

            res_source = merged.loc[:, 'Source'] \
                .resample(frq, origin=ref_date) \
                .asfreq() \
                .fillna(value='interpolation')
            resampled_columns['Source'] = res_source

            # join resampled columns and make 'Date' a column again
            merged = Telemetry(resampled_columns) \
                .__finalize__(self) \
                .reset_index() \
                .rename(columns={'index': 'Date'})

            # recalculate the time columns
            merged['SessionTime'] \
                = merged['Date'] - self.session.t0_date
            merged['Time'] \
                = merged['SessionTime'] - merged['SessionTime'].iloc[0]

        # restore data types from before merging
        for col in dtype_map.keys():
            try:
                merged[col] = merged.loc[:, col].astype(dtype_map[col])
            except ValueError:
                _logger.warning(f"Failed to preserve data type for column "
                                f"'{col}' while merging telemetry.")

        return merged

    def resample_channels(
            self,
            rule: Optional[str] = None,
            new_date_ref: Optional[pd.Series] = None,
            **kwargs: Optional[Any]
    ):
        """Resample telemetry data.

        Convenience method for frequency conversion and resampling. Up and
        down sampling of data is supported. 'Date' and 'SessionTime' need to
        exist in the data. 'Date' is used as the main time reference.

        There are two ways to use this method:

            - Usage like :meth:`pandas.DataFrame.resample`: In this case you
              need to specify the 'rule' for resampling and any additional
              keywords will be passed on to :meth:`pandas.Series.resample` to
              create a new time reference. See the pandas method to see which
              options are available.

            - using the 'new_date_ref' keyword a :class:`pandas.Series`
              containing new values for date (dtype :class:`pandas.Timestamp`)
              can be provided. The existing data will be resampled onto this
              new time reference.

        Args:
            rule: Resampling rule for :meth:`pandas.Series.resample`
            new_date_ref: New custom Series of reference dates
            **kwargs: Only in combination with 'rule'; additional parameters
                for :meth:`pandas.Series.resample`
        """
        if rule is not None and new_date_ref is not None:
            raise ValueError("You can only specify one of 'rule' or "
                             "'new_index'")
        if rule is None and new_date_ref is None:
            raise ValueError("You need to specify either 'rule' or "
                             "'new_index'")

        if new_date_ref is None:
            st = pd.Series(index=pd.DatetimeIndex(self['Date']), dtype=int) \
                .resample(rule, **kwargs).asfreq()
            new_date_ref = pd.Series(st.index)

        new_tel = Telemetry(columns=self.columns).__finalize__(self)
        new_tel.loc[:, 'Date'] = new_date_ref

        combined_tel = self.merge_channels(
            Telemetry({'Date': new_date_ref}).__finalize__(self),
            frequency='original'
        )

        mask = combined_tel['Date'].isin(new_date_ref)
        new_tel = combined_tel.loc[mask, :]

        return new_tel

    def fill_missing(self):
        """Calculate missing values in self.

        Only known telemetry channels will be interpolated. Unknown channels
        are skipped and returned unmodified. Interpolation will be done
        according to the default mapping and according to options specified for
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
            if sig_type == 'continuous':
                if ret[ch].dtype == 'object':
                    warnings.warn("Interpolation not possible for telemetry "
                                  "channel because dtype is 'object'")

                method = self._CHANNELS[ch]['method']
                if method in ('nearest', 'zero', 'slinear', 'quadratic',
                              'cubic', 'barycentric', 'polynomial'):
                    # interpolation done using scipy.interpolate.interp1d
                    interp_kwargs = {'fill_value': 'extrapolate'}
                elif method in ('pad', 'backfill', 'ffill', 'bfill'):
                    interp_kwargs = {}
                else:
                    interp_kwargs = {'limit_direction': 'both'}

                ret.loc[:, ch] = ret.loc[:, ch] \
                    .interpolate(method=method, **interp_kwargs)

            elif sig_type == 'discrete':
                with warnings.catch_warnings():
                    # deprecated since pandas 2.2.0; don't opt in to new
                    # behaviour as that would silently change behaviour for
                    # user code; irrelevant here, therefore just filter
                    warnings.filterwarnings(
                        "ignore",
                        "Downcasting object dtype arrays on .fillna, "
                        ".ffill, .bfill is deprecated",
                        FutureWarning
                    )
                    ret.loc[:, ch] = ret.loc[:, ch].ffill().ffill().bfill()
                # first ffill is a method of the resampler object and will
                # ONLY ffill values created during resampling but not already
                # existing NaN values. NaN values already existed because of
                # merging, therefore call ffill a second time as a method of
                # the returned series to fill these too only use bfill after
                # ffill to fix first row

        if 'Source' in ret.columns:
            ret.loc[:, 'Source'] = ret.loc[:, 'Source'] \
                .fillna(value='interpolation')

        if 'Date' in self.columns:
            ret['SessionTime'] = ret['Date'] - self.session.t0_date
        elif isinstance(ret.index, pd.DatetimeIndex):
            # assume index is Date
            ret['SessionTime'] = ret.index - self.session.t0_date
        ret['Time'] = ret['SessionTime'] - ret['SessionTime'].iloc[0]

        return ret

    @classmethod
    def register_new_channel(
            cls,
            name: str,
            signal_type: str,
            interpolation_method: Optional[str] = None
    ):
        """Register a custom telemetry channel.

        Registered telemetry channels are automatically interpolated when
        merging or resampling data.

        Args:
            name: Telemetry channel/column name
            signal_type: One of three possible signal types:
                - 'continuous': Speed, RPM, Distance, ...
                - 'discrete': DRS, nGear, status values, ...
                - 'excluded': Data channel will be ignored during resampling
            interpolation_method: The interpolation method
                which should be used. Can only be specified and is required
                in combination with ``signal_type='continuous'``. See
                :meth:`pandas.Series.interpolate` for possible interpolation
                methods.
        """
        if signal_type not in ('discrete', 'continuous', 'excluded'):
            raise ValueError(f"Unknown signal type {signal_type}.")
        if signal_type == 'continuous' and interpolation_method is None:
            raise ValueError("signal_type='continuous' requires "
                             "interpolation_method to be specified.")

        cls._CHANNELS[name] = {'type': signal_type,
                               'method': interpolation_method}

    def get_first_non_zero_time_index(self):
        """
        Return the first index at which the 'Time' value is not zero
        or NA/NaT
        """
        # find first row where time is not zero; usually this is the first row
        # but sometimes.....
        i_arr = np.where((self['Time'] != pd.Timedelta(0))
                         & ~pd.isna(self['Time']))[0]
        if i_arr.size != 0:
            return np.min(i_arr)
        return None

    def add_differential_distance(
            self,
            drop_existing: bool = True
    ) -> "Telemetry":
        """Add column 'DifferentialDistance' to self.

        This column contains the distance driven between subsequent samples.

        Calls :meth:`calculate_differential_distance` and joins the result
        with self.

        Args:
            drop_existing: Drop and recalculate column if it already exists
        Returns:
            self joined with new column or self if column exists
            and `drop_existing` is False.
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

    def add_distance(self, drop_existing: bool = True) -> "Telemetry":
        """Add column 'Distance' to self.

        This column contains the distance driven since the first sample of
        self in meters.

        The data is produced by integrating the differential distance between
        subsequent laps. You should not apply this function to telemetry of
        many laps simultaneously to reduce integration error.
        Instead apply it only to single laps or few laps at a time!

        Calls :meth:`integrate_distance` and joins the result with self.

        Args:
            drop_existing: Drop and recalculate column if it already exists
        Returns:
            self joined with new column or self if column exists
            and `drop_existing` is False.
        """
        if ('Distance' in self.columns) and not drop_existing:
            return self

        new_dist = pd.DataFrame({'Distance': self.integrate_distance()})
        if 'Distance' in self.columns:
            return self.drop(labels='Distance', axis=1) \
                .join(new_dist, how='outer')

        return self.join(new_dist, how='outer')

    def add_relative_distance(self, drop_existing: bool = True) -> "Telemetry":
        """Add column 'RelativeDistance' to self.

        This column contains the distance driven since the first sample as
        a floating point number where ``0.0`` is the first sample of self
        and ``1.0`` is the last sample.

        This is calculated the same way as 'Distance'
        (see: :meth:`add_distance`). The same warnings apply.

        Args:
            drop_existing: Drop and recalculate column if it already exists
        Returns:
            self joined with new column or self if column exists
            and `drop_existing` is False.
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
        return d.join(pd.DataFrame({'RelativeDistance': rel_dist}),
                      how='outer')

    def add_track_status(self, drop_existing=True):
        """Add column 'TrackStatus' to self.

        This column contains the Track Status for each event as a number.

        See :func:`fastf1.api.track_status_data` for more information.

        Args:
            drop_existing (bool): Drop and recalculate column if it already
                exists.
        Returns:
            :class:`Telemetry`: self joined with new column or self if column
                exists and `drop_existing` is False.
        """
        if 'TrackStatus' in self.columns:
            if drop_existing:
                d = self.drop(labels='TrackStatus', axis=1)
            else:
                return self
        else:
            d = self

        ts = []
        statuses = d.session.track_status['Status']
        events = d.session.t0_date + d.session.track_status['Time']

        # |--- event K ---|--- N telemetry samples ---|--- event K + 1 ---|
        #                           ^
        #                   all samples have the same
        #                 track status because of event K
        #
        # For each track status event, calculate the in between events of the
        # telemetry, up until the next track status event. For each of the in
        # between events add the corresponding track status to an array. At
        # last, create the new column 'TrackStatus' with the array of track
        # statuses.
        for index in range(events.shape[0] - 1):
            curr_e = events[index]
            next_e = events[index+1]

            dd_shape = d[(d['Date'] < next_e) & (d['Date'] >= curr_e)].shape[0]
            ts.extend([statuses[index]] * dd_shape)

        dd_shape = d[(d['Date'] > events.iloc[-1])].shape[0]
        ts.extend([statuses.iloc[-1]] * dd_shape)

        d['TrackStatus'] = ts
        return d

    def add_driver_ahead(self, drop_existing: bool = True) -> "Telemetry":
        """Add column 'DriverAhead' and 'DistanceToDriverAhead' to self.

        DriverAhead: Driver number of the driver ahead as string
        DistanceToDriverAhead: Distance to next car ahead in meters

        .. note:: Cars in the pit lane are currently not excluded from the
            data. They will show up when overtaken on pit straight even if
            they're not technically in front of the car. A fix for this is
            TBD with other improvements.

        This should only be applied to data of single laps or few laps at a
        time to reduce integration error.
        For longer time spans it should be applied per lap and the laps
        should be merged afterwards.
        If you absolutely need to apply it to a whole session, use the legacy
        implementation. Note that data of the legacy implementation will be
        considerably less smooth. (see :mod:`fastf1.legacy`)

        Calls :meth:`calculate_driver_ahead` and joins the result with self.

        Args:
            drop_existing: Drop and recalculate column if it already exists
        Returns:
            self joined with new column or self if column exists
            and `drop_existing` is False.
        """
        if (('DriverAhead' in self.columns)
                and ('DistanceToDriverAhead' in self.columns)):
            if drop_existing:
                d = self.drop(labels='DriverAhead', axis=1) \
                    .drop(labels='DistanceToDriverAhead', axis=1)
            else:
                return self
        else:
            d = self

        drv_ahead, dist, ref_tel = \
            self.calculate_driver_ahead(return_reference=True)

        # calculate driver ahead works with the unmodified source telemetry,
        # therefore it may be necessary to resample the result if self uses
        # a different timebase
        # create a Telemetry object where the calculation results are merged
        # with Date, Time and SessionTime. This is necessary so that the data
        # can be resampled from the reference timebase to the timebase of self
        dtd = ref_tel.loc[:, ('Date', 'Time', 'SessionTime')].join(
            pd.DataFrame({'DriverAhead': drv_ahead,
                          'DistanceToDriverAhead': dist},
                         index=ref_tel.index)
        )

        if ((d['Date'].shape != dtd['Date'].shape)
                or np.any((d['Date'].values
                           != dtd['Date'].values))):
            dtd = dtd.resample_channels(new_date_ref=d["Date"])

        # indices need to match as .join works index-on-index
        dtd['_SelfIndex'] = d.index
        dtd.set_index('_SelfIndex', drop=True, inplace=True)

        return d.join(dtd.loc[:, ('DriverAhead', 'DistanceToDriverAhead')],
                      how='outer')

    def calculate_differential_distance(self) -> pd.Series:
        """Calculate the distance between subsequent samples of self.

        Distance is in meters
        """
        if not all([col in self.columns for col in ('Speed', 'Time')]):
            raise ValueError("Telemetry does not contain required channels "
                             "'Time' and 'Speed'.")
        if self.size != 0:
            dt = self['Time'].dt.total_seconds().diff()
            dt.iloc[0] = self['Time'].iloc[0].total_seconds()
            ds = self['Speed'] / 3.6 * dt
            return ds
        else:
            return pd.Series()

    def integrate_distance(self):
        """Return the distance driven since the first sample of self.

        Distance is in meters. The data is produce by integration.
        Integration error will stack up when used for long slices of data.
        This should therefore only be used for data of single laps or few
        laps at a time.

        Returns:
            :class:`pd.Series`
        """
        ds = self.calculate_differential_distance()
        if not ds.empty:
            return ds.cumsum()
        else:
            return pd.Series()

    def calculate_driver_ahead(self, return_reference: bool = False):
        """Calculate driver ahead and distance to driver ahead.

        Driver ahead: Driver number of the driver ahead as string
        Distance to driver ahead: Distance to the car ahead in meters

        .. note:: This gives a smoother/cleaner result than the legacy
            implementation but WILL introduce integration error when used
            over long distances (more than one or two laps may sometimes be
            considered a long distance). If in doubt, do sanity checks
            (against the legacy version or in another way).

        Args:
            return_reference: Additionally return the reference
                telemetry data slice that is used to calculate the new data.

        Returns:
            driver ahead (numpy.array), distance to driver ahead (numpy.array),
            [reference telemetry (optional, :class:`Telemetry`)]
        """
        t_start = self['SessionTime'].iloc[0]
        t_end = self['SessionTime'].iloc[-1]

        combined_distance = pd.DataFrame()

        # Assume the following lap profile as a catch all for all drivers
        #
        # |---- Lap before ----|---- n Laps between ----|---- Lap after ----|
        #      ^                                           ^
        #      t_start                                     t_end
        # Integration of the distance needs to start at the finish line so
        # that there exists a common zero point. Therefore find the "lap
        # before" which is the lap during which the telemetry slice starts and
        # the "lap after" where the telemetry slice ends.
        # Integrate distance over all relevant laps and slice by t_start and
        # t_end after to get the interesting part only.
        own_laps = self.session.laps[
            self.session.laps['DriverNumber'] == self.driver
            ]
        first_lap_number = ((own_laps[own_laps['LapStartTime'] <= t_start])
                            ['LapNumber'].iloc[-1])
        own_ref_tel = None

        for drv in self.session.drivers:
            if drv not in self.session.car_data:
                continue
            # find correct first relevant lap; very important for correct zero
            # point in distance
            drv_laps = self.session.laps[
                self.session.laps['DriverNumber'] == drv
                ]
            if drv_laps.empty:
                # Only include drivers who participated in this session
                continue
            drv_laps_before = drv_laps[(drv_laps['LapStartTime'] <= t_start)]
            if not drv_laps_before.empty:
                lap_n_before = drv_laps_before['LapNumber'].iloc[-1]
                if lap_n_before < first_lap_number:
                    # driver is behind on track an therefore will cross the
                    # finish line AFTER self therefore above check for
                    # LapStartTime <= t_start is wrong the first relevant lap
                    # is the first lap with LapStartTime > t_start which is
                    # lap_n_before += 1
                    lap_n_before += 1
            else:
                lap_n_before = min(drv_laps['LapNumber'])

            # find last relevant lap so as to no do too much unnecessary
            # calculation later
            drv_laps_after = drv_laps[drv_laps['Time'] >= t_end]
            lap_n_after = drv_laps_after['LapNumber'].iloc[0] \
                if not drv_laps_after.empty \
                else max(drv_laps['LapNumber'])

            # pad_before/_after is used to extend the range of relevant laps
            # by up to one lap in each direction if the previously determined
            # relevant laps at the beginning or end are missing their
            # LapStartTime or Time respectively
            pad_before = 0
            pad_after = 0
            while True:
                relevant_laps = None
                try:
                    relevant_laps = drv_laps[
                        (drv_laps['LapNumber'] >= (lap_n_before - pad_before))
                        & (drv_laps['LapNumber'] <= lap_n_after + pad_after)
                    ]
                except IndexError:
                    break

                if (pad_before >= 1) or (pad_after >= 1):
                    _logger.warning(f"Car number {drv} cannot be located "
                                    f"on track while calculating the distance"
                                    f"between cars.")
                    break

                if relevant_laps.empty:
                    break

                # a relevant timestamp is NaT; pad accordingly and try again
                if relevant_laps['LapStartTime'].iloc[-1] is pd.NaT:
                    pad_before += 1
                    continue
                if relevant_laps['Time'].iloc[0] is pd.NaT:
                    pad_after += 1
                    continue
                break

            if (relevant_laps is None) or relevant_laps.empty:
                continue

            # first slice by lap and calculate distance, so that distance is
            # zero at finish line
            drv_tel = self.session.car_data[drv] \
                .slice_by_lap(relevant_laps)

            if drv_tel.empty:
                continue

            drv_tel = drv_tel.add_distance()

            # now slice again by time to only get the relevant time frame
            drv_tel = drv_tel.slice_by_time(t_start, t_end)
            if drv_tel.empty:
                continue

            if drv == self.driver:
                own_ref_tel = drv_tel

            drv_tel = drv_tel.loc[:, ('SessionTime', 'Distance')] \
                .rename(columns={'Distance': drv})

            drv_tel = drv_tel.set_index('SessionTime')
            combined_distance = combined_distance.join(drv_tel, how='outer')

        # create driver map for array
        drv_map = combined_distance \
            .loc[:, combined_distance.columns != self.driver] \
            .columns.to_numpy()

        own_dst = combined_distance.loc[:, self.driver].to_numpy()
        other_dst = combined_distance \
            .loc[:, combined_distance.columns != self.driver] \
            .to_numpy()
        # replace distance with nan if it does not change
        # prepend first row before diff so that array size stays the same;
        # but missing first sample because of that
        other_dst[
            np.diff(other_dst, n=1, axis=0, prepend=other_dst[0, :]
                    .reshape((1, -1))) == 0
            ] = np.nan

        # resize own_dst to match shape of other_dst for easy subtraction
        own_dst = np.repeat(
            own_dst.reshape((-1, 1)), other_dst.shape[1], axis=1
        )

        delta_dst = other_dst - own_dst
        # substitute nan with inf, else nan is returned as min
        delta_dst[np.isnan(delta_dst)] = np.inf
        # remove cars behind so that neg numbers are not returned as min
        delta_dst[delta_dst < 0] = np.inf

        index_ahead = np.argmin(delta_dst, axis=1)

        drv_ahead = np.array([drv_map[i] for i in index_ahead])
        # remove driver from all inf rows
        drv_ahead[np.all(delta_dst == np.inf, axis=1)] = ''

        dist_to_drv_ahead = np.array(
            [delta_dst[i, index_ahead[i]] for i in range(len(index_ahead))]
        )
        # remove value from all inf rows
        dist_to_drv_ahead[np.all(delta_dst == np.inf, axis=1)] = np.nan

        if return_reference:
            return drv_ahead, dist_to_drv_ahead, own_ref_tel

        return drv_ahead, dist_to_drv_ahead


class Session:
    """Object for accessing session specific data.

    The session class will usually be your starting point. This object will
    have various information about the session.

    .. note:: Most of the data is only available after calling
        :func:`Session.load`
    """

    def __init__(self, event, session_name, f1_api_support=False):
        self.event = event
        """:class:`~fastf1.events.Event`: Reference to the associated event
        object."""
        self.name = session_name
        """str: Name of this session, for example 'Qualifying', 'Race',
        'FP1', ..."""
        self.f1_api_support = f1_api_support
        """bool: The official F1 API supports this event and lap timing
        data and telemetry data are available."""
        self.date = self.event.get_session_date(session_name, utc=True)
        """pandas.Datetime: Date at which this session took place."""

        try:
            _api_date = self.event.get_session_date(session_name, utc=False)
        except ValueError:
            # not all backends provide local timestamps, use UTC then which
            # works in almost all cases
            _api_date = self.date
        self.api_path = api.make_path(
            self.event['EventName'],
            self.event['EventDate'].strftime('%Y-%m-%d'),
            self.name, _api_date.strftime('%Y-%m-%d')
        )
        """str: API base path for this session"""

        if self.date.year <= 2023:
            self._RACE_LIKE_SESSIONS = ('Race', 'Sprint', 'Sprint Qualifying')
            # in 2021, 'Sprint Qualifying' was used as the name for a race-like
            # session that set the grid for the main race
            self._QUALI_LIKE_SESSIONS = ('Qualifying', 'Sprint Shootout')
        else:
            self._RACE_LIKE_SESSIONS = ('Race', 'Sprint')
            self._QUALI_LIKE_SESSIONS = ('Qualifying', 'Sprint Qualifying')
            # starting from 2024, 'Sprint Qualifying' is the name for the
            # qualifying-like session that sets the grid for the Sprint
            # (previously, this was called 'Sprint Shootout')

        self._ergast = ergast.Ergast()

        self._session_info: dict

        self._session_status: pd.DataFrame
        self._race_control_messages: pd.DataFrame

        self._track_status: pd.DataFrame

        self._total_laps: Optional[int]
        self._laps: Laps

        self._t0_date: Optional[pd.Timestamp]
        self._session_start_time: Optional[pd.Timedelta]

        self._car_data: dict
        self._pos_data: dict

        self._weather_data: pd.DataFrame
        self._results: SessionResults

        self._session_split_times: Optional[list] = None

    def __repr__(self):
        return (f"{self.event.year} Season Round {self.event.RoundNumber}: "
                f"{self.event.EventName} - {self.name}")

    def _get_property_warn_not_loaded(self, name):
        if not hasattr(self, name):
            raise DataNotLoadedError(
                "The data you are trying to access has not been loaded yet. "
                "See `Session.load`"
            )
        return getattr(self, name, None)

    @property
    def session_info(self) -> dict:
        """Session information including meeting, session, country and circuit
        names and id keys.

        The id keys are unique identifiers that are used by the F1 APIs.

        (This property holds the data that is returned by the "SessionInfo"
        endpoint of the F1 livetiming API.)
        """
        return self._get_property_warn_not_loaded('_session_info')

    @property
    def drivers(self):
        """:class:`list`: List of all drivers that took part in this
        session; contains driver numbers as string.

        Data is available after calling `Session.load`
        """
        return list(self.results['DriverNumber'].unique())

    @property
    def results(self) -> "SessionResults":
        """:class:`SessionResults`: Session result with driver information.

        Data is available after calling `Session.load`
        """
        return self._get_property_warn_not_loaded('_results')

    @property
    def laps(self) -> "Laps":
        """:class:`Laps`: All laps from all drivers driven in this session.

        Data is available after calling `Session.load` with ``laps=True``
        """
        return self._get_property_warn_not_loaded('_laps')

    @property
    def total_laps(self) -> int:
        """:class:`int`: Originally scheduled number of laps for race-like
        sessions such as Race and Sprint. It takes None as a default value
        for other types of sessions or if data is unavailable

        Data is available after calling `Session.load` with ``laps=True``
        """
        return self._get_property_warn_not_loaded('_total_laps')

    @property
    def weather_data(self):
        """Dataframe containing weather data for this session as received
        from the api. See :func:`fastf1.api.weather_data` for available data
        channels. Each data channel is one row of the dataframe.

        Data is available after calling `Session.load` with ``weather=True``
        """
        return self._get_property_warn_not_loaded('_weather_data')

    @property
    def car_data(self) -> "Telemetry":
        """Dictionary of car telemetry (Speed, RPM, etc.) as received from
        the api by car number (where car number is a string and the telemetry
        is an instance of :class:`Telemetry`)

        Data is available after calling `Session.load` with ``telemetry=True``
        """
        return self._get_property_warn_not_loaded('_car_data')

    @property
    def pos_data(self) -> "Telemetry":
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
    def track_status(self):
        """:class:`pandas.Dataframe`: Track status data as returned by
        :func:`fastf1.api.track_status_data`

        Data is available after calling `Session.load` with ``laps=True``
        """
        return self._get_property_warn_not_loaded('_track_status')

    @property
    def race_control_messages(self):
        """:class:`pandas.Dataframe`: Race Control messages as returned by
        :func:`fastf1.api.race_control_messages`

        Data is available after calling `Session.load` with ``messages=True``
        """
        return self._get_property_warn_not_loaded('_race_control_messages')

    @property
    def session_start_time(self) -> pd.Timedelta:
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

    def load(self, *, laps: bool = True, telemetry: bool = True,
             weather: bool = True, messages: bool = True,
             livedata: LiveTimingData = None):
        """Load session data from the supported APIs.

        This method allows to flexibly load some or all data that FastF1 can
        give you access to. Without specifying any further options, all data
        is loaded by default.

        Usually, it is recommended to load all available data because
        internally FastF1 partially mixes data from multiple endpoints and
        data sources to correct for errors or to add more information. These
        features are optional and may not work when some data is unavailable.
        In these cases, FastF1 will return the data to the best of its
        abilities.

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
            laps: Load laps and session status data.
            telemetry: Load telemetry data.
            weather: Load weather data.
            messages: Load race control messages for the session
            livedata: instead of requesting the data from the api, locally
                saved livetiming data can be used as a data source
        """
        _logger.info(f"Loading data for "
                     f"{self.event['EventName']} - {self.name}"
                     f" [v{fastf1.__version__}]")

        self._load_session_info(livedata=livedata)
        self._load_drivers_results(livedata=livedata)

        if self.f1_api_support:
            if laps:
                self._load_session_status_data(livedata=livedata)
                self._load_total_lap_count(livedata=livedata)
                self._load_track_status_data(livedata=livedata)
                self._load_laps_data(livedata=livedata)
                self._add_first_lap_time_from_ergast()

            if telemetry:
                self._load_telemetry(livedata=livedata)

            if weather:
                self._load_weather_data(livedata=livedata)

            if messages:
                self._load_race_control_messages(livedata=livedata)

        else:
            if any((laps, telemetry, weather, messages)):
                _logger.warning(
                    "Cannot load laps, telemetry, weather, and message data "
                    "because the relevant API is not supported for this "
                    "session."
                )

        self._fix_missing_laps_retired_on_track()
        self._set_laps_deleted_from_rcm()
        self._calculate_quali_like_session_results()

        _logger.info(f"Finished loading data for {len(self.drivers)} "
                     f"drivers: {self.drivers}")

    @soft_exceptions("session info data",
                     "Failed to load session info data!",
                     _logger)
    def _load_session_info(self, livedata=None):
        self._session_info = api.session_info(self.api_path,
                                              livedata=livedata)

    @soft_exceptions("lap timing data", "Failed to load timing data!", _logger)
    def _load_laps_data(self, livedata=None):
        data, _, session_split_times \
            = api._extended_timing_data(self.api_path, livedata=livedata)

        self._session_split_times = session_split_times

        app_data = api.timing_app_data(self.api_path, livedata=livedata)
        _logger.info("Processing timing data...")
        # Matching data and app_data. Not super straightforward
        # Sometimes a car may enter the pit without changing tyres, so
        # new compound is associated with the help of logging time.
        data.drop(columns=['NumberOfPitStops'], inplace=True)
        useful = app_data[['Driver', 'Time', 'Compound', 'StartLaps', 'New',
                           'Stint']]
        useful = useful[~useful['Compound'].isnull()]

        drivers = self.drivers
        if not drivers:
            # no driver list, generate from lap data
            drivers = set(data['Driver'].unique()) \
                .intersection(set(useful['Driver'].unique()))

            _nums_df = pd.DataFrame({'DriverNumber': list(drivers)},
                                    index=list(drivers))
            _info_df = pd.DataFrame(fastf1._DRIVER_TEAM_MAPPING).T

            self._results = SessionResults(_nums_df.join(_info_df),
                                           force_default_cols=True)

            _logger.warning("Generating minimal driver "
                            "list from timing data.")

        df = None
        for i, driver in enumerate(drivers):
            d1 = data[data['Driver'] == driver]
            d2 = useful[useful['Driver'] == driver]
            if d2.shape[0] != len(d2['Stint'].unique()):
                # tyre info includes correction messages that need to be
                # applied before continuing
                d2 = self.__fix_tyre_info(d2)

            is_generated = False
            if not len(d1):
                if self.name in self._RACE_LIKE_SESSIONS and len(d2):
                    # add data for drivers who crashed on the very first lap
                    # as a downside, this potentially adds a nonexistent lap
                    # for drivers who could not start the race
                    is_generated = True
                    result = d1.copy()
                    result.reset_index(drop=True, inplace=True)
                    result['Driver'] = [driver, ]
                    result['NumberOfLaps'] = 1
                    result['Time'] = data['Time'].min()
                    result['IsPersonalBest'] = False
                    result['Compound'] = d2['Compound'].iloc[0]
                    result['TyreLife'] = d2['StartLaps'].iloc[0]
                    result['Stint'] = 0
                    result['New'] = d2['New'].iloc[0]
                else:
                    _logger.warning(f"No lap data for driver {driver}")
                    continue  # no data for this driver; skip

            elif not len(d2):
                result = d1.copy()
                result.reset_index(drop=True, inplace=True)
                result['Compound'] = str()
                result['TyreLife'] = np.nan
                result['Stint'] = 0
                result['New'] = False
                _logger.warning(f"No tyre data for driver {driver}")

            else:
                result = pd.merge_asof(d1, d2, on='Time', by='Driver') \
                    .rename(columns={'StartLaps': 'TyreLife'})

            # add flag that indicates if the data for this lap was generated
            # by FastF1
            result['FastF1Generated'] = is_generated

            # calculate lap start time by setting it to the 'Time' of the
            # previous lap
            laps_start_time = list(result['Time'])[:-1]
            if self.name in self._RACE_LIKE_SESSIONS:
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
                        if self.name in self._RACE_LIKE_SESSIONS:
                            # If this is a race-like session, we can assume the
                            # session restart time as lap start time.
                            # But only set from session status, if it is
                            # actually missing or incorrect (is correct in
                            # case backmarkers are allowed to unlap themselves
                            # at the end of the red flag by completing missing
                            # laps or if there is a formation lap for standing
                            # restart). Decide that correct if lap has laptime
                            if pd.isna(result.iloc[restart_index]['LapTime']):
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

            # set missing lap start times to pit out time, where possible
            mask = (pd.isna(result['LapStartTime'])
                    & (~pd.isna(result['PitOutTime'])))
            result.loc[mask, 'LapStartTime'] = result.loc[mask, 'PitOutTime']

            # remove first lap pitout time if it is before session_start_time
            mask = (result["PitOutTime"] < self.session_start_time) & \
                   (result["NumberOfLaps"] == 1)
            result.loc[mask, 'PitOutTime'] = pd.NaT

            # create total laps counter for each tyre used
            for npit in result['Stint'].unique():
                sel = result['Stint'] == npit
                result.loc[sel, 'TyreLife'] += np.arange(0, sel.sum()) + 1

            df = pd.concat([df, result], sort=False)

        if df is None:
            raise NoLapDataError

        laps = df.reset_index(drop=True)  # noqa: F821

        # rename some columns
        laps.rename(columns={'Driver': 'DriverNumber',
                             'NumberOfLaps': 'LapNumber',
                             'New': 'FreshTyre'}, inplace=True)

        laps['Stint'] += 1  # counting stints from 1

        # add team names and driver names based on driver number
        t_map = {r['DriverNumber']: r['TeamName']
                 for _, r in self.results.iterrows()}
        laps['Team'] = laps['DriverNumber'].map(t_map)
        d_map = {r['DriverNumber']: r['Abbreviation']
                 for _, r in self.results.iterrows()}
        laps['Driver'] = laps['DriverNumber'].map(d_map)

        # add Position based on lap timing
        laps['Position'] = np.NaN  # create empty column
        if self.name in self._RACE_LIKE_SESSIONS:
            for lap_n in laps['LapNumber'].unique():
                # get each drivers lap for the current lap number, sorted by
                # the time when each lap was set
                laps_eq_n = laps.loc[
                    laps['LapNumber'] == lap_n, ('Time', 'Position')
                ].reset_index(drop=True).sort_values(by='Time')

                # number positions and restore previous order by index
                laps_eq_n['Position'] = range(1, len(laps_eq_n) + 1)
                laps.loc[laps['LapNumber'] == lap_n, 'Position'] \
                    = laps_eq_n.sort_index()['Position'].to_list()

        self._add_track_status_to_laps(laps)

        self._laps = Laps(laps, session=self, force_default_cols=True)
        self._check_lap_accuracy()

    @soft_exceptions("generate retired laps",
                     "Failed to generate last laps for drivers that retired"
                     "on track!",
                     _logger)
    def _fix_missing_laps_retired_on_track(self):
        # generate a last lap entry with assumed end time for cars that
        # retired on track

        if not hasattr(self, '_laps'):
            return

        any_new = False
        for drv in self.laps['DriverNumber'].unique():
            drv_laps = self._laps[self.laps['DriverNumber'] == drv]

            if (len(drv_laps) == 1) and drv_laps['FastF1Generated'].iloc[0]:
                # there is only one lap which was added by FastF1, don't
                # generate a followup lap based on that
                continue

            # try to get a valid last timestamp for the last lap
            ref_time = drv_laps['Time'].iloc[-1]
            if pd.isna(ref_time):
                ref_time = drv_laps['LapStartTime'].iloc[-1]
            # split session status at reference timestamp
            # if ref_time is still NaT, next/prev_statuses will be empty
            # after comparison
            next_statuses = self.session_status[
                self.session_status['Time'] > ref_time
            ]
            prev_statuses = self.session_status[
                self.session_status['Time'] <= ref_time
            ]

            if ((not prev_statuses.empty)
                    and (prev_statuses['Status'] == 'Finished').any()):
                # driver finished session correctly, nothing to do
                continue

            if (next_statuses.empty
                    or (not (next_statuses['Status'] == 'Finished').any())):
                # there are no next statuses or no status message indicates
                # that the session finished after the current timestamp
                # -> the data is inconclusive
                continue

            if not pd.isna(drv_laps['PitInTime'].iloc[-1]):
                # last lap was an inlap
                continue

            if ((total_laps := getattr(self, '_total_laps', None)) is not None
                    and (drv_laps.shape[0] >= total_laps)):
                # driver has already completed full race distance
                # can happen because rc message timestamp is slightly off
                continue

            if ((len(drv_laps) >= 2)
                    and (not pd.isna(drv_laps['PitInTime'].iloc[-2]))
                    and pd.isna(drv_laps['PitOutTime'].iloc[-1])):
                # last lap was an inlap and a new lap was started in the pit
                # lane but the car did not leave the pits again (happens if
                # box comes after timing line in pits)
                continue

            next_status = next_statuses.iloc[0]

            if next_status['Status'] == 'Aborted':
                # the session was aborted, use the time when the session was
                # aborted as the end time of the lap
                assumed_end_time = next_status['Time']

            else:
                assumed_end_time = pd.NaT
                if drv in (car_data := getattr(self, '_car_data', {})):
                    # when car_data is available, get the first time at which
                    # the car's speed becomes zero after the reference time and
                    # add 5 seconds of margin
                    try:
                        next_zero_speed_time = car_data[drv].loc[
                            ((car_data[drv]['SessionTime'] > ref_time)
                             & (car_data[drv]['Speed'] == 0.0))
                        ].iloc[0]['SessionTime']
                    except (IndexError, KeyError):
                        pass
                    else:
                        assumed_end_time = next_zero_speed_time

                if pd.isna(assumed_end_time):
                    # still no valid timestamp extracted
                    # fallback: use an assumed lap time of 150 seconds;
                    # this should cover all situations but most of the time
                    # it will be much too long
                    assumed_end_time = ref_time + pd.Timedelta(150, 'sec')

            new_last = pd.DataFrame({
                'LapStartTime': [drv_laps['Time'].iloc[-1]],
                'Time': [assumed_end_time],
                'Driver': [drv_laps['Driver'].iloc[-1]],
                'DriverNumber': [drv_laps['DriverNumber'].iloc[-1]],
                'Team': [drv_laps['Team'].iloc[-1]],
                'LapNumber': [drv_laps['LapNumber'].iloc[-1] + 1],
                'Stint': [drv_laps['Stint'].iloc[-1]],
                'Compound': [drv_laps['Compound'].iloc[-1]],
                'TyreLife': [drv_laps['TyreLife'].iloc[-1] + 1],
                'FreshTyre': [drv_laps['FreshTyre'].iloc[-1]],
                'Position': [np.NaN],
                'FastF1Generated': [True],
                'IsAccurate': [False]
            })

            self._add_track_status_to_laps(new_last)

            # add generated laps at the end and fix sorting at the end
            self._laps = (pd.concat([self._laps, new_last])
                          .__finalize__(self._laps))
            any_new = True

        if any_new:
            # re-sort and re-index to restore correct order of the laps
            self._laps = self._laps \
                .sort_values(by=['DriverNumber', 'LapNumber']) \
                .reset_index(drop=True)

    @soft_exceptions("mark deleted laps from RCM",
                     "Failed to find deleted laps from race control messages!",
                     _logger)
    def _set_laps_deleted_from_rcm(self):
        # parse race control messages to find deleted lap times and
        # set the 'Deleted' flag in self._laps

        if ((not hasattr(self, '_laps'))
                or (not hasattr(self, '_race_control_messages'))):
            return

        # set all to False, then selectively set to True if actually deleted
        self._laps['Deleted'] = False

        msg_pattern = re.compile(
            r"CAR (\d{1,2}) .* TIME (\d:\d\d\.\d\d\d) DELETED - (.*)"
        )
        msg_pattern_reinstated = re.compile(
            r"CAR (\d{1,2}) .* TIME (\d:\d\d\.\d\d\d) .*REINSTATED.*"
        )
        timestamp_pattern = re.compile(r"\d\d:\d\d:\d\d")

        # Do a look-ahead pass to find laps that later were reinstated.
        # This way, the deletion message can be ignored on the main pass which
        # means that we do not need to preserve the state of a lap (e.g.
        # 'IsPersonalBest') in case we'd need to reinstate it again.
        reinstated_laps = list()
        for _, row in self._race_control_messages.iterrows():
            reinstated_match = msg_pattern_reinstated.match(row['Message'])
            if reinstated_match:
                drv = reinstated_match[1]
                deleted_time = to_timedelta(reinstated_match[2])
                reinstated_laps.append((drv, deleted_time))

        # do the main pass where laps are marked as deleted
        for _, row in self._race_control_messages.iterrows():
            match = msg_pattern.match(row['Message'])
            if match:
                drv = match[1]
                deleted_time = to_timedelta(match[2])
                if (drv, deleted_time) in reinstated_laps:
                    # ignore this lap because it was reinstated later
                    continue

                # remove timestamp from reasons because confusingly it is given
                # as local time at the track
                reason = timestamp_pattern.sub("", match[3])

                self._laps.loc[
                    (self._laps['DriverNumber'] == drv)
                    & (self._laps['LapTime'] == deleted_time),
                    ('Deleted', 'IsPersonalBest', 'DeletedReason')
                ] = (True, False, reason)

    @soft_exceptions("quali results",
                     "Failed to calculate quali results from lap times!",
                     _logger)
    def _calculate_quali_like_session_results(self, force=False):
        """Try to calculate quali results from lap times if no results are
        available

        Args:
            force (bool): Force calculation of quali results even if
            results are already available, (default: False)"""

        if self.name not in self._QUALI_LIKE_SESSIONS:
            return

        if not hasattr(self, '_laps'):
            return

        if not self.results['Position'].isna().all() and not force:
            # Don't do anything if results are already available
            # unless force is True
            return

        if self.laps['Deleted'].dtype.name != 'bool':
            _logger.warning(
                "Cannot calculate qualifying results: missing information "
                "about deleted laps. Make sure that race control messages are "
                "being loaded."
            )

        quali_results = (self._laps.loc[:, ['DriverNumber']].copy()
                         .drop_duplicates()
                         .reset_index(drop=True))
        sessions = self._laps.pick_accurate().split_qualifying_sessions()

        for i, session in enumerate(sessions):
            session_name = f'Q{i + 1}'
            if session is not None:
                session = session.pick_quicklaps()  # 107% rule applies per Q
                laps = (
                    session[~session['LapTime'].isna() & ~session['Deleted']]
                    .copy()
                    .groupby(['DriverNumber'])
                    .agg({'LapTime': 'min'})
                    .rename(columns={'LapTime': session_name})
                )

                quali_results = (quali_results
                                 .merge(laps, on='DriverNumber', how='left'))
            else:
                quali_results[session_name] = pd.NaT

        quali_results = quali_results \
            .sort_values(by=['Q3', 'Q2', 'Q1']) \
            .reset_index(drop=True)
        quali_results['Position'] = (quali_results.index + 1).astype('float64')
        quali_results = quali_results.set_index('DriverNumber', drop=True)

        self.results.loc[:, quali_results.columns] = quali_results
        self.results.sort_values(by=['Position'], inplace=True)

    @soft_exceptions("add track status to laps",
                     "Failed to add track status to Laps!",
                     _logger)
    def _add_track_status_to_laps(self, laps):
        # add track status information to each lap

        track_status = getattr(self, '_track_status')
        if track_status is None:
            return

        # ensure track status is not set
        laps['TrackStatus'] = ''

        def _applicator(new_status, current_status):
            if new_status not in current_status:
                return current_status + new_status
            else:
                return current_status

        # -- Track Status Timeline
        #           --> (status before) --|--- status ---|-- next_status -->
        #                                 |              |
        #                                 t              next_t
        # -- Lap Timeline ---------------------------------------------------
        # Case A (end criterion):    ----> Lap --|
        # Case B (start criterion):                |---- Lap --->
        #    (matches B and C)               |-- Lap --|
        # Case C (full overlap):     |---------- Lap ----------|

        if len(track_status['Time']) > 0:
            t = track_status['Time'][0]
            status = track_status['Status'][0]
            for next_t, next_status in zip(track_status['Time'][1:],
                                           track_status['Status'][1:]):

                # Case A: The lap ends during the current status
                sel = ((t <= laps['Time']) & (laps['Time'] <= next_t))
                # Case B: The lap starts during the current status
                sel |= ((t <= laps['LapStartTime'])
                        & (laps['LapStartTime'] <= next_t))
                # Case C: The lap fully contains the current status
                sel |= ((laps['LapStartTime'] <= t) & (next_t <= laps['Time']))

                laps.loc[sel, 'TrackStatus'] \
                    = laps.loc[sel, 'TrackStatus'].apply(
                        lambda curr: _applicator(status, curr)
                )

                t = next_t
                status = next_status

            # process the very last status: any lap that ends after this status
            # started was fully or partially set under this track status
            sel = (t <= laps['Time'])
            laps.loc[sel, 'TrackStatus'] = laps.loc[sel, 'TrackStatus'].apply(
                lambda curr: _applicator(status, curr)
            )

    @soft_exceptions("first lap time",
                     "Failed to add first lap time from Ergast!",
                     _logger)
    def _add_first_lap_time_from_ergast(self):
        # The f1 api does not provide a value for the first lap time.
        # For races, lap times are also available on Ergast -> add the
        # first lap time from there

        if not self.name == 'Race':
            return

        # load lap times for first lap from Ergast and add driver number
        # based on driver id from results
        response = self._ergast.get_lap_times(
            self.event.year, self.event.RoundNumber, lap_number=1
        )
        if response.description.empty:
            _logger.warning("Cannot load lap times for first lap from Ergast. "
                            "Timing data is not available for this session.")
            return  # no data returned

        first_lap_times = response.content[0].set_index('driverId')

        drv_num_ref = self.results \
                          .loc[:, ('DriverNumber', 'DriverId')] \
                          .set_index('DriverId')
        first_lap_times = first_lap_times.join(drv_num_ref)

        # set the first lap time for each driver individually
        # (.merge, .update, ... not easily usable because not shared index)
        failed_drvs = list()
        for _, row in first_lap_times.iterrows():
            drv = row['DriverNumber']
            try:
                self._laps.loc[
                    (self._laps['LapNumber'] == 1)
                    & (self._laps['DriverNumber'] == drv),
                    'LapTime'
                ] = row['time']
            except Exception as exc:
                _logger.debug(f"Failed to add first lap time for "
                              f"driver '{drv}'", exc_info=exc)
                failed_drvs.append(drv)

        if failed_drvs:
            _logger.warning(f"Failed to add first lap time from Ergast for "
                            f"drivers: {failed_drvs}")

    @soft_exceptions("track status data", "Failed to load track status data!",
                     _logger)
    def _load_track_status_data(self, livedata=None):
        track_status = api.track_status_data(self.api_path, livedata=livedata)
        self._track_status = pd.DataFrame(track_status)
        if not self._track_status.size:
            _logger.warning("Could not load any valid session status "
                            "information!")

    @soft_exceptions("total lap count", "Failed to load total lap count!",
                     _logger)
    def _load_total_lap_count(self, livedata=None):
        # Get the number of originally scheduled laps
        # Lap count data only exists for race-like sessions.
        if self.name in self._RACE_LIKE_SESSIONS:
            try:
                lap_count = api.lap_count(self.api_path, livedata=livedata)
                # A race-like session can have multiple intended total laps,
                # the first one being the original schedule
                self._total_laps = lap_count['TotalLaps'][0]
            except IndexError:
                self._total_laps = None
                _logger.warning("No lap count data for this session.")
        else:
            self._total_laps = None

    @soft_exceptions("session status data",
                     "Failed to load session status data!", _logger)
    def _load_session_status_data(self, livedata=None):
        # check when a session was started; for a race this indicates the
        # start of the race
        session_status = api.session_status_data(self.api_path,
                                                 livedata=livedata)
        for i in range(len(session_status['Status'])):
            if session_status['Status'][i] == 'Started':
                self._session_start_time = session_status['Time'][i]
                break
        else:
            _logger.warning("Failed to determine `Session.session_start_time`")
            self._session_start_time = None
        self._session_status = pd.DataFrame(session_status)

    def __fix_tyre_info(self, df):
        # Sometimes later corrections of tyre info are sent through the api.
        # These updates only set values that need to be changed and all other
        # values are none-like. Therefore, if correction updates exist, for
        # each stint the first received information is taken and then
        # iteratively updated with non-NA values from all updates for this
        # stint (in the order received).
        corrected = pd.DataFrame(
            {'Stint': df['Stint'].unique()}, columns=df.columns
        )

        for i, stint in enumerate(df['Stint'].unique()):
            for _, row in df.loc[df['Stint'] == stint].iterrows():
                # iterate over all messages (rows) that were received for this
                # stint
                if pd.isna(corrected.loc[i]).all():
                    # first message: set as a whole (performance)
                    corrected.loc[i] = row
                    continue

                for key, value in row.items():
                    # correction: update existing values only if new value
                    # is non-na
                    if pd.isna(value):
                        continue
                    if (key == 'Time') and not pd.isna(corrected.loc[i, key]):
                        # always keep first time stamp instead of corrected
                        # corresponds to pit stop time
                        continue
                    corrected.loc[i, key] = value

        # reapply original dtypes per column
        for col_name, dtype in zip(df.columns, df.dtypes):
            corrected[col_name] = corrected[col_name].astype(dtype)

        return corrected

    @soft_exceptions("lap accuracy check",
                     "Failed to perform lap accuracy check!",
                     _logger)
    def _check_lap_accuracy(self):
        """
        Accuracy validation; simples yes/no validation. Currently only relies
        on provided information which can't catch all problems
        """
        # TODO: check for outliers in lap start position
        for drv in self.drivers:
            is_accurate = list()
            prev_lap = None
            integrity_errors = 0
            for _, lap in self.laps[self.laps['DriverNumber'] == drv] \
                    .iterrows():
                lap_integrity_ok = True
                # require existence, non-existence and specific values for
                # some variables
                check_1 = (pd.isnull(lap['PitInTime'])
                           & pd.isnull(lap['PitOutTime'])
                           & (not lap['FastF1Generated'])
                           # slightly paranoid, allow only green + yellow flag
                           & (lap['TrackStatus'] in ('1', '2', '12', '21'))
                           & (not pd.isnull(lap['LapTime']))
                           & (not pd.isnull(lap['Sector1Time']))
                           & (not pd.isnull(lap['Sector2Time']))
                           & (not pd.isnull(lap['Sector3Time'])))

                if check_1:
                    # only do check 2 if all necessary values for this check
                    # are even available;
                    # sum of sector times should be almost equal to lap time
                    # (tolerance 3ms)
                    check_2 = np.allclose(
                        np.sum((lap['Sector1Time'], lap['Sector2Time'],
                                lap['Sector3Time'])).total_seconds(),
                        lap['LapTime'].total_seconds(),
                        atol=0.003, rtol=0, equal_nan=False
                    )
                    if not check_2:
                        lap_integrity_ok = False
                else:
                    check_2 = False  # data not available means fail

                if prev_lap is not None:
                    # first lap after safety car often has timing issues
                    # (as do all laps under safety car)
                    check_3 = (prev_lap['TrackStatus'] != '4')
                else:
                    check_3 = True  # no previous lap, no SC error

                pre_check_4 = (((not pd.isnull(lap['Time']))
                               & (not pd.isnull(lap['LapTime'])))
                               and (prev_lap is not None)
                               and (not pd.isnull(prev_lap['Time'])))

                if pre_check_4:  # needed condition for check_4
                    time_diff = np.sum((lap['Time'],
                                        -1 * prev_lap['Time'])).total_seconds()
                    lap_time = lap['LapTime'].total_seconds()
                    # If the difference between the two times is within a
                    # certain tolerance, the lap time data is considered
                    # to be valid.
                    check_4 = np.allclose(time_diff, lap_time,
                                          atol=0.003, rtol=0, equal_nan=False)

                    if not check_4:
                        lap_integrity_ok = False

                else:
                    check_4 = True

                if not lap_integrity_ok:
                    integrity_errors += 1

                result = check_1 and check_2 and check_3 and check_4
                is_accurate.append(result)
                prev_lap = lap

            if len(is_accurate) > 0:
                self._laps.loc[
                    self.laps['DriverNumber'] == drv, 'IsAccurate'
                ] = is_accurate
            else:
                _logger.warning(f"Failed to perform lap accuracy check - all "
                                f"laps marked as inaccurate (driver {drv})")
                self._laps.loc[
                    self.laps['DriverNumber'] == drv, 'IsAccurate'
                ] = False  # default should be inaccurate

            # necessary to explicitly cast to bool
            self._laps[['IsAccurate']] \
                = self._laps[['IsAccurate']].astype(bool)

            if integrity_errors > 0:
                _logger.warning(
                    f"Driver {drv: >2}: Lap timing integrity check "
                    f"failed for {integrity_errors} lap(s)")

    # @soft_exceptions("results", "Failed to load results data!", _logger)
    def _load_drivers_results(self, *, livedata=None):
        # get list of drivers and results

        driver_info_f1 = None
        driver_info_ergast = None

        info_cols = ('Abbreviation', 'FirstName', 'LastName', 'TeamName',
                     'FullName', 'DriverNumber')

        # try loading from both sources if they are supported
        # data is joined afterwards depending on availability
        if self.f1_api_support:
            # load driver info from f1 api
            driver_info_f1 = self._drivers_from_f1_api(livedata=livedata)
        if not self.event.is_testing():
            # load driver info from ergast
            driver_info_ergast = self._drivers_results_from_ergast(
                load_drivers=True, load_results=True
            )

        # set results from either source or join if both data is available
        # use driver info from F1 as primary source, only fall back to Ergast
        # if unavailable
        # use results from Ergast, unavailable from F1 API

        # no data
        if (driver_info_f1 is None) and (driver_info_ergast is None):  # LP1
            _logger.warning("Failed to load driver list and "
                            "session results!")
            self._results = SessionResults(force_default_cols=True)

        # only Ergast data
        elif driver_info_f1 is None:  # LP2
            self._results = SessionResults(driver_info_ergast,
                                           force_default_cols=True)

        # only F1 data
        elif driver_info_ergast is None:  # LP3
            self._results = SessionResults(driver_info_f1,
                                           force_default_cols=True)

        # F1 and Ergast data
        else:
            missing_drivers = list(set(driver_info_ergast['DriverNumber'])
                                   .difference(driver_info_f1['DriverNumber']))
            # drivers are missing if DNSed (did not start)
            # in that case, pull more information from Ergast for these drivers

            join_cols \
                = list(set(driver_info_ergast.columns).difference(info_cols))

            self._results = SessionResults(
                driver_info_f1.join(driver_info_ergast.loc[:, join_cols],
                                    how='outer'),
                force_default_cols=True
            )

            if missing_drivers:
                self._results.loc[missing_drivers, info_cols] \
                    = driver_info_ergast.loc[missing_drivers, info_cols]

                # set (Grid)Position to NaN instead of default last or zero to
                # make the DNS more obvious
                self._results.loc[missing_drivers,
                                  ('Position', 'GridPosition')] = np.NaN

        if (dupl_mask := self._results.index.duplicated()).any():
            dupl_drv = list(self._results.index[dupl_mask])
            _logger.warning(f"Session results contain duplicate entries for "
                            f"driver(s) {dupl_drv}")

        if 'Position' in self._results:
            self._results = self._results.sort_values('Position')

    def _drivers_from_f1_api(self, *, livedata=None):
        try:
            f1di = api.driver_info(self.api_path, livedata=livedata)
        except Exception as exc:
            _logger.warning("Failed to load extended driver information!")
            _logger.debug("Exception while loading driver list", exc_info=exc)
            driver_info = {}
        else:
            driver_info = collections.defaultdict(list)
            for key1, key2 in {
                'RacingNumber': 'DriverNumber',
                'BroadcastName': 'BroadcastName',
                'Tla': 'Abbreviation', 'TeamName': 'TeamName',
                'TeamColour': 'TeamColor', 'FirstName': 'FirstName',
                'LastName': 'LastName', 'HeadshotUrl': 'HeadshotUrl',
                'CountryCode': 'CountryCode'
            }.items():
                for entry in f1di.values():
                    driver_info[key2].append(entry.get(key1))
            if 'FirstName' in driver_info and 'LastName' in driver_info:
                for first, last in zip(driver_info['FirstName'],
                                       driver_info['LastName']):
                    driver_info['FullName'].append(f"{first} {last}")
        return pd.DataFrame(driver_info, index=driver_info['DriverNumber'])

    def _drivers_results_from_ergast(
            self, *, load_drivers=False, load_results=False
    ) -> Optional[pd.DataFrame]:
        if self.name in self._RACE_LIKE_SESSIONS + self._QUALI_LIKE_SESSIONS:
            session_name = self.name
        else:
            # this is a practice session, use drivers from race session but
            # don't load results
            session_name = 'Race'
            load_results = False

        @soft_exceptions("ergast result data",
                         "Failed to load result data from Ergast!",
                         _logger)
        def _get_data():
            if session_name == 'Race':
                return self._ergast.get_race_results(
                    self.event.year, self.event.RoundNumber
                )

            elif session_name == 'Qualifying':
                return self._ergast.get_qualifying_results(
                    self.event.year, self.event.RoundNumber
                )

            # double condition because of reuse of the "Sprint Qualifying" name
            # for a race-like session in 2018 and a quali-like session in 2024+
            # Ergast only supports the race-like sprint results.
            elif ('Sprint' in session_name
                    and session_name in self._RACE_LIKE_SESSIONS):
                return self._ergast.get_sprint_results(
                    self.event.year, self.event.RoundNumber
                )

            else:
                # TODO: Use Ergast when it supports quali-like sprint results
                # return self._ergast.get_sprint_shootout_results(
                #     self.event.year, self.event.RoundNumber
                # )
                return None

        response = _get_data()

        if not response or not response.content:
            if (('Sprint' in session_name)
                    and (session_name in self._QUALI_LIKE_SESSIONS)):
                _logger.warning(f"{session_name} is not supported by "
                                f"Ergast! Limited results are calculated from "
                                f"timing data.")
            else:
                _logger.warning("No result data for this session available on "
                                "Ergast! (This is expected for recent "
                                "sessions)")
            return None

        data = response.content[0]

        rename_return = {
            'number': 'DriverNumber',
            'driverId': 'DriverId',
            'constructorId': 'TeamId'
        }

        if load_drivers:
            rename_return.update({
                'driverCode': 'Abbreviation',
                'givenName': 'FirstName',
                'familyName': 'LastName',
                'constructorName': 'TeamName',
            })

        if load_results:
            rename_return.update({
                'position': 'Position',
            })

            if session_name in self._RACE_LIKE_SESSIONS:
                rename_return.update({
                    'positionText': 'ClassifiedPosition',
                    'grid': 'GridPosition',
                    'status': 'Status',
                    'points': 'Points',
                    'totalRaceTime': 'Time'
                })

            if session_name in self._QUALI_LIKE_SESSIONS:
                rename_return.update({
                    'Q1': 'Q1',
                    'Q2': 'Q2',
                    'Q3': 'Q3',
                })

        # ergast does not provide all data for old sessions
        # (example: 'driverCode'), select only existing columns
        existing_keys = set(rename_return.keys())\
            .intersection(data.columns)

        d = data.loc[:, list(existing_keys)] \
            .rename(columns=rename_return) \
            .astype({'DriverNumber': 'str'})

        if load_drivers:
            d['FullName'] = d['FirstName'] + " " + d['LastName']

        d.set_index('DriverNumber', drop=False, inplace=True)

        return d

    @soft_exceptions("weather data", "Failed to load weather data!", _logger)
    def _load_weather_data(self, livedata=None):
        weather_data = api.weather_data(self.api_path, livedata=livedata)
        weather_df = pd.DataFrame(weather_data)
        self._weather_data = weather_df

    @soft_exceptions("race control messages",
                     "Failed to load race control messages!", _logger)
    def _load_race_control_messages(self, livedata=None):
        race_control_messages = api.race_control_messages(self.api_path,
                                                          livedata=livedata)
        race_control_df = pd.DataFrame(race_control_messages)
        self._race_control_messages = race_control_df

    @soft_exceptions("telemetry data", "Failed to load telemetry data!",
                     _logger)
    def _load_telemetry(self, livedata: LiveTimingData = None):
        """Load telemetry data from the API.

        This method can only be called after :meth:`load_laps` has been
        called. You will usually just want to call :meth:`load_laps` with
        the optional ``with_telemetry=True`` argument instead of calling this
        method separately. The result will be the same.

        The raw data is divided into car data (Speed, RPM, ...) and position
        data (coordinates, on/off track). For each of the two types an
        instance of :class:`Telemetry` is created per driver. The properties
        :attr:`Session.car_data` and :attr:`Session.pos_data` are dictionaries
        which hold the the `Telemetry` objects keyed by driver number.

        The telemetry data can either be accessed through the above mentioned
        attributes or conveniently on a per ap basis through :class:`Lap`
        and :class:`Laps`. See :class:`Telemetry` on how to work with the
        telemetry data.

        Note that this method additionally calculates :attr:`Session.t0_date`
        and adds a `LapStartDate` column to :attr:`Session.laps`.

        Args:
            livedata: instead of requesting the data from the api, locally
                saved livetiming data can be used as a data source
        """
        try:
            car_data = api.car_data(self.api_path, livedata=livedata)
        except api.SessionNotAvailableError:
            _logger.warning("Car telemetry data is unavailable!")
            car_data = {}

        try:
            pos_data = api.position_data(self.api_path, livedata=livedata)
        except api.SessionNotAvailableError:
            _logger.warning("Car position data is unavailable!")
            pos_data = {}

        self._calculate_t0_date(car_data, pos_data)

        self._car_data = dict()
        self._pos_data = dict()

        for (src, processed) in ((car_data, self._car_data),
                                 (pos_data, self._pos_data)):
            if not src:
                continue

            for drv in self.drivers:
                # drop and recalculate timestamps based on 'Date', because
                # 'Date' has a higher resolution
                try:
                    drv_car = Telemetry(src[drv].drop(labels='Time', axis=1),
                                        session=self, driver=drv,
                                        drop_unknown_channels=True)
                except KeyError:
                    # not pos data or car data exists for this driver
                    continue

                drv_car['Date'] = drv_car['Date'].dt.round('ms')

                drv_car['Time'] = drv_car['Date'] - self.t0_date
                drv_car['SessionTime'] = drv_car['Time']

                processed[drv] = drv_car

        if hasattr(self, '_laps'):
            self._laps['LapStartDate'] \
                = self._laps['LapStartTime'] + self.t0_date

    def get_driver(self, identifier) -> "DriverResult":
        """
        Get a driver object which contains additional information about a
        driver.

        Args:
            identifier (str): driver's three letter identifier (for
                example 'VER') or driver number as string

        Returns:
            instance of :class:`DriverResult`
        """
        mask = ((self.results['Abbreviation'] == identifier)
                | (self.results['DriverNumber'] == identifier))
        if not mask.any():
            raise ValueError(f"Invalid driver identifier '{identifier}'")
        return self.results[mask].iloc[0]

    def get_circuit_info(self) -> Optional[CircuitInfo]:
        """Returns additional information about the circuit that hosts this
        event.

        This information includes the location of corners, marshal lights,
        marshal sectors and the rotation of the track map. Note that the data
        is manually created and therefore not highly accurate, but it is useful
        for annotating data visualizations.

        See :class:`~fastf1.mvapi.CircuitInfo` for detailed information.
        """
        circuit_key = self.session_info['Meeting']['Circuit']['Key']

        if ((circuit_key == 149)
                and (self.session_info['Meeting']['Circuit']['ShortName']
                     == 'Mugello')):
            circuit_key = 146

        circuit_info = get_circuit_info(year=self.event.year,
                                        circuit_key=circuit_key)
        circuit_info.add_marker_distance(
            reference_lap=self.laps.pick_fastest()
        )
        return circuit_info

    def _calculate_t0_date(self, *tel_data_sets: dict):
        """
        Calculate the date timestamp at which data for this session is
        starting.

        This does not mark the start of a race (or other sessions). This marks
        the start of the data which is sometimes far before.

        This function sets :attr:`self.t0_date` which is an internally
        required offset for some calculations.

        The current assumption is that the latest date which can be calculated
        is correct. (Based on the timestamp with the least delay.)

        Args:
            tel_data_sets: Dictionaries containing car telemetry data or
                position data
        """
        date_offset = None

        data = list()
        for tds in tel_data_sets:
            data.extend(list(tds.values()))

        for d in data:
            new_offset = max(d['Date'] - d['Time'])
            if date_offset is None or new_offset > date_offset:
                date_offset = new_offset

        if date_offset is None:
            self._t0_date = None
            _logger.warning("Failed to determine `Session.t0_date`!")
        else:
            self._t0_date = date_offset.round('ms')


class Laps(BaseDataFrame):
    """Object for accessing lap (timing) data of multiple laps.

    Args:
        *args: passed through to :class:`pandas.DataFrame` super class
        session: instance of session class; required for
          full functionality
        **kwargs: passed through to :class:`pandas.DataFrame`
          super class

    This class allows for easily picking specific laps from all laps in a
    session. It implements some additional functionality on top of the usual
    `pandas.DataFrame` functionality. Among others, the laps' associated
    telemetry data can be accessed.

    If for example you want to get the fastest lap of Bottas you can narrow
    it down like this::

        import fastf1

        session = fastf1.get_session(2019, 'Bahrain', 'Q')
        session.load()
        best_bottas = session.laps.pick_driver('BOT').pick_fastest()

        print(best_bottas['LapTime'])
        # Timedelta('0 days 00:01:28.256000')

    Slicing this class will return :class:`Laps` again for slices containing
    multiple rows. Single rows will be returned as :class:`Lap`.

    The following information is available per lap (one DataFrame column
    for each):

        - **Time** (pandas.Timedelta): Session time when the lap time was
          set (end of lap)
        - **Driver** (string): Three letter driver identifier
        - **DriverNumber** (str): Driver number
        - **LapTime** (pandas.Timedelta): Recorded lap time.
          Officially deleted lap times will *not* be deleted here.
          Deleting laps is currently not supported.
        - **LapNumber** (float): Recorded lap number
        - **Stint** (float): Stint number
        - **PitOutTime** (pandas.Timedelta): Session time when car exited
          the pit
        - **PitInTime** (pandas.Timedelta): Session time when car entered
          the pit
        - **Sector1Time** (pandas.Timedelta): Sector 1 recorded time
        - **Sector2Time** (pandas.Timedelta): Sector 2 recorded time
        - **Sector3Time** (pandas.Timedelta): Sector 3 recorded time
        - **Sector1SessionTime** (pandas.Timedelta): Session time when the
          Sector 1 time was set
        - **Sector2SessionTime** (pandas.Timedelta): Session time when the
          Sector 2 time was set
        - **Sector3SessionTime** (pandas.Timedelta): Session time when the
          Sector 3 time was set
        - **SpeedI1** (float): Speedtrap sector 1 [km/h]
        - **SpeedI2** (float): Speedtrap sector 2 [km/h]
        - **SpeedFL** (float): Speedtrap at finish line [km/h]
        - **SpeedST** (float): Speedtrap on longest straight (Not sure) [km/h]
        - **IsPersonalBest** (bool): Flag that indicates whether this lap is
          the official personal best lap of a driver. If any lap of a driver
          is quicker than their respective personal best lap, this means that
          the quicker lap is invalid and not counted. For example, this can
          happen if the track limits were exceeded.
        - **Compound** (str): Tyres event specific compound name: SOFT, MEDIUM,
          HARD, INTERMEDIATE, WET (the actual underlying compounds C1 to C5 are
          not differentiated).
        - **TyreLife** (float): Laps driven on this tire (includes laps in
          other sessions for used sets of tires)
        - **FreshTyre** (bool): Tyre had TyreLife=0 at stint start, i.e.
          was a new tire
        - **Team** (str): Team name
        - **LapStartTime** (pandas.Timedelta): Session time at the start of
          the lap
        - **LapStartDate** (pandas.Timestamp): Timestamp at the start of
          the lap
        - **TrackStatus** (str): A string that contains track status numbers
          for all track status that occurred
          during this lap. The meaning of the track status numbers is
          explained in :func:`fastf1.api.track_status_data`.
          For filtering laps by track status, you may want to use
          :func:`Laps.pick_track_status`.
        - **Position** (float): Position of the driver at the end of each lap.
          This value is NaN for FP1, FP2, FP3, Sprint Shootout, and Qualifying
          as well as for crash laps.
        - **Deleted** (Optional[bool]): Indicates that a lap was deleted by
          the stewards, for example because of a track limits violation.
          This data is only available when race control messages are loaded.
        - **DeletedReason** (str): Gives the reason for a lap time deletion.
          This data is only available when race control messages are loaded.
        - **FastF1Generated** (bool): Indicates that this lap was added by
          FastF1. Such a lap will generally have very limited information
          available and information is partly interpolated or based on
          reasonable assumptions. Cases were this is used are, for example,
          when a partial last lap is added for drivers that retired on track.
        - **IsAccurate** (bool): Indicates that the lap start and end time are
          synced correctly with other laps. Do not confuse this with the
          accuracy of the lap time or sector times. They are always considered
          to be accurate if they exist!
          If this value is True, the lap has passed as basic accuracy check
          for timing data. This does not guarantee accuracy but laps marked
          as inaccurate need to be handled with caution. They might contain
          errors which can not be spotted easily.
          Laps need to satisfy the following criteria to be marked
          as accurate:

            - not an inlap or outlap
            - set under green or yellow flag (the api sometimes has issues
              with data from SC/VSC laps)
            - is not the first lap after a safety car period
              (issues with SC/VSC might still appear on the first lap
              after it has ended)
            - has a value for lap time and all sector times
            - the sum of the sector times matches the lap time
              (If this were to ever occur, it would also be logged separately
              as a data integrity error. You usually don't need to worry about
              this.)
    """

    _COL_TYPES = {
        'Time': 'timedelta64[ns]',
        'Driver': str,
        'DriverNumber': str,
        'LapTime': 'timedelta64[ns]',
        'LapNumber': 'float64',
        'Stint': 'float64',
        'PitOutTime': 'timedelta64[ns]',
        'PitInTime': 'timedelta64[ns]',
        'Sector1Time': 'timedelta64[ns]',
        'Sector2Time': 'timedelta64[ns]',
        'Sector3Time': 'timedelta64[ns]',
        'Sector1SessionTime': 'timedelta64[ns]',
        'Sector2SessionTime': 'timedelta64[ns]',
        'Sector3SessionTime': 'timedelta64[ns]',
        'SpeedI1': 'float64',
        'SpeedI2': 'float64',
        'SpeedFL': 'float64',
        'SpeedST': 'float64',
        'IsPersonalBest': bool,
        'Compound': str,
        'TyreLife': 'float64',
        'FreshTyre': bool,
        'Team': str,
        'LapStartTime': 'timedelta64[ns]',
        'LapStartDate': 'datetime64[ns]',
        'TrackStatus': str,
        'Position': 'float64',  # need to support NaN
        'Deleted': Optional[bool],
        'DeletedReason': str,
        'FastF1Generated': bool,
        'IsAccurate': bool
    }

    _metadata = ['session']
    _internal_names = BaseDataFrame._internal_names + ['telemetry']
    _internal_names_set = set(_internal_names)

    QUICKLAP_THRESHOLD = 1.07
    """Used to determine 'quick' laps. Defaults to the 107% rule."""

    def __init__(self,
                 *args,
                 session: Optional[Session] = None,
                 force_default_cols: bool = False,
                 **kwargs):

        if force_default_cols:
            kwargs['columns'] = list(self._COL_TYPES.keys())

        super().__init__(*args, **kwargs)

        if force_default_cols:
            # apply column specific dtypes
            for col, _type in self._COL_TYPES.items():
                if col not in self.columns:
                    continue
                convert = True
                if self[col].isna().all():
                    if isinstance(_type, str):
                        self[col] = pd.Series(dtype=_type)
                    elif type(None) in typing.get_args(_type):
                        # column is optional, cannot force dtype, set to None
                        self[col] = None
                        convert = False
                    else:
                        self[col] = _type()

                if convert:
                    self[col] = self[col].astype(_type)

        self.session = session

    @property
    def _constructor_sliced_horizontal(self) -> Callable[..., "Lap"]:
        return Lap

    @cached_property
    def telemetry(self) -> Telemetry:
        """Telemetry data for all laps in `self`

        This is a cached (!) property for :meth:`get_telemetry`. It will
        return the same value as `get_telemetry` but cache the result so that
        the involved processing is only done once.

        This is mainly provided for convenience and backwards compatibility.

        See :meth:`get_telemetry` for more information.

        .. note:: Telemetry can only be returned if `self` contains laps of
            one driver only.

        Returns:
            instance of :class:`Telemetry`"""
        return self.get_telemetry()

    def get_telemetry(self,
                      *,
                      frequency: Union[int, Literal['original'], None] = None
                      ) -> Telemetry:
        """Telemetry data for all laps in `self`

        Telemetry data is the result of merging the returned data from
        :meth:`get_car_data` and :meth:`get_pos_data`. This means that
        telemetry data at least partially contains interpolated values!
        Telemetry data additionally already has computed channels added
        (e.g. Distance).

        This method is provided for convenience and compatibility reasons. But
        using it does usually not produce the most accurate possible result.
        It is recommended to use :meth:`get_car_data` or :meth:`get_pos_data`
        when possible. This is also faster if merging of car and position data
        is not necessary and if not all computed channels are needed.

        Resampling during merging is done according to the frequency set by
        :attr:`~Telemetry.TELEMETRY_FREQUENCY`.

        .. note:: Telemetry can only be returned if `self` contains laps of one
            driver only.

        Args:
            frequency: Optional frequency to overwrite the default value set by
                :attr:`~Telemetry.TELEMETRY_FREQUENCY`.
                (Either string 'original' or integer for a frequency in Hz)

        Returns:
            instance of :class:`Telemetry`
        """
        pos_data = self.get_pos_data(pad=1, pad_side='both')
        car_data = self.get_car_data(pad=1, pad_side='both')

        # calculate driver ahead from data without padding to
        # prevent out of bounds errors
        drv_ahead = car_data.iloc[1:-1] \
            .add_driver_ahead() \
            .loc[:, ('DriverAhead', 'DistanceToDriverAhead',
                     'Date', 'Time', 'SessionTime')]

        car_data = car_data.add_distance().add_relative_distance()
        car_data = car_data.merge_channels(drv_ahead, frequency=frequency)
        merged = pos_data.merge_channels(car_data, frequency=frequency)
        return merged.slice_by_lap(self, interpolate_edges=True)

    def get_car_data(self, **kwargs) -> Telemetry:
        """
        Car data for all laps in `self`

        Slices the car data in :attr:`Session.car_data` using this set of laps
        and returns the result.

        The data returned by this method does not contain computed telemetry
        channels. The can be added by calling the appropriate `add_*()` method
        on the returned telemetry object..

        .. note:: Car data can only be returned if `self` contains laps of
            one driver only.

        Args:
            **kwargs: Keyword arguments are passed to
                :meth:`Telemetry.slice_by_lap`

        Returns:
            instance of :class:`Telemetry`
        """
        drv_num = self['DriverNumber'].unique()
        if len(drv_num) == 0:
            raise ValueError("Cannot slice telemetry because self contains "
                             "no driver number!")
        if len(drv_num) > 1:
            raise ValueError("Cannot slice telemetry because self contains "
                             "Laps of multiple drivers!")
        drv_num = drv_num[0]
        car_data = self.session.car_data[drv_num] \
            .slice_by_lap(self, **kwargs) \
            .reset_index(drop=True)

        return car_data

    def get_pos_data(self, **kwargs) -> Telemetry:
        """
        Pos data for all laps in `self`

        Slices the position data in :attr:`Session.pos_data` using this set
        of laps and returns the result.

        .. note:: Position data can only be returned if `self` contains laps
            of one driver only.

        Args:
            **kwargs: Keyword arguments are passed to
                :meth:`Telemetry.slice_by_lap`

        Returns:
            instance of :class:`Telemetry`
        """
        drv_num = self['DriverNumber'].unique()
        if len(drv_num) == 0:
            raise ValueError("Cannot slice telemetry because self contains "
                             "no driver number!")
        if len(drv_num) > 1:
            raise ValueError("Cannot slice telemetry because self contains "
                             "Laps of multiple drivers!")
        drv_num = drv_num[0]
        pos_data = self.session.pos_data[drv_num] \
            .slice_by_lap(self, **kwargs) \
            .reset_index(drop=True)
        return pos_data

    def get_weather_data(self) -> pd.DataFrame:
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
                                  Time Driver  ... WindDirection WindSpeed
            0   0 days 00:21:01.358000    LEC  ...           212       2.0
            1   0 days 00:22:21.775000    LEC  ...           207       2.7
            2   0 days 00:24:03.991000    LEC  ...           210       2.3
            3   0 days 00:25:24.117000    LEC  ...           207       3.2
            4   0 days 00:27:09.461000    LEC  ...           238       1.8
            ..                     ...    ...  ...           ...       ...
            270 0 days 00:36:38.150000    KUB  ...           192       0.9
            271 0 days 00:38:37.508000    KUB  ...           213       0.9
            272 0 days 00:33:27.227000    VER  ...           183       1.3
            273 0 days 00:35:05.865000    VER  ...           272       0.8
            274 0 days 00:36:47.787000    VER  ...           339       1.1
            <BLANKLINE>
            [275 rows x 38 columns]
        """  # noqa: E501 (due to long examples and doctest output)
        wd = [lap.get_weather_data() for _, lap in self.iterrows()]
        if wd:
            return pd.concat(wd, axis=1).T
        else:
            return pd.DataFrame(columns=self.session.weather_data.columns)

    def pick_lap(self, lap_number: int) -> "Laps":
        """Return all laps of a specific LapNumber in self based on LapNumber.

        .. deprecated:: 3.1.0
            pick_lap is deprecated and will be removed in a
            future release. Use :func:`pick_laps` instead.

            lap_1 = session_laps.pick_lap(1)
            lap_25 = session_laps.pick_lap(25)

        Args:
            lap_number (int): Lap number

        Returns:
            instance of :class:`Laps`
        """
        warnings.warn(("pick_lap is deprecated and will be removed in a "
                       "future release. Use pick_laps instead."),
                      DeprecationWarning)
        return self[self['LapNumber'] == lap_number]

    def pick_laps(self, lap_numbers: Union[int, Iterable[int]]) -> "Laps":
        """Return all laps of a specific LapNumber or a list of LapNumbers
        in self. ::

            lap_1 = session_laps.pick_laps(1)
            lap_10_to_20 = session_laps.pick_lap(range(10, 21))

        Args:
            lap_numbers: int for matching a single lap,
                an iterable of ints for matching multiple laps

        Returns:
            instance of :class:`Laps`
        """
        if isinstance(lap_numbers, (int, float)):
            lap_numbers = [lap_numbers, ]

        for i in lap_numbers:
            if isinstance(i, float) and not i.is_integer():
                raise ValueError(f"Invalid value {i} in `lap_numbers`")

        return self[self["LapNumber"].isin(lap_numbers)]

    def pick_driver(self, identifier: Union[int, str]) -> "Laps":
        """Return all laps of a specific driver in self based on the driver's
        three letters identifier or based on the driver number.

        .. deprecated:: 3.1.0
            pick_driver is deprecated and will be removed in a future release.
            Use :func:`pick_drivers` instead.

            perez_laps = session_laps.pick_driver('PER')
            bottas_laps = session_laps.pick_driver(77)
            kimi_laps = session_laps.pick_driver('RAI')

        Args:
            identifier (str or int): Driver abbreviation or number

        Returns:
            instance of :class:`Laps`
        """
        warnings.warn(("pick_driver is deprecated and will be removed"
                       " in a future release. Use pick_drivers instead."),
                      DeprecationWarning)
        identifier = str(identifier)
        if identifier.isdigit():
            return self[self['DriverNumber'] == identifier]
        else:
            return self[self['Driver'] == identifier]

    def pick_drivers(self,
                     identifiers: Union[int, str, Iterable[Union[int, str]]]
                     ) -> "Laps":
        """Return all laps of the specified driver or drivers in self based
        on the drivers' three letters identifier or the driver number. ::

            ver_laps = session_laps.pick_drivers("VER")
            some_drivers_laps = session_laps.pick_drivers([5, 'BOT', 7])

        Args:
            identifiers: Multiple driver abbreviations or driver numbers
                (can be mixed)

        Returns:
            instance of :class:`Laps`
        """
        if isinstance(identifiers, (int, str)):
            identifiers = [identifiers, ]

        names = [n.upper() for n in identifiers if not str(n).isdigit()]
        numbers = [str(n) for n in identifiers if str(n).isdigit()]
        drv, num = self['Driver'], self['DriverNumber']

        return self[(drv.isin(names) | num.isin(numbers))]

    def pick_team(self, name: str) -> "Laps":
        """Return all laps of a specific team in self based on the
        team's name.

        .. deprecated:: 3.1.0
            pick_team is deprecated and will be removed in a future release.
            Use :func:`pick_teams` instead.

            mercedes = session_laps.pick_team('Mercedes')
            alfa_romeo = session_laps.pick_team('Alfa Romeo')

        Have a look to :attr:`fastf1.plotting.TEAM_COLORS` for a quick
        reference on team names.

        Args:
            name (str): Team name

        Returns:
            instance of :class:`Laps`
        """
        warnings.warn(("pick_team is deprecated and will be removed"
                       " in a future release. Use pick_teams instead."),
                      DeprecationWarning)
        return self[self['Team'] == name]

    def pick_teams(self, names: Union[str, Iterable[str]]) -> "Laps":
        """Return all laps of the specified team or teams in self based
        on the team names. ::

            rbr_laps = session_laps.pick_teams("Red Bull")
            some_drivers_laps = session_laps.pick_teams(['Haas', 'Alpine'])

        Args:
            names: A single team name or team names

        Returns:
            instance of :class:`Laps`
        """
        if isinstance(names, str):
            return self[self['Team'] == names]

        return self[self['Team'].isin(names)]

    def pick_fastest(self, only_by_time: bool = False) -> "Lap":
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
        # TODO: Deprecate returning empty lap object when there is no lap
        # that matches definion
        if only_by_time:
            laps = self  # all laps
        else:
            # select only laps marked as personal fastest
            laps = self.loc[self['IsPersonalBest'] == True]  # noqa: E712

        if not laps.size:
            warnings.warn(("In the future, `None` will be returned instead of "
                           "an empty `Lap` object when there are no laps that "
                           "satisfy the definition for fastest lap."),
                          FutureWarning)
            return Lap(index=self.columns, dtype=object).__finalize__(self)

        if laps['LapTime'].isna().all():
            warnings.warn(("In the future, `None` will be returned instead of "
                           "an empty `Lap` object when there is no recorded "
                           "LapTime for any lap."),
                          FutureWarning)
            return Lap(index=self.columns, dtype=object).__finalize__(self)

        lap = laps.loc[laps['LapTime'].idxmin()]
        if isinstance(lap, pd.DataFrame):
            # Multiple laps, same time
            lap = lap.iloc[0]  # take first clocked

        return lap

    def pick_quicklaps(self, threshold: Optional[float] = None) -> "Laps":
        """Return all laps with `LapTime` faster than a certain limit. By
        default, the threshold is 107% of the best `LapTime` of all laps
        in self.

        Args:
            threshold: custom threshold coefficient
                (e.g. 1.05 for 105%)

        Returns:
            instance of :class:`Laps`
        """
        if threshold is None:
            threshold = Laps.QUICKLAP_THRESHOLD
        time_threshold = self['LapTime'].min() * threshold

        return self[self['LapTime'] < time_threshold]

    def pick_tyre(self, compound: str) -> "Laps":
        """Return all laps in self which were done on a specific compound.

        .. deprecated:: 3.1.0
            pick_tyre is deprecated and will be removed in a future release.
            Use :func:`pick_compounds` instead.

        Args:
            compound: may be "SOFT", "MEDIUM", "HARD",
                "INTERMEDIATE" or "WET"

        Returns:
            instance of :class:`Laps`
        """
        warnings.warn(("pick_tyre is deprecated and will be removed"
                       " in a future release. Use pick_compound instead."),
                      DeprecationWarning)
        return self[self['Compound'] == compound.upper()]

    def pick_compounds(self, compounds: Union[str, Iterable[str]]) -> "Laps":
        """Return all laps in self which were done on some specific compounds.
        ::

            soft_laps = session_laps.pick_compounds("SOFT")
            slick_laps = session_laps.pick_compounds(['SOFT', 'MEDIUM', "HARD])

        Args:
            compounds: may be "SOFT", "MEDIUM", "HARD", "INTERMEDIATE" or "WET"

        Returns:
            instance of :class:`Laps`
        """
        if isinstance(compounds, str):
            return self[self['Compound'] == compounds.upper()]

        return self[self['Compound'].isin([i.upper() for i in compounds])]

    def pick_track_status(self, status: str, how: str = 'equals') -> "Laps":
        """Return all laps set under a specific track status.

        Args:
            status (str): The track status as a string, e.g. '1'
            how (str): one of 'equals'/'contains'/'excludes'/'any'/'none'

                - how='equals': status='2' will only match '2'.
                - how='contains': status='2' will also match '267' and similar
                - how='excludes': status='26' will not match '267' but will
                  match '27'
                - how='any': status='26' will match both '2' and '6'
                - how='none': status='26' will not match either '12' or '16'

        Returns:
            instance of :class:`Laps`
        """
        if how == 'equals':
            return self[self['TrackStatus'] == status]
        elif how == 'contains':
            return self[self['TrackStatus'].str.contains(status, regex=False)]
        elif how == 'excludes':
            return self[~self['TrackStatus'].str.contains(status, regex=False)]
        elif how == 'any':
            return self[self['TrackStatus'].str.contains('|'.join(status),
                                                         regex=True)]
        elif how == 'none':
            return self[~self['TrackStatus'].str.contains('|'.join(status),
                                                          regex=True)]
        else:
            raise ValueError(f"Invalid value '{how}' for kwarg 'how'")

    def pick_wo_box(self) -> "Laps":
        """Return all laps which are NOT in laps or out laps.

        Returns:
            instance of :class:`Laps`
        """
        return self[pd.isnull(self['PitInTime'])
                    & pd.isnull(self['PitOutTime'])]

    def pick_box_laps(self, which: str = 'both') -> "Laps":
        """Return all laps which are either in-laps, out-laps, or both.
        Note: a lap could be an in-lap and an out-lap at the same time.
        In that case, it will get returned regardless of the 'which'
        parameter.

        Args:
            which (str): one of 'in'/'out'/'both'

                - which='in': only laps in which the driver entered
                  the pit lane are returned
                - which='out': only laps in which the driver exited
                  the pit lane are returned
                - which='both': both in-laps and out-laps are returned

        Returns:
            instance of :class:`Laps`
        """
        if which == 'in':
            return self[~pd.isnull(self['PitInTime'])]
        elif which == 'out':
            return self[~pd.isnull(self['PitOutTime'])]
        elif which == 'both':
            return self[~pd.isnull(self['PitInTime'])
                        | ~pd.isnull(self['PitOutTime'])]
        else:
            raise ValueError(f"Invalid value '{which}' for kwarg 'which'")

    def pick_not_deleted(self) -> "Laps":
        """Return all laps whose lap times are NOT deleted.

        Returns:
            instance of :class:`Laps`
        """
        if 'Deleted' in self.columns:
            return self[~self['Deleted']]
        else:
            raise DataNotLoadedError("The Deleted column is only available "
                                     "when race control messages are loaded. "
                                     "See `Session.load`")

    def pick_accurate(self) -> "Laps":
        """Return all laps which pass the accuracy validation check
        (lap['IsAccurate'] is True).

        Returns:
            instance of :class:`Laps`
        """
        return self[self['IsAccurate']]

    def split_qualifying_sessions(self) -> List[Optional["Laps"]]:
        """Splits a lap object into individual laps objects for each
        qualifying session.

        This method only works for qualifying sessions and requires that
        session status data is loaded.

        Example::

            q1, q2, q3 = laps.split_qualifying_sessions()

        Returns: Three :class:`Laps` objects, one for Q1, Q2 and Q3
            each. If any of these sessions was cancelled, ``None`` will be
            returned instead of :class:`Laps`.
        """
        if self.session.name not in self.session._QUALI_LIKE_SESSIONS:
            raise ValueError("Session is not a qualifying session!")
        elif self.session.session_status is None:
            raise ValueError("Session status data is unavailable!")

        if self.session._session_split_times:
            # prefer using the split times that were generated by the timing
            # data parser, those are more reliable
            split_times = self.session._session_split_times.copy()
        else:
            # get the timestamps for 'Started' from the session status data
            # note that after a red flag, a session can be 'Started' as well.
            # Therefore, it is necessary to check for red flags and ignore
            # the first 'Started' entry after a red flag.
            split_times = list()
            session_suspended = False
            for _, row in self.session.session_status.iterrows():
                if row['Status'] == 'Started':
                    if not session_suspended:
                        split_times.append(row['Time'])
                    else:
                        session_suspended = False
                elif row['Status'] == 'Aborted':
                    session_suspended = True
                elif row['Status'] == 'Finished':
                    # This handles the case when a qualifying session isn't
                    # restarted after a red flag.
                    session_suspended = False

        # add the very last timestamp, to get an end for the last interval
        split_times.append(self.session.session_status['Time'].iloc[-1])
        laps = [None, None, None]
        for i in range(len(split_times) - 1):
            # split by start time instead of end time, because the split times
            # that are generated from timing data may not account for crashed
            # cars being returned or having a generated lap time that results
            # in a late 'Time' value!
            laps[i] = self[(self['LapStartTime'] > split_times[i])
                           & (self['LapStartTime'] < split_times[i + 1])]
            if laps[i].empty:
                laps[i] = None
        return laps

    def iterlaps(self, require: Optional[Iterable] = None) \
            -> Iterable[Tuple[int, "Lap"]]:
        """Iterator for iterating over all laps in self.

        This method wraps :meth:`pandas.DataFrame.iterrows`.
        It additionally provides the `require` keyword argument.

        Args:
            require: Require is a list of column/telemetry channel names. All
                names listed in `require` must exist in the data and have a
                non-null value (tested with :func:`pandas.is_null`). The
                iterator only yields laps for which this is true. If require is
                left empty, the iterator will yield all laps.
        Yields:
            (index, lap): label and an instance of :class:`Lap`
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


class Lap(BaseSeries):
    """
    Object for accessing lap (timing) data of a single lap.

    This class wraps :class:`pandas.Series`. It provides extra functionality
    for accessing a lap's associated
    telemetry data.

    Args:
        *args: passed through to :class:`pandas.Series` super class
        **kwargs: passed through to :class:`pandas.Series`
          super class
    """
    _metadata = ['session']
    _internal_names = BaseSeries._internal_names + ['telemetry']
    _internal_names_set = set(_internal_names)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @cached_property
    def telemetry(self) -> Telemetry:
        """Telemetry data for this lap

        This is a cached (!) property for :meth:`get_telemetry`. It will
        return the same value as `get_telemetry` but cache the result so
        that the involved processing is only done once.

        This is mainly provided for convenience and backwards compatibility.

        See :meth:`get_telemetry` for more information.

        Returns:
            instance of :class:`Telemetry`"""
        return self.get_telemetry()

    def get_telemetry(self,
                      *,
                      frequency: Union[int, Literal['original'], None] = None
                      ) -> Telemetry:
        """Telemetry data for this lap

        Telemetry data is the result of merging the returned data from
        :meth:`get_car_data` and :meth:`get_pos_data`. This means that
        telemetry data at least partially contains interpolated values!
        Telemetry data additionally already has computed channels added
        (e.g. Distance).

        This method is provided for convenience and compatibility reasons. But
        using it does usually not produce the most accurate possible result.
        It is recommended to use :meth:`get_car_data` or :meth:`get_pos_data`
        when possible. This is also faster if merging of car and position data
        is not necessary and if not all computed channels are needed.

        Resampling during merging is done according to the frequency set by
        :attr:`~Telemetry.TELEMETRY_FREQUENCY` if not overwritten with the
        ``frequency`` argument.

        Args:
            frequency: Optional frequency to overwrite default value set by
                :attr:`~Telemetry.TELEMETRY_FREQUENCY`.
                (Either string 'original' or integer for a frequency in Hz)

        Returns:
            instance of :class:`Telemetry`
        """
        pos_data = self.get_pos_data(pad=1, pad_side='both')
        car_data = self.get_car_data(pad=1, pad_side='both')

        # calculate driver ahead from data without padding to
        # prevent out of bounds errors
        drv_ahead = car_data.iloc[1:-1] \
            .add_driver_ahead() \
            .loc[:, ('DriverAhead', 'DistanceToDriverAhead',
                     'Date', 'Time', 'SessionTime')]

        car_data = car_data.add_distance().add_relative_distance()
        car_data = car_data.merge_channels(drv_ahead, frequency=frequency)
        merged = pos_data.merge_channels(car_data, frequency=frequency)
        return merged.slice_by_lap(self, interpolate_edges=True)

    def get_car_data(self, **kwargs) -> Telemetry:
        """Car data for this lap

        Slices the car data in :attr:`Session.car_data` using this lap and
        returns the result.

        The data returned by this method does not contain computed telemetry
        channels. The can be added by calling the appropriate `add_*()`
        method on the returned telemetry object.

        Args:
            **kwargs: Keyword arguments are passed to
                :meth:`Telemetry.slice_by_lap`

        Returns:
            instance of :class:`Telemetry`
        """
        car_data = self.session.car_data[self['DriverNumber']] \
            .slice_by_lap(self, **kwargs) \
            .reset_index(drop=True)
        return car_data

    def get_pos_data(self, **kwargs) -> Telemetry:
        """Pos data for all laps in `self`

        Slices the position data in :attr:`Session.pos_data` using this lap
        and returns the result.

        Args:
            **kwargs: Keyword arguments are passed to
                :meth:`Telemetry.slice_by_lap`

        Returns:
            instance of :class:`Telemetry`
        """
        pos_data = self.session.pos_data[self['DriverNumber']] \
            .slice_by_lap(self, **kwargs) \
            .reset_index(drop=True)

        return pos_data

    def get_weather_data(self) -> pd.Series:
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
        mask = ((self.session.weather_data['Time'] >= self['LapStartTime'])
                & (self.session.weather_data['Time'] <= self['Time']))
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


class SessionResults(BaseDataFrame):
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
          First letter of the drivers first name plus the drivers full last
          name in all capital letters. (e.g. 'P GASLY')

        - ``FullName`` | :class:`str` |
          The drivers full name (e.g. "Pierre Gasly")

        - ``Abbreviation`` | :class:`str` |
          The drivers three letter abbreviation (e.g. "GAS")

        - ``DriverId`` | :class:`str` |
          ``driverId`` that is used by the Ergast API

        - ``TeamName`` | :class:`str` |
          The team name (short version without title sponsors)

        - ``TeamColor`` | :class:`str` |
          The color commonly associated with this team (hex value)

        - ``TeamId`` | :class:`str` |
          ``constructorId`` that is used by the Ergast API

        - ``FirstName`` | :class:`str` |
          The drivers first name

        - ``LastName`` | :class:`str` |
          The drivers last name

        - ``HeadshotUrl`` | :class:`str` |
          The URL to the driver's headshot

        - ``CountryCode`` | :class:`str` |
          The driver's country code (e.g. "FRA")

        - ``Position`` | :class:`float` |
          The drivers finishing position (values only given if session is
          'Race', 'Qualifying', 'Sprint Shootout', 'Sprint', or
          'Sprint Qualifying').

        - ``ClassifiedPosition`` | :class:`str` |
          The official classification result for each driver.
          This is either an integer value if the driver is
          officially classified or one of "R" (retired), "D" (disqualified),
          "E" (excluded), "W" (withdrawn), "F" (failed to qualify) or
          "N" (not classified).

        - ``GridPosition`` | :class:`float` |
          The drivers starting position (values only given if session is
          'Race', 'Sprint', 'Sprint Shootout' or 'Sprint Qualifying')

        - ``Q1`` | :class:`pd.Timedelta` |
          The drivers best Q1 time (values only given if session is
          'Qualifying' or 'Sprint Shootout')

        - ``Q2`` | :class:`pd.Timedelta` |
          The drivers best Q2 time (values only given if session is
          'Qualifying' or 'Sprint Shootout')

        - ``Q3`` | :class:`pd.Timedelta` |
          The drivers best Q3 time (values only given if session is
          'Qualifying' or 'Sprint Shootout')

        - ``Time`` | :class:`pd.Timedelta` |
          The drivers total race time (values only given if session is
          'Race', 'Sprint', 'Sprint Shootout' or 'Sprint Qualifying' and the
          driver was not more than one lap behind the leader)

        - ``Status`` | :class:`str` |
          A status message to indicate if and how the driver finished the race
          or to indicate the cause of a DNF. Possible values include but are
          not limited to 'Finished', '+ 1 Lap', 'Crash', 'Gearbox', ...
          (values only given if session is 'Race', 'Sprint', 'Sprint Shootout'
          or 'Sprint Qualifying')

        - ``Points`` | :class:`float` |
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
        'DriverId': str,
        'TeamName': str,
        'TeamColor': str,
        'TeamId': str,
        'FirstName': str,
        'LastName': str,
        'FullName': str,
        'HeadshotUrl': str,
        'CountryCode': str,
        'Position': 'float64',
        'ClassifiedPosition': str,
        'GridPosition': 'float64',
        'Q1': 'timedelta64[ns]',
        'Q2': 'timedelta64[ns]',
        'Q3': 'timedelta64[ns]',
        'Time': 'timedelta64[ns]',
        'Status': str,
        'Points': 'float64'
    }

    def __init__(self, *args, force_default_cols: bool = False, **kwargs):
        if force_default_cols:
            kwargs['columns'] = list(self._COL_TYPES.keys())
        super().__init__(*args, **kwargs)

        # apply column specific dtypes
        if force_default_cols:
            for col, _type in self._COL_TYPES.items():
                if col not in self.columns:
                    continue
                if self[col].isna().all():
                    if isinstance(_type, str):
                        self[col] = pd.Series(dtype=_type)
                    else:
                        self[col] = _type()

                self[col] = self[col].astype(_type)

    @property
    def _constructor_sliced_horizontal(self) -> Callable[..., "DriverResult"]:
        return DriverResult


class DriverResult(BaseSeries):
    """This class provides driver and result information for a single driver.

    This class subclasses a :class:`pandas.Series` and the usual methods
    provided by pandas can be used to work with the data.

    For information on which data is available, see :class:`SessionResults`.

    .. note:: This class is usually not instantiated directly. You should
        create a session and access the driver result through
        :func:`Session.get_driver` or by slicing the session result.

    Args:
        *args: passed through to :class:`pandas.Series` superclass
        **kwargs: passed through to :class:`pandas.Series` superclass

    .. versionadded:: 2.2
    """

    _internal_names = BaseSeries._internal_names + ['dnf']
    _internal_names_set = set(_internal_names)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def dnf(self) -> bool:
        """True if driver did not finish"""
        return not (self.Status[3:6] == 'Lap' or self.Status == 'Finished')


class DataNotLoadedError(Exception):
    """Raised if an attempt is made to access data that has not been loaded
    yet."""
    pass


class NoLapDataError(Exception):
    """
    Raised if the API request does not fail but there is no usable data
    after processing the result.
    """
    def __init__(self, *args):
        super(NoLapDataError, self).__init__("Failed to load session because "
                                             "the API did not provide any "
                                             "usable data.")


class InvalidSessionError(Exception):
    """Raised if no session for the specified event name, type and year
    can be found."""

    def __init__(self, *args):
        super(InvalidSessionError, self).__init__(
            "No matching session can be found."
        )
