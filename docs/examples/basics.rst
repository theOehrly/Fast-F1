
Getting started with the basics
===============================

FastF1 is built mainly around Pandas DataFrame and Series objects.
If you are familiar with Pandas you'll immediately recognize this and working
with the data will be fairly straightforward. (If you're
not familiar with Pandas at all, it might be helpful to check out a short
tutorial.)


Loading a session or an event
------------------------------

The :class:`fastf1.core.Session` object is an important starting point for
everything you do with FastF1. Usually, the first thing you want to do
is load a session. For this, you should use
:func:`fastf1.get_session`.

For example, let's load the Qualifying of the 7th race of the 2021 season:

.. doctest::

  >>> import fastf1
  >>> session = fastf1.get_session(2021, 7, 'Q')
  >>> session.name
  'Qualifying'
  >>> session.date
  Timestamp('2021-06-19 13:00:00')


Now, which race weekend are we actually looking at here?
For this we have the :class:`~fastf1.events.Event` object which holds
information about each event. An event can be a race weekend or a testing
event and usually consists of multiple sessions. It is accessible through the
session object.

.. doctest::

  >>> session.event
  RoundNumber                                                     7
  Country                                                    France
  Location                                             Le Castellet
  OfficialEventName    FORMULA 1 EMIRATES GRAND PRIX DE FRANCE 2021
  EventDate                                     2021-06-20 00:00:00
  EventName                                       French Grand Prix
  EventFormat                                          conventional
  Session1                                               Practice 1
  Session1Date                            2021-06-18 11:30:00+02:00
  Session1DateUtc                               2021-06-18 09:30:00
  Session2                                               Practice 2
  Session2Date                            2021-06-18 15:00:00+02:00
  Session2DateUtc                               2021-06-18 13:00:00
  Session3                                               Practice 3
  Session3Date                            2021-06-19 12:00:00+02:00
  Session3DateUtc                               2021-06-19 10:00:00
  Session4                                               Qualifying
  Session4Date                            2021-06-19 15:00:00+02:00
  Session4DateUtc                               2021-06-19 13:00:00
  Session5                                                     Race
  Session5Date                            2021-06-20 15:00:00+02:00
  Session5DateUtc                               2021-06-20 13:00:00
  F1ApiSupport                                                 True
  Name: 7, dtype: object

The :class:`~fastf1.events.Event` object is a subclass of a
:class:`pandas.Series`. The individual values can therefore be accessed as it
is common for pandas objects:

.. doctest::

  >>> session.event['EventName']
  'French Grand Prix'
  >>> session.event['EventDate']  # this is the date of the race day
  Timestamp('2021-06-20 00:00:00')

You can also load an event directly, by using the function
:func:`fastf1.get_event`. The :class:`~fastf1.events.Event` object in turn
provides methods for accessing the individual associated sessions.

.. doctest::

  >>> event = fastf1.get_event(2021, 7)
  >>> event
  RoundNumber                                                     7
  Country                                                    France
  Location                                             Le Castellet
  OfficialEventName    FORMULA 1 EMIRATES GRAND PRIX DE FRANCE 2021
  EventDate                                     2021-06-20 00:00:00
  EventName                                       French Grand Prix
  EventFormat                                          conventional
  Session1                                               Practice 1
  Session1Date                            2021-06-18 11:30:00+02:00
  Session1DateUtc                               2021-06-18 09:30:00
  Session2                                               Practice 2
  Session2Date                            2021-06-18 15:00:00+02:00
  Session2DateUtc                               2021-06-18 13:00:00
  Session3                                               Practice 3
  Session3Date                            2021-06-19 12:00:00+02:00
  Session3DateUtc                               2021-06-19 10:00:00
  Session4                                               Qualifying
  Session4Date                            2021-06-19 15:00:00+02:00
  Session4DateUtc                               2021-06-19 13:00:00
  Session5                                                     Race
  Session5Date                            2021-06-20 15:00:00+02:00
  Session5DateUtc                               2021-06-20 13:00:00
  F1ApiSupport                                                 True
  Name: 7, dtype: object
  >>> session = event.get_race()
  >>> session.name
  'Race'


Loading a session or an event by name
--------------------------------------

As an alternative to specifying an event number you can also load
events by using a clearly identifying name.

.. doctest::

  >>> event = fastf1.get_event(2021, 'French Grand Prix')
  >>> event['EventName']
  'French Grand Prix'

You do not need to provide the exact event name. FastF1 will return the
event (or session) that matches your provided name best. Even if you don't
specify the correct name chances are high that FastF1 will find the event
you are looking for.

  >>> event = fastf1.get_event(2021, 'Spain')
  >>> event['EventName']
  'Spanish Grand Prix'

But be aware that this does not always work. Sometimes another name just
matches the provided string better. For example, what we actually want is the
'Emilia Romagna Grand Prix' but we get the 'Belgian Grand Prix' if we don't
specify the name fully and/or correct enough. Why? Because FastF1 is not a
proper intelligent search engine. So check your results.

  >>> event = fastf1.get_event(2021, 'Emilian')
  >>> event['EventName']
  'Belgian Grand Prix'

