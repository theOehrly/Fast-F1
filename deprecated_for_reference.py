# This file contains deprecated, non-functional stuff that didn't survive the experimental stage
# still this code might be usefull for further reference but I want to have it out of the way


def _s3_to_start_finish_subprocess(drvs, laps_data, pos, sample_freq, ret_vals):
    end_vals_x = list()
    end_vals_y = list()
    start_vals_x = list()
    start_vals_y = list()

    for drv in drvs:
        print('Driver', drv)
        laps_this_driver = laps_data[laps_data.Driver == drv]
        max_laps = int(laps_this_driver['NumberOfLaps'].max())

        for i in range(1, max_laps):
            print(i)
            time_lap = laps_this_driver.query('NumberOfLaps == @i')['Time'].squeeze()
            sector3time = laps_this_driver.query('NumberOfLaps == @i')['Sector3Time'].squeeze().round(sample_freq)

            search_range_start = time_lap - sector3time - pd.Timedelta('00:00:01.5')
            search_range_end = time_lap + pd.Timedelta('00:00:01.5')  # TODO improvement cut out unnecessary middle part

            # range from shortly before end of sector 2 to shortly after start/finish line
            filtered_pos = pos[drv].query('@search_range_start <= Time <= @search_range_end')

            # round everything to ms precision
            filtered_pos = filtered_pos.apply(round_date, axis=1, freq=sample_freq)

            # interpolate data to 10ms frequency
            # first getz indices and upsample
            ser = filtered_pos['Date']
            idx = pd.date_range(start=ser.iloc[0], end=ser.iloc[-1], freq=sample_freq)

            # create new empty data frame from upsampled indices
            update_df = pd.DataFrame({'Time': None, 'Status': None, 'X': np.NaN, 'Y': np.NaN, 'Z': np.NaN}, index=idx)
            filtered_pos.set_index('Date', inplace=True)

            # update the extended data frame with know data
            update_df.update(filtered_pos)
            # drop unnecessary columns
            update_df.drop(columns=['Time', 'Status'], inplace=True)
            # interpolate missing position data
            update_df = update_df.interpolate().apply(round_coordinates, axis=1)

            # print(update_df)

            time0 = update_df.index[0]

            for dt in range(0, 4000, 10):
                try:
                    timedelta = pd.Timedelta(dt, unit='ms')

                    end_time = time0 + sector3time + timedelta

                    end_v = update_df.loc[end_time]
                    end_vals_x.append(end_v['X'])
                    end_vals_y.append(end_v['Y'])

                    start_vals_x.append(update_df['X'][0])
                    start_vals_y.append(update_df['Y'][0])

                except KeyError:
                    break  # TODO figure out how to get the actual length of the iteration

    ret_dict = {'xs': start_vals_x, 'ys': start_vals_y, 'xe': end_vals_x, 'ye': end_vals_y}
    ret_vals.put(ret_dict)


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def s3_to_start_finish_v1():
    # ###
    drivers = list(tel.keys())

    sample_freq = '10ms'

    q = mp.Queue()

    number_of_processes = 4
    _processes = list()
    for drvs_chunk in chunks(drivers, int(len(drivers)/number_of_processes)+1):
        p = mp.Process(target=_s3_to_start_finish_subprocess, args=(drvs_chunk, laps_data, pos, sample_freq, q))
        _processes.append(p)
        p.start()

    result = {'xs': list(), 'ys': list(), 'xe': list(), 'ye': list()}
    for i in range(number_of_processes):
        from_q = q.get()
        for key in result.keys():
            result[key].extend(from_q[key])

    print('Waiting to finish')
    time.sleep(5)
    print('joining')
    for p in _processes:
        print('+*')
        p.join()
        print('~')

    print('Done')

    end_vals_x = result['xe']
    end_vals_y = result['ye']
    start_vals_x = result['xs']
    start_vals_y = result['ys']

    pickle.dump(end_vals_x, open("var_dumps/end_vals_x_{}".format(sample_freq), "wb"))
    pickle.dump(end_vals_y, open("var_dumps/end_vals_y_{}".format(sample_freq), "wb"))
    pickle.dump(start_vals_x, open("var_dumps/start_vals_x_{}".format(sample_freq), "wb"))
    pickle.dump(start_vals_y, open("var_dumps/start_vals_y_{}".format(sample_freq), "wb"))


