from fastf1 import core, api
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from math import sqrt
import pickle
import IPython
from multiprocessing import Process, Manager
import time


"""
Distinction between "Time" and "Date":

Time:   A time stamp counting up from the start of the session.
        Might sometimes be called session time for sake of clarity.
        Format: HH:MM:SS.000
        
Date:   The actual date and time at which something happened.
        Timezone is UTC I think.
        Format: YYYY-MM-DD HH:MM:SS.000
        
The terms time and date will be used consistently with this meaning.
"""


class TrackPoint:
    """Simple point class.

    A point has an x and y coordinate and an optional date.
    A function for calculating the square of the distance to another point is also provided.

    For convenience reasons point.x and point.y can also be accessed as point['x'] and point['y'] (get only).
    Only use this implementation when necessary because it lacks clarity. It's not quite obvious then that poitn is a
    separate class (could be a dictionary for example)
    """
    def __init__(self, x, y, date=None):
        """
        :param x: x coordinate
        :type x: int or float
        :param y: y coordinate
        :type y: int or float
        :param date: optional: A pandas datetime (compatible) object
        """
        self.x = x
        self.y = y
        self.date = date

    def __getitem__(self, key):
        if key == 'x':
            return self.x
        elif key == 'y':
            return self.y
        else:
            raise KeyError

    def get_sqr_dist(self, other):
        """Calculate the square of the distance to another point.

        :param other: Another point
        :type other: TrackPoint
        :return: distance^2
        """
        dist = abs(other.x - self.x) + abs(other.y - self.y)
        return dist


