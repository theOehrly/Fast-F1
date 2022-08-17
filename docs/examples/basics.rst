
Getting started with the basics
===============================

FastF1 is built mainly around Pandas DataFrame and Series objects.
If you are familiar with Pandas you'll immediately recognize this and working
with the data will be fairly straight forward. (If you're
not familiar with Pandas at all, it might be helpful to check out a short
tutorial.)


Loading a session or an event
------------------------------

The :class:`fastf1.core.Session` object is an important starting point for
everything you do with FastF1. Usually the first thing you want to do
is loading a session. For this, you should use
:func:`fastf1.get_session`.

For example, let's load the Qualifying of the 7th race of the 2021 season:

.. doctest::

  >>> import fastf1
  >>> session = fastf1.get_session(2021, 7, 'Q')
  >>> session.name
  'Qualifying'
  >>> session.date
  Timestamp('2021-06-19 00:00:00')


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
  Session1Date                                  2021-06-18 00:00:00
  Session2                                               Practice 2
  Session2Date                                  2021-06-18 00:00:00
  Session3                                               Practice 3
  Session3Date                                  2021-06-19 00:00:00
  Session4                                               Qualifying
  Session4Date                                  2021-06-19 00:00:00
  Session5                                                     Race
  Session5Date                                  2021-06-20 00:00:00
  F1ApiSupport                                                 True
  Name: French Grand Prix, dtype: object

The :class:`~fastf1.events.Event` object is a subclass of a
:class:`pandas.Series`. The individual values can therefore be accessed as it
is common for pandas objects:

.. doctest::

  >>> session.event['EventName']
  'French Grand Prix'
  >>> session.event['EventDate']  # this is the date of the race day
  Timestamp('2021-06-20 00:00:00')

You can also load an event directly, by using the function
:func:`fastf1.get_session`. The :class:`~fastf1.events.Event` object in turn
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
  Session1Date                                  2021-06-18 00:00:00
  Session2                                               Practice 2
  Session2Date                                  2021-06-18 00:00:00
  Session3                                               Practice 3
  Session3Date                                  2021-06-19 00:00:00
  Session4                                               Qualifying
  Session4Date                                  2021-06-19 00:00:00
  Session5                                                     Race
  Session5Date                                  2021-06-20 00:00:00
  F1ApiSupport                                                 True
  Name: French Grand Prix, dtype: object
  >>> session = event.get_race()
  >>> session.name
  'Race'


Loading a session or and event by name
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
'Emiligia Romagna Grand Prix' but we get the 'Belgian Grand Prix' if we don't
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
is a subclass of a :class:`pandas.DataFrame`.

  >>> schedule = fastf1.get_event_schedule(2021)
  >>> schedule
      RoundNumber       Country      Location  ... Session5 Session5Date F1ApiSupport
  0             0       Bahrain        Sakhir  ...     None          NaT         True
  1             1       Bahrain        Sakhir  ...     Race   2021-03-28         True
  2             2         Italy         Imola  ...     Race   2021-04-18         True
  3             3      Portugal      Portimão  ...     Race   2021-05-02         True
  4             4         Spain      Montmeló  ...     Race   2021-05-09         True
  5             5        Monaco   Monte-Carlo  ...     Race   2021-05-23         True
  6             6    Azerbaijan          Baku  ...     Race   2021-06-06         True
  7             7        France  Le Castellet  ...     Race   2021-06-20         True
  8             8       Austria     Spielberg  ...     Race   2021-06-27         True
  9             9       Austria     Spielberg  ...     Race   2021-07-04         True
  10           10            UK   Silverstone  ...     Race   2021-07-18         True
  11           11       Hungary      Budapest  ...     Race   2021-08-01         True
  12           12       Belgium           Spa  ...     Race   2021-08-29         True
  13           13   Netherlands     Zandvoort  ...     Race   2021-09-05         True
  14           14         Italy         Monza  ...     Race   2021-09-12         True
  15           15        Russia         Sochi  ...     Race   2021-09-26         True
  16           16        Turkey      Istanbul  ...     Race   2021-10-10         True
  17           17           USA        Austin  ...     Race   2021-10-24         True
  18           18        Mexico   Mexico City  ...     Race   2021-11-07         True
  19           19        Brazil     São Paulo  ...     Race   2021-11-14         True
  20           20         Qatar     Al Daayen  ...     Race   2021-11-21         True
  21           21  Saudi Arabia        Jeddah  ...     Race   2021-12-05         True
  22           22           UAE     Abu Dhabi  ...     Race   2021-12-12         True
  <BLANKLINE>
  [23 rows x 18 columns]
  >>> schedule.columns  # doctest: +NORMALIZE_WHITESPACE
  Index(['RoundNumber', 'Country', 'Location', 'OfficialEventName', 'EventDate',
       'EventName', 'EventFormat', 'Session1', 'Session1Date', 'Session2',
       'Session2Date', 'Session3', 'Session3Date', 'Session4', 'Session4Date',
       'Session5', 'Session5Date', 'F1ApiSupport'],
      dtype='object')

The event schedule provides methods for selecting specific events:

  >>> gp_12 = schedule.get_event_by_round(12)
  >>> gp_12['Country']
  'Belgium'
  >>> gp_austin = schedule.get_event_by_name('Austin')
  >>> gp_austin['Country']
  'USA'


Displaying driver info and session results
------------------------------------------

