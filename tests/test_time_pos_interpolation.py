import matplotlib.pyplot as plt
import pandas as pd

# this is a somewhat unconventional test
# the results need to be reviewed manually
# the position on track is calculated from known times
# the calculated position is then converted back into a time stamp
# for both of theses conversions, interpolation is necessary
# if the resulting date is the same as the original one, both functions are working correctly (or have the same error...)
# the deviation between original and result is then calcualted for each pair of values and plotted


def plot_reversibility_test(laps_data, track):
    drivers = list(track._pos_data.keys())
    # calculate the start date of the session
    some_driver = drivers[0]  # TODO to be sure this should be done with multiple drivers
    session_start_date = track._pos_data[some_driver].head(1).Date.squeeze().round('min')

    delta_t = list()
    for _, lap in laps_data.iterrows():
        if type(lap.Driver) != str:
            continue

        test_date = session_start_date + lap.Time

        p = track.interpolate_pos_from_time(lap.Driver, test_date)
        if p:
            td = pd.Timedelta(2, 's')
            ret_date = track.get_time_from_pos(lap.Driver, p, test_date - td, test_date + td)
            delta_t.append((ret_date - test_date).total_seconds())

    fig = plt.figure()
    plt.hist(delta_t, bins=20)
    fig.suptitle("Reversibility Interpolation Test: Date -> Position -> Date")
