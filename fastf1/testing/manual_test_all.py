"""This is not an automatic test!

All sessions for 2019 (currently) will be downloaded and processed.
Any occurring exceptions will be caught and written to a log file.
"""

import fastf1 as ff1
import traceback


# GPs 2019
# NOTES
# - 17 FP3 was canceled; Japan, bad weather

for evn in range(1, 22):  # 21 races
    for ses in ('FP1', 'FP2', 'FP3', 'Q', 'R'):
        if evn == 17 and ses == 'FP3':
            continue  # session did not take place

        try:
            print(evn, ses)
            session = ff1.get_session(2019, evn, ses)
            session.load()

        except Exception as e:
            with open(f'logs/2019_{evn}_{ses}.txt', 'w') as f:
                f.write(str(e))
                f.write(traceback.format_exc())


# Testing 2020
evn = 'testing'
for ses in range(1, 7):
    try:
        print(evn, ses)
        session = ff1.get_session(2020, evn, ses)
        session.load()

    except Exception as e:
        with open(f'logs/2020_{evn}_{ses}.txt', 'w') as f:
            f.write(str(e))
            f.write(traceback.format_exc())


# GPs 2020
# NOTES:
# -  2 FP3 was canceled; Austria, bad weather
# - 11 FP1/FP2 didn't take place; Germany, bad weather
# - 13 Only one FP sessions was held on saturday (scheduled); Italy, Imola; due to long distance from Portugal

for evn in range(1, 18):  # 17 races
    for ses in ('FP1', 'FP2', 'FP3', 'Q', 'R'):
        if ((evn == '2' and ses == 'FP3')
                or (evn == '11' and ses in ('FP1', 'FP2'))):
            continue

        try:
            print(evn, ses)
            session = ff1.get_session(2020, evn, ses)
            session.load()

        except Exception as e:
            with open(f'logs/2020_{evn}_{ses}.txt', 'w') as f:
                f.write(str(e))
                f.write(traceback.format_exc())
