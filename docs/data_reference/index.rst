**************
Data Reference
**************


.. warning::

  The data reference is still under construction and currently only provides limited
  information.


The data reference provides an overview of all the data that is available via FastF1.


.. toctree::
   :maxdepth: 1
   :caption: Additional Information

   howto_accurate_calculations
   time_explanation


==============
Available Data
==============

The following is a short overview over the available data with some references
to functions and objects used to work with this data.

In most cases, the default workflow with FastF1 is to create a
:class:`~fastf1.core.Session` object using :func:`~fastf1.get_session`. You,
will then access all data through the session object. One notable exception to
this pattern is the wrapper for Ergast.

.. table:: Overview over the available data
   :widths: auto

   =====================  ==============================================================================================================================  ==================================================================================================
   Topic                  Data                                                                                                                            References
   =====================  ==============================================================================================================================  ==================================================================================================
   Event Schedule         event names, countries, locations, dates, scheduled starting times,... (previous and current season including upcoming events)  :ref:`event-schedule` :func:`~fastf1.get_event_schedule` :func:`~fastf1.get_event`
   Results                driver names, team names, finishing and grid positions, points, finishing status,...                                            :class:`~fastf1.core.SessionResults`, :class:`~fastf1.core.DriverResult`
   Timing Data            sector times, lap times, pit stops, tyre data and much more                                                                     :attr:`~fastf1.core.Session.laps` :class:`~fastf1.core.Laps`
   Track Status           flags, safety car                                                                                                               :attr:`~fastf1.core.Session.track_status`
   Session Status         started, finished, finalized                                                                                                    :attr:`~fastf1.core.Session.session_status`
   Race Control Messages  investigations, penalties, restart announcements,...                                                                            :attr:`~fastf1.core.Session.race_control_messages`
   Telemetry              speed, rpm, gear, normalized track position, ...                                                                                :class:`~fastf1.core.Telemetry` :func:`~fastf1.core.Lap.get_car_data`
   Track Markers          corner numbers, marshall sectors, marshall lights                                                                               :func:`~fastf1.core.Session.get_circuit_info`, :ref:`circuit_info`
   Jolpica-F1 API         all endpoints that are provided by Jolpica-F1 (previously Ergast)                                                               :ref:`jolpica`
   =====================  ==============================================================================================================================  ==================================================================================================


Compatibility and Availability
------------------------------

Timing data, session information, car telemetry and position data are available
from 2018 onwards. (This data is usually available within 30-120 minutes after
the end of a session.)
It is also possible to obtain this data by recording the data live stream,
using the live timing recorder that is built into FastF1. Usually this is not
necessary but there have been server issues in the past which caused the
data to be not available for download. Recording of the data live stream is
therefore mostly a solution for redundancy.

Schedule information and session results are available for older seasons as
well, going back as far as 1950 (limited to data that is available through
`Ergast <https://ergast.com/mrd/>`_).
