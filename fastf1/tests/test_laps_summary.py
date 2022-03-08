# test api laps data stuff; only make sure that nothing crashes

import pytest
import fastf1 as ff1


@pytest.mark.f1telapi
@pytest.mark.slow
def test_2019():
    for evn in range(1, 22):  # 21 races
        for ses in ('FP1', 'FP2', 'FP3', 'Q', 'R'):
            if evn == 17 and ses == 'FP3':
                continue  # session did not take place

            session = ff1.get_session(2019, evn, ses)
            session.load(telemetry=False)


@pytest.mark.f1telapi
@pytest.mark.slow
def test_2020():
    for evn in range(1, 20):  # 19 races
        for ses in ('FP1', 'FP2', 'FP3', 'Q', 'R'):
            session = ff1.get_session(2020, evn, ses)
            session.load(telemetry=False)
