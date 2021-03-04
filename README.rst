=======
Fast F1
=======

A python package for accessing F1 historical timing data and telemetry.


IMPORTANT NOTE: Status of the project (Updated: 4th March 2021)
===============================================================

Currently this module is not fully usable which is the result of server issues
with the F1 API.

See `this <https://twitter.com/F1Help/status/1335939396240093185>`_ Twitter
post for some information.

For the 2019 and 2020 seasons this means:

  - It is still **possible** to load timing data, tire data, track status
    data and session status data.

  - It is **not possible** to load car telemetry data
    (includes position data).

What this means for the 2021 season cannot yet be said.

You will need FastF1 v2.1 to load the 2019/2020 seasons easily. Previous
versions do not allow for loading laps data and car telemetry separately. Use
the new argument ``with_telemetry=False`` when calling
``Session.load_laps()`` to prevent the loading of unavailable telemetry data.

A pre-release of FastF1 v2.1 is available for download through Github's releases.
Please report bugs if (when) you find them. Feel free to report complaints about
unclear documentation too.
The available documentation is updated for this version. There may be further
changes.

If you have used previous versions of FastF1, please read the changelog in the
documentation.

V2.1 introduces some new features and some breaking changes.
The documentation is improved in general. Also, there is a new section
discussing how to get the most accurate results from the data that is
available. It may be worth reading if you want to make more complicated
analyses and visualizations.


Interested in contributing? Read on...

Roadmap
=======

This is a rather loose roadmap with no fixed timeline whatsoever.

  - Improvements to the current plotting functionality
  - Some default plots to easily allow creating nice visualizations and interesting comparisons
  - General improvements and smaller additions to the current core functionality
  - Support for F1's own data api to get information about events, sessions, drivers and venues

And if necessary:

  - recording of live timing during a session


Contributing
============

Contributions are welcome of course. If you are interested in contributing, open an issue for the proposed feature
or issue you would like to work on. This way we can coordinate so that no unnecessary work is done.

Working directly on the core and api code will require some time to understand. Creating nice default plots on the
other hand does not required as deep of an understanding of the code and is therefore easier to accomplish. Pick
whatever you like to do.


Installation
============

Install the wheel that is available for download through Github's releases:

    pip install fastf1-*version*-py3-none-any.whl

Note that Python 3.8 is required.

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
