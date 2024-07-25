"""
Data object for livetiming data
"""

import json
import warnings
from datetime import timedelta

from fastf1.logger import get_logger
from fastf1.utils import (
    recursive_dict_get,
    to_datetime
)


_logger = get_logger(__name__)


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
    :class:`~fastf1.livetiming.client.SignalRClient`. It can be passed to
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
    """
    def __init__(self, *files, **kwargs):
        # file names
        self.files = files
        # parsed data
        self.data = dict()
        # number of json errors
        self.errorcount = 0
        # flag for automatic data loading on first access
        self._files_read = False
        # date when session was started
        self._start_date = None

        if 'remove_duplicates' in kwargs:
            warnings.warn("The argument `remove_duplicates` is no longer "
                          "available. Duplicates caused by overlapping files "
                          "will now always be removed.")

    def load(self):
        """
        Read all files, parse the data and store it by category.

        Should usually not be called manually. This is called
        automatically the first time :meth:`get`, :meth:`has`
        or :meth:`list_categories` are called.
        """
        _logger.info("Reading live timing data from recording. "
                     "This may take a bit.")

        is_first = True
        _files = [*self.files, None]
        current_data, next_data = None, None

        # We always need the current and next file loaded, so we can detect
        # where they overlap. The "next" file then becomes the "current" file
        # and the next "next" file is read.
        for next_file in _files:
            # make the previous "next" file the "current" file
            current_data = next_data

            if next_file is None:
                # reached the end, there is no subsequent data anymore
                next_data = None
            else:
                # read a new file as next file
                with open(next_file) as fobj:
                    next_data = fobj.readlines()

            if current_data is None:
                # there is no "current" file yet (i.e. first iteration),
                # skip ahead once right away to read one more file
                continue

            next_line = next_data[0] if next_data else None

            self._load_single_file(current_data,
                                   is_first_file=is_first,
                                   next_line=next_line)
            is_first = False

        # set flag that all files have been read
        self._files_read = True

    def _load_single_file(self, data, *, is_first_file, next_line):
        # parse its content and add it to the already loaded
        # data (if there is data already)

        # try to find the correct start date (only if this is the first file)
        if is_first_file:
            self._try_set_correct_start_date(data)

        for line in data:
            if line == next_line:
                break
            self._parse_line(line)

        # first file was loaded, others are appended if any more are loaded
        self._previous_files = True

    def _parse_line(self, elem):
        # parse a single line of data

        # load the three parts of each data element
        elem = self._fix_json(elem)
        try:
            cat, msg, dt_str = json.loads(elem)
        except (json.JSONDecodeError, ValueError):
            self.errorcount += 1
            return

        # convert string to datetime
        dt = to_datetime(dt_str)
        if dt is None:
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

    def _try_set_correct_start_date(self, data):
        # skim content to find 'Started' session status without actually
        # decoding each line to save time
        for elem in data:
            if 'SessionStatus' in elem and 'Started' in elem:
                break
        else:
            # didn't find 'Started'
            _logger.error("Error while trying to set correct "
                          "session start date!")
            return

        # decode matching line
        elem = self._fix_json(elem)
        try:
            cat, msg, dt = json.loads(elem)
        except (json.JSONDecodeError, ValueError):
            _logger.error("Error while trying to set correct "
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
                        _logger.error("Error while trying to set correct "
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
                        _logger.error("Error while trying to set correct "
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
