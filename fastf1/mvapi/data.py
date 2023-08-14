import fastf1.core
from fastf1.mvapi.internals import _logger
from fastf1.mvapi.api import get_circuit

from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd


@dataclass
class CircuitInfo:
    """Holds information about the circuit that is useful for visualizing and
    annotating data.

    ``corners``, ``marshal_lights`` and ``marshal_sectors`` are track markers
    that all use a similar DataFrame format.
    Each set of these track markers has the following DataFrame columns:

        Columns: ``X <float>, Y <float>, Number <int>, Letter <str>,
        Angle <float>, Distance <float>``

        - ``X`` and ``Y`` specify the position on the track map
        - ``Number`` is the number of the corner. ``Letter`` is optionally used
          to differentiate corners with the same number on some circuits,
          e.g. "2A".
        - ``Angle`` is an angle in degrees, used to visually offset the
          marker's placement on a track map in a logical direction (usually
          orthogonal to the track).
        - ``Distance`` is the location of the marker as a distance from the
          start/finish line. This value needs to be computed using car
          telemetry as a reference. It will therefore only be available,
          if telemetry data is loaded.

    .. note:: This data has been manually created and is not highly accurate
        but sufficient for visualization. A big thanks to MultiViewer
        (https://multiviewer.app/) for providing this data to FastF1.
    """

    corners: pd.DataFrame
    """Location of corners.

    (DataFrame format described above)
    """

    marshal_lights: pd.DataFrame
    """Location of marshal lights.

    (DataFrame format described above)
    """

    marshal_sectors: pd.DataFrame
    """Location of marshal sectors.

    (DataFrame format described above)
    """

    rotation: float
    """Rotation of the circuit in degrees. This can be used to rotate the
    coordinate system of the telemetry (position) data to match the orientation
    of the official track map.
    """

    def add_marker_distance(self, reference_lap: "fastf1.core.Lap"):
        """:meta private:
        Computes the 'Distance' value for each track marker using the
        telemetry data of a provided reference lap.

        The distance values are computed using a best-fit approach by selecting
        the distance value of a telemetry sample, where the squared error of
        the xy-coordinates between telemetry data and track marker position
        is minimal."""

        # get merged reference telemetry and limit to data source 'pos' so that
        # only position values are used that are not interpolated
        try:
            tel = reference_lap.get_telemetry()
        except fastf1.core.DataNotLoadedError:
            _logger.warning("Failed to generate marker distance information: "
                            "telemetry data has not been loaded")
            return

        if tel.empty:
            _logger.warning("Failed to generate marker distance information: "
                            "telemetry data is empty")
            return

        tel = tel[tel['Source'] == 'pos']
        # create a numpy array of xy track coordinates
        xy_ref_array = tel.loc[:, ('X', 'Y')].to_numpy()

        for df in (self.corners, self.marshal_sectors, self.marshal_lights):
            # create a numpy array of xy marker arrays
            marker_xy_array = df.loc[:, ('X', 'Y')].to_numpy()

            n_markers = marker_xy_array.shape[0]

            # create an array of xy track coordinates with an additional
            # dimension that has the size of the number of markers
            xy_array = xy_ref_array \
                .reshape((1, -1, 2)) \
                .repeat(n_markers, axis=0)

            # subtract each marker position from a full set of track
            # coordinates and calculate the squared xy error
            diff = xy_array - marker_xy_array.reshape((-1, 1, 2))
            e = diff[..., 0] ** 2 + diff[..., 1] ** 2

            # return the index in the track coordinates at which the squared
            # error is minimal for each marker
            indices = np.nanargmin(e, axis=1)

            # get the best distance value for each marker from the telemetry
            # data and add them to the marker data frame
            distances = tel.iloc[indices]['Distance'].to_list()
            df['Distance'] = distances


def get_circuit_info(*, year: int, circuit_key: int) -> Optional[CircuitInfo]:
    """:meta private:
    Load circuit information from the MultiViewer API and convert it into
    as :class:``SessionInfo`` object.

    Args:
        year: The championship year
        circuit_key: The unique circuit key (defined by the F1 livetiming API)
    """
    data = get_circuit(year=year, circuit_key=circuit_key)

    if not data:
        _logger.warning("Failed to load circuit info")
        return None

    ret = list()
    for cat in ('corners', 'marshalLights', 'marshalSectors'):
        rows = list()
        for entry in data[cat]:
            rows.append((
                float(entry.get('trackPosition', {}).get('x', 0.0)),
                float(entry.get('trackPosition', {}).get('y', 0.0)),
                int(entry.get('number', 0)),
                str(entry.get('letter', "")),
                float(entry.get('angle', 0.0)),
                np.nan
            ))
        ret.append(
            pd.DataFrame(
                rows,
                columns=['X', 'Y', 'Number', 'Letter', 'Angle', 'Distance']
            )
        )

    rotation = float(data.get('rotation', 0.0))

    circuit_info = CircuitInfo(
        corners=ret[0],
        marshal_lights=ret[1],
        marshal_sectors=ret[2],
        rotation=rotation
    )

    return circuit_info
