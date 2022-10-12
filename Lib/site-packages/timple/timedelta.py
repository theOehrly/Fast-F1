"""
.. currentmodule:: timple.timedelta


Formatters, locators and converters
===================================


Timple timedelta format
-----------------------

Timple represents timedeltas using floating point numbers.
A value of 1.0 corresponds to a timedelta of 1 day.

There are two helper functions for converting between timedelta-like
values and Timple's floating point timedeltas.

.. autosummary::
   :nosignatures:

   timedelta2num
   num2timedelta


A wide range of specific and general purpose timedelta tick locators and
formatters are provided in this module.
You should check Matplotlib's documentation for general information on tick
locators and formatters at :mod:`matplotlib.ticker`.
These tickers and locators are described below.


Timedelta tickers
-----------------

The available date tickers are:

* :class:`FixedTimedeltaLocator`: Locate microseconds, seconds, minutes, hours
  or days (the 'base unit') in fixed intervals.
  Tick locations will always be multiples of the selected interval.
  E.g. if the interval is 15 and the base unit 'seconds', the locator will
  pick 0, 15, 30, 45 seconds as tick locations::

    loc = FixedTimedeltaLocator(base_unit='seconds', interval='15')

* :class:`AutoTimedeltaLocator`: On autoscale, this class picks the best base
  unit (e.g. 'minutes') and the best interval to set the view limits and the
  tick locations.
  Tick locations will always be a multiple of the chosen interval.


Timedelta formatters
--------------------

The available date formatters are:

* :class:`AutoTimedeltaFormatter`: attempts to figure out the best format to
  use. This is most useful when used with the `AutoTimedeltaLocator`.

* :class:`ConciseTimedeltaFormatter`: also attempts to figure out the best
  format to use, and to make the format as compact as possible while still
  having complete date information. The formatter will make use of axis
  offsets to shorten the length of the tick label when possible.
  This is most useful when used with the `AutoTimedeltaLocator`.

* :class:`TimedeltaFormatter` : use custom timedelta format strings and a
  custom axis offset.


Timedelta format strings
------------------------

Timple uses format strings to define the format of the tick labels and axis
offset.

The format strings for timedeltas defined here are similar to
`datetime.datetime.strftime` format strings but they are **not** the
same and **not** compatible.

+--------------+---------------------------+----------------------------------+
| Directive    | Meaning                   | Example                          |
+==============+===========================+==================================+
| ``%d``       | The number of days        | 0, 1, 2, ...                     |
+--------------+---------------------------+----------------------------------+
| ``%h``       | Hours up to one day       | 00 ... 23                        |
|              | (with zero-padding)       |                                  |
+--------------+---------------------------+----------------------------------+
| ``%H``       | Total number of hours     | 0, 1, 2, .... 50, 51, ...        |
+--------------+---------------------------+----------------------------------+
| ``%m``       | Minutes up to one hour    | 00 ... 59                        |
|              | (with zero-padding)       |                                  |
+--------------+---------------------------+----------------------------------+
| ``%M``       | Total number of minutes   | 0, 1, 2, ..... 100, 101, ...     |
+--------------+---------------------------+----------------------------------+
| ``%s``       | Seconds up to one minute  | 00 ... 59                        |
|              | (with zero-padding)       |                                  |
+--------------+---------------------------+----------------------------------+
| ``%S``       | Total number of seconds   | 0, 1, 2, ..... 100, 101, ...     |
+--------------+---------------------------+----------------------------------+
| ``%ms``      | Milliseconds up to one    | 000 ... 999                      |
|              | second                    |                                  |
|              | (with zero-padding)       |                                  |
+--------------+---------------------------+----------------------------------+
| ``%us``      | Microseconds up to one    | 000 ... 999                      |
|              | millisecond               |                                  |
|              | (with zero-padding)       |                                  |
+--------------+---------------------------+----------------------------------+
| ``%day``     | The string 'day' with     |  'day' or 'days'                 |
|              | correct plural            |                                  |
+--------------+---------------------------+----------------------------------+


The following two functions can be used to format timedelta values with a
format string:

.. autosummary::
   :nosignatures:

   strftimedelta
   strftdnum


String formatting examples::

    >>> import datetime

    >>> fmt = "%d %day, %h:%m"
    >>> td = datetime.timedelta(days=10, hours=6, minutes=14)
    >>> strftimedelta(td, fmt)
    10 days, 06:14

2.5 days as days and hours::

    >>> fmt = "%d %day and %h:00"
    >>> td = datetime.timedelta(days=2, hours=12)
    >>> strftimedelta(td, fmt)
    2 days and 12:00

2.5 days as hours only::

    >>> fmt = "%H:00"
    >>> td = datetime.timedelta(days=2, hours=12)
    >>> strftimedelta(td, fmt)
    60:00

Seconds with millisecond and microseconds as decimals::

    >>> fmt = "%S.%ms%us seconds"
    >>> td = datetime.timedelta(seconds=2, milliseconds=351, microseconds=16)
    >>> strftimedelta(td, fmt)
    2.351016 seconds


Timedelta converters
--------------------

Timple provides two timedelta converters which can be registered through
Matplotlib's unit conversion interface (see `matplotlib.units`):

.. autosummary::
   :nosignatures:

   TimedeltaConverter
   ConciseTimedeltaConverter

Usually you don't need to interact with these converters.
When enabling Timple, one of them is automatically registered with Matplotlib.
(see :mod:`timple.timple`)

The only difference between these converters is the default formatter that is
used. `ConciseTimdeltaConverter` will use the `ConsciseTimedeltaFormatter` by
default while `TimedeltaConverter` will use `AutoTimedeltaFormatter`.


API Reference
-------------
"""
import datetime
import string
import math
import re