We need to be a bit more precise here.

  >>> event = fastf1.get_event(2021, 'Emilia Romagna')
  >>> event['EventName']
  'Emilia Romagna Grand Prix'

Events and sessions can also be loaded by their country or location.

  >>> session = fastf1.get_session(2021, 'Silverstone', 'Q')
  >>> session.event['EventName']
  'British Grand Prix'


Working with the event schedule
-------------------------------

Instead of loading a specific session or event, it is possible to load the
full event schedule for a season. The :class:`~fastf1.events.EventSchedule`
is a subclass of a :class:`pandas.DataFrame`. Detailed information about
the data that is available in the event schedule can be found in
:mod:`~fastf1.events`.

  >>> schedule = fastf1.get_event_schedule(2021)
  >>> schedule
      RoundNumber        Country  ...     Session5DateUtc F1ApiSupport
  0             0        Bahrain  ...                 NaT        False
  1             1        Bahrain  ... 2021-03-28 15:00:00         True
  2             2          Italy  ... 2021-04-18 13:00:00         True
  3             3       Portugal  ... 2021-05-02 14:00:00         True
  4             4          Spain  ... 2021-05-09 13:00:00         True
  5             5         Monaco  ... 2021-05-23 13:00:00         True
  6             6     Azerbaijan  ... 2021-06-06 12:00:00         True
  7             7         France  ... 2021-06-20 13:00:00         True
  8             8        Austria  ... 2021-06-27 13:00:00         True
  9             9        Austria  ... 2021-07-04 13:00:00         True
  10           10  Great Britain  ... 2021-07-18 14:00:00         True
  11           11        Hungary  ... 2021-08-01 13:00:00         True
  12           12        Belgium  ... 2021-08-29 13:00:00         True
  13           13    Netherlands  ... 2021-09-05 13:00:00         True
  14           14          Italy  ... 2021-09-12 13:00:00         True
  15           15         Russia  ... 2021-09-26 12:00:00         True
  16           16         Turkey  ... 2021-10-10 12:00:00         True
  17           17  United States  ... 2021-10-24 19:00:00         True
  18           18         Mexico  ... 2021-11-07 19:00:00         True
  19           19         Brazil  ... 2021-11-14 17:00:00         True
  20           20          Qatar  ... 2021-11-21 14:00:00         True
  21           21   Saudi Arabia  ... 2021-12-05 17:30:00         True
  22           22      Abu Dhabi  ... 2021-12-12 13:00:00         True
  <BLANKLINE>
  [23 rows x 23 columns]
  >>> schedule.columns  # doctest: +NORMALIZE_WHITESPACE
  Index(['RoundNumber', 'Country', 'Location', 'OfficialEventName', 'EventDate',
         'EventName', 'EventFormat', 'Session1', 'Session1Date',
         'Session1DateUtc', 'Session2', 'Session2Date', 'Session2DateUtc',
         'Session3', 'Session3Date', 'Session3DateUtc', 'Session4',
         'Session4Date', 'Session4DateUtc', 'Session5', 'Session5Date',
         'Session5DateUtc', 'F1ApiSupport'],
        dtype='object')

The event schedule provides methods for selecting specific events:

  >>> gp_12 = schedule.get_event_by_round(12)
  >>> gp_12['Country']
  'Belgium'
  >>> gp_austin = schedule.get_event_by_name('Austin')
  >>> gp_austin['Country']
  'United States'


Displaying driver info and session results
------------------------------------------

We have created a session now but everything has been rather boring so far.
So let's make it a bit more interesting by taking a look at the results of
this session. For this, it is first necessary to call
:func:`Session.load <fastf1.core.Session.load>`. This will load all available data for the
session from various APIs. Downloading and processing of the data may take a
few seconds. It is highly recommended to utilize FastF1's built-in caching
functionality to speed up data loading and prevent excessive API requests.

  >>> session = fastf1.get_session(2021, 'French Grand Prix', 'Q')
  >>> session.load()
  >>> session.results
     DriverNumber BroadcastName Abbreviation  ... Time Status Points
  33           33  M VERSTAPPEN          VER  ...  NaT           NaN
  44           44    L HAMILTON          HAM  ...  NaT           NaN
  77           77      V BOTTAS          BOT  ...  NaT           NaN
  11           11       S PEREZ          PER  ...  NaT           NaN
  55           55       C SAINZ          SAI  ...  NaT           NaN
  10           10       P GASLY          GAS  ...  NaT           NaN
  16           16     C LECLERC          LEC  ...  NaT           NaN
  4             4      L NORRIS          NOR  ...  NaT           NaN
  14           14      F ALONSO          ALO  ...  NaT           NaN
  3             3   D RICCIARDO          RIC  ...  NaT           NaN
  31           31        E OCON          OCO  ...  NaT           NaN
  5             5      S VETTEL          VET  ...  NaT           NaN
  99           99  A GIOVINAZZI          GIO  ...  NaT           NaN
  63           63     G RUSSELL          RUS  ...  NaT           NaN
  47           47  M SCHUMACHER          MSC  ...  NaT           NaN
  6             6      N LATIFI          LAT  ...  NaT           NaN
  7             7   K RAIKKONEN          RAI  ...  NaT           NaN
  9             9     N MAZEPIN          MAZ  ...  NaT           NaN
  18           18      L STROLL          STR  ...  NaT           NaN
  22           22     Y TSUNODA          TSU  ...  NaT           NaN
  <BLANKLINE>
  [20 rows x 21 columns]