class TrackMap:
    # TODO check: can it somehow be that specifically the last poitn of the unsorted points is corrupted?!
    #  missing value specifically there in 2019-10-R
    # TODO determine track direction
    # TODO reorder points when start finish line position is known
    """Track map class; does all track map related processing.

    Although there are more than one hundred thousand points of position data per session, the number of
    unique points on track is limited. Typically there is about one unique point per meter of track length.
    This does not mean that the points have a fixed distance though. In slow corners they are closer together than
    on straights. A typical track has between 5000 and 7000 unique points.
    When generating the track map, all duplicate points are removed from the points so that only unique points are left.
    Then those points are sorted so they have the correct order.
    Not all unique points of a given track are necessarily present in each session. There is simply a chance that position
    data from no car is ever sent from a point. In this case we can't know that this point exist. This is not a problem
    though. But the following needs to be kept in mind:

    A track map is only a valid representation for the data it was calculated from.
    E.g. do not use a track map for race data when it was calculated from qualifying data.

    Sharing a track map between multiple sessions may be possible if the all points from all of these
    sessions where joined before and the track map was therefore calculated from both sessions at the same time.
    Although this may be possible, it is neither tested, nor intended or recommended.
    """

    def __init__(self, pos_frame):
        """Create a new track map object.

        The unit (if any) of F1's coordinate system is unknown to me. Approx.: value / 3,61 = value in meters
        There seems to be one data point per meter of track length.

        :param pos_frame: Pandas DataFrame with position data for all cars (as returned by fastf1.api.position)
        :type pos_frame: pandas.DataFrame
        """

        self._raw_pos_data = pos_frame

        self.unsorted_points = list()
        self.sorted_points = list()
        self.excluded_points = list()

        self.distances = list()
        self.distances_normalized = list()

        self.track = None

        self._next_point = None

        self._vis_freq = 0
        self._vis_counter = 0
        self._fig = None

        # extract point from position data frame
        self._unsorted_points_from_pos_data()

    def _unsorted_points_from_pos_data(self):
        numbers = list(self._raw_pos_data.keys())
        # create combined data frame with all column names but without data
        combined = pd.DataFrame(columns=['index', *self._raw_pos_data[numbers[0]].columns])

        for n in numbers:
            tmp = self._raw_pos_data[n].reset_index()
            combined = combined.append(tmp)

        # filter out data points where the car is not on track
        is_on_track = combined['Status'] == 'OnTrack'
        combined = combined[is_on_track]

        no_dupl_combined = combined.reset_index().filter(items=('X', 'Y')).drop_duplicates()

        # create a points object for each point
        for index, data in no_dupl_combined.iterrows():
            self.unsorted_points.append(TrackPoint(data['X'], data['Y']))

    def _init_viusualization(self):
        self._vis_counter = 0
        plt.ion()
        self._fig = plt.figure()
        self._ax = self._fig.add_subplot(111)
        self._ax.axis('equal')
        self._line2, = self._ax.plot((), (), 'r-')
        self._line1, = self._ax.plot((), (), 'b-')

    def _cleanup_visualization(self):
        if self._fig:
            plt.ioff()
            plt.clf()
            self._fig = None

    def _visualize_sorting_progress(self):
        """Do a visualization of the current progress.
        Updates the plot with the current data.
        """
        if not self._vis_freq:
            return  # don't do visualization if _vis_freq is zero

        if not self._fig:
            self._init_viusualization()  # first call, setup the plot

        self._vis_counter += 1

        if self._vis_counter % self._vis_freq == 0:
            # visualize current state
            xvals_sorted = list()
            yvals_sorted = list()
            for point in self.sorted_points:
                xvals_sorted.append(point.x)
                yvals_sorted.append(point.y)

            xvals_unsorted = list()
            yvals_unsorted = list()
            for point in self.unsorted_points:
                xvals_unsorted.append(point.x)
                yvals_unsorted.append(point.y)

            # update plot
            self._line1.set_data(xvals_sorted, yvals_sorted)  # set plot data
            self._line2.set_data(xvals_unsorted, yvals_unsorted)  # set plot data
            self._ax.relim()  # recompute the data limits
            self._ax.autoscale_view()  # automatic axis scaling
            self._fig.canvas.draw()
            self._fig.canvas.flush_events()

    def _integrate_distance(self):
        """Integrate distance over all points and save distance from start/finish line for each point."""
        self.distances.append(0)  # distance is obviously zero at the starting point

        distance_covered = 0  # distance since first point

        for i in range(1, len(self.sorted_points)):
            # calculate the length of the segment between the last and the current point
            segment_length = sqrt(self.sorted_points[i-1].get_sqr_dist(self.sorted_points[i]))
            distance_covered += segment_length
            self.distances.append(distance_covered)

        for dist in self.distances:
            self.distances_normalized.append(dist / self.distances[-1])

    def _sort_points(self):
        # TODO remove outliers before sorting!!!
        """Does the actual sorting of points."""
        # sort points
        # Get the first point as a starting point. Any point could be used as starting point. Later the next closest point is used as next point.
        self._next_point = self.unsorted_points.pop(0)

        while self.unsorted_points:
            self._visualize_sorting_progress()

            # calculate all distances between the next point and all other points
            distances = list()
            for pnt in self.unsorted_points:
                distances.append(self._next_point.get_sqr_dist(pnt))

            # get the next closest point and its index
            min_dst = min(distances)
            index_min = distances.index(min_dst)

            # Check if the closest point is within a reasonable distance. There are some outliers which are very clearly not on track.
            # The limit value was determined experimentally. Usually the distance between to points is approx. 100.
            # (This is the square of the distance. Not the distance itself.)
            # If the _next_point has no other point within a reasonable distance, it is considered an outlier and removed.
            if min_dst > 200:
                self.excluded_points.append(self._next_point)
            else:
                self.sorted_points.append(self._next_point)

            # Get a new _next_point. The new point is the one which was closest to the last one.
            self._next_point = self.unsorted_points.pop(index_min)

        # append the last point if it is not an outlier
        if self._next_point.get_sqr_dist(self.sorted_points[-1]) <= 200:
            self.sorted_points.append(self._next_point)

        self._cleanup_visualization()

    def generate_track(self, visualization_frequency=0):
        """Generate a track map from the raw points.

        Sorts all points. Then determines the correct direction and starting point.
        Finally the lap distance is calculated by integrating over all points.
        The distance since start is saved for each point. Additionally, the lap distance is saved normalized to a range of 0 to 1.
        :param visualization_frequency: (optional) specify  after how many calculated points the plot should be updated.
            Set to zero for never (default: never). Plotting is somewhat slow. A visualization frequency greater than 50 is recommended.
        :type visualization_frequency: int
        """
        self._vis_freq = visualization_frequency

        self._sort_points()
        self._integrate_distance()  # TODO this should not be done before determining track direction and start/finish line position

        xvals = list()
        yvals = list()
        for point in self.sorted_points:
            xvals.append(point.x)
            yvals.append(point.y)

        self.track = pd.DataFrame({'X': xvals,
                                   'Y': yvals,
                                   'Distance': self.distances,
                                   'Normalized': self.distances_normalized})

    def print_stats(self):
        print("Number of points: {}".format(len(self.sorted_points)))
        print("Excluded points: {}".format(len(self.excluded_points)))

    def get_closest_point(self, point):
        # this assumes that the track is made up of all possible points
        # this assumption is valid within the scope of the data from which the track was calculated.
        # see disclaimer for track map class in general

        distances = list()
        for track_point in self.sorted_points:
            distances.append(track_point.get_sqr_dist(point))

        return self.sorted_points[distances.index(min(distances))]

    def get_points_between(self, point1, point2, short=True, include_ref=True):
        i1 = self.sorted_points.index(point1)
        i2 = self.sorted_points.index(point2)

        # n_in = i1 - i2  # number of points between 1 and 2 in list
        # n_out = len(self.sorted_points) - n_in  # number of point around, i.e. beginning and end of list to 1 and 2

        if short:
            # the easy way, simply slice between the two indices
            pnt_range = self.sorted_points[min(i1, i2)+1: max(i1, i2)]
            if include_ref:
                if i1 < i2:
                    pnt_range.insert(0, point1)
                    pnt_range.append(point2)
                else:
                    pnt_range.insert(0, point2)
                    pnt_range.append(point1)
        else:
            first = self.sorted_points[:min(i1, i2)]
            second = self.sorted_points[max(i1, i2)+1:]
            pnt_range = second + first
            if include_ref:
                if i1 < i2:
                    pnt_range.insert(0, point2)
                    pnt_range.append(point1)
                else:
                    pnt_range.insert(0, point1)
                    pnt_range.append(point2)

        return pnt_range

    def get_second_coord(self, val, ref_point_1, ref_point_2, from_coord='x'):
        p_range = self.get_points_between(ref_point_1, ref_point_2)

        # find the closest point in this range; only valid if the range is approximately straight
        # because we're only checking against one coordinate
        distances = list()
        for p in p_range:
            distances.append(abs(p[from_coord] - val))

        min_i = min_index(distances)
        p_a = p_range[min_index(distances)]  # closest point
        # second closest point (with edge cases if closest point is first or last point in list)
        if min_i == 0:
            p_b = p_range[1] if distances[1] < distances[-1] else p_range[-1]
        elif min_i == len(distances) - 1:
            p_b = p_range[0] if distances[0] < distances[-2] else p_range[-2]
        else:
            p_b = p_range[min_i+1] if distances[min_i+1] < distances[min_i-1] else p_range[min_i-1]

        # do interpolation
        delta_x = p_b.x - p_a.x
        delta_y = p_b.y - p_a.y

        if from_coord == 'x':
            interp_delta_x = val - p_a.x
            interp_y = p_a.y + delta_y * interp_delta_x / delta_x
            return TrackPoint(val, interp_y)
        else:
            interp_delta_y = val - p_a.y
            interp_x = p_a.x + delta_x * interp_delta_y / delta_y
            return TrackPoint(interp_x, val)

    def get_time_from_pos(self, drv, x, y, time_range_start, time_range_end):
        drv_pos = self._raw_pos_data[drv]  # get DataFrame for driver

        # calculate closest point in DataFrame (a track map contains all points from the DataFrame)
        pnt = TrackPoint(x, y)
        closest_track_pnt = self.get_closest_point(pnt)

        # create an array of boolean values for filtering points which exactly match the given coordinates
        is_x = drv_pos.X = closest_track_pnt.X
        is_y = drv_pos.Y = closest_track_pnt.Y
        is_closest_pnt = is_x and is_y

        # there may be multiple points from different laps with the given coordinates
        # therefore an estimated time range needs to be provided
        res_pnts = drv_pos[is_closest_pnt]
        for p in res_pnts:
            if time_range_start <= p.Date <= time_range_end:
                return p.Date
        else:
            return None

    def interpolate_pos_from_time(self, drv, query_date):
        # use linear interpolation to determine position at arbitrary time
        drv_pos = self._raw_pos_data[drv]  # get DataFrame for driver

        closest = drv_pos.iloc[(drv_pos['Date'] - query_date).abs().argsort()[:2]]
        delta_t = closest.iloc[1]['Date'] - closest.iloc[0]['Date']
        delta_x = closest.iloc[1]['X'] - closest.iloc[0]['X']
        delta_y = closest.iloc[1]['Y'] - closest.iloc[0]['Y']
        interp_delta_t = query_date - closest.iloc[0]['Date']

        interp_x = closest.iloc[0]['X'] + delta_x * interp_delta_t / delta_t
        interp_y = closest.iloc[0]['Y'] + delta_y * interp_delta_t / delta_t

        return TrackPoint(interp_x, interp_y)