import numpy as np

import matplotlib as mpl
from matplotlib import ticker, units

try:
    # only available for matplotlib version >= 3.4.0
    from matplotlib.dates import _wrap_in_tex
except ImportError:
    def _wrap_in_tex(text):
        p = r'([a-zA-Z]+)'
        ret_text = re.sub(p, r'}$\1$\\mathdefault{', text)

        # Braces ensure dashes are not spaced like binary operators.
        ret_text = '$\\mathdefault{' + ret_text.replace('-', '{-}') + '}$'
        ret_text = ret_text.replace('$\\mathdefault{}$', '')
        return ret_text

__all__ = ('num2timedelta', 'timedelta2num',
           'TimedeltaFormatter', 'ConciseTimedeltaFormatter',
           'AutoTimedeltaFormatter',
           'TimedeltaLocator', 'AutoTimedeltaLocator', 'FixedTimedeltaLocator',
           'TimedeltaConverter', 'ConciseTimedeltaConverter')


"""
Time-related constants.
"""
HOURS_PER_DAY = 24.
MIN_PER_HOUR = 60.
SEC_PER_MIN = 60.

MINUTES_PER_DAY = MIN_PER_HOUR * HOURS_PER_DAY

SEC_PER_HOUR = SEC_PER_MIN * MIN_PER_HOUR
SEC_PER_DAY = SEC_PER_HOUR * HOURS_PER_DAY

MUSECONDS_PER_DAY = 1e6 * SEC_PER_DAY


def _td64_to_ordinalf(d):
    """
    Convert `numpy.timedelta64` or an ndarray of those types to a number of
    days as float. Roundoff is float64 precision. Practically: microseconds
    for up to 292271 years, milliseconds for larger time spans.
    (see `numpy.timedelta64`).
    """

    # the "extra" ensures that we at least allow the dynamic range out to
    # seconds.  That should get out to +/-2e11 years.
    dseconds = d.astype('timedelta64[s]')
    extra = (d - dseconds).astype('timedelta64[ns]')
    dt = dseconds.astype(np.float64)
    dt += extra.astype(np.float64) / 1.0e9
    dt = dt / SEC_PER_DAY

    NaT_int = np.timedelta64('NaT').astype(np.int64)
    d_int = d.astype(np.int64)
    try:
        dt[d_int == NaT_int] = np.nan
    except TypeError:
        if d_int == NaT_int:
            dt = np.nan
    return dt


def timedelta2num(t):
    """
    Convert timedelta objects to Timple's timedeltas.

    Parameters
    ----------
    t : `datetime.timedelta`, `numpy.timedelta64` or `pandas.Timedelta`
        or sequences of these

    Returns
    -------
    float or sequence of floats
        Number of days
    """
    if hasattr(t, "values"):
        # this unpacks pandas series or dataframes...
        t = t.values

    # make an iterable, but save state to unpack later:
    iterable = np.iterable(t)
    if not iterable:
        t = [t]

    t = np.asarray(t)
    if not t.size:
        # deals with an empty array...
        return t.astype('float64')

    if hasattr(t.take(0), 'value'):
        # elements are pandas objects; temporarily convert data to numbers
        # pandas nat is defined as the minimum value of int64,
        # replace all 'min int' values with the string 'nat' and convert the
        # array to the dtype of the first non-nat value
        values = np.asarray([x.value for x in t], dtype='object')
        nat_mask = (np.iinfo('int64').min == values)
        if not all(nat_mask):
            _ttype = t[~nat_mask].take(0).to_numpy().dtype
        else:
            _ttype = 'timedelta64[us]'  # default in case of all NaT
        t = np.where(nat_mask, 'nat', values).astype(_ttype)

    # convert to datetime64 or timedelta64 arrays, if not already:
    if not np.issubdtype(t.dtype, np.timedelta64):
        t = t.astype('timedelta64[us]')

    t = _td64_to_ordinalf(t)

    return t if iterable else t[0]


_ordinalf_to_timedelta_np_vectorized = np.vectorize(
    lambda x: datetime.timedelta(days=x), otypes="O")


