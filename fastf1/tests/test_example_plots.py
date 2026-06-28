import pytest
from matplotlib import pyplot as plt

import fastf1
import fastf1.plotting


fastf1.plotting.setup_mpl(color_scheme='fastf1')

# generate baseline with
# >pytest --mpl-generate-path=fastf1/tests/mpl-baseline


@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_readme_example():
    session = fastf1.get_session(2020, 'Belgian', 'R')
    session.load()

    lec = session.laps.pick_drivers('LEC')
    ham = session.laps.pick_drivers('HAM')

    fig, ax = plt.subplots()
    ax.plot(lec['LapNumber'], lec['LapTime'], color='red')
    ax.plot(ham['LapNumber'], ham['LapTime'], color='cyan')
    ax.set_title("LEC vs HAM")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")

    return fig


@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_doc_example_fast_lec():
    session = fastf1.get_session(2020, 'Belgian', 'R')

    session.load()
    fast_leclerc = session.laps.pick_drivers('LEC').pick_fastest()
    t = fast_leclerc.telemetry['Time']
    vCar = fast_leclerc.telemetry['Speed']

    fig, ax = plt.subplots()
    ax.plot(t, vCar, label='Fast')
    ax.set_xlabel('Time')
    ax.set_ylabel('Speed [Km/h]')
    ax.set_title('Leclerc is')
    ax.legend()

    return fig

@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_speed_trace():
    session = fastf1.get_session(2020, 'Belgian', 'R')
    session.load()

    fastest = session.laps.pick_fastest().telemetry

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(fastest['Time'], fastest['Speed'])

    return fig