def min_index(_iterable):
    """Return the index of the minimum value in an iterable"""
    return _iterable.index(min(_iterable))


def reject_outliers(data, *secondary, m=2.):
    """Reject outliers from a numpy array.

    Calculates the deviation of each value from the median of the arrays values. Then calculates the median of
    all deviations. If a values deviation is greater than m times the median deviation, it is removed.
    An arbitrary number of additional arrays can be passed to this function. For each value that is removed
    from the reference array, the value at the corresponding index is removed from the other arryays."""
    d = np.abs(data - np.median(data))
    mdev = np.median(d)
    s = d/mdev if mdev else 0.

    ret_secondary = list()
    for i in range(len(secondary)):
        ret_secondary.append(secondary[i][s < m])

    return data[s < m], *ret_secondary


def dump_raw_data(year, gp, event):
    session = core.get_session(year, gp, event)
    pos = api.position(session.api_path)
    tel = api.car_data(session.api_path)
    laps_data, stream_data = api.timing_data(session.api_path)

    for var, fname in zip((session, pos, tel, laps_data, stream_data), ('session', 'pos', 'tel', 'laps_data', 'stream_data')):
        with open("var_dumps/" + fname, "wb") as fout:
            pickle.dump(var, fout)


class AdvancedSyncSolver:
    """Advanced Data Synchronization and Determination of Sectors and Start/Finish Line Position
        assumptions
          - a session is always started on a full minute
              --> should be able to do without but it is easier for now

        conditions for syncing data
          - the start/finish line needs to be in a fixed place (x/y coordinates)
          - last lap start time + lap duration = current lap start time

        possible issues
          - lap and sector times are reported with what seems to be a +-0.5s accuracy
              with no further information about this process, it has to be assumed that a lap/sector time can be reported with
              an earlier or later time than its correct time (correct time = the time it was actually set at)
          - inaccuracies due to only ms precision --> max error ~50ms after the race; probably not that critical
          - laps with pit stops --> skip laps with pit in or pit out for now; only add the lap times
          - there is no fixed start time which is the sme for every driver --> maybe use race end timing?

        possible further sources of data
          - race result time between drivers for fixed values at the end too

        approach for now
          - get min/max values for start finish position from the first coarse synchronization
          - iterate over this range in small increments
              - always skip first lap
              - from selected position, interpolate a lap start time
              - add all lap times up to get a lap start time for each
              - interpolate start/finish x/y for each lap which does not have pit in or pit out
          - calculate metrics after each pass
              - arithmetic mean of x and y
              - standard deviation of x and y
              --> plot metrics
        """
    def __init__(self, track, telemetry_data, position_data, laps_data, processes=1):
        """Initiate the solver.

        :param track: Track class for this session. The track map needs to be generated beforehand!
        :type track: TrackMap
        :param telemetry_data: Car telemetry data from the fastf1 api as returned by api.car_data
        :type telemetry_data: dict
        :param position_data: Car position data from the fastf1 api as returned by api.position
        :type position_data: dict
        :param laps_data: Lap data from the fastf1 api as returned by api.timing_data
        :type laps_data: pandas.DataFrame
        :param processes: Specifies the number of worker subprocesses where the actual data processing takes place.
            The total number of python processes will be higher but the worker processes will be the only ones which
            create significant cpu usage. One worker will approximately utilize one cpu core to 100%. Never specify
            the use of more processes than you have (virtual) cores in your system. Recommended is one or two processes
            less than the number of cores.
        :type processes: int
        """
        self.track = track
        self.tel = telemetry_data
        self.pos = position_data
        self.laps = laps_data

        self.results = dict()

        self.conditions = list()

        self.manager = None
        self.task_queue = None
        self.result_queue = None
        self.command_queue = None
        self.number_of_processes = processes
        self.subprocesses = list()

        self.drivers = None
        self.session_start_date = None
        self.x_range = [0, 0]
        self.y_range = [0, 0]

    def setup(self):
        """Do some one-off calculations. This needs to be called before solve() can be _run."""
        self.drivers = list(self.tel.keys())

        # calculate the start date of the session
        some_driver = self.drivers[0]  # TODO to be sure this should be done with multiple drivers
        self.session_start_date = self.pos[some_driver].head(1).Date.squeeze().round('min')

        # get all current start/finish line positions
        x_coords, y_coords = self._get_start_line_range()

        # get range start and end
        self.x_range[0] = min(x_coords)
        self.x_range[1] = max(x_coords)
        i_start, = np.where(x_coords == self.x_range[0])
        i_end, = np.where(x_coords == self.x_range[1])
        self.y_range[0] = y_coords[i_start]
        self.y_range[1] = y_coords[i_end]

    def log_setup_stats(self):
        """Print some very broad statistics from the setup"""
        print("Number of Drivers: {}".format(len(self.drivers)))
        print("Start/Finish Line in Range x={},{} | y={},{}".format(*self.x_range, *self.y_range))

    def _wait_for_results(self):
        """Wait for all processes to send their results through the result queue.
        Then results are then joined together and returned. This function blocks until all results have been received.
        This also means that all processes are guaranteed to be in an idle state when it returns."""

        idle_count = 0
        results = dict()

        while idle_count != self.number_of_processes:
            res = self.result_queue.get()

            # res is a dictionary containing multiple {key: [list(), list(), ...]} pairs
            # join all lists together per key
            for key in list(res.keys()):
                # this key exists in the joined results; extend all the existing lists with the new values
                if key in results:
                    for i in range(len(results[key])):
                        results[key][i].extend(res[key][i])

                # this key does not yet exist; create it
                else:
                    results[key] = res[key]

            idle_count += 1

        return results

    def _queue_return_command(self):
        """Queue as many 'return' commands as there are processes. When a process receives this commands, it will return its calculation
        results and go into an idle state. During idle it will wait for further commands passed through the result_queue."""
        for _ in range(self.number_of_processes):
            self.task_queue.put('return')

    def _exit_all(self):
        """Queue as many exit commands on the command queue as there are processes."""
        for _ in range(self.number_of_processes):
            self.command_queue.put('exit')

    def _resume_all(self):
        """Queue as many resume commands on the command queue as there are processes."""
        for _ in range(self.number_of_processes):
            self.command_queue.put('resume')

    def _join_all(self):
        """Join all processes."""
        for process in self.subprocesses:
            process.join()

    def solve(self):
        """Main solver function which starts all the processing."""

        # data which the processes need
        shared_data = {'track': self.track,
                       'laps': self.laps,
                       'pos': self.pos,
                       'session_start_date': self.session_start_date}

        for cond in self.conditions:
            cond.set_data(shared_data)

        # each condition needs to be calculated for each driver
        # create a queue and populate it with (condition, driver) pairs
        self.manager = Manager()
        self.task_queue = self.manager.Queue()  # main -> subprocess: holds all tasks and the commands for returning the results
        self.result_queue = self.manager.Queue()  # subprocess -> main: return results
        self.command_queue = self.manager.Queue()  # main -> subprocess: processes block on this queue while idle waiting for a command

        self.subprocesses = list()

        print("Starting processes...")
        # create and start the processes
        for _ in range(self.number_of_processes):
            p = SolverSubprocess(self.task_queue, self.result_queue, self.command_queue, self.conditions)
            p.start()
            self.subprocesses.append(p)

        self.results = {'mean_x': list(), 'mean_y': list(), 'mad_x': list(), 'mad_y': list(), 'tx': list(), 'ty': list()}

        print("Starting calculations...")
        start_time = time.time()  # start time for measuring _run time

        cnt = 0
        for test_x in range(int(self.x_range[0]), int(self.x_range[1]), 15):
            cnt += 1
            print(cnt)  # simplified progress report

            # interpolate y
            test_y = self.y_range[0] + (self.y_range[1] - self.y_range[0]) * (test_x - self.x_range[0]) / (self.x_range[1] - self.x_range[0])
            test_point = TrackPoint(test_x, test_y)

            # Create tasks: one task consists of a condition, driver and test point
            # Do one calculation _run per test point. The results for this point are then collected and the next _run for teh next point is done.
            # Per calculation _run 'number of conditions' * 'number of drivers' = 'number of tasks'

            for condition in self.conditions:
                for driver in self.drivers:
                    # the list of conditions is passed to the process when it is created; only pass the index for a condition because sending whole
                    # classes through the queue is inefficient
                    c_index = self.conditions.index(condition)
                    self.task_queue.put((c_index, driver, test_point))
                    # each process can now fetch an item from the queue and calculate the condition for the specified driver

            # add return commands to task queue so that all processes will return their results and go to idle when the end of the queue is reached
            self._queue_return_command()
            # wait until all processes have finished processing the tasks and have returned their results
            res = self._wait_for_results()

            # process results
            x_series = pd.Series(res[0][0])
            y_series = pd.Series(res[0][1])
            print(x_series.mad())
            self.results['mean_x'].append(x_series.mean())
            self.results['mean_y'].append(y_series.mean())
            self.results['mad_x'].append(x_series.mad())
            self.results['mad_y'].append(y_series.mad())
            self.results['tx'].append(test_x)
            self.results['ty'].append(test_y)

            self._resume_all()  # send a resume command to all processes; they will block on the empty task queue until task are added

        # all tasks have been calculated
        print('Finished')
        print('Took:', time.time() - start_time)

        self._queue_return_command()  # queue a return command; processes currently only take exit commands while in idle state
        self._wait_for_results()  # wait for the processes to go to idle state
        self._exit_all()  # send exit command to all processes
        self._join_all()  # wait for all processes to actually exit

    def add_condition(self, condition, *args, **kwargs):
        """Add a condition class to the solver. Currently there is no check against adding duplicate conditions. Conditions can also not
        be removed again."""
        cond_inst = condition(*args, **kwargs)  # create an instance of the condition and add it to the list of solver conditions
        self.conditions.append(cond_inst)

    def _get_start_line_range(self):
        """Calculate a range of coordinates for a possible position of the start/finish line. This is done based
        on the existing lap data from the api. Extreme outliers are removed from the range of coordinates.

        :return: Two numpy arrays of x and y coordinates respectively
        """
        # find the highest and lowest x/y coordinates for the current start/finish line positions
        # positions in plural; the preliminary synchronization is not perfect
        x_coords = list()
        y_coords = list()
        usable_laps = 0  # for logging purpose

        for drv in self.drivers:
            is_drv = (self.laps.Driver == drv)  # create a list of booleans for filtering laps_data by current driver
            drv_total_laps = self.laps[is_drv].NumberOfLaps.max()  # get the current drivers total number of laps in this session

            for _, lap in self.laps[is_drv].iterrows():
                # first lap, last lap, in-lap, out-lap and laps with no lap number are skipped
                # data of these might be unreliable or imprecise
                if (pd.isnull(lap.NumberOfLaps) or
                        lap.NumberOfLaps in (1, drv_total_laps) or
                        not pd.isnull(lap.PitInTime) or
                        not pd.isnull(lap.PitOutTime)):

                    continue

                else:
                    approx_lap_end_date = self.session_start_date + lap.Time  # start of the session plus time at which the lap was registered (approximately end of lap)
                    end_pnt = self.track.interpolate_pos_from_time(drv, approx_lap_end_date)
                    x_coords.append(end_pnt.x)
                    y_coords.append(end_pnt.y)

                    usable_laps += 1

        print("{} usable laps".format(usable_laps))

        # there will still be some outliers; it's only very few though
        # so... statistics to the rescue then but allow for very high deviation as we want a long range of possible points for now
        # we only want to sort out the really far away stuff
        x_coords = np.array(x_coords)
        y_coords = np.array(y_coords)
        x_coords, y_coords = reject_outliers(x_coords, y_coords, m=100.0)  # m defines the threshold for outliers; very high here
        print("Rejected {} outliers".format(usable_laps - len(x_coords)))

        # calculate mean absolute deviation after outlier rejection (for logging purpose)
        mad_x = pd.Series(x_coords).mad()
        mad_y = pd.Series(y_coords).mad()
        print("Mean absolute deviation of preliminary lap starting position:\n\t x={} y={}".format(round(mad_x), round(mad_y)))

        return x_coords, y_coords