def num2timedelta(x):
    """
    Convert number of days to a `~datetime.timedelta` object.

    If *x* is a sequence, a sequence of `~datetime.timedelta` objects will
    be returned.

    Parameters
    ----------
    x : float, sequence of floats
        Number of days. The fraction part represents hours, minutes, seconds.

    Returns
    -------
    `datetime.timedelta` or list[`datetime.timedelta`]
    """
    return _ordinalf_to_timedelta_np_vectorized(x).tolist()


class _TimedeltaFormatTemplate(string.Template):
    # formatting template for datetime-like formatter strings
    delimiter = '%'


def strftimedelta(td, fmt_str):
    """
    Return a string representing a timedelta, controlled by an explicit
    format string.

    Arguments
    ---------
    td : datetime.timedelta
    fmt_str : str
        format string
    """
    # *_t values are not partially consumed by there next larger unit
    # e.g. for timedelta(days=1.5): d=1, h=12, H=36
    s_t = td.total_seconds()
    sign = '-' if s_t < 0 else ''
    s_t = abs(s_t)

    d, s = divmod(s_t, SEC_PER_DAY)
    m_t, s = divmod(s, SEC_PER_MIN)
    h, m = divmod(m_t, MIN_PER_HOUR)
    h_t, _ = divmod(s_t, SEC_PER_HOUR)

    us = td.microseconds
    ms, us = divmod(us, 1e3)

    # create correctly zero padded string for substitution
    # last one is a special for correct day(s) plural
    values = {'d': int(d),
              'H': int(h_t),
              'M': int(m_t),
              'S': int(s_t),
              'h': '{:02d}'.format(int(h)),
              'm': '{:02d}'.format(int(m)),
              's': '{:02d}'.format(int(s)),
              'ms': '{:03d}'.format(int(ms)),
              'us': '{:03d}'.format(int(us)),
              'day': 'day' if d == 1 else 'days'}

    try:
        result = _TimedeltaFormatTemplate(fmt_str).substitute(**values)
    except KeyError:
        raise ValueError(f"Invalid format string '{fmt_str}' for timedelta")
    return sign + result


def strftdnum(td_num, fmt_str):
    """
    Return a string representing a float based timedelta,
    controlled by an explicit format string.

    Arguments
    ---------
    td_num : float
        timedelta in timple float representation
    fmt_str : str
        format string
    """
    td = num2timedelta(td_num)
    return strftimedelta(td, fmt_str)


