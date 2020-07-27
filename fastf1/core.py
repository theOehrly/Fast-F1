"""
:mod:`fastf1.core` - Core module
================================
"""
from fastf1 import utils
from fastf1 import ergast
from fastf1 import api
from fuzzywuzzy import fuzz
import warnings
import pandas as pd
import numpy as np
import logging
import functools
import scipy
from scipy import spatial
logging.basicConfig(level=logging.INFO)

TESTING_LOOKUP = {'2020': ['2020-02-19', '2020-02-20', '2020-02-21',
                           '2020-02-26', '2020-02-27', '2020-02-28']}

D_LOOKUP = [[44, 'HAM', 'Mercedes'], [77, 'BOT', 'Mercedes'],
            [5, 'VET', 'Ferrari'], [16, 'LEC', 'Ferrari'],
            [33, 'VER', 'Red Bull'], [23, 'ALB', 'Red Bull'],
            [55, 'SAI', 'McLaren'], [4, 'NOR', 'McLaren'],
            [11, 'PER', 'Racing Point'], [18, 'STR', 'Racing Point'],
            [3, 'RIC', 'Renault'], [31, 'OCO', 'Renault'],
            [26, 'KVY', 'Alpha Tauri'], [10, 'GAS', 'Alpha Tauri'],
            [8, 'GRO', 'Haas F1 Team'], [20, 'MAG', 'Haas F1 Team'],
            [7, 'RAI', 'Alfa Romeo'], [99, 'GIO', 'Alfa Romeo'],
            [6, 'LAT', 'Williams'], [63, 'RUS', 'Williams'],
            [88, 'KUB', 'Alfa Romeo']]

def _gen_results():
    results = []
    for driver in D_LOOKUP:
        results.append({
            'number': str(driver[0]),
            'Driver': {'code': driver[1]},
            'Constructor': {'name': driver[2]}})
    return results

def get_session(year, gp, event=None):
    """Main core function. It will take care of crafting an object
    corresponding to the requested session.
    If not specified, full weekend is returned.

    Args:
        year: session year (Tested only with 2019)
        gp: name or weekend number (1: Australia, ..., 21: Abu Dhabi)
            if gp is a string, a fuzzy match will be performed on the
            season rounds and the most likely will be selected.
            'bahrain', 'australia', 'abudabi' are some of the examples
            that you can pass and the correct week will be selected.

            Pass 'testing' to fetch barcelona tests.

        event (=None): may be 'FP1', 'FP2', 'FP3', 'Q' or 'R', if not 
                       specified you get the full :class:`Weekend`.
                       If gp is 'testing' event is the test day (1 to 6)

    Returns:
        :class:`Weekend` or :class:`Session`

    """
    if type(gp) is str and gp == 'testing':
        try:
            event = int(event)
            week = 1 if event < 4 else 2
        except:
            msg = "Cannot fetch testing without correct event day."
            raise Exception(msg)
        gp = f'Pre-Season Test {week}'
        event = f'Practice {event}'
        weekend = Weekend(year, gp)
        return Session(weekend, event)

    if type(gp) is str:
        gp = get_round(year, gp)
    weekend = Weekend(year, gp)
    if event == 'R':
        return Session(weekend, 'Race')
    if event == 'Q':
        return Session(weekend, 'Qualifying')
    if event == 'FP3':
        return Session(weekend, 'Practice 3')
    if event == 'FP2':
        return Session(weekend, 'Practice 2')
    if event == 'FP1':
        return Session(weekend, 'Practice 1')
    return weekend


def get_round(year, match):
    ratios = np.array([])
    def build_string(d):
        r = len('https://en.wikipedia.org/wiki/')
        c, l = d['Circuit'], d['Circuit']['Location']
        return (f"{d['url'][r:]} {d['raceName']} {c['circuitId']} "
                + f"{c['url'][r:]} {c['circuitName']} {l['locality']} "
                + f"{l['country']}")
    races = ergast.fetch_season(year)
    to_match = [build_string(block) for block in races]
    ratios = np.array([fuzz.partial_ratio(match, ref) for ref in to_match])
    return int(races[np.argmax(ratios)]['round'])


