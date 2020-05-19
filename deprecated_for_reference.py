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