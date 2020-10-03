import fastf1 as ff1
from fastf1 import plotting, utils
from matplotlib import pyplot as plt

import pytest

# generate baseline with
# >pytest tests --mpl-generate-path=tests/mpl-baseline


@pytest.mark.mpl_image_compare
def test_readme_example():
    race = ff1.get_session(2019, 'Bahrain', 'R')
    laps = race.load_laps()

    lec = laps.pick_driver('LEC')
    ham = laps.pick_driver('HAM')

    fig, ax = plt.subplots()
    plotting.laptime_axis(ax)
    ax.plot(lec['LapNumber'], lec['LapTime'], color='red')
    ax.plot(ham['LapNumber'], ham['LapTime'], color='cyan')
    ax.set_title("LEC vs HAM")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")

    return fig


def test_doc_example_pronto_seb():
    monza_quali = ff1.get_session(2019, 'Monza', 'Q')

    vettel = monza_quali.get_driver('VET')
    assert f"Pronto {vettel.name}?" == "Pronto Sebastian?"


@pytest.mark.mpl_image_compare
def test_doc_example_fast_lec():
    monza_quali = ff1.get_session(2019, 'Monza', 'Q')

    laps = monza_quali.load_laps()
    fast_leclerc = laps.pick_driver('LEC').pick_fastest()
    t = fast_leclerc.telemetry['Time']
    vCar = fast_leclerc.telemetry['Speed']

    fig, ax = plt.subplots()
    ax.plot(t, vCar, label='Fast')
    ax.set_xlabel('Time')
    ax.set_ylabel('Speed [Km/h]')
    ax.set_title('Leclerc is')
    ax.legend()

    return fig


@pytest.mark.mpl_image_compare
def test_doc_example_delta_time():
    quali = ff1.get_session(2019, 'Spain', 'Q')
    laps = quali.load_laps()
    lec = laps.pick_driver('LEC').pick_fastest()
    ham = laps.pick_driver('HAM').pick_fastest()

    fig, ax = plt.subplots()
    ax.plot(lec.telemetry['Space'], lec.telemetry['Speed'], color=plotting.TEAM_COLORS[lec['Team']])
    ax.plot(ham.telemetry['Space'], ham.telemetry['Speed'], color=plotting.TEAM_COLORS[ham['Team']])
    twin = ax.twinx()
    twin.plot(ham.telemetry['Space'], utils.delta_time(ham, lec), '--', color=plotting.TEAM_COLORS[lec['Team']])

    return fig


@pytest.mark.mpl_image_compare
def test_speed_trace():
    session = ff1.get_session(2020, 5, 'Q')
    session.load_laps()

    fastest = session.laps.pick_fastest().telemetry

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(fastest['Time'], fastest['Speed'])

    plotting.laptime_axis(ax, 'xaxis')

    return fig
