######
FastF1
######

For the passionate F1 nerds.

============
Introduction
============

FastF1 gives you access to F1 lap timing, car telemetry and position,
tyre data, weather data, the event schedule and session results.

**Main features**:

- Access to F1 timing data, telemetry, sessions results and more
- Full support for `Ergast <http://ergast.com/mrd/>`_ to access current and
  historical F1 data
- All data is provided in the form of extended Pandas DataFrames to make
  working with the data easy while having powerful tools available
- Adds custom functions to the Pandas objects specifically to make working
  with F1 data quick and simple
- Integration with Matplotlib to facilitate data visualization
- Implements caching for all API requests to speed up your scripts


To get a quick overview over how to use FastF1, check out
:doc:`examples/index` or the :doc:`examples_gallery/index`.

Note that FastF1 handles big chunks of data (~50-100mb per session). To improve
performance, data is per default cached locally. The default placement
of the cache is operating system specific. A custom location can be set if
desired. For more information see :class:`~fastf1.req.Cache`.

Have fun!

============
Installation
============

It is recommended to install FastF1 using `pip`:

.. code-block:: bash

   pip install fastf1

Note that Python 3.8 or higher is required.

Alternatively, a wheel or a source distribution can be downloaded from Pypi.

You can also install using `conda`:

.. code-block:: bash

  conda install -c conda-forge fastf1


Third-party packages
--------------------

- R package that wraps FastF1: https://cran.r-project.org/package=f1dataR

These packages are not directly related to the FastF1 project. Questions and
suggestions regarding these packages need to be directed at their respective
maintainers.



======================
Supporting the Project
======================

If you want to support the continuous development of FastF1, you can sponsor me
on GitHub or buy me a coffee.


.. raw:: html

  <iframe src="https://github.com/sponsors/theOehrly/button" title="Sponsor theOehrly" height="32" width="114" style="border: 0; border-radius: 6px; margin: 0 30px 0 0; padding: 0px;"></iframe>

  <a href="https://www.buymeacoffee.com/fastf1" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/default-orange.png" alt="Buy Me A Coffee" height="31"  width="134"></a>


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
   Event Schedule         event names, countries, locations, dates, scheduled starting times,... (previous and current season including upcoming events)  :mod:`~fastf1.events` :func:`~fastf1.get_event_schedule` :func:`~fastf1.get_event`
   Results                driver names, team names, finishing and grid positions, points, finishing status,...                                            :class:`~fastf1.core.SessionResults`, :class:`~fastf1.core.DriverResult`
   Timing Data            sector times, lap times, pit stops, tyre data and much more                                                                     :attr:`~fastf1.core.Session.laps` :class:`~fastf1.core.Laps`
   Track Status           flags, safety car                                                                                                               :attr:`~fastf1.core.Session.track_status`
   Session Status         started, finished, finalized                                                                                                    :attr:`~fastf1.core.Session.session_status`
   Race Control Messages  investigations, penalties, restart announcements,...                                                                            :attr:`~fastf1.core.Session.race_control_messages`
   Telemetry              speed, rpm, gear, normalized track position, ...                                                                                :class:`~fastf1.core.Telemetry` :func:`~fastf1.core.Lap.get_car_data`
   Track Markers          corner numbers, marshall sectors, marshall lights                                                                               :func:`~fastf1.core.Session.get_circuit_info`, :ref:`circuit_info`
   Ergast API             all endpoints that are provided by Ergast                                                                                       :ref:`ergast`
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
`Ergast <http://ergast.com/mrd/>`_).


========
Contents
========


.. toctree::
   ← Back to Github <https://github.com/theOehrly/Fast-F1>

.. toctree::
   :maxdepth: 1
   :caption: Contents:

   examples/index
   examples_gallery/index
   fastf1
   core
   events
   api
   ergast
   circuit_info
   utils
   plotting
   livetiming
   logging
   legacy

.. toctree::
   :maxdepth: 1
   :caption: Information:

   time_explanation
   howto_accurate_calculations
   known_bugs
   troubleshooting
   contributing/index
   changelog/index


========================================================
Questions, Contacting the Maintainer and Code of Conduct
========================================================

For questions that may be of interest to the whole community, please use the
Github `Discussions <https://github.com/theOehrly/Fast-F1/discussions>`_
section to ask for help. This includes general support questions.

In case of questions that you prefer to discuss privately, feel free to contact
me via email at oehrly@mailbox.org. Any requests to this address will be
treated with confidentiality, if desired. **Do not use this email address for
general support requests! Such requests will likely be ignored.**

FastF1 has a `Code of Conduct <https://github.com/theOehrly/Fast-F1/blob/master/CODE_OF_CONDUCT.md>`_.
Complaints about a perceived breach of this code of conduct should be sent to
oehrly@mailbox.org, in almost all cases. Please refer to the Code of Conduct,
available through the main page of the GitHub repository (or click
`here <https://github.com/theOehrly/Fast-F1/blob/master/CODE_OF_CONDUCT.md>`_),
for information on how breaches are reported, how the
Code of Conduct is enforced and what values FastF1 encourages.


==================
Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


======
Notice
======

FastF1 and this website are unofficial and are not associated in any way with
the Formula 1 companies. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD
CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of Formula One
Licensing B.V.

