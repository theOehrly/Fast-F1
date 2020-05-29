from unittest import TestCase
from experimental import TrackPoint, Track


class TestTrackGetPointsBetween(TestCase):
    def __init__(self, *args):
        super().__init__(*args)
        mod_track = Track  # Track for all get_points_between tests
        mod_track._unsorted_points_from_pos_data = lambda *nothing: None  # disable this function
        self.track = mod_track(dict())  # don't pass any position data for this test
        self.a = TrackPoint(1, 1)
        self.b = TrackPoint(2, 2)
        self.c = TrackPoint(3, 3)
        self.d = TrackPoint(4, 4)
        self.e = TrackPoint(5, 5)
        self.f = TrackPoint(6, 6)
        self.g = TrackPoint(7, 7)

        self.track.sorted_points = [self.a, self.b, self.c, self.d, self.e, self.f, self.g]

    def test_get_points_between_short_ref(self):
        res = self.track.get_points_between(self.b, self.f, short=True, include_ref=True)
        self.assertEqual(res, [self.b, self.a, self.g, self.f])

    def test_get_points_between_short_noref(self):
        res = self.track.get_points_between(self.b, self.f, short=True, include_ref=False)
        self.assertEqual(res, [self.a, self.g])

    def test_get_points_between_long_ref(self):
        res = self.track.get_points_between(self.b, self.f, short=False, include_ref=True)
        self.assertEqual(res, [self.b, self.c, self.d, self.e, self.f])

    def test_get_points_between_long_noref(self):
        res = self.track.get_points_between(self.b, self.f, short=False, include_ref=False)
        self.assertEqual(res, [self.c, self.d, self.e])

    def test_get_points_between_short_ref_edge(self):
        res = self.track.get_points_between(self.e, self.g, short=True, include_ref=True)
        self.assertEqual(res, [self.e, self.f, self.g])

    def test_get_points_between_short_noref_edge(self):
        res = self.track.get_points_between(self.e, self.g, short=True, include_ref=False)
        self.assertEqual(res, [self.f, ])

    def test_get_points_between_long_ref_edge(self):
        res = self.track.get_points_between(self.e, self.g, short=False, include_ref=True)
        self.assertEqual(res, [self.e, self.d, self.c, self.b, self.a, self.g])

    def test_get_points_between_long_noref_edge(self):
        res = self.track.get_points_between(self.e, self.g, short=False, include_ref=False)
        self.assertEqual(res, [self.d, self.c, self.b, self.a])