class TimedeltaFormatter(ticker.Formatter):
    """
    Format a tick (in days) with a format string or using as custom
    `.FuncFormatter`.

    This `.Formatter` formats ticks according to a fixed specification.
    Ticks can optionally be offset to generate shorter tick labels.

    .. note:: The format strings for timedeltas work similar to
      `datetime.datetime.strftime` format strings but they are **not** the
      same and **not** compatible.

    Examples
    --------
    Example plot::

        import numpy as np
        import datetime
        import matplotlib.pyplot as plt
        import timple
        import timple.timedelta as tmpldelta

        tmpl = timple.Timple()
        tmpl.enable()

        base = datetime.timedelta(days=100)
        timedeltas = np.array([base + datetime.timedelta(minutes=(4 * i))
                              for i in range(720)])
        N = len(timedeltas)
        np.random.seed(19680801)
        y = np.cumsum(np.random.randn(N))

        fig, ax = plt.subplots(constrained_layout=True)
        locator = tmpldelta.AutoTimedeltaLocator()
        formatter = tmpldelta.TimedeltaFormatter("%H:%m", offset_on='days',
                                                 offset_fmt="%d %day")
        ax.xaxis.set_major_locator(locator)
        ax.xaxis.set_major_formatter(formatter)

        ax.plot(timedeltas, y)
        ax.set_title('Timedelta Formatter with Offset on Days')

    .. image:: _static/timedelta_formatter_example.svg


    Parameters
    ----------
        fmt : str or callable
            a format string or a callable for formatting the tick values

        offset_on : str, optional
            One of ``('days', 'hours', 'minutes', 'seconds')``

            Specifies how to offset large values; default is no offset.
            If ``offset_on`` is set but ``offset_fmt`` is not, the offset will
            be applied but not shown.

        offset_fmt : str or callable, optional
            A format string or a callable for formatting the offset string.
            This also requires ``offset_on`` to be specified.

        show_offset_zero : bool, optional
            Show axis offset if the offset is zero.

        usetex : bool, default: `text.usetex` from Matplotlib's rcParams
            To enable/disable the use of TeX's math mode for rendering the
            results of the formatter.
    """
    def __init__(self, fmt, *, offset_on=None, offset_fmt=None,
                 show_offset_zero=True, usetex=None):
        super().__init__()
        if (offset_on is None) and (offset_fmt is not None):
            raise ValueError("'offset_fmt' requires 'offset_on to be "
                             "specified.'")
        self.fmt = fmt
        self.offset_fmt = offset_fmt
        self.offset_on = offset_on
        self.show_offset_zero = show_offset_zero
        self.offset_string = ''
        self._usetex = (usetex if usetex is not None else
                        mpl.rcParams['text.usetex'])

    def __call__(self, x, pos=None):
        return self._format_tick(x, pos)

    def _format_tick(self, x, pos=None):
        # format a single tick value
        if isinstance(self.fmt, str):
            return strftdnum(x, self.fmt)
        elif callable(self.fmt):
            return self.fmt(x, pos)
        else:
            raise TypeError('Unexpected type passed to {0!r} as string '
                            'formatter.'.format(self))

    def get_offset(self):
        """Return the formatted axis offset string."""
        return self.offset_string

    def _offset_values(self, values):
        # offset the values based on data or view limits
        ref = min(values)
        # evaluate data interval if available
        # the leftmost (i.e. smallest) data value inside the view window
        # is used as a reference value
        # the offset is calculated so that the value of the reference is zero
        # on the offset level
        # Example: 1 day 12:00, 2 days 00:00, 2 days 12:00; offset on day
        # Resulting offset: 1 day
        # Resulting values: 0 days 12:00, 1 day 00:00, 1 day 12:00
        if self.axis is not None:
            data_ref = min(self.axis.get_data_interval())
            ref = max(data_ref, ref)
            # ref based on data if fully zoomed out else based on view

        # prevent floating point errors; 13 digits > musecond precision
        ref = round(ref, 13)

        # calculate offset based on the reference value and the level
        # specified by self.offset_on
        if self.offset_on == 'days':
            offset = math.floor(ref)
        elif self.offset_on == 'hours':
            offset = math.floor(ref*HOURS_PER_DAY)/HOURS_PER_DAY
        elif self.offset_on == 'minutes':
            offset = math.floor(ref*MINUTES_PER_DAY)/MINUTES_PER_DAY
        elif self.offset_on == 'seconds':
            offset = math.floor(ref*SEC_PER_DAY)/SEC_PER_DAY
        else:
            raise ValueError("Invalid value passed to {0!r} for "
                             "'offset_on'".format(self))

        # return the values with the offset applied and the offset itself
        return [val - offset for val in values], offset

    def format_ticks(self, values):
        offset = None
        if self.offset_on is not None:
            # apply an offset to all values
            values, offset = self._offset_values(values)
        # create labels based on the values after the offset was applied
        result = [self._format_tick(val) for val in values]

        if self._usetex:
            result = [_wrap_in_tex(label) for label in result]

        if self.offset_fmt is not None and (self.show_offset_zero or offset):
            # format the applied offset itself so it can be displayed
            # as axis offset; only show offset if the offset value is not
            # zero or if zero offset are set to be shown
            if isinstance(self.offset_fmt, str):
                offset_str = strftdnum(offset, self.offset_fmt)
            elif callable(self.offset_fmt):
                offset_str = self.offset_fmt(offset)
            else:
                raise TypeError('Unexpected type passed to {0!r} as offset '
                                'string formatter.'.format(self))

            if self._usetex:
                offset_str = _wrap_in_tex(offset_str)

            self.offset_string = offset_str
        else:
            # reset offset string
            self.offset_string = ""

        return result


