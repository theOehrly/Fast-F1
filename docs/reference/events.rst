.. _event-schedule:

Event Schedule
==============

.. currentmodule:: fastf1.events

Events and the Event Schedule are represented using the following objects.
To access schedule data, see :ref:`loading-data`.

.. autosummary::
    :toctree: api_autogen/
    :template: class_summary_noinherited.rst

    EventSchedule
    Event


The :class:`EventSchedule` provides information about past and upcoming
Formula 1 events.

An :class:`Event` can be a race weekend or a testing event. Each event
consists of multiple :class:`~fastf1.core.Session`.

The event schedule objects are built on top of pandas'
:class:`pandas.DataFrame` (event schedule) and :class:`pandas.Series` (event).
Therefore, the usual methods of these pandas objects can be used in addition
to the special methods described here.


.. _event-schedule-data:

Event Schedule Data
-------------------

The event schedule and each event provide the following information as
DataFrame columns or Series values:

.. list-table::
   :widths: 20 20 60
   :header-rows: 1

   * - Name
     - Data Type
     - Description
   * - **RoundNumber**
     - :class:`int`
     - The number of the championship round. This is unique for race weekends, while testing events all share the round number zero.
   * - **Country**
     - :class:`str`
     - The country in which the event is held.
   * - **Location**
     - :class:`str`
     - The event location; usually the city or region in which the track is situated.
   * - **OfficialEventName**
     - :class:`str`
     - The official event name as advertised, including sponsor names and stuff.
   * - **EventName**
     - :class:`str`
     - A shorter event name usually containing the country or location but no no sponsor names. This name is required internally for proper api access.
   * - **EventDate**
     - :class:`pd.Timestamp`
     - The events reference date and time. This is used mainly internally. Usually, this is the same as the date of the last session.
   * - **EventFormat**
     - :class:`str`
     - The format of the event. One of 'conventional', 'sprint', 'sprint_shootout', 'sprint_qualifying', 'testing'. See :ref:`event-formats`
   * - **Session[1-5]**
     - :class:`str`
     - The name of the session. One of 'Practice 1', 'Practice 2', 'Practice 3', 'Qualifying', 'Sprint', 'Sprint Shootout' or 'Race'. Testing sessions are considered practice.
   * - **Session[1-5]Date**
     - :class:`pd.Timestamp`
     - The date and time at which the session is scheduled to start or was scheduled to start as timezone-aware local timestamp. (Timezone-aware local timestamps are not available when the ``'ergast'`` backend is used.)
   * - **Session[1-5]DateUtc**
     - :class:`pd.Timestamp`
     - The date and time at which the session is scheduled to start or was scheduled to start as non-timezone-aware UTC timestamp.
   * - **F1ApiSupport**
     - :class:`bool`
     - Denotes whether this session is supported by the official F1 API. Lap timing data and telemetry data can only be loaded if this is true.


.. _event-supported-seasons:

Supported Seasons
.................

FastF1 provides its own event schedule for the 2018 season and all later
seasons. The schedule for all seasons before 2018 is built using data from
the Ergast API. Only limited data is available for these seasons. Usage of the
Ergast API can be enforced for all seasons by setting ``backend='ergast'``,
in which case the same limitations apply for the more recent seasons too.

**Exact scheduled starting times for all sessions**:
Supported starting with the 2018 season.
Starting dates for sessions before 2018 (or when enforcing usage of the Ergast
API) assume that each race weekend was held according to the 'conventional'
schedule (Practice 1/2 on friday, Practice 3/Qualifying on Saturday, Race on
Sunday). A starting date and time can only be provided for the race session.
All other sessions are calculated from this and no starting times can be
provided for these. These assumptions will be incorrect for certain events!

**Testing events**: Supported for the 2020 season and later seasons. Not
supported if usage of the Ergast API is enforced.


.. _event-formats:

Event Formats
.............

- ``"conventional"``: **Practice 1, Practice 2, Practice 3, Qualifying, Race**

- ``"sprint"``: **Practice 1, Qualifying, Practice 2, Sprint, Race**

  This is the original sprint format that was used in some races in 2021 and
  2022. The Qualifying on friday set the grid for the Sprint on saturday.
  The results from the Sprint set the grid for the Race on sunday.

- ``"sprint_shootout"``: **Practice 1, Qualifying, Sprint Shootout, Sprint, Race**

  This format was used in 2023. The Qualifying on friday sets the grid for the
  main Race on sunday. The Sprint Shootout on saturday is held in similar
  fashion to a normal Qualifying session and sets the grid for the Sprint that
  takes place on saturday as well.

- ``"sprint_qualifying"``: **Practice 1, Sprint Qualifying, Sprint, Qualifying,
  Race**

  This format is used starting from 2024. In general, it is similar to the
  previous 'sprint_shootout' format, but the order of the sessions was changed
  and 'Sprint Shootout' is renamed to 'Sprint Qualifying'. This means that
  the Sprint Qualifying on friday is held in similar fashion to a normal
  Qualifying and sets the grid for the Sprint on saturday. The Qualifying later
  on saturday then sets the grid for the race on Sunday.

- ``"testing"``: **no fixed session order**

  usually three practice sessions on three separate days


.. _event-session-identifier:

Session identifiers
...................

Multiple event (schedule) related functions and methods make use of a session
identifier to differentiate between the various sessions of one event.
This identifier can currently be one of the following:

- session name abbreviation: ``'FP1', 'FP2', 'FP3', 'Q', 'S', 'SS', 'SQ',
  'R'``
- full session name: ``'Practice 1', 'Practice 2',
  'Practice 3', 'Sprint', 'Sprint Shootout', 'Sprint Qualifying',
  'Qualifying', 'Race'``;
  provided names will be normalized, so that the name is
  case-insensitive
- number of the session: ``1, 2, 3, 4, 5``

.. note::
    The old ``'sprint'`` event format from 2021 and 2022 originally
    used the name 'Sprint Qualifying' before renaming these sessions to just
    'Sprint'. The official schedule for 2021 now lists all these sessions as
    'Sprint' and FastF1 will therefore return all these sessions as 'Sprint'.
    When querying for a specific session, FastF1 will also accept the
    'Sprint Qualifying'/'SQ' identifier instead of only 'Sprint'/'S' for
    backwards compatibility.
