.. _time-explanation:

===================================
Time, Date and Timing - Explanation
===================================

Working with Formula 1 data (or any motorsport data for that matter) requires working working with lots of different
values of time. These values can denote a point in time or a duration. The following is an explanation of the different
values of time which are used in this module.


Points in Time
--------------

Three different values of time can denote a point in time in this module. These are:
  - Time
  - SessionTime
  - Date

`SessionTime` is a time which has a more or less arbitrary zero point multiple minutes before a session officially starts.
It is directly provided by the F1 live timing api. SessionTime zero marks the beginning of all data streams. The
SessionTime references events within the boundaries of one session.

  --> SessionTime is relative to the beginning of a session

`Date` is a UTC timestamp containing date and time. It is therefore an absolute reference to tell when something
happened in the context of the time of day.

  --> Date is an absolute point in time

`Time` references data relative in the current data set. The first sample of a given set of data will always mark the
zero point for this set of data.

  --> Time is relative to the first sample of data in a set of data


For a sample of telemetry data this means, that the sample will always have the same value for its `Date` and
`SessionTime`. But its value for `Time` will change when the dataset is modified.

Take the following set of example telemetry. Lets assume the variable `tel` holds previously loaded telemetry data
for one driver an for a full session (only time data is shown for simplification).

.. doctest::
  :hide:

  >>> import fastf1
  >>> import pandas
  >>> session = fastf1.get_session(2020, 8, 'R')
  >>> session.load()

.. doctest::

  >>> tel = session.car_data['33'].loc[:, ['Time', 'SessionTime', 'Date']]
  >>> tel
                          Time            SessionTime                    Date
  0     0 days 00:00:02.984000 0 days 00:00:02.984000 2020-09-06 12:40:03.180
  1     0 days 00:00:03.224000 0 days 00:00:03.224000 2020-09-06 12:40:03.420
  2     0 days 00:00:03.464000 0 days 00:00:03.464000 2020-09-06 12:40:03.660
  3     0 days 00:00:03.704000 0 days 00:00:03.704000 2020-09-06 12:40:03.900
  4     0 days 00:00:03.944000 0 days 00:00:03.944000 2020-09-06 12:40:04.140
  ...                      ...                    ...                     ...
  35533 0 days 02:23:27.764000 0 days 02:23:27.764000 2020-09-06 15:03:27.960
  35534 0 days 02:23:28.004000 0 days 02:23:28.004000 2020-09-06 15:03:28.200
  35535 0 days 02:23:28.244000 0 days 02:23:28.244000 2020-09-06 15:03:28.440
  35536 0 days 02:23:28.484000 0 days 02:23:28.484000 2020-09-06 15:03:28.680
  35537 0 days 02:23:28.724000 0 days 02:23:28.724000 2020-09-06 15:03:28.920
  <BLANKLINE>
  [35538 rows x 3 columns]

The telemetry comprises approximately 2 hours and 23 minutes of data.
The session (a race in this case) did not last this long, but the data starts
before the beginning of the session and ends after the end.
`SessionTime` and `Time` are exactly the same for this set of data.
This is how the data looks as it is created by the api functions.
Next, the data is sliced to only include a subset of the full session.

.. doctest::

  >>> t1 = pandas.Timedelta(hours=1, minutes=20)
  >>> t2 = pandas.Timedelta(hours=1, minutes=30)
  >>> tel.slice_by_time(t1, t2)
                          Time            SessionTime                    Date
  19811 0 days 00:00:00.195000 0 days 01:20:00.195000 2020-09-06 14:00:00.391
  19812 0 days 00:00:00.435000 0 days 01:20:00.435000 2020-09-06 14:00:00.631
  19813 0 days 00:00:00.676000 0 days 01:20:00.676000 2020-09-06 14:00:00.872
  19814 0 days 00:00:00.916000 0 days 01:20:00.916000 2020-09-06 14:00:01.112
  19815 0 days 00:00:01.156000 0 days 01:20:01.156000 2020-09-06 14:00:01.352
  ...                      ...                    ...                     ...
  22288 0 days 00:09:59.076000 0 days 01:29:59.076000 2020-09-06 14:09:59.272
  22289 0 days 00:09:59.277000 0 days 01:29:59.277000 2020-09-06 14:09:59.473
  22290 0 days 00:09:59.517000 0 days 01:29:59.517000 2020-09-06 14:09:59.713
  22291 0 days 00:09:59.757000 0 days 01:29:59.757000 2020-09-06 14:09:59.953
  22292 0 days 00:09:59.997000 0 days 01:29:59.997000 2020-09-06 14:10:00.193
  <BLANKLINE>
  [2482 rows x 3 columns]

`SessionTime` and `Date` have kept there reference point. But the reference point for `Time` has changed and its new
zero is now the first sample of this set of data.
If this subset of data was sliced again, `Time` would change again so as to start at zero on the first sample.

All three of these values have a use for different reasons. Here are some examples.

To check which other cars are on track while one driver is on a fast lap `SessionTime` is useful.

When overlapping multiple laps for comparison the data can be plotted over `Time` so that different laps have
a common zero point.

`Date` is useful when checking out something in reference to commonly used human time.

The relation between `SessionTime` and `Date` is a constant offset. This value is available through the session class.

.. doctest::

  >>> session.t0_date
  Timestamp('2020-09-06 12:40:00.196000')

As already mentioned above, the zero point of the session time is before the actual start of a session. The session
itself officially starts at some later point in time. This value is also available through the session class.

.. doctest::

  >>> session.session_start_time
  datetime.timedelta(seconds=2008, microseconds=79000)
  >>> str(session.session_start_time)
  '0:33:28.079000'



Lap timing
----------

.. currentmodule:: fastf1.core

Lap timing data is available in an instance of :class:`Laps` in :attr:`Session.laps`.
For each lap, the usual official timing information is available. It consists of the lap time and the sector times.
The columns for this data in :class:`Laps` are called 'LapTime', 'Sector1Time', 'Sector2Time' and 'Sector3Time'.
These four values are highly accurate and are considered the absolute truth.

For each lap, additional data is available. Amongst others the following time related data:
  - 'Time': This marks the point in time when a lap was set, i.e. finished, as a SessionTime. The name 'Time' is
    confusing here as it should be 'SessionTime'. It is kept mainly for backwards compatibility.
  - 'Sector*SessionTime': For each sector a session time is available. This marks the point in time when a sector time
    was set. The 'Sector3Session' time is mathematically the same as the end of the lap ('Time'). In most cases this is
    true, but there can be minor deviations in some edge cases. (In some cases the api function can not calculate the
    timestamps correctly.)
  - 'LapStartTime': This marks the point in time (SessionTime) when a lap was started and is equivalent to the 'Time'
    and 'Sector3Time' of the previous lap.
  - 'LapStartDate': This is the same as 'LapStartTime' just expressed as 'Date' instead of 'SessionTime'
  - 'PitInTime'/'PitOutTime': This marks the point in time (SessionTime) when a car entered or left the pits.

These additional timestamps are not provided by the api. They are calculated as accurate as possible from the available
data but the accuracy can not be verified to millisecond precision.
