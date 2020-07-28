=======
Fast F1
=======

A python package for accessible F1 historical data and telemetry. 

Installation
============

You can install and update this package using the following command
::
    pip install git+https://github.com/theOehrly/Fast-F1.git

Note that Python 3.8 is required.

Usage
=====

Full documentation can be found
`here <https://theoehrly.github.io/Fast-F1/fastf1.html>`_.

Setting up an experiment is easy, especially if you are already familiar
with pandas and numpy.

Suppose that we want to analyse the race pace of Leclerc compared to 
Hamilton from the Bahrain GP (weekend number 2) of 2019.

.. code:: python

    import fastf1 as ff1
    from fastf1 import plotting
    from matplotlib import pyplot as plt

    ff1.utils.enable_cache('path/to/folder/for/cache')  # optional but recommended

    race = ff1.get_session(2019, 'Bahrain', 'R')
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
    plotting.laptime_axis(ax)
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

Starting with the Austrian GP 2020 the API provides the position data in a
somewhat different format. This currently breaks ALL functionality of the track class.
Maybe also other functionality.

The library is fully compatible with 2018 and 2019 season.  Older seasons are still
accessible and it is possible to obtain general weekend information (limited to
`Ergast web api <http://ergast.com/mrd/>`_). Live timing and telemetry is only
available starting from 2018.
