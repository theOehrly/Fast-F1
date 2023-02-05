import pytest

from matplotlib import pyplot as plt

import fastf1
import fastf1.plotting
import fastf1.utils

fastf1.plotting.setup_mpl()

# generate baseline with
# >pytest tests --mpl-generate-path=tests/mpl-baseline


@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_readme_example():
    session = fastf1.get_session(2020, 'Belgian', 'R')
    session.load()

    lec = session.laps.pick_driver('LEC')
    ham = session.laps.pick_driver('HAM')

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
    fastf1.Cache.enable_cache("test_cache/")
    session = fastf1.get_session(2020, 'Belgian', 'R')

    session.load()
    fast_leclerc = session.laps.pick_driver('LEC').pick_fastest()
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
def test_doc_example_delta_time():
    fastf1.Cache.enable_cache("test_cache/")
    session = fastf1.get_session(2020, 'Belgian', 'R')
    session.load()
    lec = session.laps.pick_driver('LEC').pick_fastest()
    ham = session.laps.pick_driver('HAM').pick_fastest()

    fig, ax = plt.subplots()
    ax.plot(lec.telemetry['Distance'], lec.telemetry['Speed'],
            color=fastf1.plotting.team_color(lec['Team']))
    ax.plot(ham.telemetry['Distance'], ham.telemetry['Speed'],
            color=fastf1.plotting.team_color(ham['Team']))
    twin = ax.twinx()
    delta_time, ham_car_data, lec_car_data = fastf1.utils.delta_time(ham, lec)
    ham_car_data = ham_car_data.add_distance()
    twin.plot(ham_car_data['Distance'], delta_time, '--',
              color=fastf1.plotting.team_color(lec['Team']))

    return fig


@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_speed_trace():
    fastf1.Cache.enable_cache("test_cache/")
    session = fastf1.get_session(2020, 'Belgian', 'R')
    session.load()

    fastest = session.laps.pick_fastest().telemetry

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(fastest['Time'], fastest['Speed'])

    return fig
