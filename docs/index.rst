######################
Introduction to FastF1
######################

FastF1 gives you access to F1 lap timing, car telemetry and position,
tyre data, weather data, the event schedule and session results.


.. raw:: html

    <style>
      .doc-tile-container {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 20px;
        margin: 30px 0;
      }
      .doc-tile {
        width: 200px;
        box-shadow: 0 4px 8px var(--pst-color-shadow, rgba(0, 0, 0, 0.1));
        border-radius: 5px;
        padding: 20px;
        text-align: center;
        background-color: var(--pst-color-surface, var(--pst-color-background, white));
        transition: transform 0.3s, box-shadow 0.3s;
        text-decoration: none !important;
        color: inherit !important;
        display: block;
      }
      .doc-tile:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 16px var(--pst-color-shadow, rgba(0, 0, 0, 0.2));
      }
      .doc-tile h2 {
        margin-top: 0;
        font-size: 1.2rem;
        margin-bottom: 5px;
        color: var(--pst-color-text-base);
      }
      .doc-tile p {
        margin: 0;
        font-size: 0.9rem;
        color: var(--pst-color-text-muted, #666);
      }
      .doc-tile-icon {
        font-size: 3rem;
        margin-bottom: 15px;
        color: #e74c3c;
      }
    </style>
    <div class="doc-tile-container">
      <a href="getting_started/index.html" class="doc-tile">
        <div class="doc-tile-icon">📚</div>
        <h2>Getting Started</h2>
        <p>Examples and tutorials to help you get started with FastF1</p>
      </a>
      <a href="user_guide/index.html" class="doc-tile">
        <div class="doc-tile-icon">📖</div>
        <h2>User Guide</h2>
        <p>Comprehensive guide to using FastF1 effectively</p>
      </a>
      <a href="api_reference/index.html" class="doc-tile">
        <div class="doc-tile-icon">🔍</div>
        <h2>API Reference</h2>
        <p>Detailed documentation of FastF1's classes and functions</p>
      </a>
       <a href="gen_modules/examples_gallery/index.html" class="doc-tile">
         <div class="doc-tile-icon">🖼️</div>
         <h2>Example Gallery</h2>
         <p>Browse through examples showing FastF1's capabilities</p>
       </a>

      <a href="#available-data" class="doc-tile">
        <div class="doc-tile-icon">📊</div>
        <h2>Available Data</h2>
        <p>Overview of all F1 data available through FastF1</p>
      </a>
      <a href="contributing/index.html" class="doc-tile">
        <div class="doc-tile-icon">⚙️</div>
        <h2>Development</h2>
        <p>How to contribute to FastF1 and help improve the package</p>
      </a>
    </div>



========
Features
========

- Access to F1 timing data, telemetry, sessions results and more
- Full support for the Ergast compatible `jolpica-f1 <https://github.com/jolpica/jolpica-f1/blob/main/docs/README.md>`_ API to access current and
  historical F1 data
- All data is provided in the form of extended Pandas DataFrames to make
  working with the data easy while having powerful tools available
- Adds custom functions to the Pandas objects specifically to make working
  with F1 data quick and simple
- Integration with Matplotlib to facilitate data visualization
- Implements caching for all API requests to speed up your scripts


..
    To get a quick overview over how to use FastF1, check out
    :doc:`examples/index` or the :doc:`gen_modules/examples_gallery/index`.

    Note that FastF1 handles big chunks of data (~50-100mb per session). To improve
    performance, data is per default cached locally. The default placement
    of the cache is operating system specific. A custom location can be set if
    desired. For more information see :class:`~fastf1.req.Cache`.


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


========
Contents
========

.. toctree::
   :maxdepth: 1

   getting_started/index
   gen_modules/examples_gallery/index
   api_reference/index
   data_reference/index
   changelog/index
   contributing/index


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


======
Notice
======

FastF1 and this website are unofficial and are not associated in any way with
the Formula 1 companies. F1, FORMULA ONE, FORMULA 1, FIA FORMULA ONE WORLD
CHAMPIONSHIP, GRAND PRIX and related marks are trade marks of Formula One
Licensing B.V.

