"""
:mod:`fastf1.core` - Core module
================================
"""
from fastf1 import utils
from fastf1 import ergast
from fastf1 import api
from fuzzywuzzy import fuzz
import pandas as pd
import numpy as np
import logging
import functools
logging.basicConfig(level=logging.INFO)


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
        event (=None): may be 'FP1', 'FP2', 'FP3', 'Q' or 'R', if not 
                       specified you get the full :class:`Weekend`.

    Returns:
        :class:`Weekend` or :class:`Session`

    """
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
        self.session_name = session_name
        w, s = self.weekend, self.session_name
        self.api_path = api.make_path(w.name, w.date, s)
        self.results = ergast.load(w.year, w.gp, s)

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
                - `Status` (string): flags OffTrack/OnTrack for GPS 
                - `SessionTime` (timedelta): time elapsed from session start

        .. note:: Absolute time is not super accurate. The moment a lap
            is logged is not always the same and there will be some
            jitter. At the moment absolute lap time reference is set to
            when "Sector 1" time is fired. Expect an error of ±10m when 
            overlapping telemetry data of different laps.

        Returns:
            laps

        """
        logging.info(f"Loading laps for {self.weekend.name} {self.session_name}")
        self.laps = self._load_summary()
        telemetry, lap_start_date = self._load_telemetry()
        self.laps['LapStartDate'] = lap_start_date
        self.laps['telemetry'] = telemetry
        logging.info(f"Laps loaded and saved!")
        self.laps = Laps(self.laps)
        return self.laps

    def get_driver(self, identifier):
        if type(identifier) is str:
            for info in self.results:
                if info['Driver']['code'] == identifier:
                    return Driver(self, info)
        return None

    def _get_driver_map(self):
        lookup = {}
        for block in self.results:
            lookup[block['number']] = block['Driver']['code']
        return lookup

    def _get_team_map(self):
        lookup = {}
        for block in self.results:
            lookup[block['number']] = block['Constructor']['name']
        return lookup

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
        laps_data, _ = api.timing_data(self.api_path)
        laps_app_data = api.timing_app_data(self.api_path)
        # Now we do some manipulation to make it beautiful
        logging.info("Formatting summary...")
        df = None
        laps_data['Stint'] = laps_data['NumberOfPitStops'] + 1
        laps_data.drop(columns=['NumberOfPitStops'], inplace=True)
        # Matching laps_data and laps_app_data. Not super straightworward
        # Sometimes a car may enter the pit without changing tyres, so
        # new compound is associated with the help of logging time.
        useful = laps_app_data[['Driver', 'Time', 'Compound', 'TotalLaps', 'New']]
        useful = useful[~useful['Compound'].isnull()]
        for driver in laps_data['Driver'].unique():
            d1 = laps_data[laps_data['Driver'] == driver]
            d2 = useful[useful['Driver'] == driver]
            d1 = d1.sort_values('Time')
            d2 = d2.sort_values('Time')
            result = pd.merge_asof(d1, d2, on='Time', by='Driver')
            for stint in result['Stint'].unique():
                sel = result['Stint'] == stint
                result.loc[sel, 'TotalLaps'] += np.arange(0, sel.sum()) + 1
            df = result if df is None else pd.concat([df, result], sort=False)    
        df.rename(columns={'TotalLaps': 'TyreLife', 'New': 'FreshTyre'}, inplace=True)
        summary = df.reset_index(drop=True)
        numbers = summary['Driver']
        summary['DriverNumber'] = numbers
        summary['Team'] = numbers.map(self._get_team_map())
        summary['Driver'] = numbers.map(self._get_driver_map())
        summary.rename(columns={'LastLapTime': 'LapTime',
                                 'NumberOfLaps': 'LapNumber'},
                                 inplace=True)
        return summary

    def _load_telemetry(self):
        """Load telemetry data to be associated for each lap.

        """
        rtel, rpos, event_telemetry, lap_start_date = {}, {}, [], []
        logging.info("Getting telemetry data...")
        car_data = api.car_data(self.api_path)
        logging.info("Getting position data...")
        position = api.position(self.api_path)
        logging.info("Resampling telemetry...")
        for driver in car_data:
            rtel[driver] = self._resample(car_data[driver])
            rpos[driver] = self._resample(position[driver])
        logging.info("Creating laps...")
        for i in self.laps.index:
            _log_progress(i, len(self.laps.index))
            lap = self.laps.loc[i]
            if str(lap['LapTime']) != 'NaT':
                time, driver = lap['Time'], lap['DriverNumber']
                full_tel, full_pos = rtel[driver][0], rpos[driver][0]
                full_tel = rtel[driver][0]
                telemetry = self.__slice_stream(full_tel, lap)
                telemetry = self.__inject_space(telemetry)
                telemetry = self.__inject_position(full_pos, lap, telemetry)
                event_telemetry.append(telemetry)
                # Calc lap start date
                lap_start_time = telemetry['SessionTime'].iloc[0]
                lap_start_date.append(rtel[driver][1] + lap_start_time)
            else:
                event_telemetry.append(None)
                lap_start_date.append(None)
        return event_telemetry, lap_start_date

    def __inject_position(self, position, lap, _telemetry):
        lap_position = self.__slice_stream(position, lap, pad=1)
        lap_position, unmap = self.__map_objects(lap_position)
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

    def __inject_space(self, _telemetry):
        dt = _telemetry['Time'].dt.total_seconds().diff()
        dt.iloc[0] = _telemetry['Time'].iloc[0].total_seconds()
        ds = _telemetry['Speed'] / 3.6 * dt
        _telemetry['Space'] = ds.cumsum()
        return _telemetry

    def __slice_stream(self, df, lap, pad=0):
        pad = pd.to_timedelta(f'{pad*0.1}s')
        end_time, lap_time = lap['Time'], lap['LapTime']
        sel = ((df['Time'] < (end_time + pad))
                & (df['Time'] >= (end_time - lap_time - pad)))
        lap_stream = df.loc[sel].copy()
        lap_stream['SessionTime'] = lap_stream['Time']
        # Then shift time to 0 so laps can overlap
        lap_stream['Time'] += lap_time - end_time
        return lap_stream

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
        mapped, unmap = self.__map_objects(pre)
        # Resample:
        # Date contains the corret time spacing information, so we use that
        # 90% of function time is spent in the next line
        res = mapped.resample('0.1S', on='Time').mean().interpolate(method='linear')
        if 'nGear' in res.columns and 'DRS' in res.columns:
            res[['nGear', 'DRS']] = res[['nGear', 'DRS']].round().astype(int)
        res = unmap(res)
        res['Time'] = pd.to_timedelta(res.index, unit='s')
        return res.reset_index(drop=True), offset_date
        #return res, offset_date

    def __map_objects(self, df):
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

    def _inject_position(self, laps):
        position = api.position(self.api_path)
        for i in laps.index:
            lap = laps.loc[i]
            driver = lap['Driver']
        return laps


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

    def __pick_wrap(func):
        @functools.wraps(func)
        def decorator(*args, **kwargs):
            res = func(*args, **kwargs)
            return Laps(res) if isinstance(res, pd.DataFrame) else res
        return decorator

    @__pick_wrap
    def pick_driver(self, name):
        """Select driver given his three letters identifier
        """
        return self[self['Driver'] == name]

    @__pick_wrap
    def pick_drivers(names):
        """Select drivers given a list of their three letters identifiers
        """
        return self[self['Driver'].isin(names)]

    @__pick_wrap
    def pick_team(name):
        """Select team given its name
        """
        return self[self['Team'] == name]

    @__pick_wrap
    def pick_teams(names):
        """Select teams given a list of names
        """
        return self[self['Team'].isin(names)]

    @__pick_wrap
    def pick_fastest(self):
        """Select fastest lap time 
        """
        return self.loc[self['LapTime'].idxmin()]

    @__pick_wrap
    def pick_quicklaps(self):
        """Select laps with lap time below :attr:`QUICKLAP_THRESHOLD`
        (default 107%) of the fastest lap from the given laps set
        """
        time_threshold = self['LapTime'].min() * Laps.QUICKLAP_THRESHOLD
        return self[self['LapTime'] < time_threshold]


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


def _log_progress(i, length, c=30):
    if (logging.root.level >= logging.INFO and i % int(length / (c-1)) == 0):
        p = round((i / length) * c)
        is_last = (p * (c+1)/c) > c
        print(f"\r[{'+'*p}{'-'*(c-p)}] ({length if is_last else i}/{length})",
              end="\n" if is_last else '')
