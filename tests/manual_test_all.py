"""This is not an automatic test!

All sessions for 2019 (currently) will be downloaded and processed.
Any occurring exceptions will be caught and written to a log file.
"""

import fastf1 as ff1
import traceback


for evn in range(1, 21):
    for ses in ('FP1', 'FP2', 'FP3', 'Q', 'R'):
        if evn == 17 and ses == 'FP3':
            continue  # session did not take place

        try:
            print(evn, ses)
            session = ff1.get_session(2019, evn, ses)
            session.load_laps()

        except Exception as e:
            with open(f'logs/{evn}_{ses}.txt', 'w') as f:
                f.write(str(e))
                f.write(traceback.format_exc())