class ConciseTimedeltaFormatter(ticker.Formatter):
    """
    A `.Formatter` which attempts to figure out the best format to use for the
    timedelta, and to make it as compact as possible, but still be complete.
    This is most useful when used with the `AutoTimedeltaLocator`::

    >>> locator = AutoTimedeltaLocator()
    >>> formatter = ConciseTimedeltaFormatter(locator)

    The formatter will make use of the axis offset. Depending on the tick
    frequency of the locator, the axis offset as well as the format for ticks
    and offset will be determined.

    There are 5 tick levels. These are the same as the base units of the
    locator. The levels are ``('days', 'hours', 'minutes', 'seconds',
    'microseconds')``.
    For each tick level a format string, an offset format string and the
    offset position can be specified. Else, the defaults will be used.


    Parameters
    ----------
    locator : `.Locator`
        Locator that the axis is using.

    formats : list of 5 strings, optional
        Format strings for tick labels.
        The default is::

            ["%d %day",
             "%H:00",
             "%H:%m",
             "%M:%s.0",
             "%S.%ms%us"]

    offset_formats : list of 5 tuples, optional
        A combination of ``(offset format, offset position)`` where the offset
        format is a format string similar to the tick format string.
        Offset position specifies on which level the offset should be applied.
        See the ``offset_fmt=`` and ``offset_on=`` arguments of
        `TimedeltaFormatter`.
        The default is::

            [(None, None),
             ("%d %day", "days"),
             ("%d %day", "days"),
             ("%d %day, %h:00", "hours"),
             ("%d %day, %h:%m", "minutes")]

        For no offset, set both values of a level to None. To apply an offset
        but don't show it, set only the format string to None.

    show_offset : bool, default: True
        Whether to show the offset or not.

    show_offset_zero : bool, optional
        Show axis offset if the offset is zero.

    usetex : bool, default: `text.usetex` from Matplotlib's rcParams
        To enable/disable the use of TeX's math mode for rendering the results
        of the formatter.
    """
    def __init__(self, locator, formats=None, offset_formats=None,
                 show_offset=True, show_offset_zero=True, *, usetex=None):
        self._locator = locator
        self.defaultfmt = "%d %day"
        self.show_offset = show_offset
        self.show_offset_zero = show_offset_zero

        # 5 formatting levels
        self._levels = (1,
                        1/HOURS_PER_DAY,
                        1/MINUTES_PER_DAY,
                        1/SEC_PER_DAY,
                        1/MUSECONDS_PER_DAY)
        if formats:
            if len(formats) != 5:
                raise ValueError('formats argument must be a list of '
                                 '5 format strings (or None)')
            self.formats = formats
        else:
            self.formats = [
                "%d %day",
                "%H:00",
                "%H:%m",
                "%M:%s.0",
                "%S.%ms%us"
            ]

        if offset_formats:
            if len(offset_formats) != 5:
                raise ValueError('offset_formats argument must be a list of '
                                 '5 pairs of (format string, offset position)'
                                 '(or None)')
            self.offset_formats = offset_formats
        else:
            self.offset_formats = [
                (None, None),
                ("%d %day", "days"),
                ("%d %day", "days"),
                ("%d %day, %h:00", "hours"),
                ("%d %day, %h:%m", "minutes")
            ]
        self.offset_str = ''
        self._usetex = (usetex if usetex is not None else
                        mpl.rcParams['text.usetex'])

    def __call__(self, x, pos=None):
        # docstring inherited
        # temporarily wrap x in a list and format with self.format_ticks
        return self.format_ticks([x, ])[0]

    def format_ticks(self, values):
        # docstring inherited
        try:
            locator_unit_scale = float(self._locator._get_unit())
        except AttributeError:
            locator_unit_scale = 1
        # get the level index corresponding to the locator unit scale and
        # select the appropriate format strings and offset position
        i = self._levels.index(locator_unit_scale)
        fmt = self.formats[i]
        offset_fmt, offset_on = self.offset_formats[i]
        formatter = TimedeltaFormatter(fmt, offset_fmt=offset_fmt,
                                       offset_on=offset_on,
                                       show_offset_zero=self.show_offset_zero,
                                       usetex=self._usetex)
        formatter.set_axis(self.axis)
        labels = formatter.format_ticks(values)
        if self.show_offset:
            self.offset_str = formatter.get_offset()

        return labels

    def get_offset(self):
        """Return the formatted axis offset string."""
        return self.offset_str


class AutoTimedeltaFormatter(ticker.Formatter):
    """
    A `.Formatter` which attempts to figure out the best format to use. This
    is most useful when used with the `AutoTimedeltaLocator`.

    The AutoTimedeltaFormatter has a scale dictionary that maps the scale
    of the tick (the distance in days between one major tick) and a
    format string.  The default looks like this::

        self.scaled = {
            1: "%d %day",
            1 / HOURS_PER_DAY: '%d %day, %h:%m',
            1 / MINUTES_PER_DAY: '%d %day, %h:%m',
            1 / SEC_PER_DAY: '%d %day, %h:%m:%s',
            1e3 / MUSECONDS_PER_DAY: '%d %day, %h:%m:%s.%ms',
            1 / MUSECONDS_PER_DAY: '%d %day, %h:%m:%s.%ms%us',
        }

    The algorithm picks the key in the dictionary that is >= the
    current scale and uses that format string.  You can customize this
    dictionary by doing::

    >>> locator = AutoTimedeltaLocator()
    >>> formatter = AutoTimedeltaFormatter(locator)
    >>> formatter.scaled[1/(24.*60.)] = '%M:%S' # only show min and sec

    A custom `.FuncFormatter` can also be used. See `AutoDateLocator` for an
    example of this.

    Parameters
    ----------
    locator : `.Locator`
        Locator that this axis is using

    defaultfmt : str
        The default format to use if none of the values in ``self.scaled``
        are greater than the unit returned by ``locator._get_unit()``.

    usetex : bool, default: `text.usetex` from Matplotlib's rcParams
        To enable/disable the use of TeX's math mode for rendering the
        results of the formatter. If any entries in ``self.scaled`` are set
        as functions, then it is up to the customized function to enable or
        disable TeX's math mode itself.

    scaled : dict, optional
        Allows to overwrite the `scaled` instance attribute at creation.
        The default values are **updated** with the values of this argument.
        You can therefore only add or modify exisiting key-value pairs through
        this argument.
    """
    def __init__(self, locator, defaultfmt='%d %day, %h:%m', scaled=None, *,
                 usetex=None):
        self._locator = locator
        self.defaultfmt = defaultfmt
        self._usetex = (usetex if usetex is not None else
                        mpl.rcParams['text.usetex'])

        self.scaled = {
            1: "%d %day",
            1 / HOURS_PER_DAY: '%d %day, %h:%m',
            1 / MINUTES_PER_DAY: '%d %day, %h:%m',
            1 / SEC_PER_DAY: '%d %day, %h:%m:%s',
            1e3 / MUSECONDS_PER_DAY: '%d %day, %h:%m:%s.%ms',
            1 / MUSECONDS_PER_DAY: '%d %day, %h:%m:%s.%ms%us',
        }
        if scaled is not None:
            try:
                self.scaled.update(scaled)
            except TypeError:
                raise TypeError('scaled needs to be a dictionary that maps '
                                'format strings to tick scales!')

    def _set_locator(self, locator):
        self._locator = locator

    def __call__(self, x, pos=None):
        # docstring inherited
        # temporarily wrap x in a list and format with self.format_ticks
        return self.format_ticks([x, ])[0]

    def format_ticks(self, values):
        # docstring inherited
        try:
            locator_unit_scale = float(self._locator._get_unit())
        except AttributeError:
            locator_unit_scale = 1
        # Pick the first scale which is greater than the locator unit.
        fmt = next((fmt for scale, fmt in sorted(self.scaled.items())
                    if scale >= locator_unit_scale),
                   self.defaultfmt)

        if isinstance(fmt, str):
            _formatter = TimedeltaFormatter(fmt, usetex=self._usetex)
            result = [_formatter(val) for val in values]
        elif callable(fmt):
            result = [fmt(val) for val in values]
        else:
            raise TypeError('Unexpected type passed to {0!r}.'.format(self))

        return result


