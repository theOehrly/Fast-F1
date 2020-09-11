"""
:mod:`fastf1.core` - Core module
================================

Contains the main classes and functions.
"""

from fastf1 import utils
from fastf1 import ergast
from fastf1 import api
import pandas as pd
import numpy as np
import logging
import functools
import scipy
from scipy import spatial
import pathlib
import os

import warnings
with warnings.catch_warnings():
    warnings.filterwarnings('ignore', message="Using slow pure-python SequenceMatcher")
    # suppress that warning, it's confusing at best here, we don't need fast sequence matching
    # and the installation (on windows) some effort
    from fuzzywuzzy import fuzz

logging.basicConfig(level=logging.INFO, style='{', format="{module: <8} {levelname: >10} \t{message}")


TESTING_LOOKUP = {'2020': [['2020-02-19', '2020-02-20', '2020-02-21'],
                           ['2020-02-26', '2020-02-27', '2020-02-28']]}

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

REFERENCE_LAP_RESOLUTION = 0.667
"""A distance in meters which indicates the resolution of the reference
lap. This reference is used to project car positions and calculate
things like distance between cars.
"""

MANUAL_PATCHES = {'5': {'/static/2020/2020-02-21_Pre-Season_Test_1/2020-02-21_Practice_3/': 'vettel_test_2020_02_21.csv'},
                  '77': {'/static/2020/2020-02-28_Pre-Season_Test_2/2020-02-28_Practice_3/': 'bottas_test_2020_02_28.csv'}}


def get_session(year, gp, event=None):
    """Main core function. It will take care of crafting an object
    corresponding to the requested session.
    If not specified, full weekend is returned.

    Args:
        year (number): Session year
        gp (number or string): Name or weekend number (1: Australia,
                               ..., 21: Abu Dhabi). If gp is a string,
                               a fuzzy match will be performed on the
                               season rounds and the most likely will be
                               selected.

                               Some examples that will be correctly
                               interpreted: 'bahrain', 'australia',
                               'abudabi', 'monza'.

                               Pass 'testing' to fetch Barcelona winter
                               tests.

        event (=None): may be 'FP1', 'FP2', 'FP3', 'Q' or 'R', if not 
                       specified you get the full :class:`Weekend`.
                       If gp is 'testing' event is the test day (1 to 6)

    Returns:
        :class:`Weekend` or :class:`Session`

    """
    if type(gp) is str and gp == 'testing':
        pre_season_week, event = _get_testing_week_event(year, event)
        print(pre_season_week, event)
        weekend = Weekend(year, pre_season_week)
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
    """From the year and a text to match, will try to find the most
    likely week number of the event.

    Args:
        year (int): Year of the event
        match (string): Name of the race or gp (e.g. 'Bahrain')

    Returns:
        The round number. (2019, 'Bahrain') -> 2

    """
    ratios = np.array([])

    def build_string(d):
        r = len('https://en.wikipedia.org/wiki/')  # TODO what the hell is this
        c, l = d['Circuit'], d['Circuit']['Location']
        return (f"{d['url'][r:]} {d['raceName']} {c['circuitId']} "
                + f"{c['url'][r:]} {c['circuitName']} {l['locality']} "
                + f"{l['country']}")

    races = ergast.fetch_season(year)
    to_match = [build_string(block) for block in races]
    ratios = np.array([fuzz.partial_ratio(match, ref) for ref in to_match])

    return int(races[np.argmax(ratios)]['round'])


def _get_testing_week_event(year, day):
    """Get the correct weekend and event for testing from the
    year and day of the test. (where day is 1, 2, 3, ...)
    """
    try:
        day = int(day)
        week = 1 if day < 4 else 2  # TODO Probably will change from 2021
    except:
        msg = "Cannot fetch testing without correct event day."
        raise Exception(msg)
    week_day = ((day - 1) % 3) + 1  # TODO Probably will change from 2021
    pre_season_week = f'Pre-Season Test {week}'
    event = f'Practice {week_day}'

    return pre_season_week, event


