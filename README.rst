=======
Fast F1
=======

A python package for accessing F1 historical timing data and telemetry.


UPDATE: Telemetry data is available for download again!
=======================================================

Car telemetry and position data can be downloaded after a session again.
The api problems that caused this data to be unavailable have
*apparently* been fixed!

This means, that the full functionality of this package is available
again without the need to record the live timing data stream.

Data seems to be fully available for the 2018 to 2021 season.

A word of caution: I do not have any insight into the server side
of the api. This problem has solved itself as surprisingly as it had
started. If you think that you "rely" on this data for some reason, you
*should* go ahead and **continue recording** the live data stream
...redundancy and stuff.


Installation
============

It is recommended to install FastF1 using pip:

    pip install fastf1

Note that Python 3.8 is required.

Alternatively, a wheel or a source distribution can be downloaded from the
Github releases page or from Pypi.


Documentation
=============

... can be found `here <https://theoehrly.github.io/Fast-F1/fastf1.html>`_.



General Information
===================

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

Interested in contributing? There's some info at the end of this document...


Usage
=====

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


For more information, check the documentation
`here <https://theoehrly.github.io/Fast-F1/fastf1.html>`_.


Compatibility
=============

Timing data, car telemetry and position data is available for the 2018 to 2021 seasons.
Very basic weekend information is available for older seasons (limited to
`Ergast web api <http://ergast.com/mrd/>`_).


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

Also, the documentation needs an examples section. You can provide some snippets of your code as examples for
others, to help them get started easier.
