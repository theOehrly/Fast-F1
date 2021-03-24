=======
Fast F1
=======

A python package for accessing F1 historical timing data and telemetry.


IMPORTANT NOTE: Status of the project (Update 3: 13th March 2021)
=================================================================

**FastF1 v2.1 is now available for installation through pip.
The old way of installing via pip + git directly from the master branch is no
longer recommended.**

It is no longer possible to download telemetry and car position data after a
session!

See `this <https://twitter.com/F1Help/status/1335939396240093185>`_ Twitter
post for some information.

This means:

  - It is still **possible** to load timing data, tire data, track status
    data and session status data.

  - It is **not possible** to load car telemetry data
    (includes position data). You need to record live timing data during
    a session for this!


Live timing data
----------------

**A livetiming client has been added for the v2.1 release. The client can be
used to save the live timing telemetry data stream that is available during
sessions. This can potentially be used to work around the problem of missing
data on the server.**

The live timing client does not and will never parse data in real time!
Data can only be parsed and used after a session has completed. This is a
limitation of FastF1's api parser. For various reasons there is no
intention of changing this.

Consider all live timing related functionality as beta-grade at best.

For usage see the documentation.


Changes
-------

If you have used previous versions of FastF1, please read the changelog in the
documentation.

V2.1 introduces some new features and some breaking changes.
The documentation is improved in general. Also, there is a new section
discussing how to get the most accurate results from the data that is
available. It may be worth reading if you want to make more complicated
analyses and visualizations.

Other
-----

Please report bugs if (when) you find them. Feel free to report complaints about
unclear documentation too.
The available documentation is updated for this version.


Interested in contributing? See below...


Installation
============

It is recommended to install FastF1 using pip:

    pip install fastf1

Note that Python 3.8 is required.

Alternatively a wheel or a source distribution can be downloaded from the
Github releases page.

Usage
=====

Full documentation can be found
`here <https://theoehrly.github.io/Fast-F1/fastf1.html>`_.

Creating a simple analysis is not very difficult, especially if you are already familiar
with pandas and numpy.

Suppose that we want to analyse the race pace of Leclerc compared to 
Hamilton from the Bahrain GP (weekend number 2) of 2019.

.. code:: python

    import fastf1 as ff1
    from fastf1 import plotting
    from matplotlib import pyplot as plt

    plotting.setup_mpl()

    ff1.Cache.enable_cache('path/to/folder/for/cache')  # optional but recommended

    race = ff1.get_session(2020, 'Turkish Grand Prix', 'R')
    laps = race.load_laps()

    lec = laps.pick_driver('LEC')
    ham = laps.pick_driver('HAM')

Once the session is loaded, and drivers are selected, you can plot the
information.

:code:`fastf1.plotting` provides some special axis formatting and data type conversion. This is required
for generating a correct plot.

It is not necessary to enable the usage of a cache but it is recommended. Simply provide
the path to some empty folder on your system.

.. code:: python

    fig, ax = plt.subplots()
    ax.plot(lec['LapNumber'], lec['LapTime'], color='red')
    ax.plot(ham['LapNumber'], ham['LapTime'], color='cyan')
    ax.set_title("LEC vs HAM")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")
    plt.show()

.. image:: docs/_static/readme.svg
    :target: docs/_static/readme.svg


Compatibility
=============

Timing data is available for the 2018, 2019 and 2020 season.
Very basic weekend information is available for older seasons (limited to
`Ergast web api <http://ergast.com/mrd/>`_). Live timing and telemetry is only
available starting from 2018.



Roadmap
=======

This is a rather loose roadmap with no fixed timeline whatsoever.

  - Improvements to the current plotting functionality
  - Some default plots to easily allow creating nice visualizations and interesting comparisons
  - General improvements and smaller additions to the current core functionality
  - Support for F1's own data api to get information about events, sessions, drivers and venues



Contributing
============

Contributions are welcome of course. If you are interested in contributing, open an issue for the proposed feature
or issue you would like to work on. This way we can coordinate so that no unnecessary work is done.

Working directly on the core and api code will require some time to understand. Creating nice default plots on the
other hand does not required as deep of an understanding of the code and is therefore easier to accomplish. Pick
whatever you like to do.