class SolverSubprocess:
    """This class represents a single subprocess/worker.
    It will store all calculation results until the main process request them. The results will then be send
    trough a queue to the main process. The main process will join all results from all subprocesses."""
    def __init__(self, task_queue, result_queue, command_queue, conditions):
        """Initiate the subprocess.

        :param task_queue: main -> subprocess: tasks and command for returning data
        :type task_queue: multiprocessing.Queue
        :param result_queue: subprocess -> main: return calculation results
        :type result_queue: multiprocessing.Queue
        :param command_queue: main -> subprocess: commands for resume or exit; process will block on this queue while idling
        :type command_queue: multiprocessing.Queue
        :param conditions: List of all conditions added to the solver. Each task will contain an index which references a condition from this list.
        :type conditions: list
        """
        # use a dictionary to hold all results from processed conditions
        # multiple processes can process the same condition for different drivers simultaneously
        # therefore it is not safe to immediately save the results in the condition class
        # instead, the subprocess collects all results from the calculations from one _run (one iteration)
        # they are stored in the dictionary and teh condition's index is used as a key
        # when all subprocesses are finished, the results are collected and the conditions are updated
        self._task_queue = task_queue
        self._result_queue = result_queue
        self._command_queue = command_queue
        self._conditions = conditions
        self._results = dict()

        self._process = Process(target=self._run)

    def start(self):
        """Start the process. Wraps multiprocessing.Process.start"""
        self._process.start()

    def join(self):
        """Wait for this process to join. Wraps multiprocessing.Process.join"""
        self._process.join()

    def _add_result(self, index, data):
        """Add a single calculation result."""
        if index not in self._results.keys():
            self._results[index] = data
        else:
            for i in range(len(data)):
                self._results[index][i].extend(data[i])

    def _run(self):
        """This is the main function which will loop for the lifetime of the process.
        It receives tasks and commands from the main process and calculates the results."""

        while True:
            task = self._task_queue.get()

            if task == 'return':
                # print('Going into idle', self)
                # return the calculation results and wait for commands ("idle")
                self._result_queue.put(self._results)
                self._results = dict()  # delete all results after they have been returned

                cmd = self._command_queue.get()
                if cmd == 'exit':
                    print("Exiting", self)
                    return

                elif cmd == 'resume':
                    # print("Resuming", self)
                    continue

            # print('New task', self)

            # process the received task
            # a task consists of a condition which is to be calculated, a driver to calculate if for and a test point for
            # a probable start/finish line position
            c_index, drv, point = task
            condition = self._conditions[c_index]  # get the condition from its index
            res = condition.for_driver(drv, point)  # calculate the condition and store the results
            self._add_result(c_index, res)


