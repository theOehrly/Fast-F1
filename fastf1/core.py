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
logging.basicConfig(level=logging.INFO)


def get_session(year, gp, event=None):
    """Main core function, also the only to be exposed at package level.
    It will take care of crafting an object corresponding to the
    requested session. If not specified, full weekend is returned.

    Args:
        year: session year (Tested only with 2019)
        gp: name or weekend number (1: Australia, ..., 21: Abu Dhabi)
            if gp is a string, a fuzzy match will be performed on the
            season rounds and the most likely will be selected.
            'bahrain', 'australia', 'abudabi' are some of the examples
            that you can pass and the correct week will be selected.
        event(=None): may be 'R' or 'Q', full weekend otherwise.

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
        """Load summary data to be associated for each lap.
        """
        logging.info("Getting summary...")
        summary = api.summary(self.api_path)
        logging.info("Formatting summary...")
        numbers = summary['Driver']
        summary['DriverNumber'] = numbers
        summary['Team'] = numbers.map(self._get_team_map())
        summary['Driver'] = numbers.map(self._get_driver_map())
        summary.rename(columns={'LastLapTime': 'LapTime',
                                 'NumberOfLaps': 'LapNumber'},
                                 inplace=True)
        def __time_formatter(x):
            return x if x is None else '00:' + x
        formatted_time = summary['LapTime'].apply(__time_formatter)
        summary['LapTime'] = pd.to_timedelta(formatted_time)
        for column in ['Time', 'PitOutTime', 'PitInTime']:
            summary[column] = pd.to_timedelta(summary[column])
        for column in ['Sector1Time','Sector2Time', 'Sector3Time']:
            numeric = pd.to_numeric(summary[column])
            summary[column] = pd.to_timedelta(numeric, unit='seconds')
        return summary

    def _load_telemetry(self):
        """Load telemetry data to be associated for each lap.
        """
        logging.info("Getting telemetry data...")
        car_data, res = api.car_data(self.api_path), {}
        logging.info("Parsing temetry...")
        car_data['Time'] = pd.to_timedelta(car_data['Time'])
        for _drv in self.laps['DriverNumber'].unique():
            to_pass = car_data[car_data['Driver'] == _drv] # 30 % time
            res[_drv] = self._resample(to_pass) # 70 % time
        event_telemetry =  []
        lap_start_date = []
        for i in self.laps.index:
            row = self.laps.loc[i]
            if str(lap_time := row['LapTime']) != 'NaT':
                time = row['Time']
                driver = row['DriverNumber']
                car_data = res[driver][0]
                offset_date = res[driver][1]
                sel = ((car_data['Time'] < time)
                        & (car_data['Time'] >= (time - lap_time)))
                telemetry = car_data[sel].copy()
                # First calc lap start date
                lap_start_date.append(offset_date + telemetry['Time'].iloc[0])
                # Then shift time to 0 so laps can overlap
                telemetry['Time'] += (lap_time - time)
                telemetry = telemetry.drop(columns='Driver')
                def put_space(_telemetry):
                    dt = _telemetry['Time'].dt.total_seconds().diff()
                    dt.iloc[0] = _telemetry['Time'].iloc[0].total_seconds()
                    ds = _telemetry['Speed'] / 3.6 * dt
                    _telemetry['Space'] = ds.cumsum()
                    return _telemetry
                telemetry = put_space(telemetry)
                event_telemetry.append(telemetry)
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
        if len(drivers := df['Driver'].unique()) > 1:
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
        # Resample:
        # Date contains the corret time spacing information, so we use that
        # 90% of function time is spent in the next line
        res = pre.resample('0.1S', on='Time').mean().interpolate(method='linear')
        res['Driver'] = drivers[0] # Populate and fix columns lost with resampling 
        res[['nGear', 'DRS']] = res[['nGear', 'DRS']].round().astype(int)
        res['Time'] = pd.to_timedelta(res.index, unit='s')
        return res.reset_index(drop=True), offset_date


class Laps(pd.DataFrame):
    """This class wraps :attr:`Session.laps` which is a classic pandas
    DataFrame with the addition of the :meth:`sel` method.
    """

    def sel(self, _filter_):
        """This method allows to simplify usage and code readability.
        You can access useful lap entries quickly in combination with
        :mod:`fastf1.selectors`.

        If for example you want to get the fastest lap of Bottas you can
        narrow it down like this::

            import fastf1 as ff1
            from fastf1 import selectors as ect    

            laps = ff1.get_session(2019, 'Bahrain', 'Q').load_laps()
            best_bottas = laps.sel(ect.driver('BOT')).sel(ect.fastest)

            print(best_bottas['LapTime'])
            # Timedelta('0 days 00:01:28.256000')

        Args:
            _filter_: selector function

        Returns:
            :class:`Laps` or pandas Series if only 1 entry is left
    
        """
        res = _filter_(self)
        return Laps(res) if isinstance(res, pd.DataFrame) else res


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


