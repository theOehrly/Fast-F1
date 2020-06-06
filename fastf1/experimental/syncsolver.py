from fastf1.track import Track, TrackPoint
from fastf1.func import reject_outliers, min_index, max_index
from matplotlib import pyplot as plt
import pandas as pd
import numpy as np
from multiprocessing import Process, Manager
import time


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
        :type track: Track
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
        self.point_range = list()

    def setup(self):
        """Do some one-off calculations. This needs to be called before solve() can be _run."""
        self.drivers = list(self.tel.keys())

        # calculate the start date of the session
        some_driver = self.drivers[0]  # TODO to be sure this should be done with multiple drivers
        self.session_start_date = self.pos[some_driver].head(1).Date.squeeze().round('min')

        # get all current start/finish line positions
        self.point_range = self._get_start_line_range()

    def _wait_for_results(self):
        """Wait for all processes to send their results through the result queue.
        Then results are then joined together and returned. This function blocks until all results have been received.
        This also means that all processes are guaranteed to be in an idle state when it returns."""

        idle_count = 0
        results = dict()

        while idle_count != self.number_of_processes:
            res = self.result_queue.get()

            # res is a dictionary containing {name: {key: list(), key: list(), ...}, name: ...}
            # join all lists together per key
            for name in res.keys():
                # this key exists in the joined results; extend all the existing lists with the new values
                if name in results.keys():
                    for key in res[name].keys():
                        results[name][key].extend(res[name][key])

                # this key does not yet exist; create it
                else:
                    results[name] = res[name]

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

        for condition in self.conditions:
            self.results[condition.name] = dict()

        print("Starting calculations...")
        start_time = time.time()  # start time for measuring _run time

        cnt = 0
        print(len(self.point_range))
        for test_point in self.point_range[0::3]:
            cnt += 1
            print(cnt)  # simplified progress report

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

            for condition in self.conditions:
                c_index = self.conditions.index(condition)

                proc_res = condition.generate_results(res[c_index], test_point)

                for key in proc_res.keys():
                    if key in self.results[condition.name].keys():
                        self.results[condition.name][key].append(proc_res[key])
                    else:
                        self.results[condition.name][key] = [proc_res[key], ]

            self._resume_all()  # send a resume command to all processes; they will block on the empty task queue until task are added

        # all tasks have been calculated
        print('Finished')
        print('Took:', time.time() - start_time)

        self._queue_return_command()  # queue a return command; processes currently only take exit commands while in idle state
        self._wait_for_results()  # wait for the processes to go to idle state
        self._exit_all()  # send exit command to all processes
        self._join_all()  # wait for all processes to actually exit

    def solve_one_condition_single_process(self):
        """Alternative way for solving the condition (usage not recommended!)

        This function will do all processing inside the main thread. Additionally, only one condition can
        be solved. If conditions were added, only the one which was added first will be considered.

        This function is not intended for productive use, but rather for debugging or profiling!
        """

        # data which the processes need
        shared_data = {'track': self.track,
                       'laps': self.laps,
                       'pos': self.pos,
                       'session_start_date': self.session_start_date}

        self.conditions[0].set_data(shared_data)

        self.results = dict()

        print("Starting calculations...")
        start_time = time.time()  # start time for measuring _run time

        cnt = 0
        print(len(self.point_range))
        for test_point in self.point_range[0::3]:
            cnt += 1
            print(cnt)  # simplified progress report

            values = dict()
            for driver in self.drivers:
                data = self.conditions[0].for_driver(driver, test_point)
                if not values:
                    values = data
                else:
                    for key in data.keys():
                        values[key].extend(data[key])

            proc_res = self.conditions[0].generate_results(values, test_point)

            name = self.conditions[0].name
            for key in proc_res.keys():
                if key in self.results.keys():
                    self.results[key].append(proc_res[key])
                else:
                    self.results[key] = [proc_res[key], ]

        # all tasks have been calculated
        print('Finished')
        print('Took:', time.time() - start_time)

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
                    # start of the session plus time at which the lap was registered (approximately end of lap)
                    approx_lap_end_date = self.session_start_date + lap.Time

                    end_pnt = self.track.interpolate_pos_from_time(drv, approx_lap_end_date)
                    if not end_pnt:
                        continue  # coordinates for the given date were not valid

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

        points = list()
        index_on_track = list()
        for x, y in zip(x_coords, y_coords):
            point = self.track.get_closest_point(TrackPoint(x, y))
            points.append(point)
            index_on_track.append(self.track.sorted_points.index(point))

        point_a = points[min_index(index_on_track)]
        point_b = points[max_index(index_on_track)]

        point_range = self.track.get_points_between(point_a, point_b, short=True, include_ref=True)

        print("Searching for start/finish line in range x={},y={} | x={}, y={}".format(point_a.x, point_a.y, point_b.x, point_b.y))

        return point_range


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

    def _add_result(self, name, data):
        """Add a single calculation result."""
        if name not in self._results.keys():
            self._results[name] = data
        else:
            for key in data.keys():
                self._results[name][key].extend(data[key])

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