class TimedeltaLocator(ticker.MultipleLocator):
    """
    Determines the tick locations when plotting timedeltas.

    This class is subclassed by other Locators and
    is not meant to be used on its own.

    Attributes
    ----------
    base_units : list

        list of all supported base units

        By default those are::

            self.base_units = ['days',
                               'hours',
                               'minutes',
                               'seconds',
                               'microseconds']

    base_factors : dict

        mapping of base units to conversion factors to convert from the
        default day representation to hours, seconds, ...
    """
    def __init__(self):
        super().__init__()
        self.base_factors = {'days': 1,
                             'hours': HOURS_PER_DAY,
                             'minutes': MINUTES_PER_DAY,
                             'seconds': SEC_PER_DAY,
                             'microseconds': MUSECONDS_PER_DAY}
        # don't rely on order of dict
        self.base_units = ['days',
                           'hours',
                           'minutes',
                           'seconds',
                           'microseconds']  # mind docstring for fixed locator

    def datalim_to_td(self):
        """Convert axis data interval to timedelta objects."""
        tmin, tmax = self.axis.get_data_interval()
        if tmin > tmax:
            tmin, tmax = tmax, tmin

        return num2timedelta(tmin), num2timedelta(tmax)

    def viewlim_to_td(self):
        """Convert the view interval to timedelta objects."""
        tmin, tmax = self.axis.get_view_interval()
        if tmin > tmax:
            tmin, tmax = tmax, tmin
        return num2timedelta(tmin), num2timedelta(tmax)

    def _create_locator(self, base, interval):
        """
        Create an instance of :class:`ticker.MultipleLocator` using base unit
        and interval

        Parameters
        ----------
        base : {'days', 'hours', 'minutes',  'seconds', 'microseconds'}
        interval : int or float

        Returns
        -------
        instance of :class:`matplotlib.ticker.MultipleLocator`
        """
        factor = self.base_factors[base]

        locator = ticker.MultipleLocator(base=interval/factor)
        locator.set_axis(self.axis)

        if self.axis is not None:
            self.axis.set_view_interval(*self.axis.get_view_interval())
            self.axis.set_data_interval(*self.axis.get_data_interval())

        return locator

    def _get_unit(self):
        """
        Return how many days a unit of the locator is; used for
        intelligent autoscaling.
        """
        return 1

    def _get_interval(self):
        """
        Return the number of units for each tick.
        """
        return 1

    def nonsingular(self, vmin, vmax):
        """
        Given the proposed upper and lower extent, adjust the range
        if it is too close to being singular (i.e. a range of ~0).
        """
        if not np.isfinite(vmin) or not np.isfinite(vmax):
            # Except if there is no data, then use 1 day - 2 days as default.
            return (timedelta2num(datetime.timedelta(days=1)),
                    timedelta2num(datetime.timedelta(days=2)))
        if vmax < vmin:
            vmin, vmax = vmax, vmin
        unit = self._get_unit()
        interval = self._get_interval()
        if abs(vmax - vmin) < 1e-6:
            vmin -= 2 * unit * interval
            vmax += 2 * unit * interval
        return vmin, vmax


