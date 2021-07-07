===============
Getting Started
===============

This section offers various examples to get started with FastF1.


.. toctree::
  :caption: Introduction:

  basics


Example Plot
============

FastF1 is largely built ontop of Pandas DataFrames and Series. But It adds
its own convenient methods for working specifically with F1 data. This makes
it much easier to get started and work with the data in general. Still, you
have all the capabilities of Pandas at hand whenever you need them.

Let's get started with a very simple script:

.. doctest::

    >>> import fastf1 as ff1
    >>> ff1.Cache.enable_cache('path/to/folder/for/cache')  # doctest: +SKIP
    >>> monza_quali = ff1.get_session(2019, 'Monza', 'Q')
    >>> vettel = monza_quali.get_driver('VET')
    >>> print(f"Pronto {vettel.name}?")
    Pronto Sebastian?

For some more advanced stuff, it's just a few more steps.

.. plot::
    :include-source:

    from matplotlib import pyplot as plt
    import fastf1 as ff1
    from fastf1 import plotting

    plotting.setup_mpl()

    monza_quali = ff1.get_session(2019, 'Monza', 'Q')

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


It is not necessary to enable the usage of the cache but it is highly recommended. Simply provide
the path to some empty folder on your system. Using the cache will greatly speed up loading of the data.
