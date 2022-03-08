
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
  Timestamp('2021-06-19 00:00:00')


Now, which race weekend are we actually looking at here?
For this we have the :class:`fastf1.core.Weekend` object which holds
information about each race weekend. It is accessible through the
session object.

.. doctest::

  >>> session.event
  round_number                                                      7
  country                                                      France
  location                                               Le Castellet
  official_event_name    FORMULA 1 EMIRATES GRAND PRIX DE FRANCE 2021
  event_date                                      2021-06-20 00:00:00
  event_name                                        French Grand Prix
  event_format                                           conventional
  session1                                                 Practice 1
  session1_date                                   2021-06-18 00:00:00
  session2                                                 Practice 2
  session2_date                                   2021-06-18 00:00:00
  session3                                                 Practice 3
  session3_date                                   2021-06-19 00:00:00
  session4                                                 Qualifying
  session4_date                                   2021-06-19 00:00:00
  session5                                                       Race
  session5_date                                   2021-06-20 00:00:00
  f1_api_support                                                 True
  Name: French Grand Prix, dtype: object

Let's see which race weekend this actually is.

.. doctest::

  >>> session.event.event_name
  'French Grand Prix'
  >>> session.event.event_date  # this is the date of the race day
  Timestamp('2021-06-20 00:00:00')

If you do not specify which session you want to load, ``.get_session()``
will return a :class:`fastf1.core.Weekend` object instead of a session.
The weekend object provides methods which return the individual sessions.

.. doctest::

  >>> event = fastf1.get_event(2021, 7)
  >>> event
  round_number                                                      7
  country                                                      France
  location                                               Le Castellet
  official_event_name    FORMULA 1 EMIRATES GRAND PRIX DE FRANCE 2021
  event_date                                      2021-06-20 00:00:00
  event_name                                        French Grand Prix
  event_format                                           conventional
  session1                                                 Practice 1
  session1_date                                   2021-06-18 00:00:00
  session2                                                 Practice 2
  session2_date                                   2021-06-18 00:00:00
  session3                                                 Practice 3
  session3_date                                   2021-06-19 00:00:00
  session4                                                 Qualifying
  session4_date                                   2021-06-19 00:00:00
  session5                                                       Race
  session5_date                                   2021-06-20 00:00:00
  f1_api_support                                                 True
  Name: French Grand Prix, dtype: object
  >>> session = event.get_race()
  >>> session.name
  'Race'


Loading a session by name
-------------------------

As an alternative to specifying a race weekends number you can also load
weekends by their official name.

.. doctest::

  >>> event = fastf1.get_event(2021, 'French Grand Prix')
  >>> event.event_name
  'French Grand Prix'

You do not need to provide the exact name. FastF1 will return the weekend or
session that matches your provided name best. Even if you don't specify the
correct name chances are high that FastF1 will find the event you are looking
for.

  >>> event = fastf1.get_event(2021, 'Spain')
  >>> event.event_name
  'Spanish Grand Prix'

But be aware that this does not always work. Sometimes another name just
matches the provided string better. For example, what we actually want is the
'Emiligia Romagna Grand Prix' but we get the 'Belgian Grand Prix' if we don't
specify the name fully and/or correct enough. Why? Because FastF1 is not a
proper intelligent search engine. So check your results.

  >>> event = fastf1.get_event(2021, 'Emilian')
  >>> event.event_name
  'Belgian Grand Prix'

We need to be a bit more precise here.

  >>> event = fastf1.get_event(2021, 'Emilia Romagna')
  >>> event.event_name
  'Emilia Romagna Grand Prix'


Working with laps and lap times
-------------------------------

We have loaded a session now but it has been rather boring so far. So lets make it
a bit more interesting and take a look at some individual laps.

  >>> session = fastf1.get_session(2021, 'French Grand Prix', 'Q')
  >>> session.load()
  >>> session.laps
                        Time DriverNumber  ... IsAccurate            LapStartDate
  0   0 days 00:28:44.908000           33  ...      False 2021-06-19 13:03:06.950
  1   0 days 00:31:14.909000           33  ...      False 2021-06-19 13:14:12.111
  2   0 days 00:32:45.910000           33  ...       True 2021-06-19 13:16:42.112
  3   0 days 00:50:42.329000           33  ...      False 2021-06-19 13:18:13.113
  4   0 days 00:52:59.529000           33  ...      False 2021-06-19 13:36:09.532
  ..                     ...          ...  ...        ...                     ...
  265 0 days 00:39:10.594000           18  ...      False 2021-06-19 13:22:15.102
  266 0 days 00:41:23.178000           18  ...       True 2021-06-19 13:24:37.797
  267 0 days 00:41:30.642000           18  ...      False 2021-06-19 13:26:50.381
  268 0 days 00:17:40.791000           22  ...      False 2021-06-19 13:00:22.952
  269 0 days 00:26:20.982000           22  ...      False 2021-06-19 13:03:07.994
  <BLANKLINE>
  [270 rows x 26 columns]

That's 250 laps right there and 25 columns of information. If you are familiar
with Pandas you'll immediately recognize this output as a DataFrame. (If you're
not familiar with Pandas at all, it might be helpful to check out a short
tutorial.)

As this is basically a Pandas DataFrame we can take a look at what columns
there are.

  >>> session.laps.columns  # doctest: +NORMALIZE_WHITESPACE
  Index(['Time', 'DriverNumber', 'LapTime', 'LapNumber', 'Stint', 'PitOutTime',
         'PitInTime', 'Sector1Time', 'Sector2Time', 'Sector3Time',
         'Sector1SessionTime', 'Sector2SessionTime', 'Sector3SessionTime',
         'SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST', 'Compound', 'TyreLife',
         'FreshTyre', 'LapStartTime', 'Team', 'Driver', 'TrackStatus',
         'IsAccurate', 'LapStartDate'],
        dtype='object')

The detailed explanation for all these columns can be found in the
docuemntation of the :class:`.core.Laps` class.

The :class:`.core.Laps` object is not a simple DataFrame though. Like FastF1's
other data objects it provides some more features specifically for working
with F1 data.

One of these additional features are methods for selecting specific laps.
So let's see what the fastest laptime was and who is on pole.

  >>> fastest_lap = session.laps.pick_fastest()
  >>> fastest_lap['LapTime']
  Timedelta('0 days 00:01:29.990000')
  >>> fastest_lap['Compound']
  'SOFT'
  >>> fastest_lap['Driver']
  'VER'


Check out this example that shows how you can plot lap times:
:ref:`sphx_glr_examples_gallery_plot_qualifying_results.py`

