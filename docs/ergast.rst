Ergast API Interface - :mod:`fastf1.ergast`
===========================================

.. currentmodule::
  fastf1.ergast

Introduction
------------

This module can be used to interface with the Ergast F1 API
(https://ergast.com/mrd/). All Ergast endpoints are supported.

The :class:`Ergast` object provides access to all API Endpoints of the
Ergast API.

The terms of use of Ergast apply (https://ergast.com/mrd/terms/).
Especially take care not to exceed the specified rate limits.

FastF1 will handle caching and it will try to enforce rate limits where
possible. Make sure to know what limits apply. For more information on
caching and rate limiting see :ref:`requests-and-caching`.

Response Types
..............

Data can be returned in two different formats:

**Raw Response**

.. autosummary::
   :nosignatures:

   ~interface.ErgastRawResponse

This format is a JSON-like representation of the original JSON data (using
``json.load``).

**Flattened into Pandas DataFrames**

.. autosummary::
   :nosignatures:

   ~interface.ErgastSimpleResponse
   ~interface.ErgastMultiResponse

The complexity of the data that is returned by the API endpoint determines
the exact response type. The return type is documented for each endpoint.

An :class:`~fastf1.ergast.interface.ErgastSimpleResponse` wraps a Pandas
``DataFrame`` directly.

An :class:`~fastf1.ergast.interface.ErgastMultiResponse` consists of a
descriptive ``DataFrame``
(:attr:`~fastf1.ergast.interface.ErgastMultiResponse.description`)
and a list of ``DataFrames`` that contain the main content of the response
(:attr:`~fastf1.ergast.interface.ErgastMultiResponse.content`).


General Options
...............

The following arguments are available as default values on :class:`Ergast` or
individually for each endpoint method:

    - ``result_type`` ('raw' or 'pandas'): Select between RAW responses or
        Pandas DataFrame responses.

    - ``auto_cast`` (`bool`): Select whether all values are automatically
        cast from their default string representation to the most appropriate
        data type.

    - ``limit`` (`int`): Set the limit for the maximum number of results that
        are returned in one request. The server default (30 results) applies
        if this value is not set. The maximum allowed value is 1000 results.


Examples
........

First, import :class:`~fastf1.ergast.Ergast` and create and interface with
all default arguments.

.. doctest::

    >>> from fastf1.ergast import Ergast
    >>> ergast = Ergast()

Now, get information about all circuits that hosted a Grand Prix in 2022.
This is an endpoint that returns an
:class:`~fastf1.ergast.interface.ErgastSimpleResponse`, meaning one single
DataFrame.


.. doctest::

    >>> response_frame = ergast.get_circuits(season=2022)
    >>> response_frame
            circuitId  ...       country
    0     albert_park  ...     Australia
    1        americas  ...           USA
    2         bahrain  ...       Bahrain
    ...
    19     villeneuve  ...        Canada
    20     yas_marina  ...           UAE
    21      zandvoort  ...   Netherlands
    <BLANKLINE>
    [22 rows x 7 columns]

To get the raw data instead of the DataFrame response, specify the return type
as 'raw':

.. doctest::

  >>> ergast.get_circuits(season=2022, result_type='raw')  # doctest: +NORMALIZE_WHITESPACE
  [{'circuitId': 'albert_park',
    'url': 'http://en.wikipedia.org/wiki/Melbourne_Grand_Prix_Circuit',
    'circuitName': 'Albert Park Grand Prix Circuit',
    'Location': {'lat': -37.8497,
                 'long': 144.968,
                 'locality': 'Melbourne',
                 'country': 'Australia'}},
  ...]

Note that in the response DataFrame some keys are renamed from the raw response
so that all column names are unique when flattening more complex responses.
Compare the column names from the result frame with the raw response above and
note that 'url' has changed to 'circuitUrl'. This is because other responses
include a 'constructorUrl' and a 'driverUrl', for example.

.. doctest::

  >>> response_frame.columns
  Index(['circuitId', 'circuitUrl', 'circuitName', 'lat', 'long', 'locality',
         'country'],
        dtype='object')

Also note, that by default all values will automatically be cast to the most
suitable data type. Ergast itself does provide all values as string, though.
Automatic type casting can be very useful because most of the time it will
make it easier to work with the data. But it is possible to disable automatic
type casting by setting ``auto_cast=False``. For example, by default auto
casting is enabled and *'lat'* and *'long'* will be cast to ``float``,

.. doctest::

  >>> ergast.get_circuits(season=2022, result_type='raw')[0]['Location']
  {'lat': -37.8497, 'long': 144.968, 'locality': 'Melbourne', 'country': 'Australia'}

but with ``auto_cast=False`` both values remain ``str``.

.. doctest::

  >>> ergast.get_circuits(season=2022, result_type='raw', auto_cast=False)[0]['Location']
  {'lat': '-37.8497', 'long': '144.968', 'locality': 'Melbourne', 'country': 'Australia'}

The documentation for each API endpoint will include an "API Mapping" that
shows the structure of the raw response, the updated key names for flattening
and the data types for automatic type casting. Additionally, there is be a
"DataFrame Description" that shows which column names will be present in the
result frame. This way it easy to see which keys are renamed.
Additionally, both the "API Mapping" and the "DataFrame Description" will
show the data type to which a value is cast when ``auto_cast=True``.

Also, there are API endpoints that return more complex responses. When 'pandas'
is selected as response type, these endpoints return a
:class:`~fastf1.ergast.interface.ErgastMultiResponse`. One such endpoint is
the constructor standings endpoint.

.. doctest::

  >>> standings = ergast.get_constructor_standings()

Called without any 'season' specifier, it returns standings for multiple
seasons. An overview over the returned data is available as a ``.description``
of the response:

.. doctest::

  >>> standings.description
     season  round
  0    1958     11
  1    1959      9
  2    1960     10


Due to the maximum number of returned results being limited, only data for
three seasons is returned, as can be seen.

The actual standings information is available in separate DataFrames for
each season. These can be accessed as ``.content`` of the response.
The first element in ``.content`` is associated with the first row of the
``.description`` and so on.

.. doctest::

  >>> standings.content[0]
     position positionText  ...  constructorName  constructorNationality
  0         1            1  ...          Vanwall                 British
  1         2            2  ...          Ferrari                 Italian
  ...
  7         8            8  ...        Connaught                 British
  8         9            9  ...             OSCA                 Italian
  <BLANKLINE>
  [9 rows x 8 columns]

All Ergast response objects inherit from
:class:`~fastf1.ergast.interface.ErgastResultMixin`. This object provides
support for pagination on all response objects. Ergast uses pagination
to serve results for specific requests on multiple 'pages' when the response
exceeds the limit for the maximum number of results.

For example, when limiting the sesason list to three results, Ergast
responds with:

.. doctest::

  >>> seasons = ergast.get_seasons(limit=3)
  >>> seasons
     season                                          seasonUrl
  0    1950  http://en.wikipedia.org/wiki/1950_Formula_One_...
  1    1951  http://en.wikipedia.org/wiki/1951_Formula_One_...
  2    1952  http://en.wikipedia.org/wiki/1952_Formula_One_...

It is possible to check whether a response contains all results and to obtain
the total number of results:

.. doctest::

  >>> seasons.is_complete
  False
  >>> seasons.total_results # doctest: +SKIP
  74

Now, the builtin pagination can be used to obtain the next result page. The
same limit as before is used.

.. doctest::

  >>> seasons.get_next_result_page()
     season                                          seasonUrl
  0    1953  http://en.wikipedia.org/wiki/1953_Formula_One_...
  1    1954  http://en.wikipedia.org/wiki/1954_Formula_One_...
  2    1955  http://en.wikipedia.org/wiki/1955_Formula_One_...

It is also possible to manually specify an offset into the dataset:

.. doctest::

  >>> ergast.get_seasons(limit=3, offset=6)
     season                                          seasonUrl
  0    1956  http://en.wikipedia.org/wiki/1956_Formula_One_...
  1    1957  http://en.wikipedia.org/wiki/1957_Formula_One_...
  2    1958  http://en.wikipedia.org/wiki/1958_Formula_One_...


API Reference
-------------

Main Interface
..............


.. autoclass:: Ergast
    :members:


Response Objects
................

.. autoclass:: fastf1.ergast.interface.ErgastRawResponse
    :members:

.. autoclass:: fastf1.ergast.interface.ErgastSimpleResponse
    :members:

.. autoclass:: fastf1.ergast.interface.ErgastMultiResponse
    :members:

.. autoclass:: fastf1.ergast.interface.ErgastResultFrame
    :members:

.. autoclass:: fastf1.ergast.interface.ErgastResponseMixin
    :members:


Exceptions
..........

.. autoclass:: fastf1.ergast.interface.ErgastError

.. autoclass:: fastf1.ergast.interface.ErgastJsonError

.. autoclass:: fastf1.ergast.interface.ErgastInvalidRequestError
