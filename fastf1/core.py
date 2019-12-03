"""
:mod:`fastf1.core` - Core module
================================
"""
from fastf1 import ergast
from fastf1 import api


def get_session(year, gp, event=None):
    """Main core function, will take care of crafting an object
    corresponding to the requested session. If not specified, full
    weekend is returned.

    Args:
        year: session year (Tested only with 2019)
        gp: weekend number (1: Australia, ..., 21: Abu Dhabi)
        event(=None): may be 'R' or 'Q', full weekend otherwise.

    Returns:
        :class:`Weekend` or :class:`Session`

    """
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


class Weekend:

    def __init__(self, year, gp):
        self.year = year
        self.gp = gp
        self._loaded = False

    def init(self):
        """Load web data
        """
        if not self._loaded:
            self.data = ergast.fetch_weekend(self.year, self.gp)
            self._loaded = True
        return self

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

    def __init__(self, weekend, session_name):
        self.weekend = weekend
        self.session_name = session_name

    def init(self):
        """Load web data or cache if available and populate object
        """
        w, s = self.weekend.init(), self.session_name
        self.results = ergast.load(w.year, w.gp, s)
        self.event = api.load(w.name, w.date, s)
        self.summary = api.summary(api.make_path(w.name, w.date, s))
        numbers = self.summary['Driver']
        self.summary['Driver'] = numbers.map(self._get_driver_map())
        return self

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


class Driver:

    def __init__(self, session, info):
        self.session = session
        self.info = info
        self.identifier = info['Driver']['code']
        self.number = info['number']
        self.car_data = self._filter(self.session.event['car_data'])
        self.car_position = self._filter(self.session.event['position'])

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

