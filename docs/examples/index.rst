===============
Getting Started
===============

This section offers various examples to get started with FastF1.


.. toctree::
  :caption: Introduction:

  basics


Example Plot
============

FastF1 is largely built on top of Pandas DataFrames and Series. But It adds
its own convenient methods for working specifically with F1 data. This makes
it much easier to get started and work with the data in general. Still, you
have all the capabilities of Pandas at hand whenever you need them.

Let's get started with a very simple script:

.. doctest::

    >>> import fastf1
    >>> session = fastf1.get_session(2019, 'Monza', 'Q')
    >>> session.load(telemetry=False, laps=False, weather=False)
    >>> vettel = session.get_driver('VET')
    >>> print(f"Pronto {vettel['FirstName']}?")
    Pronto Sebastian?

For some more advanced stuff, it's just a few more steps.

.. plot::
    :include-source:

    from matplotlib import pyplot as plt
    import fastf1
    import fastf1.plotting

    fastf1.plotting.setup_mpl()

    session = fastf1.get_session(2019, 'Monza', 'Q')

    session.load()
    fast_leclerc = session.laps.pick_driver('LEC').pick_fastest()
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