class Weekend:
    """If you want to handle multiple sessions from the same race event
    you can use a :class:Weekend instance.

    For example you could do the following::

        import fastf1 as ff1

        weekend = ff1.get_session(2019, 'Monza')
        quali = weekend.get_quali() # Q Session
        race = weekend.get_race() # R Session

    """

    def __init__(self, year, gp):
        self.year = year
        self.gp = gp
        if self.is_testing():
            logging.warning("Ergast api not supported for testing.")
            self.data = {
                'raceName': gp,
                'date': TESTING_LOOKUP[str(year)][int(gp[-1]) - 1][-1]}
        else:
            self.data = ergast.fetch_weekend(self.year, self.gp)

    def get_practice(self, number):
        """
        Args:
            number: 1, 2 or 3 Free practice session number
        Returns:
            :class:`Session` instance
        """
        return Session(self, f'Practice {number}')

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
    """The session class usually will be your starting point. This
    object will have various information about the event such as `name` and
    `date`. To get the sessions laps use :meth:`Session.load_laps`.
    """

    def __init__(self, weekend, session_name):
        self.weekend = weekend
        self.name = session_name
        self.date = self._get_session_date()
        self.api_path = api.make_path(self.weekend.name,
                                      self.weekend.date,
                                      self.name, self.date)
        if not self.weekend.is_testing():
            try:
                self.results = ergast.load(self.weekend.year,
                                           self.weekend.gp,
                                           self.name)
            except:
                # Ergast will take some time after a session until the data is available
                # while the data is not yet available, an error will be raised
                # TODO improve the very broad except at least for the pupose of better logging
                logging.warning("Ergast lookup failed")
                self._create_empty_ergast_result()

        else:
            self._create_empty_ergast_result()

        self.laps = Laps(pd.DataFrame())

    def _create_empty_ergast_result(self):
        """In case Ergast has no data, this function creates an empty result
        to emulate the structure."""
        self.results = []
        for driver in D_LOOKUP:
            self.results.append({
                'number': str(driver[0]),
                'Driver': {'code': driver[1]},
                'Constructor': {'name': driver[2]}})

    def _get_session_date(self):
        """Session date formatted as '%Y-%m-%d' (e.g. '2019-03-12')"""
        if self.weekend.is_testing():
            year = str(self.weekend.year)
            week_index = int(self.weekend.name[-1]) - 1
            day_index = int(self.name[-1]) - 1
            date = TESTING_LOOKUP[year][week_index][day_index]
        elif self.name in ('Qualifying', 'Practice 3'):
            # Assuming that quali was one day before race which is not always correct
            # TODO Should check if also formula1 makes this assumption
            offset_date = pd.to_datetime(self.weekend.date) + pd.DateOffset(-1)
            date = offset_date.strftime('%Y-%m-%d')
        elif self.name in ('Practice 1', 'Practice 2'):
            # Again, assuming that practice 1/2 are the day before quali (except Monaco)
            _ = -3 if self.weekend.name == 'Monaco Grand Prix' else -2
            offset_date = pd.to_datetime(self.weekend.date) + pd.DateOffset(_)
            date = offset_date.strftime('%Y-%m-%d')
        else:  # Race
            date = self.weekend.date

        return date

    @utils._cached_laps
    def load_laps(self):
        """With load laps all the timing information is merged into a
        single pandas dataframe. The first time you run this method on
        a session it may take a while to load. Multiple megabytes of
        data have to be downloaded and processed. After that, laps will
        be stored locally and execution will be much faster.

        The returned :class:`Laps` instance can be used just like a
        pandas DataFrame with some additional enhancements.

        The dataframe columns, therefore, each lap, has the following
        properties:

            - **Time** (pandas.Timedelta): Time when the lap time was set (end of lap)
            - **Driver** (string): Three letters driver identifier
            - **LapTime** (pandas.Timedelta): Recorded lap time
            - **LapNumber** (int): Recorded lap number
            - **PitOutTime** (pandas.Timedelta): Time when car exited the pit
            - **PitInTime** (pandas.Timedelta): Time when car entered the pit
            - **Sector1Time** (pandas.Timedelta): Sector 1 recorded time
            - **Sector2Time** (pandas.Timedelta): Sector 2 recorded time
            - **Sector3Time** (pandas.Timedelta): Sector 3 recorded time
            - **Sector1Time** (pandas.Timedelta): Sector 1 timestamp (end of sector)
            - **Sector2Time** (pandas.Timedelta): Sector 2 timestamp (end of sector)
            - **Sector3Time** (pandas.Timedelta): Sector 3 timestamp (end of sector)
            - **SpeedI1** (float): Speedtrap sector 1
            - **SpeedI2** (float): Speedtrap sector 2
            - **SpeedFL** (float): Speedtrap at finish line
            - **SpeedST** (float): Speedtrap on longest straight (Not sure)
            - **Stint** (int): Indicates the stint number
            - **Compound** (str): Tyre compound name: SOFT, MEDIUM ..
            - **TyreLife** (int): Laps spent on that compound
            - **FreshTyre** (bool): Tyre had TyreLife=0 at stint start
            - **DriverNumber** (str): Car number
            - **Team** (str): Team name
            - **LapStartDate** (pandas.Timestamp): Timestamp (Date+Time) for the start of the lap
            - **telemetry** (pandas.DataFrame): Telemetry with the following channels:

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
                - `DistanceToDriverAhead` (string): distance to next car in m
                - `DriverAhead` (string): the car ahead

        .. note:: Absolute time is not super accurate. The moment a lap
            is logged is not always the same and there will be some
            jitter. At the moment lap time reference is synchronised
            on the sector time triggered with lowest latency.
            Expect an error of around ±10m when overlapping telemetry
            data of different laps.

        Returns:
            :class:`Laps`

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
        """
        Args:
            identifier (str): driver's three letter identifier (for example 'VER')

        Returns:
            instance of :class:`Driver`
        """
        if type(identifier) is str:
            for info in self.results:
                if info['Driver']['code'] == identifier:
                    return Driver(self, info)

        return None

    def _load_summary(self):
        """From `timing_data` and `timing_app_data` a summary table is
        built. Lap by lap, information on tyre, sectors and times are 
        organised in an accessible pandas data frame.

        Returns:
            pandas dataframe

        """
        logging.info("Getting summary...")
        data, _ = api.timing_data(self.api_path)
        app_data = api.timing_app_data(self.api_path)
        # Now we do some manipulation to make it beautiful
        logging.info("Formatting summary...")

        # Matching data and app_data. Not super straightforward
        # Sometimes a car may enter the pit without changing tyres, so
        # new compound is associated with the help of logging time.
        useful = app_data[['Driver', 'Time', 'Compound', 'TotalLaps', 'New']]
        useful = useful[~useful['Compound'].isnull()]

        for i, driver in enumerate(data['Driver'].unique()):
            d1 = data[data['Driver'] == driver]
            d2 = useful[useful['Driver'] == driver]

            if not driver or len(d2) == 0:
                continue  # no data for this driver; skip

            result = pd.merge_asof(d1, d2, on='Time', by='Driver')

            for npit in result['NumberOfPitStops'].unique():
                sel = result['NumberOfPitStops'] == npit
                result.loc[sel, 'TotalLaps'] += np.arange(0, sel.sum()) + 1
            # check if df is defined already before concat (vars is a builtin function)
            df = result if 'df' not in vars() else pd.concat([df, result], sort=False)

        summary = df.reset_index(drop=True)
        summary.rename(columns={'TotalLaps': 'TyreLife',
                                'NumberOfPitStops': 'Stint',
                                'Driver': 'DriverNumber',
                                'NumberOfLaps': 'LapNumber',
                                'New': 'FreshTyre'}, inplace=True)
        summary['Stint'] += 1  # counting stints from 1
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
                logging.warning(f"Could not find telemetry data for driver {driver}")
            if driver in position:
                pos[driver], _ = self._resample(position[driver])
            else:
                logging.warning(f"Could not find position data for driver {driver}")

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
            if not pd.isnull(lap['LapTime']) and driver in tel:
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
                    logging.warning(f"Empty telemetry slice from lap {lap['LapNumber']} of driver {driver}")
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

        # find first row where time is not zero; usually this is the first row but sometimes.....
        i_min = np.min(np.where((df['Time'] != pd.Timedelta(0)) & ~pd.isna(df['Time'])))

        # Align:
        counter, last_val = 0, None
        for i, val in enumerate(df['Time'].values):
            if i < i_min:
                continue
            if val == last_val:
                counter += 1
            elif counter > 2:
                i -= 1
                break  # found align point at sample i
            else:
                counter = 0
            last_val = val

        pre = df.copy().reset_index(drop=True)
        ref_date = df.iloc[i]['Date']
        ref_time = df.iloc[i]['Time']

        offset_date = ref_date - ref_time
        pre['Time'] = (pre['Date'] - ref_date) + ref_time

        # Map non numeric
        mapped, unmap = self._map_objects(pre)

        # Resample:
        # Date contains the correct time spacing information, so we use that
        # 90% of function time is spent in the next line
        res = mapped.resample('0.1S', on='Date', origin=ref_date).mean().interpolate(method='linear')

        if 'nGear' in res.columns and 'DRS' in res.columns:
            res[['nGear', 'DRS']] = res[['nGear', 'DRS']].round().astype(int)

        res = unmap(res)
        res['Time'] = res.index - offset_date

        return res.reset_index(drop=True), offset_date

    def _inject_position(self, position, lap, _telemetry):
        lap_position = self._slice_stream(position, lap, pad=1)
        lap_position, unmap = self._map_objects(lap_position)
        ref_time = _telemetry['Time'].values
        pos_time = lap_position['Time'].values
        ref_x = pd.to_numeric(ref_time)
        ref_xp = pd.to_numeric(pos_time)

        for column in lap_position.columns:
            if column not in _telemetry:
                if ref_xp.any():  # data can be missing; make sure it exists
                    y = np.interp(ref_x, ref_xp, lap_position[column].values)
                else:
                    y = (np.nan, ) * len(ref_x)  # create empty values
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
        pad = pd.to_timedelta(f'{pad * 0.1}s')
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

        if lap is not None:
            driver_ahead = self._make_trajectory(lap)

        else:
            logging.warning("Telemetry data is missing! No valid car data has been found for any lap!")
            driver_ahead = dict()  # create empty data
            for drv in self.position:
                empty_drv = (None, ) * len(self.position[drv])
                empty_dist = (np.nan, ) * len(self.position[drv])
                driver_ahead[drv] = pd.DataFrame({'DistanceToDriverAhead': empty_dist, 'DriverAhead': empty_drv})

        for drv in self.position:
            self.position[drv] = self.position[drv].join(driver_ahead[drv])

    def _get_reference_lap(self):
        times = self.laps['LapTime'].copy()
        times = times.sort_values()

        for i in range(len(self.laps)):
            lap = self.laps.loc[times.index[i]].copy()
            time, driver = lap['Time'], lap['DriverNumber']
            tele = self._slice_stream(self.car_data[driver], lap)
            if np.all(tele['Speed'] > 0):  # check for valid telemetry
                break
        else:
            return None

        tele = self._inject_position(self.position[driver], lap, tele)
        tele = self._inject_space(tele)
        lap['telemetry'] = tele

        return lap

    def _inject_space(self, _telemetry):
        if _telemetry.size != 0:
            dt = _telemetry['Time'].dt.total_seconds().diff()
            dt.iloc[0] = _telemetry['Time'].iloc[0].total_seconds()
            ds = _telemetry['Speed'] / 3.6 * dt
            _telemetry['Space'] = ds.cumsum()
        else:
            _telemetry['Space'] = ()

        return _telemetry

    def _make_trajectory(self, lap):
        """Create telemetry space
        """
        if lap.telemetry.size != 0:
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

            reference_s = np.arange(0, total_s, REFERENCE_LAP_RESOLUTION)

            reference_x = np.interp(reference_s, full_s, full_x)
            reference_y = np.interp(reference_s, full_s, full_y)
            reference_z = np.interp(reference_s, full_s, full_z)

            ssize = len(reference_s)

            """Build track map and project driver position to one trajectory
            """

            def fix_suzuka(projection_index, _s):
                """Yes, suzuka is bad
                """

                #  For tracks like suzuka (therefore only suzuka) we have
                # a beautiful crossing point. So, FOR F**K SAKE, sometimes
                # shortest distance may fall below the bridge or viceversa
                # gotta do some monotony sort of check. Not the cleanest
                # solution.
                def moving_average(a, n=3):
                    ret = np.cumsum(a, dtype=float)
                    ret[n:] = ret[n:] - ret[:-n]
                    ma = ret[n - 1:] / n

                    return np.concatenate([ma[0:n // 2], ma, ma[-n // 2:-1]])

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

        else:
            # no data to base calculations on; create empty results
            driver_ahead = dict()
            for drv in self.position.keys():
                data = {'DistanceToDriverAhead': (), 'DriverAhead': ()}
                driver_ahead[drv] = pd.DataFrame(data)

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

    def pick_drivers(self, identifiers):
        """Select drivers given a list of their identifiers. Same as
        :meth:`Laps.pick_driver` but for lists::

            some_drivers_laps = ff1.pick_drivers([5, 'BOT', 7])

        """
        names = [n for n in identifiers if not str(n).isdigit()]
        numbers = [str(n) for n in identifiers if str(n).isdigit()]
        drv, num = self['Driver'], self['DriverNumber']

        return self[(drv.isin(names) | num.isin(numbers))]

    def pick_team(self, name):
        """Select team given its name::

            mercedes = ff1.pick_team('Mercedes')
            alfa_romeo = ff1.pick_team('Alfa Romeo')

        Have a look to :attr:`fastf1.plotting.TEAM_COLORS` for a quick
        reference on team names.
        """
        return self[self['Team'] == name]

    def pick_teams(self, names):
        """Same as :meth:`Laps.pick_team` but for a list of teams.
        """
        return self[self['Team'].isin(names)]

    def pick_fastest(self):
        """Get lap with best `LapTime`.
        """
        lap = self.loc[self['LapTime'].idxmin()]
        if isinstance(lap, pd.DataFrame):
            # More laps, same time
            lap = lap.iloc[0]  # take first clocked

        return lap

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

    def pick_tyre(self, compound):
        """Get laps done on a specific compound.

        Args:
            compound (string): may be "SOFT", "MEDIUM" or "HARD"

        """
        return self[self['Compound'] == compound]


class Driver:
    """Driver class that provides some information on drivers and their finishing results.

    see also :func:`Session.get_driver`

    .. note:: Driver data is only available if the Ergast api lookup did not fail.

    """
    def __init__(self, session, info):
        self.session = session
        self.info = info
        """`Driver.info` contains some more info from the Ergast api"""
        self.identifier = info['Driver']['code']
        self.number = info['number']

    @property
    def dnf(self):
        """True if driver did not finish"""
        s = self.info['status']
        return not (s[3:6] == 'Lap' or s == 'Finished')

    @property
    def grid(self):
        """Grid position"""
        return int(self.info['grid'])

    @property
    def position(self):
        """Finishing position"""
        return int(self.info['position'])

    @property
    def name(self):
        """Driver first name"""
        return self.info['Driver']['givenName']

    @property
    def familyname(self):
        """Driver family name"""
        return self.info['Driver']['familyName']

    @property
    def team(self):
        """Team name"""
        return self.info['Constructor']['name']


def _log_progress(i, length, c=30):
    """Simple progress bar for console logging.

    Args:
        i (int): current value
        length (int): maximum value
        c (int, optional): number of steps when displaying the progress bar
    """
    if length < c:
        c = length
    if logging.root.level >= logging.INFO and i % int(length / (c - 1)) == 0:
        p = round((i / length) * c)
        is_last = (p * (c + 1) / c) > c
        print(f"\r[{'+' * p}{'-' * (c - p)}] ({length if is_last else i}/{length})",
              end="\n" if is_last else '')