class Weekend:
    """Weekend class
    """

    def __init__(self, year, gp):
        self.year = year
        self.gp = gp
        if self.is_testing():
            warnings.warn("Ergast api not supported for testing.")
            self.data = {
                'raceName': gp,
                'date': TESTING_LOOKUP[str(year)][int(gp[-1]) * 3 - 1]}
        else:
            self.data = ergast.fetch_weekend(self.year, self.gp)

    def get_practice(self, number):
        """
        Args:
            number: 1, 2 or 3 Free practice session number
        Returns:
            :class:`Session` instance
        """
        return Session(self, 'Qualifying')

    def get_quali(self):
        """
        Returns:
            :class:`Session` instance
        """
        return Session(self, 'Qualifying')

    def get_race(self):
        """
        Returns:
            :class:`Session` instance
        """
        return Session(self, 'Race')

    def is_testing(self):
        if type(self.gp) is str:
            return 'Test' in self.gp
        else:
            return False

    @property
    def name(self):
        """Weekend name, e.g. "British Grand Prix"
        """
        return self.data['raceName']

    @property
    def date(self):
        """Weekend race date (YYYY-MM-DD)
        """
        return self.data['date']


class Session:
    """Session class
    """

    def __init__(self, weekend, session_name):
        self.weekend = weekend
        self.name = session_name
        if self.weekend.is_testing():
            self.date = TESTING_LOOKUP[str(weekend.year)][int(session_name[-1]) - 1]
        elif session_name == 'Race':
            self.date = weekend.date

        # Assuming  date offsets here which is not always correct
        # Should check if also formula1 makes this assumption
        elif session_name in ('Qualifying', 'Practice 3'):
            offset_date = pd.to_datetime(weekend.date) + pd.DateOffset(-1)
            self.date = offset_date.strftime('%Y-%m-%d')
        elif session_name in ('Practice 1', 'Practice 2'):
            offset_date = pd.to_datetime(weekend.date) + pd.DateOffset(-2)
            self.date = offset_date.strftime('%Y-%m-%d')

        w, s = self.weekend, self
        self.api_path = api.make_path(w.name, w.date, s.name, s.date)
        if not weekend.is_testing():
            try:
                self.results = ergast.load(w.year, w.gp, s)
            except:
                logging.warning("Ergast lookup failed")
        else:
            self.results = _gen_results()

    @utils._cached_laps
    def load_laps(self):
        """With load laps all the timing information is merged in a
        single pandas dataframe. The first time you run the method on
        a session it may take a while to load, some megabytes are of
        data are downloaded and processed, but then laps will be 
        stored locally. Each dataframe entry has the following columns:

            - `Time` (timedelta): Time when the lap was recorded
            - `Driver` (string): Three letters driver identifier
            - `LapTime` (timedelta): Recorded lap time
            - `LapNumber` (int): Recorded lap number
            - `PitOutTime` (timedelta): Time when car exited the pit
            - `PitInTime` (timedelta): Time when car entered the pit
            - `Sector1Time` (timedelta): Sector 1 recorded time
            - `Sector2Time` (timedelta): Sector 2 recorded time
            - `Sector3Time` (timedelta): Sector 3 recorded time
            - `SpeedI1` (float): Speedtrap sector 1
            - `SpeedI2` (float): Speedtrap sector 2
            - `SpeedFL` (float): Speedtrap sector 3 (Not sure)
            - `SpeedST` (float): Speedtrap on longest straight (Not sure)
            - `Stint` (int): Indicates the stint number
            - `Compound` (str): Tyre compound name: SOFT, MEDIUM ..
            - `TyreLife` (int): Laps spent on that compound
            - `FreshTyre` (bool): Tyre had TyreLife=0 at stint start
            - `DriverNumber` (str): Car number
            - `Team` (str): Team name
            - `LapStartDate` (datetime): When the lap started
            - `telemetry`: (pandas dataframe of lap telemetry)
                - `Time` (timedelta): Time axis (0 is start of lap)
                - `Space` (float): Space in meters (from speed and time)
                - `Speed` (float): Car speed
                - `RPM` (int): Car RPM
                - `nGear` (int): Car gear number
                - `Throttle` (float): 0-100 Throttle pedal pressure
                - `Brake` (float): 0-100 Brake pedal pressure
                - `DRS` (int): DRS indicator
                - `X` (float): GPS X position (normalized)
                - `Y` (float): GPS X position (normalized)
                - `Z` (float): GPS Z position (normalized)
                - `Status` (string): flags OffTrack/OnTrack for GPS 
                - `SessionTime` (timedelta): time elapsed from session start
                - `DistanceToDriverAhead` (string): distance to next car
                - `DriverAhead` (string): the car ahead

        .. note:: Absolute time is not super accurate. The moment a lap
            is logged is not always the same and there will be some
            jitter. At the moment lap time reference is synchronised
            on the sector time triggered with lowest latency.
            Expect an error of around ±10m when overlapping telemetry
            data of different laps.

        Returns:
            laps

        """
        logging.info(f"Loading {self.weekend.name} {self.name}")
        self.laps = Laps(self._load_summary())
        telemetry, lap_start_date = self._load_telemetry()
        self.laps['LapStartDate'] = lap_start_date
        self.laps['telemetry'] = telemetry
        self.laps = Laps(self.laps)
        logging.info(f"Laps loaded and saved!")
        return self.laps

    def get_driver(self, identifier):
        if type(identifier) is str:
            for info in self.results:
                if info['Driver']['code'] == identifier:
                    return Driver(self, info)
        return None

    def _load_summary(self):
        """From `timing_data` and `timing_app_data` a summary table is
        built. Lap by lap, information on tyre, sectors and times are 
        organised in an accessible pandas data frame.

        Args:
            path: path returned from :func:`make_path`

        Returns:
            pandas dataframe

        """
        logging.info("Getting summary...")
        data, _ = api.timing_data(self.api_path)
        app_data = api.timing_app_data(self.api_path)
        # Now we do some manipulation to make it beautiful
        logging.info("Formatting summary...")
        # Matching data and app_data. Not super straightworward
        # Sometimes a car may enter the pit without changing tyres, so
        # new compound is associated with the help of logging time.
        useful = app_data[['Driver', 'Time', 'Compound', 'TotalLaps', 'New']]
        useful = useful[~useful['Compound'].isnull()]
        for i, driver in enumerate(data['Driver'].unique()):
            d1 = data[data['Driver'] == driver]
            d2 = useful[useful['Driver'] == driver]
            try:
                result = pd.merge_asof(d1, d2, on='Time', by='Driver')
            except:
                # From 2018 to 2020 there is Vettel pre season 2020-02-21 who
                # is not synchronised correctly. A manually patched file is loaded
                if (driver == '5'
                    and self.api_path == ('/static/2020/2020-02-21_Pre-Season_Test_1'
                                        + '/2020-02-21_Practice_3/')):
                        import pathlib, os
                        path = pathlib.Path(__file__).parent.absolute()
                        file_path = os.path.join(path, 'vettel_test_2020_21_03.csv')
                        result = pd.read_csv(file_path)
                        for col in result.columns:
                            if 'Time' in col:
                                result[col] = pd.to_timedelta(result[col])
                        result['Driver'] = '5'
                else:
                    print("ERROR: Could not merge timing data with timing app data!")
                    exit()

            for npit in result['NumberOfPitStops'].unique():
                sel = result['NumberOfPitStops'] == npit
                result.loc[sel, 'TotalLaps'] += np.arange(0, sel.sum()) + 1
            df = result if i == 0 else pd.concat([df, result], sort=False)    
        summary = df.reset_index(drop=True)
        summary.rename(columns={'TotalLaps': 'TyreLife',
                                'LastLapTime': 'LapTime', 
                                'NumberOfPitStops': 'Stint',
                                'Driver': 'DriverNumber',
                                'NumberOfLaps': 'LapNumber',
                                'New': 'FreshTyre'}, inplace=True)
        summary['Stint'] += 1 # counting stints from 1
        t_map = {r['number']: r['Constructor']['name'] for r in self.results}
        summary['Team'] = summary['DriverNumber'].map(t_map)
        d_map = {r['number']: r['Driver']['code'] for r in self.results}
        summary['Driver'] = summary['DriverNumber'].map(d_map)
        return summary


    def _load_telemetry(self):
        """Load telemetry data to be associated for each lap.

        """
        tel, pos, date_offset = {}, {}, {}
        event_telemetry, lap_start_date = [], []
        logging.info("Getting telemetry data...")
        car_data = api.car_data(self.api_path)
        logging.info("Getting position data...")
        position = api.position(self.api_path)
        logging.info("Resampling telemetry...")
        for driver in self.laps['DriverNumber'].unique():
            if driver in car_data:
                tel[driver], date_offset[driver] = self._resample(car_data[driver])
            else:
                warnings.warn(f"Could not find telemetry data for driver {driver}")
            if driver in position:
                pos[driver], _ = self._resample(position[driver])
            else:
                warnings.warn(f"Could not find gps data for driver {driver}")
        self.car_data, self.position = tel, pos
        can_find_reference = position != {}
        if can_find_reference:
            self._augment_position()
        d_map = {r['number']: r['Driver']['code'] for r in self.results}
        logging.info("Creating laps...")
        for i in self.laps.index:
            _log_progress(i, len(self.laps.index))
            lap = self.laps.loc[i]
            driver = lap['DriverNumber']
            if str(lap['LapTime']) != 'NaT' and driver in tel:
                telemetry = self._slice_stream(tel[driver], lap)
                if len(telemetry.index):
                    if driver in pos:
                        telemetry = self._inject_position(pos[driver], lap, telemetry)
                    telemetry = self._inject_space(telemetry)
                    if can_find_reference:
                        telemetry['DriverAhead'] = telemetry['DriverAhead'].map(d_map)
                    event_telemetry.append(telemetry)
                    # Calc lap start date
                    lap_start_time = telemetry['SessionTime'].iloc[0]
                    lap_start_date.append(date_offset[driver] + lap_start_time)
                else:
                    warnings.warn("Empty telemetry slice from lap "
                                  + f"{lap['LapNumber']} of driver {driver}")
                    event_telemetry.append(None)
                    lap_start_date.append(None)
            else:
                event_telemetry.append(None)
                lap_start_date.append(None)
        return event_telemetry, lap_start_date


    def _resample(self, df):
        """`car_data` is aligned with main time reference (time used in
        summary). For constant frequency a resampling to 10Hz is applied.
        
        `car_data` (telemetry) has a 'Date' entry which is the actual time
        the sample was taken (I guess), but anyway, is unique. So from
        the time step before resampling is taken from this column and
        Time is aligned on Date.

        One time sample may carry more than one Date sample. Single time
        entries at the beginning are often messed up, so the last time
        of a consecutive stike is chosen as alignment point.

        Time = [t1, t2, t3, t3, t3, t4, t4, ... ]
        Date = [d1, d2, d3, d4, d5, d6, d7, ... ]
                                ^
                                Start of alignment

        So in this example t3 is kept as reference for start time and
        the incrementals from Date are added to have a correctly spaced
        time column. d5 will be used for the `offset_date` which is then
        used to find the lap start time.

        Now data can be resampled on Time.

        """
        if 'Driver' in df.columns and len(df['Driver'].unique()) > 1:
                raise Exception("Cannot resample with multiple drivers")
        # Align:
        counter, last_val = 0, None
        for i, val in enumerate(df['Time'].values):
            if val == last_val:
                counter += 1
            elif counter > 2:
                i -= 1
                break # found align point at sample i
            else:
                counter = 0
            last_val = val
        # Disclaimer: In the alignment process some samples are lost :(
        # Just because it is easier then to resample, but shouldn't really
        # matter, recordings start quite early and we don't loose
        # relevant information.
        pre = df.iloc[i:].copy().reset_index(drop=True)
        start_date, start_time = pre['Date'].iloc[0], pre['Time'].iloc[0]
        offset_date = start_date - start_time
        pre['Time'] = (pre['Date'] - start_date) + start_time
        # Map non numeric
        mapped, unmap = self._map_objects(pre)
        # Resample:
        # Date contains the corret time spacing information, so we use that
        # 90% of function time is spent in the next line
        res = (mapped.resample('0.1S', on='Time').mean()
                     .interpolate(method='linear'))
        if 'nGear' in res.columns and 'DRS' in res.columns:
            res[['nGear', 'DRS']] = res[['nGear', 'DRS']].round().astype(int)
        res = unmap(res)
        res['Time'] = pd.to_timedelta(res.index, unit='s')
        return res.reset_index(drop=True), offset_date
        #return res, offset_date

    def _inject_position(self, position, lap, _telemetry):
        lap_position = self._slice_stream(position, lap, pad=1)
        lap_position, unmap = self._map_objects(lap_position)
        ref_time = _telemetry['Time'].values
        pos_time = lap_position['Time'].values
        new_lap_position = {}
        ref_x = pd.to_numeric(ref_time)
        ref_xp = pd.to_numeric(pos_time)
        for column in lap_position.columns:
            if column not in _telemetry:
                y = np.interp(ref_x, ref_xp, lap_position[column].values) 
                _telemetry[column] = y
        return unmap(_telemetry)

    def _map_objects(self, df):
        nnummap = {}
        for column in df.columns:
            if df[column].dtype == object:
                backward = dict(enumerate(df[column].unique()))
                forward = {v: k for k, v in backward.items()}
                df[column] = df[column].map(forward)
                nnummap[column] = backward
        def unmap(res):
            for column in nnummap:
                res[column] = res[column].round().map(nnummap[column])
            return res
        return df, unmap

    def _slice_stream(self, df, lap, pad=0):
        pad = pd.to_timedelta(f'{pad*0.1}s')
        end_time, lap_time = lap['Time'], lap['LapTime']
        sel = ((df['Time'] < (end_time + pad))
                & (df['Time'] >= (end_time - lap_time - pad)))
        lap_stream = df.loc[sel].copy()
        lap_stream['SessionTime'] = lap_stream['Time']
        # Then shift time to 0 so laps can overlap
        lap_stream['Time'] += lap_time - end_time
        return lap_stream


    def _augment_position(self):
        """Improves laps information content

            - Adds 'DistanceToCarAhead' channel to driver position
        """
        lap = self._get_reference_lap()
        driver_ahead = self._make_trajectory(lap) 
        for d in self.position:
            self.position[d] = self.position[d].join(driver_ahead[d])


    def _get_reference_lap(self):
        valid_tele = False
        times = self.laps['LapTime'].copy()
        times = times.sort_values()
        i = 0
        while not valid_tele:
            lap = self.laps.loc[times.index[i]].copy()
            time, driver = lap['Time'], lap['DriverNumber']
            tele = self._slice_stream(self.car_data[driver], lap)
            valid_tele = np.all(tele['Speed'] > 0)
            i += 1
        tele = self._inject_position(self.position[driver], lap, tele)
        tele = self._inject_space(tele)
        lap['telemetry'] = tele
        return lap


    def _inject_space(self, _telemetry):
        dt = _telemetry['Time'].dt.total_seconds().diff()
        dt.iloc[0] = _telemetry['Time'].iloc[0].total_seconds()
        ds = _telemetry['Speed'] / 3.6 * dt
        _telemetry['Space'] = ds.cumsum()
        return _telemetry


    def _make_trajectory(self, lap):
        """Create telemetry space
        """
        telemetry = lap.telemetry
        x = telemetry['X'].values
        y = telemetry['Y'].values
        z = telemetry['Z'].values
        s = telemetry['Space'].values

        # Assuming constant speed in the last tenth
        dt0_ = (lap['LapTime'] - telemetry['Time'].iloc[-1]).total_seconds()
        ds0_ = (telemetry['Speed'].iloc[-1] / 3.6) * dt0_
        total_s = s[-1] + ds0_

        # To prolong start and finish and have a correct linear interpolation 
        full_s = np.concatenate([s - total_s, s, s + total_s])
        full_x = np.concatenate([x, x, x]) 
        full_y = np.concatenate([y, y, y])
        full_z = np.concatenate([z, z, z])

        reference_s = np.arange(0, total_s, 0.667)
        reference_x = np.interp(reference_s, full_s, full_x)
        reference_y = np.interp(reference_s, full_s, full_y)
        reference_z = np.interp(reference_s, full_s, full_z)

        ssize = len(reference_s)

        """Build track map and project driver position to one trajectory 
        """
        def fix_suzuka(projection_index, _s):
            """Yes, suzuka is bad
            """
            # For tracks like suzuka (therefore only suzuka) we have
            # a beautiful crossing point. So, FOR F**K SAKE, sometimes
            # shortest distance may fall below the bridge or viceversa
            # gotta do some monotony sort of check. Not the cleanest
            # solution.
            def moving_average(a, n=3):
                ret = np.cumsum(a, dtype=float)
                ret[n:] = ret[n:] - ret[:-n]
                ma = ret[n - 1:] / n
                return np.concatenate([ma[0:n//2], ma, ma[-n//2:-1]])
            ma_projection = moving_average(_s[projection_index], n=3)
            spikes = np.absolute(_s[projection_index] - ma_projection)
            # 1000 and 3000, very suzuka specific. Damn magic numbers
            sel_bridge = np.logical_and(spikes > 1000, spikes < 3000)
            unexpected = np.where(sel_bridge)[0]
            max_length = _s[-1]
            for p in unexpected:
                # Just assuming linearity for this 2 or 3 samples
                last_value = _s[projection_index[p - 1]]
                last_step = last_value - _s[projection_index[p - 2]]
                if (last_value + last_step) > max_length:
                    # Over the finish line
                    corrected_distance = -max_length + last_step + last_value 
                else:
                    corrected_distance = last_value + last_step 
                corrected_index = np.argmin(np.abs(_s - corrected_distance))
                projection_index[p] = corrected_index
            return projection_index

        track = np.empty((ssize, 3))
        track[:, 0] = reference_x
        track[:, 1] = reference_y
        track[:, 2] = reference_z

        track_tree = scipy.spatial.cKDTree(track)
        drivers_list = np.array(list(self.position))
        stream_length = len(self.position[drivers_list[0]])
        dmap = np.empty((stream_length, len(drivers_list)), dtype=int)

        fast_query = {'n_jobs': 2, 'distance_upper_bound': 500}
        # fast_query < Increases speed
        for index, driver in enumerate(self.position):
            trajectory = self.position[driver][['X', 'Y', 'Z']].values
            projection_index = track_tree.query(trajectory, **fast_query)[1]
            # When tree cannot solve super far points means there is some
            # pit shit shutdown. We can replace these index with 0
            projection_index[projection_index == len(reference_s)] = 0
            dmap[:, index] = fix_suzuka(projection_index.copy(), reference_s)

        """Create transform matrix to change distance point of reference
        """
        t_matrix = np.empty((ssize, ssize))
        for index in range(ssize):
            rref = reference_s - reference_s[index]
            rref[rref <= 0] = total_s + rref[rref <= 0]
            t_matrix[index, :] = rref

        """Create mask to remove distance elements when car is on track
        """
        time = self.position[drivers_list[0]]['Time']
        pit_mask = np.zeros((stream_length, len(drivers_list)), dtype=bool)
        for driver_index, driver_number in enumerate(drivers_list):
            laps = self.laps.pick_driver(driver_number)
            in_pit = True
            times = [[], []]
            for lap_index in laps.index:
                lap = laps.loc[lap_index]
                if not pd.isnull(lap['PitInTime']) and not in_pit:
                    times[1].append(lap['PitInTime'])
                    in_pit = True
                if not pd.isnull(lap['PitOutTime']) and in_pit:
                    times[0].append(lap['PitOutTime'])
                    in_pit = False
            if not in_pit:
                # Car crashed, we put a time and 'Status' will take care
                times[1].append(lap['Time'])
            times = np.transpose(np.array(times))
            for inout in times:
                out_of_pit = np.logical_and(time >= inout[0], time < inout[1])
                pit_mask[:, driver_index] |= out_of_pit
            on_track = (self.position[driver_number]['Status'] == 'OnTrack')
            pit_mask[:, driver_index] &= on_track.values

        """Calculate relative distances using transform matrix
        """
        driver_ahead = {}
        stream_axis = np.arange(stream_length)
        for my_di, my_d in enumerate(drivers_list):
            rel_distance = np.empty(np.shape(dmap))
            for his_di, his_d in enumerate(drivers_list):
                my_pos_i = dmap[:, my_di]
                his_pos_i = dmap[:, his_di]
                rel_distance[:, his_di] = t_matrix[my_pos_i, his_pos_i]
            his_in_pit = ~pit_mask.copy()
            his_in_pit[:, my_di] = False
            my_in_pit = ~pit_mask[:, drivers_list == my_d][:, 0]
            rel_distance[his_in_pit] = np.nan

            closest_index = np.nanargmin(rel_distance, axis=1)
            closest_distance = rel_distance[stream_axis, closest_index]
            closest_driver = drivers_list[closest_index].astype(object)
            closest_distance[my_in_pit] = np.nan
            closest_driver[my_in_pit] = None

            data = {'DistanceToDriverAhead': closest_distance,
                    'DriverAhead': closest_driver}
            driver_ahead[my_d] = pd.DataFrame(data)
        return driver_ahead


class Laps(pd.DataFrame):
    """This class wraps :attr:`Session.laps` which is a classic pandas
    DataFrame with the addition of a few 'pick' methods to simplify lap
    selection and filtering.

    If for example you want to get the fastest lap of Bottas you can
    narrow it down like this::

        import fastf1 as ff1

        laps = ff1.get_session(2019, 'Bahrain', 'Q').load_laps()
        best_bottas = laps.pick_driver('BOT').pick_fastest()

        print(best_bottas['LapTime'])
        # Timedelta('0 days 00:01:28.256000')

    Pick methods will return :class:`Laps` or pandas Series if only 1
    entry is left.
    """

    QUICKLAP_THRESHOLD = 1.07

    @property
    def _constructor(self):
        return Laps

    def __pick_wrap(func):
        @functools.wraps(func)
        def decorator(*args, **kwargs):
            res = func(*args, **kwargs)
            return Laps(res) if isinstance(res, pd.DataFrame) else res
        return decorator

    @__pick_wrap
    def pick_driver(self, identifier):
        """Select driver given his three letters identifier or its car
        number::

            perez_laps = ff1.pick_driver('PER')
            bottas_laps = ff1.pick_driver(77)
            kimi_laps = ff1.pick_driver('RAI')

        """
        identifier = str(identifier)
        if identifier.isdigit():
            return self[self['DriverNumber'] == identifier]
        else:
            return self[self['Driver'] == identifier]

    @__pick_wrap
    def pick_drivers(self, identifiers):
        """Select drivers given a list of their identifiers. Same as
        :meth:`Laps.pick_driver` but for lists::

            some_drivers_laps = ff1.pick_drivers([5, 'BOT', 7])

        """
        names = [n for n in identifiers if not str(n).isdigit()]
        numbers = [str(n) for n in identifiers if str(n).isdigit()]
        drv, num = self['Driver'], self['DriverNumber']
        return self[(drv.isin(names) | num.isin(numbers))]

    @__pick_wrap
    def pick_team(self, name):
        """Select team given its name::

            mercedes = ff1.pick_team('Mercedes')
            alfa_romeo = ff1.pick_team('Alfa Romeo')

        Have a look to :attr:`fastf1.plotting.TEAM_COLORS` for a quick
        reference on team names.
        """
        return self[self['Team'] == name]

    @__pick_wrap
    def pick_teams(self, names):
        """Same as :meth:`Laps.pick_team` but for a list of teams.
        """
        return self[self['Team'].isin(names)]

    @__pick_wrap
    def pick_fastest(self):
        """Get lap with best `LapTime`.
        """
        lap = self.loc[self['LapTime'].idxmin()]
        if isinstance(lap, pd.DataFrame):
            # More laps, same time
            lap = lap.iloc[0] # take first clocked
        return lap

    @__pick_wrap
    def pick_quicklaps(self, threshold=None):
        """Select laps with `LapTime` faster than a certain limit.
        By default 107% of the best `LapTime` of the given laps set.

        Args:
            threshold (optional, float): custom threshold coefficent
                (e.g. 1.05 for 105%)

        """
        if threshold is None:
            threshold = Laps.QUICKLAP_THRESHOLD
        time_threshold = self['LapTime'].min() * threshold
        return self[self['LapTime'] < time_threshold]

    @__pick_wrap
    def pick_tyre(self, compound):
        """Get laps done on a specific compound.

        Args:
            compound (string): may be "SOFT", "MEDIUM" or "HARD"

        """
        return self[self['Compound'] == compound]


class Driver:

    def __init__(self, session, info):
        self.session = session
        self.info = info
        self.identifier = info['Driver']['code']
        self.number = info['number']

    @property
    def dnf(self):
        """True if driver did not finish
        """
        s = self.info['status']
        return not (s[3:6] == 'Lap' or s == 'Finished')

    @property
    def grid(self):
        """Grid position
        """
        return int(self.info['grid'])

    @property
    def position(self):
        """Finishing position
        """
        return int(self.info['position'])

    @property
    def name(self):
        return self.info['Driver']['givenName']

    @property
    def team(self):
        """Team name
        """
        return self.info['Constructor']['name']

    def _filter(self, df):
        return df[df['Driver'] == self.number]


class ETL:

    def __init__(self, api_path):
        self.api_path = api_path


def _log_progress(i, length, c=30):
    if (logging.root.level >= logging.INFO and i % int(length / (c-1)) == 0):
        p = round((i / length) * c)
        is_last = (p * (c+1)/c) > c
        print(f"\r[{'+'*p}{'-'*(c-p)}] ({length if is_last else i}/{length})",
              end="\n" if is_last else '')