class FixedTimedeltaLocator(TimedeltaLocator):
    """
    Make ticks in an interval of the base unit.

    Examples::

      # Ticks every 2 days
      locator = TimedeltaLocatorManual('days', 2)

      # Ticks every 20 seconds
      locator = TimedeltaLocatorManual('seconds', 20)


    Parameters
    ----------
        base_unit: {'days', 'hours', 'minutes', 'seconds', 'microseconds'}
        interval: `int` or `float`
    """
    def __init__(self, base_unit, interval):
        super().__init__()
        if base_unit not in self.base_units:
            raise ValueError(f"base must be one of {self.base_units}")
        self.base = base_unit
        self.interval = interval
        self._freq = 1 / self.base_factors[base_unit]

    def __call__(self):
        # docstring inherited
        locator = self._create_locator(self.base, self.interval)
        return locator()

    def tick_values(self, vmin, vmax):
        return self._create_locator(self.base, self.interval)\
            .tick_values(vmin, vmax)

    def _get_unit(self):
        return self._freq

    def nonsingular(self, vmin, vmax):
        if not np.isfinite(vmin) or not np.isfinite(vmax):
            # Except if there is no data, then use 1 day - 2 days as default.
            return (timedelta2num(datetime.timedelta(days=1)),
                    timedelta2num(datetime.timedelta(days=2)))
        if vmax < vmin:
            vmin, vmax = vmax, vmin
        unit = self._get_unit()
        interval = self._get_interval()
        # factor adjusts unit from days to hours, seconds, ... if necessary
        factor = self.base_factors[self.base]
        if abs(vmax - vmin) < 1e-6 / factor:
            vmin -= 2 * unit * interval / factor
            vmax += 2 * unit * interval / factor
        return vmin, vmax


class AutoTimedeltaLocator(TimedeltaLocator):
    """
    This class automatically finds the best base unit and interval for setting
    view limits and tick locations.

    Parameters
    ----------
        minticks : int
            The minimum number of ticks desired; controls whether ticks occur
            daily, hourly, etc.
        maxticks : dict or int
            The maximum number of ticks desired; controls the interval between
            ticks (ticking every other, every 3, etc.).  For fine-grained
            control, this can be a dictionary mapping individual base units
            ('days', 'hours', etc.) to their own maximum
            number of ticks.  This can be used to keep the number of ticks
            appropriate to the format chosen in `AutoDateFormatter`. Any
            frequency not specified in this dictionary is given a default
            value.


    Attributes
    ----------
    intervald : dict

        Mapping of tick frequencies to multiples allowed for that ticking.
        The default is ::

            self.intervald = {
                'days': [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000, 2000,
                         5000, 10000, 20000, 50000, 100000, 200000, 500000,
                         1000000],
                'hours': [1, 2, 3, 4, 6, 8, 12],
                'minutes': [1, 2, 3, 5, 10, 15, 20, 30],
                'seconds': [1, 2, 3, 5, 10, 15, 20, 30],
                'microseconds': [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000,
                                 2000, 5000, 10000, 20000, 50000, 100000,
                                 200000, 500000, 1000000],
            }

        The interval is used to specify multiples that are appropriate for
        the frequency of ticking. For instance, every 12 hours is sensible
        for hourly ticks, but for minutes/seconds, 15 or 30 make sense.

        When customizing, you should only modify the values for the existing
        keys. You should not add or delete entries.

        Example for forcing ticks every 3 hours::

            locator = AutoTimedeltaLocator()
            locator.intervald['hours'] = [3]  # only show every 3 hours

        For forcing ticks in one specific interval only,
        :class:`FixedTimedeltaLocator` might be preferred.
    """
    def __init__(self, minticks=5, maxticks=None):
        super().__init__()
        self.intervald = {
            'days': [1, 2, 5, 10, 20, 25, 50, 100, 200, 500, 1000, 2000,
                     5000, 10000, 20000, 50000, 100000, 200000, 500000,
                     1000000],
            'hours': [1, 2, 3, 4, 6, 8, 12],
            'minutes': [1, 2, 3, 5, 10, 15, 20, 30],
            'seconds': [1, 2, 3, 5, 10, 15, 20, 30],
            'microseconds': [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000,
                             5000, 10000, 20000, 50000, 100000, 200000, 500000,
                             1000000],
        }  # mind the default in the docstring
        self.minticks = minticks
        self.maxticks = {'days': 11, 'hours': 12,
                         'minutes': 11, 'seconds': 11, 'microseconds': 8}
        if maxticks is not None:
            try:
                self.maxticks.update(maxticks)
            except TypeError:
                # Assume we were given an integer. Use this as the maximum
                # number of ticks for every frequency and create a
                # dictionary for this
                self.maxticks = dict.fromkeys(self.base_units, maxticks)
        self._freq = 1.0  # default is daily

    def __call__(self):
        # docstring inherited
        tmin, tmax = self.viewlim_to_td()
        locator = self.get_locator(tmin, tmax)
        return locator()

    def tick_values(self, vmin, vmax):
        locator = self.get_locator(vmin, vmax)
        return locator.tick_values(vmin, vmax)

    def nonsingular(self, vmin, vmax):
        # whatever is thrown at us, we can scale the unit.
        # But default nonsingular date plots at an ~4 day period.
        if not np.isfinite(vmin) or not np.isfinite(vmax):
            # Except if there is no data, then use 1 day - 2 days as default.
            return (timedelta2num(datetime.timedelta(days=1)),
                    timedelta2num(datetime.timedelta(days=2)))
        if vmax < vmin:
            vmin, vmax = vmax, vmin
        if vmin == vmax:
            vmin -= 2
            vmax += 2
        return vmin, vmax

    def _get_unit(self):
        return self._freq

    def get_locator(self, vmin, vmax):
        """
        Create the best locator based on the given limits.

        This will choose the settings for a
        :class:`matplotlib.ticker.MultipleLocator`
        based on the available base units and associated intervals.
        The locator is created so that there are as few ticks as possible
        but more ticks than specified with min_ticks in init.

        Returns
        -------
        instance of :class:`matplotlib.ticker.MultipleLocator`
        """
        tdelta = vmax - vmin

        # take absolute difference
        if vmin > vmax:
            tdelta = -tdelta

        tdelta = timedelta2num(tdelta)

        # find an appropriate base unit and interval for it
        base = self._get_base(tdelta)
        factor = self.base_factors[base]
        norm_delta = tdelta * factor
        self._freq = 1/factor
        interval = self._get_interval_for_base(norm_delta, base)

        return self._create_locator(base, interval)

    def _get_base(self, tdelta):
        # find appropriate base unit for given time delta
        base = 'days'  # fallback
        for base in self.base_units:
            try:
                factor = self.base_factors[base]
                if tdelta * factor >= self.minticks:
                    break
            except KeyError:
                continue  # intervald was modified
        return base

    def _get_interval_for_base(self, norm_delta, base):
        # find appropriate interval for given delta and min ticks
        # norm_delta = tdelta * base_factor
        base_intervals = self.intervald[base]
        interval = 1  # fallback (and for static analysis)
        # for interval in reversed(base_intervals):
        #     if norm_delta // interval >= self.minticks:
        for interval in base_intervals:
            if norm_delta // interval <= self.maxticks[base]:
                break

        return interval


