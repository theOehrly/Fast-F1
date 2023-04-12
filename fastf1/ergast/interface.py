import copy
import json
from typing import List, Literal, Optional, Union

from fastf1.req import Cache
import fastf1.ergast.structure as API
from fastf1.version import __version__


import pandas as pd


BASE_URL = 'https://ergast.com/api/f1'
HEADERS = {'User-Agent': f'FastF1/{__version__}'}


class ErgastResponseMixin:
    """A Mixin class that adds support for pagination to Ergast response
    objects.

    All Ergast response objects provide the methods that are implemented by
    this Mixin.
    """
    _internal_names = ['_response_headers', '_query_filters',
                       '_query_metadata', '_selectors']

    def __init__(self, *args, response_headers: dict, query_filters: dict,
                 metadata: dict, selectors: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self._response_headers = response_headers
        self._query_filters = query_filters
        self._query_metadata = metadata
        self._selectors = selectors

    @property
    def _ergast_constructor(self) -> object:
        return Ergast

    @property
    def total_results(self) -> int:
        """Returns the total number of available results for the request
        associated with this response."""
        return int(self._response_headers.get("total", 0))

    @property
    def is_complete(self) -> bool:
        """Indicates if the response contains all available results for the
        request that is associated with it."""
        # if offset is non-zero, data is missing at the beginning
        if int(self._response_headers.get('offset', 0)) != 0:
            return False

        # can only be complete if limit >= total
        return (int(self._response_headers.get("limit", 0))
                >= int(self._response_headers.get("total", 0)))

    def get_next_result_page(self) -> Union['ErgastSimpleResponse',
                                            'ErgastMultiResponse',
                                            'ErgastRawResponse']:
        """Returns the next page of results within the limit that was specified
        in the request that is associated with this response.

        Raises:
            ValueError: there is no result page after the current page
        """
        n_last = (int(self._response_headers.get("offset", 0))
                  + int(self._response_headers.get("limit", 0)))

        if n_last >= int(self._response_headers.get("total", 0)):
            raise ValueError("No more data after this response.")

        return self._ergast_constructor()._build_default_result(  # noqa: access to builtin
            **self._query_metadata,
            selectors=self._selectors,
            limit=int(self._response_headers.get("limit")),
            offset=n_last
        )

    def get_prev_result_page(self) -> Union['ErgastSimpleResponse',
                                            'ErgastMultiResponse',
                                            'ErgastRawResponse']:
        """Returns the previous page of results within the limit that was
        specified in the request that is associated with this response.

        Raises:
            ValueError: there is no result page before the current page
        """
        n_first = int(self._response_headers.get("offset", 0))

        if n_first <= 0:
            raise ValueError("No more data before this response.")

        limit = int(self._response_headers.get("limit", 0))
        new_offset = max(n_first - limit, 0)

        return self._ergast_constructor()._build_default_result(  # noqa: access to builtin
            **self._query_metadata,
            selectors=self._selectors,
            limit=int(self._response_headers.get("limit")),
            offset=new_offset
        )


class ErgastResultFrame(pd.DataFrame):
    """
    Wraps a Pandas ``DataFrame``. Additionally, this class can be
    initialized from Ergast response data with automatic flattening and type
    casting of the data.

    Args:
        data: Passed through to the DataFrame constructor (must be None if
            `response` is provided)
        category: Reference to a category from :mod:`fastf1.ergast.structure`
            that describes the result data
        response: JSON-like response data from Ergast; used to generate `data`
            from an Ergast response (must be None if `data` is provided)
        auto_cast: Determines if values are automatically cast to the most
            appropriate data type from their original string representation
    """
    _internal_names = pd.DataFrame._internal_names + ['base_class_view']
    _internal_names_set = set(_internal_names)

    def __init__(self, data=None, *,
                 category: Optional[dict] = None,
                 response: Optional[list] = None,
                 auto_cast: bool = True,
                 **kwargs):
        if (data is not None) and (response is not None):
            raise ValueError(f"Cannot initialize {type(self)} with `data`"
                             f"and `response`.")
        if (data is None) and (response is not None):
            data = self._prepare_response(response, category, auto_cast)
        super().__init__(data, **kwargs)

    @classmethod
    def _prepare_response(cls, response: list, category: dict, cast: bool):
        data = copy.deepcopy(response)  # TODO: efficiency?
        for i in range(len(data)):
            _, data[i] = cls._flatten_element(data[i], category, cast)

        if (finalizer := category.get('finalize')) is not None:
            data = finalizer(data)

        return data

    @classmethod
    def _flatten_element(cls, nested: dict, category: dict, cast: bool):
        flat = {}

        # call the categories associated flattening method on the data
        # (operations on 'nested' and 'flat' are inplace, therefore no return)
        category['method'](nested, category, flat, cast=cast)

        # recursively step into subcategories; updated the flattened result
        # dict with the result from the renaming of the subcategory values
        for subcategory in category['sub']:
            if (subname := subcategory['name']) not in nested:
                continue
            _, subflat = cls._flatten_element(
                nested[subname], subcategory, cast
            )
            flat.update(subflat)

        return nested, flat

    @property
    def _constructor(self):
        def _new(*args, **kwargs):
            return ErgastResultFrame(*args, **kwargs).__finalize__(self)

        return _new

    @property
    def _constructor_sliced(self):
        def _new(*args, **kwargs):
            name = kwargs.get('name')
            if name and (name in self.columns):
                # vertical slice
                return pd.Series(*args, **kwargs).__finalize__(self)

            # horizontal slice
            return ErgastResultSeries(*args, **kwargs).__finalize__(self)

        return _new

    @property
    def base_class_view(self):
        """For a nicer debugging experience; can view DataFrame through
        this property in various IDEs"""
        return pd.DataFrame(self)


class ErgastResultSeries(pd.Series):
    """
    Wraps a Pandas ``Series``.

    Currently, no extra functionality is implemented.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @property
    def _constructor(self):
        def _new(*args, **kwargs):
            return ErgastResultSeries(*args, **kwargs).__finalize__(self)

        return _new


class ErgastRawResponse(ErgastResponseMixin, list):
    """
    Provides the raw JSON-like response data from Ergast.

    This class wraps a ``list`` and adds response information
    and paging (see :class:`ErgastResponseMixin`).

    This "raw" response does not actually contain the complete JSON response
    that the API provides. Instead, only the actual data part of the response
    is returned while metadata (version, query parameters, response length,
    ...) are not included. But metadata is used internally to provide
    pagination and information that are implemented by the
    :class:`ErgastResponseMixin`.

    Args:
        category: Reference to a category from :mod:`fastf1.ergast.structure`
            that describes the result data
        auto_cast: Determines if values are automatically cast to the most
            appropriate data type from their original string representation
    """
    def __init__(self, *, query_result, category, auto_cast, **kwargs):
        if auto_cast:
            query_result = self._prepare_response(query_result, category)

        super().__init__(query_result, **kwargs)

    @classmethod
    def _prepare_response(cls, query_result, category):
        # query_result is a list of json-like data. Each element in that list
        # has the same structure. Iterate over all elements and call the
        # recursive _auto_cast method to convert data types
        query_result = copy.deepcopy(query_result)  # TODO: efficiency?
        for i in range(len(query_result)):
            query_result[i] = cls._auto_cast(query_result[i], category)
        return query_result

    @classmethod
    def _auto_cast(cls, data, category):
        # convert datatypes for all known elements
        for name, mapping in category['map'].items():
            if name not in data:
                continue
            data[name] = mapping['type'](data[name])

        # recursively step into known subcategories and convert data types
        for subcategory in category['sub']:
            if (subname := subcategory['name']) not in data:
                continue
            subcast = cls._auto_cast(data[subname], subcategory)
            data[subname] = subcast

        return data


class ErgastSimpleResponse(ErgastResponseMixin, ErgastResultFrame):
    """
    Provides simple Ergast result data in the form of a Pandas ``DataFrame``.

    This class wraps an :class:`ErgastResultFrame` and adds response
    information and paging (see :class:`ErgastResponseMixin`).
    """
    _internal_names = \
        ErgastResultFrame._internal_names \
        + ErgastResponseMixin._internal_names
    _internal_names_set = set(_internal_names)


class ErgastMultiResponse(ErgastResponseMixin):
    """
    Provides complex Ergast result data in the form of multiple Pandas
    ``DataFrames``.

    This class additionally offers response information and paging
    (see :class:`ErgastResponseMixin`).

    Note: This object is usually not instantiated by the user. Instead,
    you should use one of the API endpoint methods that are provided by
    :class:`Ergast` get data from the API.

    Example:

    .. doctest::

        >>> from fastf1.ergast import Ergast
        >>> ergast = Ergast(result_type='pandas', auto_cast=True)
        >>> result = ergast.get_race_results(season=2022)

        # The description shows that the result includes data from two
        # grand prix.
        >>> result.description
           season  round  ... locality       country
        0    2022      1  ...   Sakhir       Bahrain
        1    2022      2  ...   Jeddah  Saudi Arabia
        <BLANKLINE>
        [2 rows x 13 columns]

        # As expected, ``result.content`` contains two elements, one for each
        # row of the description
        >>> len(result.content)
        2

        # The first element contains all results from the first of the two
        # grand prix.
        >>> result.content[0]
            number  position  ... fastestLapAvgSpeedUnits  fastestLapAvgSpeed
        0       16         1  ...                     kph             206.018
        1       55         2  ...                     kph             203.501
        2       44         3  ...                     kph             202.469
        ...
        17      11        18  ...                     kph             202.762
        18       1        19  ...                     kph             204.140
        19      10        20  ...                     kph             200.189
        <BLANKLINE>
        [20 rows x 26 columns]

        # The second element is incomplete and only contains the first 10
        # positions of the second Grand Prix. This is because by default,
        # every query on Ergast is limited to 30 result values. You can
        # manually change this limit for each request though.
        >>> result.content[1]
           number  position  ... fastestLapAvgSpeedUnits  fastestLapAvgSpeed
        0       1         1  ...                     kph             242.191
        1      16         2  ...                     kph             242.556
        2      55         3  ...                     kph             241.841
        ...
        7      10         8  ...                     kph             237.796
        8      20         9  ...                     kph             239.562
        9      44        10  ...                     kph             239.001
        <BLANKLINE>
        [10 rows x 26 columns]

    Args:
        response_description: Ergast response containing only the "descriptive"
            information (only data that is available in :attr:`.description`)
        response_data: A list of the "content" data that has been split from
            the Ergast response (data that is available in :attr:`.content`)
        category: A category object from :mod:`fastf1.ergast.structure`
            that defines the main category.
        subcategory: A category object from :mod:`fastf1.ergast.structure`
            that defines the subcategory which is the content data.
        auto_cast: Flag that enables or disables automatic casting from the
            original string representation to the most suitable data type.
    """
    def __init__(self, *args,
                 response_description: dict,
                 response_data: list,
                 category: dict,
                 subcategory: dict,
                 auto_cast: bool,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self._description = ErgastResultFrame(response=response_description,
                                              category=category,
                                              auto_cast=auto_cast)
        self._content = [ErgastResultFrame(response=elem,
                                           category=subcategory,
                                           auto_cast=auto_cast)
                         for elem in response_data]

    @property
    def description(self) -> ErgastResultFrame:
        """An :class:`ErgastResultFrame` that describes the data in
        :attr:`.content`.

        Each row of this :class:`ErgastResultFrame` contains the descriptive
        information for one element in :attr:`.content`.
        """
        return self._description

    @property
    def content(self) -> List[ErgastResultFrame]:
        """A ``list`` of :class:`ErgastResultFrame` that contain the main
        response data.

        Descriptive data for each :class:`ErgastResultFrame` is given in the
        corresponding row of :attr:`.description`.
        """
        return self._content


class Ergast:
    """
    The main object that acts as an interface to the Ergast API.

    For each API endpoint, there is a separate method implemented to
    request data. All methods have in common, that they can be preceded by a
    call to :func:`.select` to filter the results.

    Args:
        result_type: Determines the default type of the returned result object

            - 'raw': :class:`~interface.ErgastRawResponse`
            - 'pandas': :class:`~interface.ErgastSimpleResponse` or
              :class:`~interface.ErgastMultiResponse` depending on endpoint

        auto_cast: Determines whether result values are cast from there default
            string representation to a better matching type

        limit: The maximum number of results returned by the API. Defaults to
            30 if not set. Maximum: 1000. See also "Response Paging" on
            https://ergast.com/mrd/.
    """
    def __init__(self,
                 result_type: Literal['raw', 'pandas'] = 'pandas',
                 auto_cast: bool = True,
                 limit: Optional[int] = None):
        self._default_result_type = result_type
        self._default_auto_cast = auto_cast
        self._limit = limit

    @staticmethod
    def _build_url(
            endpoint: str,
            season: Union[Literal['current'], int] = None,
            round: Union[Literal['last'], int] = None,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            results_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            lap_number: Optional[int] = None,
            stop_number: Optional[int] = None,
            standings_position: Optional[int] = None
    ) -> str:
        selectors = list()

        if season is not None:
            selectors.append(f"/{season}")
        if round is not None:
            selectors.append(f"/{round}")
        if circuit is not None:
            selectors.append(f"/circuits/{circuit}")
        if constructor is not None:
            selectors.append(f"/constructors/{constructor}")
        if driver is not None:
            selectors.append(f"/drivers/{driver}")
        if grid_position is not None:
            selectors.append(f"/grid/{grid_position}")
        if results_position is not None:
            selectors.append(f"/results/{results_position}")
        if fastest_rank is not None:
            selectors.append(f"/fastest/{fastest_rank}")
        if status is not None:
            selectors.append(f"/status/{status}")

        # some special cases: the endpoint may also be used as selector
        # therefore, if the specifier is defined, do not add the endpoint
        # string additionally
        if standings_position is not None:
            if endpoint == 'driverStandings':
                selectors.append(f"/driverStandings/{standings_position}")
                endpoint = None
            elif endpoint == 'constructorStandings':
                selectors.append(f"/constructorStandings/{standings_position}")
                endpoint = None

        if lap_number is not None:
            selectors.append(f"/laps/{lap_number}")
            if endpoint == 'laps':
                endpoint = None

        if stop_number is not None:
            selectors.append(f"/pitstops/{stop_number}")
            if endpoint == 'pitstops':
                endpoint = None

        if endpoint is not None:
            selectors.append(f"/{endpoint}")

        return BASE_URL + "".join(selectors) + ".json"

    @classmethod
    def _get(cls, url: str, params: dict) -> Union[dict, list]:
        # request data from ergast and load the returned json data.
        r = Cache.requests_get(url, headers=HEADERS, params=params)
        if r.status_code == 200:
            try:
                return json.loads(r.content.decode('utf-8'))
            except Exception as exc:
                Cache.delete_response(url)  # don't keep a corrupted response
                raise ErgastJsonError(
                    f"Failed to parse Ergast response ({url})"
                ) from exc
        else:
            raise ErgastInvalidRequestError(
                f"Invalid request to Ergast ({url})\n"
                f"Server response: '{r.reason}'"
            )

    @classmethod
    def _build_result(
            cls, *,
            endpoint: str,
            table: str,
            category: dict,
            subcategory: Optional[dict],
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            selectors: Optional[dict] = None,
    ) -> Union[ErgastSimpleResponse,
               ErgastMultiResponse,
               ErgastRawResponse]:
        # query the Ergast database and
        # split the raw response into multiple parts, depending also on what
        # type was selected for the response data format.

        url = cls._build_url(endpoint, **selectors)
        params = {'limit': limit, 'offset': offset}

        # get response and split it into individual parts
        resp = cls._get(url, params)
        resp = resp['MRData']
        body = resp.pop(table)
        # response headers remain in response
        query_result = body.pop(category['name'])
        # query filters remain in body

        query_metadata = {'endpoint': endpoint, 'table': table,
                          'category': category, 'subcategory': subcategory,
                          'result_type': result_type, 'auto_cast': auto_cast}

        if result_type == 'raw':
            return ErgastRawResponse(
                response_headers=resp, query_filters=body,
                metadata=query_metadata, selectors=selectors,
                query_result=query_result, category=category,
                auto_cast=auto_cast
            )

        if result_type == 'pandas':
            # result element description remains in query result
            result_element_data = list()
            if subcategory is not None:
                for i in range(len(query_result)):
                    result_element_data.append(
                        query_result[i].pop(subcategory['name'])
                    )
                return ErgastMultiResponse(
                    response_headers=resp, query_filters=body,
                    metadata=query_metadata, selectors=selectors,
                    response_description=query_result,
                    response_data=result_element_data,
                    category=category, subcategory=subcategory,
                    auto_cast=auto_cast
                )
            else:
                return ErgastSimpleResponse(
                    response_headers=resp, query_filters=body,
                    metadata=query_metadata, selectors=selectors,
                    response=query_result, category=category,
                    auto_cast=auto_cast
                )

    def _build_default_result(
            self, *,
            selectors: dict,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            **kwargs
    ) -> Union[ErgastSimpleResponse,
               ErgastMultiResponse,
               ErgastRawResponse]:
        # use defaults or per-call overrides if specified
        if result_type is None:
            result_type = self._default_result_type
        if auto_cast is None:
            auto_cast = self._default_auto_cast
        if limit is None:
            limit = self._limit

        return self._build_result(
            result_type=result_type,
            auto_cast=auto_cast,
            limit=limit,
            selectors=selectors,
            **kwargs
        )

    # ### endpoints with single-result responses ###
    #
    # can be represented by a DataFrame-like object
    def get_seasons(
            self,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            results_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of seasons.

        See: https://ergast.com/mrd/methods/seasons/

        .. ergast-api-map:: Seasons
            :describe-dataframe:

        Args:
            circuit: select a circuit by its circuit id (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            results_position: select a finishing result by its position
                (default: all)
            fastest_rank: select fastest by rank number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastSimpleResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'circuit': circuit,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'results_position': results_position,
                     'fastest_rank': fastest_rank,
                     'status': status}

        return self._build_default_result(endpoint='seasons',
                                          table='SeasonTable',
                                          category=API.Seasons,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_race_schedule(
            self,
            season: Union[Literal['current'], int],
            round: Optional[Union[Literal['last'], int]] = None,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            results_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of races.

        See: https://ergast.com/mrd/methods/schedule/

        .. ergast-api-map:: Races_Schedule
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            circuit: select a circuit by its circuit id (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            results_position: select a finishing result by its position
                (default: all)
            fastest_rank: select fastest by rank number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastSimpleResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'circuit': circuit,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'results_position': results_position,
                     'fastest_rank': fastest_rank,
                     'status': status}

        return self._build_default_result(endpoint='races',
                                          table='RaceTable',
                                          category=API.Races_Schedule,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_driver_info(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            results_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of drivers.

        See: https://ergast.com/mrd/methods/drivers/

        .. ergast-api-map:: Drivers
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            circuit: select a circuit by its circuit id (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            results_position: select a finishing result by its position
                (default: all)
            fastest_rank: select fastest by rank number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastSimpleResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'circuit': circuit,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'results_position': results_position,
                     'fastest_rank': fastest_rank,
                     'status': status}

        return self._build_default_result(endpoint='drivers',
                                          table='DriverTable',
                                          category=API.Drivers,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_constructor_info(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            results_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of constructors.

        See: https://ergast.com/mrd/methods/constructors/

        .. ergast-api-map:: Constructors
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            circuit: select a circuit by its circuit id (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            results_position: select a finishing result by its position
                (default: all)
            fastest_rank: select fastest by rank number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastSimpleResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'circuit': circuit,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'results_position': results_position,
                     'fastest_rank': fastest_rank,
                     'status': status}

        return self._build_default_result(endpoint='constructors',
                                          table='ConstructorTable',
                                          category=API.Constructors,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_circuits(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            results_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of circuits.

        See: https://ergast.com/mrd/methods/circuits/

        .. ergast-api-map:: Circuits
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            results_position: select a finishing result by its position
                (default: all)
            fastest_rank: select fastest by rank number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastSimpleResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'results_position': results_position,
                     'fastest_rank': fastest_rank,
                     'status': status}

        return self._build_default_result(endpoint='circuits',
                                          table='CircuitTable',
                                          category=API.Circuits,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_finishing_status(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            results_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of finishing status codes.

        See: https://ergast.com/mrd/methods/status/

        .. ergast-api-map:: Status
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            circuit: select a circuit by its circuit id (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            results_position: select a finishing result by its position
                (default: all)
            fastest_rank: select fastest by rank number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastSimpleResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'circuit': circuit,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'results_position': results_position,
                     'fastest_rank': fastest_rank,
                     'status': status}

        return self._build_default_result(endpoint='status',
                                          table='StatusTable',
                                          category=API.Status,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    # ### endpoint with multi-result responses ###
    #
    # example: qualifying results filtered only by season will yield a
    # result for each weekend
    #
    # needs to be represented by multiple DataFrame-like objects
    def get_race_results(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get race results for one or multiple races.

        See: https://ergast.com/mrd/methods/results/

        .. ergast-api-map:: Races_RaceResults
            :subcategory: RaceResults
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            circuit: select a circuit by its circuit id (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            fastest_rank: select fastest by rank number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastMultiResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'circuit': circuit,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'fastest_rank': fastest_rank,
                     'status': status}

        return self._build_default_result(endpoint='results',
                                          table='RaceTable',
                                          category=API.Races_RaceResults,
                                          subcategory=API.RaceResults,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_qualifying_results(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            results_position: Optional[int] = None,
            fastest_rank: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get qualifying results for one or multiple qualifying sessions.

        See: https://ergast.com/mrd/methods/qualifying/

        .. ergast-api-map:: Races_QualifyingResults
            :subcategory: QualifyingResults
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            circuit: select a circuit by its circuit id (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            results_position: select a finishing result by its position
                (default: all)
            fastest_rank: select fastest by rank number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastMultiResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'circuit': circuit,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'results_position': results_position,
                     'fastest_rank': fastest_rank,
                     'status': status}

        return self._build_default_result(endpoint='qualifying',
                                          table='RaceTable',
                                          category=API.Races_QualifyingResults,
                                          subcategory=API.QualifyingResults,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_sprint_results(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            circuit: Optional[str] = None,
            constructor: Optional[str] = None,
            driver: Optional[str] = None,
            grid_position: Optional[int] = None,
            status: Optional[str] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get sprint results for one or multiple sprints.

        See: https://ergast.com/mrd/methods/sprint/

        .. ergast-api-map:: Races_SprintResults
            :subcategory: SprintResults
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            circuit: select a circuit by its circuit id (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            driver: select a driver by its driver id (default: all)
            grid_position: select a grid position by its number (default: all)
            status: select by finishing status (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastMultiResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'circuit': circuit,
                     'constructor': constructor,
                     'driver': driver,
                     'grid_position': grid_position,
                     'status': status}

        return self._build_default_result(endpoint='sprint',
                                          table='RaceTable',
                                          category=API.Races_SprintResults,
                                          subcategory=API.SprintResults,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_driver_standings(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            driver: Optional[str] = None,
            standings_position: Optional[int] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get driver standings at specific points of a season.

        See: https://ergast.com/mrd/methods/standings/

        .. ergast-api-map:: StandingsLists_Driver
            :subcategory: DriverStandings
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            driver: select a driver by its driver id (default: all)
            standings_position: select a result by position in the standings
                (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastMultiResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'driver': driver,
                     'standings_position': standings_position}

        return self._build_default_result(endpoint='driverStandings',
                                          table='StandingsTable',
                                          category=API.StandingsLists_Driver,
                                          subcategory=API.DriverStandings,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_constructor_standings(
            self,
            season: Optional[Union[Literal['current'], int]] = None,
            round: Optional[Union[Literal['last'], int]] = None,
            constructor: Optional[str] = None,
            standings_position: Optional[int] = None,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get constructor standings at specific points of a season.

        See: https://ergast.com/mrd/methods/standings/

        .. ergast-api-map:: StandingsLists_Constructor
            :subcategory: ConstructorStandings
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            constructor: select a constructor by its constructor id
                (default: all)
            standings_position: select a result by position in the standings
                (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastMultiResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'constructor': constructor,
                     'standings_position': standings_position}

        return self._build_default_result(
            endpoint='constructorStandings',
            table='StandingsTable',
            category=API.StandingsLists_Constructor,
            subcategory=API.ConstructorStandings,
            result_type=result_type,
            auto_cast=auto_cast,
            limit=limit,
            offset=offset,
            selectors=selectors
        )

    def get_lap_times(self,
                      season: Union[Literal['current'], int],
                      round: Union[Literal['last'], int],
                      lap_number: Optional[int] = None,
                      driver: Optional[str] = None,
                      result_type: Optional[Literal['pandas', 'raw']] = None,
                      auto_cast: Optional[bool] = None,
                      limit: Optional[int] = None,
                      offset: Optional[int] = None
                      ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get sprint results for one or multiple sprints.

        See: https://ergast.com/mrd/methods/laps/

        .. ergast-api-map:: Races_Laps
            :subcategory: Laps
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            lap_number: select lap times by a specific lap number
                (default: all)
            driver: select a driver by its driver id (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastMultiResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'driver': driver,
                     'lap_number': lap_number}

        return self._build_default_result(endpoint='laps',
                                          table='RaceTable',
                                          category=API.Races_Laps,
                                          subcategory=API.Laps,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)

    def get_pit_stops(self,
                      season: Union[Literal['current'], int],
                      round: Union[Literal['last'], int],
                      stop_number: Optional[int] = None,
                      lap_number: Optional[int] = None,
                      driver: Optional[str] = None,
                      result_type: Optional[Literal['pandas', 'raw']] = None,
                      auto_cast: Optional[bool] = None,
                      limit: Optional[int] = None,
                      offset: Optional[int] = None
                      ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get pit stop information for one or multiple sessions.

        See: https://ergast.com/mrd/methods/standings/

        .. ergast-api-map:: Races_PitStops
            :subcategory: PitStops
            :describe-dataframe:

        Args:
            season: select a season by its year (default: all, oldest first)
            round: select a round by its number (default: all)
            lap_number: select pit stops by a specific lap number
                (default: all)
            stop_number: select pit stops by their stop number
                (default: all)
            driver: select a driver by its driver id (default: all)
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.

        Returns:
            :class:`~interface.ErgastMultiResponse` or
            :class:`~interface.ErgastRawResponse`, depending on the
            ``result_type`` parameter
        """
        selectors = {'season': season,
                     'round': round,
                     'driver': driver,
                     'lap_number': lap_number,
                     'stop_number': stop_number}

        return self._build_default_result(endpoint='pitstops',
                                          table='RaceTable',
                                          category=API.Races_PitStops,
                                          subcategory=API.PitStops,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset,
                                          selectors=selectors)


class ErgastError(Exception):
    """Base class for Ergast API errors."""
    pass


class ErgastJsonError(ErgastError):
    """The response that was returned by the server could not be parsed."""
    pass


class ErgastInvalidRequestError(ErgastError):
    """The server rejected the request because it was invalid."""
    pass
