from fastf1.func import min_index
from matplotlib import pyplot as plt
import pandas as pd
from math import sqrt

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


class Track:
    # TODO reorder points when start finish line position is known
    """Track position related data processing.

    The unit (if any) of F1's coordinate system is unknown to me. Approx.: value / 3,61 = value in meters

    Although there are more than one hundred thousand points of position data per session, the number of
    unique points on track is limited. Typically there is about one unique point per meter of track length.
    This does not mean that the points have a fixed distance though. In slow corners they are closer together than
    on straights. A typical track has between 5000 and 7000 unique points.
    When generating the track map, all duplicate points are removed from the raw data so that only unique points are left.
    Then those points are sorted into the correct order.
    Not all unique points of a given track are necessarily present in each session. There is simply a chance that position
    data from no car is ever sent from a point. In this case we can't know that this point exist.
    This is not a problem, but the following needs to be kept in mind:

    The track class and its track map are only a valid representation of the data they were calculated from.
    E.g. do not use a track map for race data when it was calculated from qualifying data.

    Sharing a track map between multiple sessions may be possible if the all points from all of these
    sessions where joined before and the track map was therefore calculated from both sessions at the same time.
    Although this may be possible, it is neither tested, nor intended, recommended or implemented (yet). If consistency
    of position data between sessions can be validated, this might be a way of getting more data and thereby increased accuracy of
    some statistically computed values.
    """

    def __init__(self, pos_frame):
        """Create a new track map object.

        :param pos_frame: Dictionary containing a pandas.DataFrame with position data per car (as returned by fastf1.api.position)
        :type pos_frame: dict
        """

        self._pos_data = pos_frame

        self.unsorted_points = list()
        self.sorted_points = list()
        self.excluded_points = list()

        self.sorted_x = list()  # list of sorted coordinates for easy plotting and lazy coordinate validation
        self.sorted_y = list()

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
        """Extract all unique track points from the position data."""
        # get all driver numbers
        drivers = list(self._pos_data.keys())

        # create a combined data frame with all column names but without data; use the data of the first driver to get the column names
        combined = pd.DataFrame(columns=[*self._pos_data[drivers[0]].columns])

        # add the data of all drivers
        for n in drivers:
            combined = combined.append(self._pos_data[n])

        # filter out data points where the car is not on track
        is_on_track = combined['Status'] == 'OnTrack'
        combined = combined[is_on_track]

        # filter out anything but X and Y coordinates and drop duplicate values
        no_dupl_combined = combined.filter(items=('X', 'Y')).drop_duplicates()

        # create a point object for each point
        for index, data in no_dupl_combined.iterrows():
            self.unsorted_points.append(TrackPoint(data['X'], data['Y']))

    def _init_viusualization(self):
        """Initiate the plot for visualizing the progress of sorting the track points."""
        self._vis_counter = 0
        plt.ion()
        self._fig = plt.figure()
        self._ax = self._fig.add_subplot(111)
        self._ax.axis('equal')
        self._line2, = self._ax.plot((), (), 'r-')
        self._line1, = self._ax.plot((), (), 'b-')

    def _cleanup_visualization(self):
        """Clean up the sorting visualization plot and 'reset' matplotlib so following plots are not influenced."""
        if self._fig:
            plt.close()
            plt.ioff()
            plt.clf()
            self._fig = None

    def _visualize_sorting_progress(self):
        """Visualize the current progress of sorting of the track points.

        Updates the plot with the current data. The plot is created first if this is
        the first call to this function.
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
        # TODO this is currently not implemented; need start/finish line position and direction. Maybe then save results per point in point object
        self.distances.append(0)  # distance is obviously zero at the starting point

        distance_covered = 0  # distance since first point

        for i in range(1, len(self.sorted_points)):
            # calculate the length of the segment between the last and the current point
            segment_length = sqrt(self.sorted_points[i-1].get_sqr_dist(self.sorted_points[i]))
            distance_covered += segment_length
            self.distances.append(distance_covered)

        for dist in self.distances:
            self.distances_normalized.append(dist / self.distances[-1])

    def _determine_track_direction(self):
        """Check if the track direction is correct and if not reverse the list of sorted points to correct it.

        This is done by getting two arbitrary points from the position (telemetry) data. Then it is checked that the first
        of these two points is also first in the list of sorted points. If not, the list is reversed.
        """
        drivers = list(self._pos_data.keys())
        n = 0
        while True:
            drv = drivers[n]  # select a driver
            on_track = self._pos_data[drv][self._pos_data[drv].Status == "OnTrack"]  # use 2nd lap as a sample lap

            if on_track.empty:
                n += 1  # this driver was never on track; try the next driver
                continue

            try:
                p1 = on_track.iloc[100]  # get two points; doesn't really matter which points are used
                p2 = on_track.iloc[101]
            except IndexError:
                n += 1  # driver wasn't on track very long apparently; try the next driver
                continue

            point1 = self.get_closest_point(TrackPoint(p1.X, p1.Y))  # the resulting point will have the same coordinates but the exact instance
            point2 = self.get_closest_point(TrackPoint(p2.X, p2.Y))  # is required to get its index in the next step

            idx1 = self.sorted_points.index(point1)
            idx2 = self.sorted_points.index(point2)

            if idx1 > idx2 and not (idx1 - idx2) > 0.9 * len(self.sorted_points):
                # first part of this check: The point with the higher index is the one which is later in the lap. This should be the second point.
                #                           If this is not the case, the list needs to be reversed.
                # second part: The exception is, if the list divides the track between these two points. In this case the first point would have
                #               a higher index because it right at the end of the list while the second point is at the beginning. In case that
                #               more than 90% of the list are between these two points this edge case is assumed. The list will not be reversed.
                self.sorted_points.reverse()

            break

    def _sort_points(self):
        """Does the actual sorting of points."""
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
        else:
            self.excluded_points.append(self._next_point)

        self._cleanup_visualization()

    def generate_track(self, visualization_frequency=0):
        """Generate a track map from the raw points.

        Sorts all points. Then determines the correct direction and starting point (both not implemented yet).
        Finally the lap distance is calculated by integrating over all points (implemented partially, not enabled, depending on previous).
        The distance since start is saved for each point. Additionally, the lap distance is saved normalized to a range of 0 to 1.
        :param visualization_frequency: (optional) specify  after how many calculated points the plot should be updated.
            Set to zero for never (default: never). Plotting is somewhat slow. A visualization frequency greater than 50 is recommended.
        :type visualization_frequency: int
        """
        self._vis_freq = visualization_frequency

        self._sort_points()
        self._determine_track_direction()

        for point in self.sorted_points:
            self.sorted_x.append(point.x)
            self.sorted_y.append(point.y)

        # self._integrate_distance()  # TODO this should not be done before determining track direction and start/finish line position

        # xvals = list()  # TODO rethink this
        # yvals = list()
        # for point in self.sorted_points:
        #     xvals.append(point.x)
        #     yvals.append(point.y)
        #
        # self.track = pd.DataFrame({'X': xvals,
        #                            'Y': yvals,
        #                            'Distance': self.distances,
        #                            'Normalized': self.distances_normalized})

    def lazy_is_track_point(self, x, y):
        """Lazy check for whether two coordinates are the coordinates of a unique track point.

        This function only checks both coordinates independently. But it does not verify that the
        combination of both coordinates is a valid unique track point (therefore "lazy" check).
        This is an intentional measure for saving time.
        """
        if x in self.sorted_x and y in self.sorted_y:
            return True
        return False

    def direction_to_point(self, ref_point, other, rel_max=0.49):
        """Check if a point is behind or in front of a reference point on track.

        Do not use this function in long iterations as it is comparably slow!

        :param ref_point: The reference point
        :type ref_point: TrackPoint
        :param other: The second point
        :type other: TrackPoint
        :param rel_max: (optional) maximum relative distance on track for checking if the point is before or after.
            If a value is more than this relative distance away zero is returned. Distance is measured in points here which is
            exactly equal to actual distance here.
            This value needs to be 0.49 or smaller. (Default is 0.49)
        :return: -1 -> behind; 1 -> in front; 0 -> outside of max relative distance or could not be determined
        """
        ref_u = self.get_closest_point(ref_point)  # get the closest unique track points
        other_u = self.get_closest_point(other)

        ref_i = self.sorted_points.index(ref_u)  # get the indices for the unique points
        other_i = self.sorted_points.index(other_u)
        delta_i = other_i - ref_i

        if delta_i < -(1 - rel_max) * len(self.sorted_points):
            return 1  # edge case; point is before but the end of the list is in between

        if abs(delta_i) > rel_max*len(self.sorted_points):
            return 0  # point is too far away

        if delta_i > 0:
            return 1  # point is in front

        elif delta_i < 0:
            return -1  # point is behind

        else:
            # point is so close that the unique points are the same
            # check based on vector direction from point to point; for very short distances (like here) this is a sufficient criteria.
            # For longer distances this is not even a necessary criteria though!
            dx_q = other.x - ref_point.x  # (dx_q, dy_q) form the vector from ref to other (q for query)
            dy_q = other.y - ref_point.y

            if ref_i + 1 < len(self.sorted_points):  # get the next point (with edge case handling for current point is last point in list)
                next_u = self.sorted_points[ref_i + 1]
            else:
                next_u = self.sorted_points[0]

            dx_t = next_u.x - ref_u.x  # (dx_t, dy_t) form the vector from unique ref to next on track (t for track)
            dy_t = next_u.y - ref_u.y

            # test if the vectors point in the same direction by calculating the dot product
            # the dot product is greater than zero if the angle between the vectors is less than 90 degree
            dp = dx_q * dx_t + dy_q * dy_t
            if dp > 0:
                return 1
            elif dp < 0:
                return -1
            else:
                return 0

    def get_closest_point(self, point):
        """Find the closest unique track point to any given point.

        'point' can be an arbitrary point anywhere. If 'point' is one of the unique track points
        the same point will be returned as no point is closer to it than itself.

        This function assumes that the track is made up of all possible points.
        This assumption is valid within the scope of the data from which the track was calculated.
        See disclaimer for track map class in general

        :param point: A point with arbitrary coordinates
        :type point: TrackPoint
        :return: A single TrackPoint
        """

        distances = list()
        for track_point in self.sorted_points:
            distances.append(track_point.get_sqr_dist(point))

        return self.sorted_points[distances.index(min(distances))]

    def get_points_between(self, point1, point2, short=True, include_ref=True):
        """Returns all unique track points between two points.

        'point1' and 'point2' must be unique track points. The cannot be points with random coordinates.
        If you want to use any given point, call .get_closest_point() first to get the unique track point
        which is closest to your point. You can then pass it as reference point to this function.

        :param point1: First boundary point
        :type point1: TrackPoint
        :param point2: Second boundary point
        :type point2: TrackPoint
        :param short: Whether you want to have the result going the long or the short distance between the boundary points.
        :param include_ref: Whether to include the given boundary points in the returned list of points
        :return: List of TrackPoints
        """

        i1 = self.sorted_points.index(point1)
        i2 = self.sorted_points.index(point2)

        if abs(i1 - i2) < 0.5 * len(self.sorted_points):
            short_is_inner = True
        else:
            short_is_inner = False

        if (short and short_is_inner) or (not short and not short_is_inner):
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
            # the harder way; we need the first and last part of the list but not the middle
            first = self.sorted_points[:min(i1, i2)]
            second = self.sorted_points[max(i1, i2)+1:]

            # add the reference points correctly
            # also reverse if necessary to keep a consistent returned order. the first reference point should also be first in the result
            if i1 > i2:
                if include_ref:
                    second.insert(0, point1)
                    first.append(point2)
                pnt_range = second + first
            else:
                if include_ref:
                    second.insert(0, point2)
                    first.append(point1)
                pnt_range = second + first
                pnt_range.reverse()

        return pnt_range

    def get_second_coord(self, val, ref_point_1, ref_point_2, from_coord='x'):
        """Calculate the second coordinate if either x or y are known.

        The known coordinate does not need to be the coordinate of a unique track point. The result
        will be interpolated.
        This requires two reference points between which the point your interested in is located.
        This is somewhat unstable. If the range between the two points is to long, there might be
        multiple possible results for your value. In this case this function will fail silently!
        One of the results will be returned.
        The track between the two given points should be approximtely straight for this function to
        work correctly. If the value you're interested in is in a corner, the corner segment between
        ref_point_1 and ref_point_2 should be sufficiently short.
        The reference points need to be unique track points.

        :param val: known x or y coordinate
        :type val: int or float
        :param ref_point_1: First boundary point
        :type ref_point_1: TrackPoint
        :param ref_point_2: Second boundary point
        :type ref_point_2: TrackPoint
        :param from_coord: Specify whether the given value is the x or y coordinate; one of 'x', 'y'
        :type from_coord: str
        :return: TrackPoint
        """
        p_range = self.get_points_between(ref_point_1, ref_point_2)

        # find the closest point in this range; only valid if the range is approximately straight
        # because we're only checking against one coordinate
        distances = list()
        for p in p_range:
            distances.append(abs(p[from_coord] - val))

        min_i = min_index(distances)
        p_a = p_range[min_index(distances)]  # closest point
        # second closest point (with edge cases if closest point is first or last point in list)
        # This works because the points returned by get_points_between() are sorted. The second
        # closest point therefore needs to be the one before or after the closest point.
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

    def get_time_from_pos(self, drv, point, time_range_start, time_range_end):
        """Calculate the time at which a driver was at a specific coordinate.

        The point can be any point. It does not need to be a unique track point.
        A time range needs to be specified because of course a driver passes all parts of the track
        once every lap (surprise there...). The specified time range should therefore be no longer
        than one lap so that there are not multiple possible solutions.
        But shorter is faster in terms of calculating the result. So keep it as short as possible.
        :param drv: Number of the driver as a string
        :type drv: str
        :param point: The point you're interested in
        :type point: TrackPoint
        :param time_range_start: A pandas.Timestamp compatible date
        :param time_range_end: A pandas.Timestamp compatible date
        :return: pandas.Timestamp or None
        """
        drv_pos = self._pos_data[drv]  # get DataFrame for driver

        # calculate closest point in DataFrame (a track map contains all points from the DataFrame)
        closest_track_pnt = self.get_closest_point(point)

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

        return None

    def interpolate_pos_from_time(self, drv, query_date):
        """Calculate the position of a driver at any given date.

        :param drv: The number of the driver as a string
        :type drv: str
        :param query_date: The date you're interested in (pandas.Timestamp compatible)
        :return: TrackPoint
        """
        # use linear interpolation to determine position at arbitrary time
        drv_pos = self._pos_data[drv]  # get DataFrame for driver

        closest = drv_pos.iloc[(drv_pos['Date'] - query_date).abs().argsort()[:2]]

        # verify both points are valid unique track points
        if not (self.lazy_is_track_point(closest.iloc[0]['X'], closest.iloc[0]['Y']) and
                self.lazy_is_track_point(closest.iloc[1]['X'], closest.iloc[1]['Y'])):

            return None

        delta_t = closest.iloc[1]['Date'] - closest.iloc[0]['Date']
        delta_x = closest.iloc[1]['X'] - closest.iloc[0]['X']
        delta_y = closest.iloc[1]['Y'] - closest.iloc[0]['Y']
        interp_delta_t = query_date - closest.iloc[0]['Date']

        interp_x = closest.iloc[0]['X'] + delta_x * interp_delta_t / delta_t
        interp_y = closest.iloc[0]['Y'] + delta_y * interp_delta_t / delta_t

        return TrackPoint(interp_x, interp_y)
