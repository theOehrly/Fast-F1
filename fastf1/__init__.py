"""
Introduction
============

This package features two main online sources of data:
    - The official f1 data stream ->
      `f1-live <https://www.formula1.com/en/f1-live.html>`_
    - Ergast web api -> `ergast.com <http://ergast.com/mrd/>`_

Car position, speed traces, tyres, timings and weekend history are some
of the many available resources. No formula1 account is needed.

The library is designed to be interfaced with matplotlib (although you
can use whatever you want) but there is a neat :mod:`fastf1.plotting` module which
you can use to create nice graphs more easily.

This package handles big chunks of data (~50-100mb per session) so most of the
information is stored locally as cached requests (be aware).

Have fun!


Getting started
===============

Setting up a running snippet is straightforward::

    import fastf1 as ff1

    ff1.Cache.enable_cache('path/to/folder/for/cache')  # optional but highly recommended

    monza_quali = ff1.get_session(2019, 'Monza', 'Q')

    vettel = monza_quali.get_driver('VET')
    print(f"Pronto {vettel.name}?")
    # Pronto Se🅱️astian?

For some more advanced stuff, just a few more steps::

    from matplotlib import pyplot as plt
    from fastf1 import plotting

    plotting.setup_mpl()

    laps = monza_quali.load_laps(with_telemetry=True)
    fast_leclerc = laps.pick_driver('LEC').pick_fastest()
    lec_car_data = fast_leclerc.get_car_data()
    t = lec_car_data['Time']
    vCar = lec_car_data['Speed']

    # The rest is just plotting
    fig, ax = plt.subplots()
    ax.plot(t, vCar, label='Fast')
    ax.set_xlabel('Time')
    ax.set_ylabel('Speed [Km/h]')
    ax.set_title('Leclerc is')
    ax.legend()
    plt.show()

.. image:: _static/gettingstarted.svg
    :target: _static/gettingstarted.svg


It is not necessary to enable the usage of the cache but it is highly recommended. Simply provide
the path to some empty folder on your system. Using the cache will greatly speed up loading of the data.


Package functions
=================
Available functions directly accessible from fastf1 package

.. autofunction:: fastf1.core.get_session
    :noindex:

.. autofunction:: fastf1.api.Cache.enable_cache
    :noindex:

.. autofunction:: fastf1.api.Cache.clear_cache
    :noindex:

"""
from fastf1.core import get_session  # noqa: F401
from fastf1.api import Cache  # noqa: F401
from fastf1 import legacy  # noqa: F401
from fastf1.version import __version__   # noqa: F401
