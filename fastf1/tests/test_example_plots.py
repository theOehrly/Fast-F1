import pytest
import fastf1 as ff1
from fastf1 import plotting, utils
from matplotlib import pyplot as plt
plotting.setup_mpl()

# generate baseline with
# >pytest tests --mpl-generate-path=tests/mpl-baseline


@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_readme_example():
    ff1.Cache.enable_cache("test_cache/")
    race = ff1.get_session(2020, 'Belgian', 'R')
    laps = race.load_laps()

    lec = laps.pick_driver('LEC')
    ham = laps.pick_driver('HAM')

    fig, ax = plt.subplots()
    ax.plot(lec['LapNumber'], lec['LapTime'], color='red')
    ax.plot(ham['LapNumber'], ham['LapTime'], color='cyan')
    ax.set_title("LEC vs HAM")
    ax.set_xlabel("Lap Number")
    ax.set_ylabel("Lap Time")

    return fig


@pytest.mark.f1telapi
def test_doc_example_pronto_seb():
    ff1.Cache.enable_cache("test_cache/")
    session = ff1.get_session(2020, 'Belgian', 'R')

    vettel = session.get_driver('VET')
    assert f"Pronto {vettel.name}?" == "Pronto Sebastian?"


@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_doc_example_fast_lec():
    ff1.Cache.enable_cache("test_cache/")
    session = ff1.get_session(2020, 'Belgian', 'R')

    laps = session.load_laps()
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


@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_doc_example_delta_time():
    ff1.Cache.enable_cache("test_cache/")
    quali = ff1.get_session(2020, 'Belgian', 'R')
    laps = quali.load_laps()
    lec = laps.pick_driver('LEC').pick_fastest()
    ham = laps.pick_driver('HAM').pick_fastest()

    fig, ax = plt.subplots()
    ax.plot(lec.telemetry['Distance'], lec.telemetry['Speed'], color=plotting.TEAM_COLORS[lec['Team']])
    ax.plot(ham.telemetry['Distance'], ham.telemetry['Speed'], color=plotting.TEAM_COLORS[ham['Team']])
    twin = ax.twinx()
    delta_time, ham_car_data, lec_car_data = utils.delta_time(ham, lec)
    ham_car_data = ham_car_data.add_distance()
    twin.plot(ham_car_data['Distance'], delta_time, '--', color=plotting.TEAM_COLORS[lec['Team']])

    return fig


@pytest.mark.f1telapi
@pytest.mark.mpl_image_compare(style='default')
def test_speed_trace():
    ff1.Cache.enable_cache("test_cache/")
    session = ff1.get_session(2020, 'Belgian', 'R')
    session.load_laps()

    fastest = session.laps.pick_fastest().telemetry

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    ax.plot(fastest['Time'], fastest['Speed'])

    return fig
