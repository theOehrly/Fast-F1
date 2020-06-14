"""
:mod:`fastf1.experimental.conditions` - Solver conditions
=========================================================
"""

from fastf1.track import TrackPoint
import pandas as pd
from math import sqrt


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

    def generate_results(self, results, test_point):
        pass


class SectorBorderCondition(BaseCondition):
    def __init__(self, *args, **kwargs):
        super().__init__()

    def _get_test_date(self, lap, drv, test_point):
        approx_time = self.data['session_start_date'] + lap.Time
        # now we have an approximate time for the end of the lap and we have test_x/test_y which is not unique track point
        # to get an exact time at which the car was at test_point, define a window of +-delta_t around approx_time
        delta_t = pd.to_timedelta(5, "s")
        t_start = approx_time - delta_t
        t_end = approx_time + delta_t
        pos_range = self.data['pos'][drv].query("@t_start < Date < @t_end")
        # search the two points in this range which are closest to test_point
        dists_points = list()
        for _, row in pos_range.iterrows():
            pnt = TrackPoint(row.X, row.Y, row.Date)
            dist = test_point.get_sqr_dist(pnt)
            dists_points.append((dist, pnt))

        dists_points.sort(key=lambda itm: itm[0])  # sort the list by first value of each tuple (distance)

        p_a = dists_points[0][1]  # closest point
        p_b = dists_points[1][1]  # second closest point

        dist_a_b = sqrt(p_a.get_sqr_dist(p_b))
        if dist_a_b == 0:
            return None  # I have no idea how this is even possible, looks like an error in the data retrieved from the api

        dist_test_a = sqrt(p_a.get_sqr_dist(test_point))

        # interpolate the time for test_point from those two points
        test_date = p_a.date + (p_b.date - p_a.date) * dist_test_a / dist_a_b
        return test_date

    def for_driver(self, drv, test_point):
        pass

    def generate_results(self, data, test_point):
        # process results
        x_series = pd.Series(data['x'])
        y_series = pd.Series(data['y'])

        result = {
            'mean_x': x_series.mean(),
            'mean_y': y_series.mean(),
            'mad_x': x_series.mad(),
            'mad_y': y_series.mad(),
            'tx': test_point.x,
            'ty': test_point.y
        }

        return result


class StartFinishCondition(SectorBorderCondition):
    """Solver condition for constant start/finish line position.

    How this condition works:
    Subtract the last lap time from the test point. (Yes subtract time from position... fancy shit going on here)
    If the test point is the actual start finish line position, this should result in the same point again. And this should
    be the case for each lap and driver.
    If the test point is not the actual start/finish line position the variation in driving between laps should cause
    a variation of the result.
    The test point at which there is the least variance in the result is deemed the correct position (simplified).
    """
    name = "StartFinish"

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
                test_date = self._get_test_date(lap, drv, test_point)
                if not test_date:
                    continue

                # calculate start date for last lap and get position for that date
                last_lap_start = test_date - lap.LastLapTime
                lap_start_point = self.data['track'].interpolate_pos_from_time(drv, last_lap_start)

                if not lap_start_point:
                    continue  # coordinates for the given date were not valid

                # add point coordinates to list of results for this pass
                res_x.append(lap_start_point.x)
                res_y.append(lap_start_point.y)

        return {'x': res_x, 'y': res_y}

    def generate_results(self, data, test_point):
        # process results
        x_series = pd.Series(data['x'])
        y_series = pd.Series(data['y'])

        result = {
            'mean_x': x_series.mean(),
            'mean_y': y_series.mean(),
            'mad_x': x_series.mad(),
            'mad_y': y_series.mad(),
            'tx': test_point.x,
            'ty': test_point.y
        }

        return result


