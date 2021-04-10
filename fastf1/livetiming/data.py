"""
Data object for livetiming data
"""

from datetime import timedelta
import json
import hashlib
import logging

from fastf1.utils import to_datetime, recursive_dict_get


_track_status_mapping = {
    'AllClear': '1',
    'Yellow': '2',
    'SCDeployed': '4',
    'Red': '5',
    'VSCDeployed': '6',
    'VSCEnding': '7'
}


class LiveTimingData:
    """Live timing data object for using saved livetiming data as data source.

    This object is created from data that was recorded using
    :class:`fastf1.livetiming.SignalRClient`. It can be passed to
    various api calling functions using the ``livedata`` keyword.

    Usually you will only instantiate this function and pass it to
    other functions.

    See :mod:`fastf1.livetiming` for a usage example.

    If you want to load data from multiple files you can simply pass multiple
    filenames::

        livedata = LiveTimingData('file1.txt', 'file2.txt', 'file3.txt')

    The files need to be in chronological order but may overlap. I.e. if the
    last five minutes of file1 are the same as the first 5 minutes of file2
    this will be recognized while loading the data. No duplicate data will
    be loaded.

    Args:
        *files (str): One or multiple file names
        remove_duplicates (bool): Remove duplicate lines. Mainly useful when
            loading multiple overlapping recordings. (Checking for duplicates
            is currently very slow for large files. Therefore, it can be
            disabled if this may cause problems.)
    """
    def __init__(self, *files, remove_duplicates=True):
        # file names
        self.files = files
        # parsed data
        self.data = dict()
        # number of json errors
        self.errorcount = 0
        # flag for auto loading on first access
        self._files_read = False
        # date when session was started
        self._start_date = None
        # whether any files were loaded previously, i.e. appending data
        self._previous_files = False
        # hash each line, used to skip duplicates from multiple files
        self._line_hashes = list()
        self._remove_duplicates = remove_duplicates

    def load(self):
        """
        Read all files, parse the data and store it by category.

        Should usually not be called manually. This is called
        automatically the first time :meth:`get`, :meth:`has`
        or :meth:`list_categories` are called.
        """
        logging.info("Reading live timing data from recording. "
                     "This may take a bit.")
        for fname in self.files:
            self._load_single_file(fname)
        self._files_read = True

    def _load_single_file(self, fname):
        # read one file, parse its content and add it to the already loaded
        # data (if there is data already)
        with open(fname, 'r') as fobj:
            data = fobj.readlines()

        # try to find the correct start date (only if this is the first file)
        if not self._previous_files:
            self._try_set_correct_start_date(data)

        for line in data:
            self._parse_line(line)

        # first file was loaded, others are appended if any more are loaded
        self._previous_files = True

    def _parse_line(self, elem):
        # parse a single line of data

        if self._remove_duplicates:
            # prevent duplicates when loading data (slow, but it works...)
            # allows to load data from overlapping recordings
            lhash = hashlib.md5(elem.encode()).hexdigest()
            if lhash in self._line_hashes:
                return
            self._line_hashes.append(lhash)

        # load the three parts of each data element
        elem = self._fix_json(elem)
        try:
            cat, msg, dt = json.loads(elem)
        except (json.JSONDecodeError, ValueError):
            self.errorcount += 1
            return

        # convert string to datetime
        try:
            dt = to_datetime(dt)
        except (ValueError, TypeError):
            self.errorcount += 1
            return

        # if no start date could be determined beforehand, simply use the
        # first timestamp as we need to have some date as start date;
        # convert timestamp to timedelta (SessionTime) base on start date
        if self._start_date is None:
            self._start_date = dt
            td = timedelta(seconds=0)
        else:
            td = dt - self._start_date

        self._store_message(cat, td, msg)

    def _store_message(self, cat, td, msg):
        # stores parsed messages by category
        # TrackStatus and SessionStatus categories need special handling
        if cat == 'SessionData':
            self._parse_session_data(msg)
        elif cat not in ('TrackStatus', 'SessionStatus'):
            self._add_to_category(cat, [td, msg])

    def _fix_json(self, elem):
        # fix F1's not json compliant data
        elem = elem.replace("'", '"') \
            .replace('True', 'true') \
            .replace('False', 'false')
        return elem

    def _add_to_category(self, cat, entry):
        if cat not in self.data:
            self.data[cat] = [entry, ]
        else:
            self.data[cat].append(entry)

    def _parse_session_data(self, msg):
        # make sure the categories exist as we want to append to them
        if 'TrackStatus' not in self.data.keys():
            self.data['TrackStatus'] = {'Time': [], 'Status': [], 'Message': []}
        if 'SessionStatus' not in self.data.keys():
            self.data['SessionStatus'] = {'Time': [], 'Status': []}

        if ('StatusSeries' in msg) and isinstance(msg['StatusSeries'], dict):
            for entry in msg['StatusSeries'].values():
                # convert timestamp to timedelta
                try:
                    status_dt = to_datetime(entry['Utc'])
                except (KeyError, ValueError, TypeError):
                    self.errorcount += 1
                    continue
                status_timedelta = status_dt - self._start_date

                # add data to category
                if 'TrackStatus' in entry.keys():
                    status_value = str(entry['TrackStatus'])
                    # convert to numeric system used by the api
                    if not status_value.isnumeric():
                        status_value = _track_status_mapping[status_value]
                    self.data['TrackStatus']['Time'].append(status_timedelta)
                    self.data['TrackStatus']['Status'].append(status_value)
                    self.data['TrackStatus']['Message'].append("")

                elif 'SessionStatus' in entry.keys():
                    self.data['SessionStatus']['Time'].append(status_timedelta)
                    self.data['SessionStatus']['Status'].append(entry['SessionStatus'])

    def _try_set_correct_start_date(self, data):
        # skim content to find 'Started' session status without actually
        # decoding each line to save time
        for elem in data:
            if 'SessionStatus' in elem and 'Started' in elem:
                break
        else:
            # didn't find 'Started'
            logging.error("Error while trying to set correct "
                          "session start date!")
            return

        # decode matching line
        elem = self._fix_json(elem)
        try:
            cat, msg, dt = json.loads(elem)
        except (json.JSONDecodeError, ValueError):
            logging.error("Error while trying to set correct "
                          "session start date!")
            return

        # find correct entry in series
        try:
            for entry in msg['StatusSeries']:
                status = recursive_dict_get(entry, 'SessionStatus')
                if status == 'Started':
                    try:
                        self._start_date = to_datetime(entry['Utc'])
                    except (KeyError, ValueError, TypeError):
                        self.errorcount += 1
                        logging.error("Error while trying to set correct "
                                      "session start date!")
                        return
        except AttributeError:
            for entry in msg['StatusSeries'].values():
                status = entry.get('SessionStatus', None)
                if status == 'Started':
                    try:
                        self._start_date = to_datetime(entry['Utc'])
                    except (KeyError, ValueError, TypeError):
                        self.errorcount += 1
                        logging.error("Error while trying to set correct "
                                      "session start date!")
                        return

    def get(self, name):
        """
        Return data for category name.

        Will load data on first call, this will take a bit.

        Args:
            name (str): name of the category
            """
        if not self._files_read:
            self.load()
        return self.data[name]

    def has(self, name):
        """
        Check if data for a category name exists.

        Will load data on first call, this will take a bit.

        Args:
            name (str): name of the category
        """
        if not self._files_read:
            self.load()
        return name in self.data.keys()

    def list_categories(self):
        """
        List all available data categories.

        Will load data on first call, this will take a bit.

        Returns:
            list of category names
        """
        if not self._files_read:
            self.load()
        return list(self.data.keys())
