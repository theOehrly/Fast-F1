"""
============
F1 Telemetry
============

A python framework for the passionate F1 nerds.
-----------------------------------------------

Introduction
============

This package interfaces with two main online sources of data:
    - The official f1 data stream ->
        `link`<https://www.formula1.com/en/f1-live.html>_
    - Ergast web api -> `link`<http://ergast.com/mrd/>_

Car position, speed traces, tyres, timings and weekend history are some
of the many features available and no formula1 account is needed.

The library is designed to be interfaced with matplotlib (although you
can use whatever you want) but there is a neat :mod:`plots` module which
you can import and gives some color to your graphs. 

Modules handle big chunks of data (~30mb per session) so most of the
information is stored locally as cached requests, be aware!

Getting started
===============

Setting up a running snippet is straightforward::

    import f1telemetry as f1

    monza_quali = f1.get_session(2019, 14, 'Q')
    monza_quali = monza_quali.init()

    vettel = monza_quali.get_driver('VET')
    print(f"Pronto {vettel.name}?")
    # Pronto Se🅱️astian?

For some more advanced stuff just a few more steps::

    from matplotlib import pyplot as plt
    from f1telemetry import plots

    leclerc = monza_quali.get_driver('LEC')
    t = leclerc.car_data['Time']
    vCar = leclerc.car_data['Speed']
    
    # The rest is just plotting
    fig, ax = plt.subplots()
    ax.plot(t, vCar, label='Fast')
    ax.set_xlabel('Time')
    ax.set_ylabel('Speed [Km/h]')
    ax.set_title('Leclerc is')
    ax.legend()
    plt.show()

"""
from f1telemetry.core import get_session

version = 'v0.1.0'