We have created a session now but everything has been rather boring so far.
So lets make it a bit more interesting by taking a look at the results of
this session. For this, it is first necessary to call
:func:`Session.load <fastf1.core.Session.load>`. This will load all available data for the
session from various APIs. Downloading and processing of the data may take a
few seconds. It is highly recommended to utilize FastF1's builtin caching
functionality to speed up data loading and to prevent excessive API requests.

  >>> fastf1.Cache.enable_cache("path/to/empty/folder")  # doctest: +SKIP
  >>> session = fastf1.get_session(2021, 'French Grand Prix', 'Q')
  >>> session.load()
  >>> session.results
     DriverNumber BroadcastName Abbreviation  ... Time Status Points
  33           33  M VERSTAPPEN          VER  ...  NaT           0.0
  44           44    L HAMILTON          HAM  ...  NaT           0.0
  77           77      V BOTTAS          BOT  ...  NaT           0.0
  11           11       S PEREZ          PER  ...  NaT           0.0
  55           55       C SAINZ          SAI  ...  NaT           0.0
  10           10       P GASLY          GAS  ...  NaT           0.0
  16           16     C LECLERC          LEC  ...  NaT           0.0
  4             4      L NORRIS          NOR  ...  NaT           0.0
  14           14      F ALONSO          ALO  ...  NaT           0.0
  3             3   D RICCIARDO          RIC  ...  NaT           0.0
  31           31        E OCON          OCO  ...  NaT           0.0
  5             5      S VETTEL          VET  ...  NaT           0.0
  99           99  A GIOVINAZZI          GIO  ...  NaT           0.0
  63           63     G RUSSELL          RUS  ...  NaT           0.0
  47           47  M SCHUMACHER          MSC  ...  NaT           0.0
  6             6      N LATIFI          LAT  ...  NaT           0.0
  7             7   K RAIKKONEN          RAI  ...  NaT           0.0
  9             9     N MAZEPIN          MAZ  ...  NaT           0.0
  18           18      L STROLL          STR  ...  NaT           0.0
  22           22     Y TSUNODA          TSU  ...  NaT           0.0
  <BLANKLINE>
  [20 rows x 16 columns]

The results object (:class:`fastf1.core.SessionResults`) is a subclass of a
:class:`pandas.DataFrame`. Therefore, we can take a look at what data columns
there are:

  >>> session.results.columns  # doctest: +NORMALIZE_WHITESPACE
  Index(['DriverNumber', 'BroadcastName', 'Abbreviation', 'TeamName',
         'TeamColor', 'FirstName', 'LastName', 'FullName', 'Position',
         'GridPosition', 'Q1', 'Q2', 'Q3', 'Time', 'Status', 'Points'],
        dtype='object')

As an example, lets display the top ten drivers and their
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
:attr:`Session.laps <fastf1.core.Session.laps>`. The laps are represented in
as :class:`~fastf1.core.Laps` object which again is a subclass of a
:class:`pandas.DataFrame`.

  >>> session = fastf1.get_session(2021, 'French Grand Prix', 'Q')
  >>> fastf1.Cache.enable_cache("path/to/empty/folder")  # doctest: +SKIP
  >>> session.load()
  >>> session.laps
                        Time DriverNumber  ... IsAccurate            LapStartDate
  0   0 days 00:28:44.908000           33  ...      False 2021-06-19 13:03:06.950
  1   0 days 00:31:14.909000           33  ...      False 2021-06-19 13:14:12.111
  2   0 days 00:32:45.910000           33  ...       True 2021-06-19 13:16:42.112
  3   0 days 00:50:42.329000           33  ...      False 2021-06-19 13:18:13.113
  4   0 days 00:52:59.529000           33  ...      False 2021-06-19 13:36:10.262
  ..                     ...          ...  ...        ...                     ...
  265 0 days 00:39:10.594000           18  ...      False 2021-06-19 13:22:15.102
  266 0 days 00:41:23.178000           18  ...       True 2021-06-19 13:24:37.797
  267 0 days 00:41:30.642000           18  ...      False 2021-06-19 13:26:50.381
  268 0 days 00:17:40.791000           22  ...      False 2021-06-19 13:00:22.952
  269 0 days 00:26:20.982000           22  ...      False 2021-06-19 13:03:07.994
  <BLANKLINE>
  [270 rows x 27 columns]

That's more than 250 laps right there and 26 columns of information.

The following data columns are available:

  >>> session.laps.columns  # doctest: +NORMALIZE_WHITESPACE
  Index(['Time', 'DriverNumber', 'LapTime', 'LapNumber', 'PitOutTime',
         'PitInTime', 'Sector1Time', 'Sector2Time', 'Sector3Time',
         'Sector1SessionTime', 'Sector2SessionTime', 'Sector3SessionTime',
         'SpeedI1', 'SpeedI2', 'SpeedFL', 'SpeedST', 'IsPersonalBest',
         'Compound', 'TyreLife', 'FreshTyre', 'Stint', 'LapStartTime', 'Team',
         'Driver', 'TrackStatus', 'IsAccurate', 'LapStartDate'],
        dtype='object')

The detailed explanation for all these columns can be found in the
documentation of the :class:`~fastf1.core.Laps` class.

The :class:`~fastf1.core.Laps` object is not a simple DataFrame though.
Like FastF1's other data objects it provides some more features specifically
for working with Formula 1 data.

One of these additional features are methods for selecting specific laps.
So let's see what the fastest laptime was and who is on pole.

  >>> fastest_lap = session.laps.pick_fastest()
  >>> fastest_lap['LapTime']
  Timedelta('0 days 00:01:29.990000')
  >>> fastest_lap['Driver']
  'VER'


Check out this example that shows how you can plot lap times:
:ref:`sphx_glr_examples_gallery_plot_qualifying_results.py`