class TimedeltaConverter(units.ConversionInterface):
    """
    Converter for `datetime.timedelta`, `numpy.timedelta64` and
    `pandas.Timedelta` data.

    The 'unit' tag for such data is None.

    Parameters
    ----------
    formatter_args : dict, optional
        A dictionary of keyword arguments which are passed on to
        :class:`AutoTimedeltaFormatter` instances.
    """

    def __init__(self, formatter_args=None):
        super().__init__()

        if not formatter_args:
            self.formatter_args = {}
        else:
            self.formatter_args = formatter_args

    def axisinfo(self, unit, axis):
        """
        Return the `~matplotlib.units.AxisInfo`.

        The *unit* and *axis* arguments are required but not used.
        """
        majloc = AutoTimedeltaLocator()
        majfmt = AutoTimedeltaFormatter(majloc, **self.formatter_args)
        datemin = datetime.timedelta(days=1)
        datemax = datetime.timedelta(days=2)

        return units.AxisInfo(majloc=majloc, majfmt=majfmt, label='',
                              default_limits=(datemin, datemax))

    @staticmethod
    def convert(value, unit, axis):
        """
        If *value* is not already a number or sequence of numbers, convert it
        with `timedelta2num`.

        The *unit* and *axis* arguments are not used.
        """
        return timedelta2num(value)


class ConciseTimedeltaConverter(TimedeltaConverter):
    """
    Converter for `datetime.timedelta`, `numpy.timedelta64` and
    `pandas.Timedelta` data (prefers short tick formats).

    The 'unit' tag for such data is None.

    Parameters
    ----------
    formatter_args : dict, optional
        A dictionary of keyword arguments which are passed on to
        :class:`ConciseTimedeltaFormatter` instances.

    """
    def __init__(self, formatter_args=None):
        super().__init__()
        if not formatter_args:
            self.formatter_args = {}
        else:
            self.formatter_args = formatter_args

    def axisinfo(self, unit, axis):
        # docstring inherited
        majloc = AutoTimedeltaLocator()
        majfmt = ConciseTimedeltaFormatter(majloc, **self.formatter_args)
        datemin = datetime.timedelta(days=1)
        datemax = datetime.timedelta(days=2)

        return units.AxisInfo(majloc=majloc, majfmt=majfmt, label='',
                              default_limits=(datemin, datemax))
