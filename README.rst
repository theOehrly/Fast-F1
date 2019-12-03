=======
Fast F1
=======

A python package for accessible F1 historical data and telemetry. 

Installation
============

You can install this package using pip
::
    pip install git+https://github.com/Ax6/fast-f1.git

Usage
=====

Full documentation can be found
`here <https://ax6.github.io/Fast-F1/fast-f1.html>`_.

Setting up an experiment is easy, especially if you are already familiar
with pandas and numpy.

Suppose that we want to analyse the race pace of Leclerc compared to 
Hamilton from the Bahrain GP of 2019.::

    import fastf1 as f1
    from fastf1 import plots
    from matplotlib import pyplot as plt

    race = f1.get_session(2019, 2, 'R').init()
    # Season, Race number and session (FP#, Q and R)

    lec = race.summary['Driver'] == 'LEC'
    ham = race.summary['Driver'] == 'HAM'

Once the session is loaded, and drivers are selected, you can plot the
information::

    fig, ax = plt.subplots()
    ax.plot(race.summary[lec]['NumberOfLaps'], race.summary[lec]['LapTime'], color='red')
    ax.plot(race.summary[ham]['NumberOfLaps'], race.summary[ham]['LapTime'], color='cyan')
    plt.show()

.. image:: docs/source/_static/readme.svg
    :target: docs/source/_static/readme.svg

Compatibility
=============

Library is fully compatible with 2018 and 2019 season.
While previous seasons are still accessible and it is possible to obtain
general weekend information (basically what you can get from
`Ergast web api <http://ergast.com/mrd/>`_) live timing and telemetry
data is only available starting from 2018.