class Sector23Condition(SectorBorderCondition):
    """Solver condition for constant sector2/sector3 border position.

    How this condition works:
    Subtract the last 3rd sector time from the test point.
    If the test point is the actual start finish line position, the sector border should be the same for each lap and driver.
    Basically the same as StartFinishCondition.
    """
    name = "Sector23"

    def __init__(self, *args, **kwargs):
        super().__init__()

    def for_driver(self, drv, test_point):
        """ Calculate the condition for a driver and test point.

        :param drv: The driver for which to calculate the condition (driver number as a string)
        :type drv: string
        :param test_point: Start/finish line position (test) for which to calculate the condition
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
                test_date = self._get_test_date(lap, drv, test_point)
                if not test_date:
                    continue

                # calculate start date for last sector 3 and get position for that date
                last_sector3_start = test_date - lap.Sector3Time
                lap_sector3_point = self.data['track'].interpolate_pos_from_time(drv, last_sector3_start)

                if not lap_sector3_point:
                    continue  # coordinates for the given date were not valid

                # add point coordinates to list of results for this pass
                res_x.append(lap_sector3_point.x)
                res_y.append(lap_sector3_point.y)

        return {'x': res_x, 'y': res_y}

    def generate_results(self, data, test_point):
        # process results
        x_series = pd.Series(data['x'])
        y_series = pd.Series(data['y'])

        result = {
            'mean_x': x_series.mean(),
            'mean_y': y_series.mean(),
            'mad_x': x_series.mad(),
            'mad_y': y_series.mad(),
            'tx': test_point.x,
            'ty': test_point.y
        }

        return result


class Sector12Condition(SectorBorderCondition):
    """Solver condition for constant sector1/sector2 border position.

    How this condition works:
    Subtract the last 3rd sector time and 2nd sector time from the test point.
    If the test point is the actual start finish line position, the sector border should be the same for each lap and driver.
    Basically the same as StartFinishCondition.
    """
    name = "Sector12"

    def __init__(self, *args, **kwargs):
        super().__init__()

    def for_driver(self, drv, test_point):
        """ Calculate the condition for a driver and test point.

        :param drv: The driver for which to calculate the condition (driver number as a string)
        :type drv: string
        :param test_point: Start/finish line position (test) for which to calculate the condition
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
                test_date = self._get_test_date(lap, drv, test_point)
                if not test_date:
                    continue

                # calculate start date for last sector 2 and get position for that date
                last_sector2_start = test_date - lap.Sector3Time - lap.Sector2Time
                lap_sector2_point = self.data['track'].interpolate_pos_from_time(drv, last_sector2_start)

                if not lap_sector2_point:
                    continue  # coordinates for the given date were not valid

                # add point coordinates to list of results for this pass
                res_x.append(lap_sector2_point.x)
                res_y.append(lap_sector2_point.y)

        return {'x': res_x, 'y': res_y}

    def generate_results(self, data, test_point):
        # process results
        x_series = pd.Series(data['x'])
        y_series = pd.Series(data['y'])

        result = {
            'mean_x': x_series.mean(),
            'mean_y': y_series.mean(),
            'mad_x': x_series.mad(),
            'mad_y': y_series.mad(),
            'tx': test_point.x,
            'ty': test_point.y
        }

        return result


class AllSectorBordersCondition(SectorBorderCondition):
    """Solver condition for constant sector1/sector2 border position.

    How this condition works:
    Subtract the last 3rd sector time and 2nd sector time from the test point.
    If the test point is the actual start finish line position, the sector border should be the same for each lap and driver.
    Basically the same as StartFinishCondition.
    """
    name = "AllSectors"

    def __init__(self, *args, **kwargs):
        super().__init__()

    def for_driver(self, drv, test_point):
        """ Calculate the condition for a driver and test point.

        :param drv: The driver for which to calculate the condition (driver number as a string)
        :type drv: string
        :param test_point: Start/finish line position (test) for which to calculate the condition
        :type test_point: TrackPoint
        :return: [results x, results y] where results_* is a list of values containing the results for each lap
        """
        is_drv = (self.data['laps'].Driver == drv)
        drv_last_lap = self.data['laps'][is_drv].NumberOfLaps.max()  # get the last lap of this driver

        res = {'x1': list(), 'y1': list(), 'x2': list(), 'y2': list(), 'x3': list(), 'y3': list()}

        for _, lap in self.data['laps'][is_drv].iterrows():
            # first lap, last lap, in-lap, out-lap and laps with no lap number are skipped
            if (pd.isnull(lap.NumberOfLaps) or
                    lap.NumberOfLaps in (1, drv_last_lap) or
                    not pd.isnull(lap.PitInTime) or
                    not pd.isnull(lap.PitOutTime)):

                continue

            else:
                test_date = self._get_test_date(lap, drv, test_point)
                if not test_date:
                    continue

                # sector 1/2
                last_sector2_start = test_date - lap.Sector3Time - lap.Sector2Time
                lap_sector2_point = self.data['track'].interpolate_pos_from_time(drv, last_sector2_start)
                # sector 2/3
                last_sector3_start = test_date - lap.Sector3Time
                lap_sector3_point = self.data['track'].interpolate_pos_from_time(drv, last_sector3_start)
                # start/finish
                last_lap_start = test_date - lap.LastLapTime
                lap_start_point = self.data['track'].interpolate_pos_from_time(drv, last_lap_start)

                if not (lap_sector2_point and lap_sector3_point and lap_start_point):
                    continue  # coordinates for at least one of the given dates were not valid

                # add point coordinates to list of results for this pass
                res['x1'].append(lap_start_point.x)
                res['y1'].append(lap_start_point.y)
                res['x2'].append(lap_sector2_point.x)
                res['y2'].append(lap_sector2_point.y)
                res['x3'].append(lap_sector3_point.x)
                res['y3'].append(lap_sector3_point.y)

        return res

    def generate_results(self, data, test_point):
        # process results
        x1_series = pd.Series(data['x1'])
        y1_series = pd.Series(data['y1'])
        x2_series = pd.Series(data['x2'])
        y2_series = pd.Series(data['y2'])
        x3_series = pd.Series(data['x3'])
        y3_series = pd.Series(data['y3'])

        result = {
            'mean_x1': x1_series.mean(),
            'mean_y1': y1_series.mean(),
            'mad_x1': x1_series.mad(),
            'mad_y1': y1_series.mad(),
            'mean_x2': x2_series.mean(),
            'mean_y2': y2_series.mean(),
            'mad_x2': x2_series.mad(),
            'mad_y2': y2_series.mad(),
            'mean_x3': x3_series.mean(),
            'mean_y3': y3_series.mean(),
            'mad_x3': x3_series.mad(),
            'mad_y3': y3_series.mad(),
            'tx': test_point.x,
            'ty': test_point.y
        }

        return result
