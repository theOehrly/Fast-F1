
Getting started with the basics
===============================


Loading a session
-----------------

The :class:`fastf1.core.Session` object is an important starting point for
everything you do with FastF1. Usually the first thing you want to do
is loading a session. For this, you should use
:func:`fastf1.get_session() <fastf1.core.get_session>`.

For example, let's load the Qualifying of the 7th race of the 2021 season:

.. doctest::

  >>> import fastf1
  >>> session = fastf1.get_session(2021, 7, 'Q')
  >>> session.name
  'Qualifying'
  >>> session.date
  '2021-06-19'


Now, which race weekend are we actually looking at here?
For this we have the :class:`fastf1.core.Weekend` object which holds
information about each race weekend. It is accessible through the
session object.

.. doctest::

  >>> session.weekend  # doctest: +ELLIPSIS
  <fastf1.core.Weekend object at ...>

Let's see which race weekend this actually is.

.. doctest::

  >>> session.weekend.name
  'French Grand Prix'
  >>> session.weekend.date  # this is the date of the race day
  '2021-06-20'

If you do not specify which session you want to load, ``.get_session()``
will return a :class:`fastf1.core.Weekend` object instead of a session.
The weekend object provides methods which return the individual sessions.

.. doctest::

  >>> weekend = fastf1.get_session(2021, 7)
  >>> weekend # doctest: +ELLIPSIS
  <fastf1.core.Weekend object at ...>
  >>> session = weekend.get_race()
  >>> session.name
  'Race'


Loading a session by name
-------------------------

As an alternative to specifying a race weekends number you can also load
weekends by their official name.

.. doctest::

  >>> weekend = fastf1.get_session(2021, 'French Grand Prix')
  >>> weekend.name
  'French Grand Prix'

You do not need to provide the exact name. FastF1 will return the weekend or
session that matches your provided name best. Even if you don't specify the
correct name chances are high that FastF1 will find the event you are looking
for.

  >>> weekend = fastf1.get_session(2021, 'Barcelona GP')
  >>> weekend.name
  'Spanish Grand Prix'

But be aware that this does not always work. Sometimes another name just
matches the provided string better. For example, what we actually want is the
'Emiligia Romagna Grand Prix' but we get the 'Brazilian Grand Prix' if we don't
specify the name fully. Why? Because FastF1 is not a proper intelligent search
engine. So check your results.

  >>> weekend = fastf1.get_session(2021, 'Emilia Grand Prix')
  >>> weekend.name
  'Brazilian Grand Prix'

We need to be a bit more precise here.

  >>> weekend = fastf1.get_session(2021, 'Emilia Romagna Grand Prix')
  >>> weekend.name
  'Emilia Romagna Grand Prix'


Working with laps and lap times
-------------------------------

We have loaded a session now but it has been rather boring so far. So lets make it
a bit more interesting and take a look at some individual laps.

  >>> quali = fastf1.get_session(2021, 'French Grand Prix', 'Q')
  >>> laps = quali.load_laps()
  >>> laps
                        Time DriverNumber  ... TrackStatus  IsAccurate
  0   0 days 00:28:44.908000           33  ...           1       False
  1   0 days 00:31:14.909000           33  ...           1       False
  2   0 days 00:32:45.910000           33  ...           1        True
  3   0 days 00:50:42.329000           33  ...          25       False
  4   0 days 00:52:59.529000           33  ...           1       False
  ..                     ...          ...  ...         ...         ...
  245 0 days 00:28:51.659000            9  ...          25       False
  246 0 days 00:31:39.717000            9  ...           1       False
  247 0 days 00:33:13.271000            9  ...           1        True
  248 0 days 00:38:02.565000            9  ...           1       False
  249 0 days 00:40:30.783000            9  ...           1       False
  <BLANKLINE>
  [250 rows x 25 columns]

That's 250 laps right there and 25 columns of information. If you are familiar
with Pandas you'll immediately recognize this output as a DataFrame. (If you're
not familiar with Pandas at all, it might be helpful to check out a short
tutorial.)

As this is basically a Pandas DataFrame we can take a look at what columns
there are.

  >>> laps.columns  # doctest: +NORMALIZE_WHITESPACE
  Index(['Time', 'DriverNumber', 'LapTime', 'LapNumber', 'Stint', 'PitOutTime',
         'PitInTime', 'Sector1Time', 'Sector2Time', 'Sector3Time',
         'Sector1SessionTime', 'Sector2SessionTime', 'Sector3SessionTime',
         'SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST', 'Compound', 'TyreLife',
         'FreshTyre', 'LapStartTime', 'Team', 'Driver', 'TrackStatus',
         'IsAccurate'],
         dtype='object')

The detailed explanation for all these columns can be found in the
docuemntation of the :class:`.core.Laps` class.

The :class:`.core.Laps` object is not a simple DataFrame though. Like FastF1's
other data objects it provides some more features specifically for working
with F1 data.

One of these additional features are methods for selecting specific laps.
So let's see what the fastest laptime was and who is on pole.

  >>> fastest_lap = laps.pick_fastest()
  >>> fastest_lap['LapTime']
  Timedelta('0 days 00:01:29.990000')
  >>> fastest_lap['Compound']
  'SOFT'
  >>> fastest_lap['Driver']
  'VER'


Check out this example that shows how you can plot lap times:
:ref:`sphx_glr_examples_gallery_plot_qualifying_results.py`