def visualize_track_and_distribution():
    track_points = track_points_from_csv(csv_name)
    track_map = TrackMap(points=track_points, visualization_frequency=0)
    track_map.generate_track()

    end_vals_x = pickle.load(open("var_dumps/end_vals_x_10ms", "rb"))
    end_vals_y = pickle.load(open("var_dumps/end_vals_y_10ms", "rb"))
    start_vals_x = pickle.load(open("var_dumps/start_vals_x_10ms", "rb"))
    start_vals_y = pickle.load(open("var_dumps/start_vals_y_10ms", "rb"))

    assert len(start_vals_x) == len(end_vals_x)

    end_vals_x = np.array(end_vals_x)
    end_vals_y = np.array(end_vals_y)
    start_vals_x = np.array(start_vals_x)
    start_vals_y = np.array(start_vals_y)

    print("Number of Data Points:", len(end_vals_x))
    # reject outliers based on end values; most probably cuased by incorrect sector times
    end_vals_x, start_vals_x, start_vals_y, end_vals_y = reject_outliers(end_vals_x, start_vals_x, start_vals_y, end_vals_y)

    print("Dividing data into classes")
    min_start_x = min(start_vals_x)
    max_start_x = max(start_vals_x)
    min_end_x = min(end_vals_x)
    max_end_x = max(end_vals_x)
    min_end_y = min(end_vals_y)
    max_end_y = max(end_vals_y)
    n_classes = 150

    step_start_x = (max_start_x - min_start_x) / n_classes
    step_end_x = (max_end_x - min_end_x) / n_classes
    step_end_y = (max_end_y - min_end_y) / n_classes

    classified_start_x = list()
    classified_end_x = list()
    classified_end_y = list()
    classified_n = list()

    end_x_range_0 = min_end_x
    end_y_range_0 = min_end_y
    start_x_range_0 = min_start_x

    for _ in range(n_classes):
        start_x_range_1 = start_x_range_0 + step_start_x
        end_x_range_1 = end_x_range_0 + step_end_x
        end_y_range_1 = end_y_range_0 + step_end_y

        classified_start_x.append((start_x_range_1 + start_x_range_0) / 2)
        classified_end_x.append((end_x_range_1 + end_x_range_0) / 2)
        classified_end_y.append((end_y_range_1 + end_y_range_0) / 2)

        counter = 0
        for i in range(len(end_vals_x)):
            if (start_x_range_0 <= start_vals_x[i] < start_x_range_1) and (end_x_range_0 <= end_vals_x[i] < end_x_range_1):
                counter += 1
        classified_n.append(counter)

        start_x_range_0 += step_start_x
        end_x_range_0 += step_end_x
        end_y_range_0 += step_end_y

    bottom = np.zeros_like(classified_n)

    # generating graphs
    print('Generating plots')
    fig = plt.figure()

    ax1 = fig.add_subplot(2, 2, 1, projection='3d')
    ax1.bar3d(classified_start_x, classified_end_x, bottom, 10, 10, classified_n, shade=True)
    ax1.set_xlabel("Start X")
    ax1.set_ylabel("End X")
    ax1.set_zlabel("N")

    ax2 = fig.add_subplot(2, 2, 2)
    ax2.bar(classified_end_x, classified_n)
    ax2.set_xlabel("End X")
    ax2.set_ylabel("N")

    x_guess = classified_end_x[classified_n.index(max(classified_n))]
    y_guess = classified_end_y[classified_n.index(max(classified_n))]
    ax3 = fig.add_subplot(2, 2, 3)
    ax3.scatter(start_vals_y, start_vals_x, color='r')
    ax3.scatter(end_vals_y, end_vals_x, color='y')
    ax3.plot(track_map.track.Y, track_map.track.X, color='g')
    ax3.axhline(x_guess, min(classified_end_y), max(classified_end_y))
    ax3.axvline(y_guess, min(classified_end_x), max(classified_end_x))
    ax3.set_xlabel("Y")
    ax3.set_ylabel("X")
    ax3.axis('equal')
    ax3.invert_yaxis()

    ax4 = fig.add_subplot(2, 2, 4)
    ax4.bar(classified_end_y, classified_n)
    ax4.set_xlabel("End Y")
    ax4.set_ylabel("N")

    plt.show()