The results object (:class:`fastf1.core.SessionResults`) is a subclass of a
:class:`pandas.DataFrame`. Therefore, we can take a look at what data columns
there are:

  >>> session.results.columns  # doctest: +NORMALIZE_WHITESPACE
  Index(['DriverNumber', 'BroadcastName', 'Abbreviation', 'DriverId', 'TeamName',
         'TeamColor', 'TeamId', 'FirstName', 'LastName', 'FullName',
         'HeadshotUrl', 'CountryCode', 'Position', 'ClassifiedPosition',
         'GridPosition', 'Q1', 'Q2', 'Q3', 'Time', 'Status', 'Points'],
        dtype='object')

As an example, let's display the top ten drivers and their
respective Q3 times. The results are sorted by finishing position, therefore,
this is easy.

  >>> session.results.iloc[0:10].loc[:, ['Abbreviation', 'Q3']]
     Abbreviation                     Q3
  33          VER 0 days 00:01:29.990000
  44          HAM 0 days 00:01:30.248000
  77          BOT 0 days 00:01:30.376000
  11          PER 0 days 00:01:30.445000
  55          SAI 0 days 00:01:30.840000
  10          GAS 0 days 00:01:30.868000
  16          LEC 0 days 00:01:30.987000
  4           NOR 0 days 00:01:31.252000
  14          ALO 0 days 00:01:31.340000
  3           RIC 0 days 00:01:31.382000


Working with laps and lap times
-------------------------------

All individual laps of a session can be accessed through the property
:attr:`Session.laps <fastf1.core.Session.laps>`. The laps are represented 
as :class:`~fastf1.core.Laps` object which again is a subclass of a
:class:`pandas.DataFrame`.

  >>> session = fastf1.get_session(2021, 'French Grand Prix', 'Q')
  >>> session.load()
  >>> session.laps
                        Time Driver  ... FastF1Generated IsAccurate
  0   0 days 00:17:35.479000    GAS  ...           False      False
  1   0 days 00:27:42.702000    GAS  ...           False      False
  2   0 days 00:30:15.038000    GAS  ...           False      False
  3   0 days 00:31:46.936000    GAS  ...           False       True
  4   0 days 00:34:20.695000    GAS  ...           False      False
  ..                     ...    ...  ...             ...        ...
  265 0 days 00:54:22.881000    GIO  ...           False       True
  266 0 days 01:00:32.369000    GIO  ...           False      False
  267 0 days 01:03:24.940000    GIO  ...           False      False
  268 0 days 01:04:56.753000    GIO  ...           False       True
  269 0 days 01:06:42.885000    GIO  ...           False      False
  <BLANKLINE>
  [270 rows x 31 columns]

That's more than 250 laps right there and 26 columns of information.

The following data columns are available:

  >>> session.laps.columns  # doctest: +NORMALIZE_WHITESPACE
  Index(['Time', 'Driver', 'DriverNumber', 'LapTime', 'LapNumber', 'Stint',
         'PitOutTime', 'PitInTime', 'Sector1Time', 'Sector2Time', 'Sector3Time',
         'Sector1SessionTime', 'Sector2SessionTime', 'Sector3SessionTime',
         'SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST', 'IsPersonalBest',
         'Compound', 'TyreLife', 'FreshTyre', 'Team', 'LapStartTime',
         'LapStartDate', 'TrackStatus', 'Position', 'Deleted', 'DeletedReason',
         'FastF1Generated', 'IsAccurate'],
        dtype='object')

A detailed explanation for all these columns can be found in the
documentation of the :class:`~fastf1.core.Laps` class.

The :class:`~fastf1.core.Laps` object is not a simple DataFrame though.
Like FastF1's other data objects, it provides some more features specifically
for working with Formula 1 data.

One of these additional features are methods for selecting specific laps.
So let's see what the fastest lap time was and who is on pole.

  >>> fastest_lap = session.laps.pick_fastest()
  >>> fastest_lap['LapTime']
  Timedelta('0 days 00:01:29.990000')
  >>> fastest_lap['Driver']
  'VER'


Check out this example that shows how you can plot lap times:
:ref:`sphx_glr_examples_gallery_plot_qualifying_results.py`

