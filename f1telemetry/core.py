from f1telemetry import ergast
from f1telemetry import api

class Weekend:

    def __init__(self, year, gp):
        self.data = ergast.fetch_weekend(year, gp)
        self.year = year
        self.gp = gp

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
        self.results = ergast.load(weekend.year, weekend.gp, self.session)
        self.event = api.load(weekend.name, weekend.date, self.session)

    def get_driver(self, identifier):
        if type(identifier) is str:
            for p in self.results:
                if p['Driver']['code'] == identifier:
                    return Driver(p)
        return None

    def get_data(self, session):
        year, gp = self.weekend.year, self.weekend.gp
        return ergast.fetch_day(year, gp, session)


class Quali(Classification):

    session = 'Qualifying'


class Race(Classification):

    session = 'Race'


class Driver:

    def __init__(self, info):
        self.info = info

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
    def team(self):
        """Team name
        """
        return self.info['Constructor']['name']