class BaseCondition:
    """A base class for all solver conditions.

    This class cannot be used directly but needs to be subclassed by and actual condition class."""
    def __init__(self):
        self.data = None

    def set_data(self, data):
        """
        :param data: Dictionary containing data which needs to be accessible when a subprocess calculates the condition.
        :type data: dict
        """
        self.data = data

    def for_driver(self, drv, test_point):
        """This function needs to be reimplemented by the subclass.

        :param drv: The number of the driver (as a string) for which the condition is to be calculated.
        :type drv: string
        :param test_point: A point for a possible start/finish line position
        :type test_point: TrackPoint
        """
        pass


class StartFinishCondition(BaseCondition):
    """Solver condition for constant start/finish line position.

    How this condition works:
    Subtract the last lap time from the test point. (Yes subtract time from position... fancy shit going on here)
    If the test point is the actual start finish line position, this should result in the same point again. And this should
    be the case for each lap and driver.
    If the test point is not the actual start/finish line position the variation in driving between laps should cause
    a variation of the result.
    The test point at which there is the least variance in the result is deemed the correct position (simplified).
    """
    def __init__(self, *args, **kwargs):
        super().__init__()

    def for_driver(self, drv, test_point):
        """ Calculate the condition for a driver and test point.

        :param drv: The driver for which to calculate the condition (driver number as a string)
        :type drv: string
        :param test_point: Start/finsih line position (test) for which to calculate the condition
        :type test_point: TrackPoint
        :return: [results x, results y] where results_* is a list of values containing the results for each lap
        """
        is_drv = (self.data['laps'].Driver == drv)
        drv_last_lap = self.data['laps'][is_drv].NumberOfLaps.max()  # get the last lap of this driver

        res_x = list()
        res_y = list()

        for _, lap in self.data['laps'][is_drv].iterrows():
            # first lap, last lap, in-lap, out-lap and laps with no lap number are skipped
            if (pd.isnull(lap.NumberOfLaps) or
                    lap.NumberOfLaps in (1, drv_last_lap) or
                    not pd.isnull(lap.PitInTime) or
                    not pd.isnull(lap.PitOutTime)):

                continue

            else:
                approx_time = self.data['session_start_date'] + lap.Time
                # now we have an approximate time for the end of the lap and we have test_x/test_y which is not unique track point
                # to get an exact time at which the car was at test_point, define a window of +-delta_t around approx_time
                delta_t = pd.to_timedelta(10, "s")
                t_start = approx_time - delta_t
                t_end = approx_time + delta_t
                pos_range = self.data['pos'][drv].query("@t_start < Date < @t_end")
                # search the two points in this range which are closest to test_point
                pos_distances = list()
                neg_distances = list()
                pos_points = list()
                neg_points = list()
                for _, row in pos_range.iterrows():
                    pnt = TrackPoint(row.X, row.Y, row.Date)
                    dist = test_point.get_sqr_dist(pnt)
                    if pnt.x < test_point.x:
                        pos_distances.append(dist)
                        pos_points.append(pnt)
                    else:
                        neg_distances.append(dist)
                        neg_points.append(pnt)

                # make sure that there are points before and after this one
                if (not neg_distances) or (not pos_distances):
                    continue

                # distances, points = zip(*sorted(zip(distances, points)))  # sort distances and sort point_range exactly the same way
                p_a = pos_points[min_index(pos_distances)]
                p_b = neg_points[min_index(neg_distances)]

                # interpolate the time for test_point from those two points
                test_date = p_a.date + (p_b.date - p_a.date) * (test_point.x - p_a.x) / (p_b.x - p_a.x)
                # calculate start date for last lap and get position for that date
                last_lap_start = test_date - lap.LastLapTime
                lap_start_point = self.data['track'].interpolate_pos_from_time(drv, last_lap_start)
                # add point coordinates to list of results for this pass
                res_x.append(lap_start_point.x)
                res_y.append(lap_start_point.y)

        return [res_x, res_y]


if __name__ == '__main__':
    session = pickle.load(open("var_dumps/session", "rb"))
    pos = pickle.load(open("var_dumps/pos", "rb"))
    tel = pickle.load(open("var_dumps/tel", "rb"))
    laps_data = pickle.load(open("var_dumps/laps_data", "rb"))
    track = pickle.load(open("var_dumps/track_map", "rb"))

    solver = AdvancedSyncSolver(track, tel, pos, laps_data, processes=6)
    solver.setup()
    solver.log_setup_stats()
    solver.add_condition(StartFinishCondition)
    solver.solve()

    IPython.embed()
