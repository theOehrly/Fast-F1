# test api laps data stuff; only make sure that nothing crashes

import fastf1 as ff1


def test_2019():
    for evn in range(1, 21):
        for ses in ('FP1', 'FP2', 'FP3', 'Q', 'R'):
            if evn == 17 and ses == 'FP3':
                continue  # session did not take place

            session = ff1.get_session(2019, evn, ses)
            session._load_summary()


def test_2020():
    for evn in range(1, 7):
        for ses in ('FP1', 'FP2', 'FP3', 'Q', 'R'):
            session = ff1.get_session(2020, evn, ses)
            session._load_summary()
