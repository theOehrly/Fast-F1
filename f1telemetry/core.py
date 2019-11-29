from f1telemetry import ergast
from f1telemetry import api


def get_session(year, gp, event=None):
    """Main core function, will take care of crafting an object
    corresponding to the requested session. If not specified, full
    weekend is returned.

    Args:
        year: session year (Tested only with 2019)
        gp: weekend number (1: Australia, ..., 21: Abu Dhabi)
        event(=None): may be 'R' or 'Q', full weekend otherwise.

    Returns:
        :class:`Weekend`, :class:`Race` or :class:`Quali`

    """
    weekend = Weekend(year, gp)
    if event == 'Q':
        return weekend.get_quali()
    if event == 'R':
        return weekend.get_race()
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

    def get_quali(self):
        """Fetch and returns Race instance of weekend
        """
        return Quali(self)

    def get_race(self):
        """Fetch and returns Race instance of weekend
        """
        return Race(self)

    @property
    def name(self):
        """Weekend name, e.g. "British Grand Prix"
        """
        return self.data['raceName']

    @property
    def date(self):
        """Weekend race date
        """
        return self.data['date']


class Classification:

    def __init__(self, weekend):
        self.weekend = weekend

    def init(self):
        """Load web data
        """
        w, s = self.weekend.init(), self.session
        self.results = ergast.load(w.year, w.gp, s)
        self.event = api.load(w.name, w.date, s)
        return self

    def get_driver(self, identifier):
        if type(identifier) is str:
            for info in self.results:
                if info['Driver']['code'] == identifier:
                    return Driver(self, info)
        return None


class Quali(Classification):

    session = 'Qualifying'


class Race(Classification):

    session = 'Race'


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

