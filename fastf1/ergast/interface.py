import copy
import json
from typing import List, Literal, Optional, Union

from fastf1.api import Cache
import fastf1.ergast.structure as API
from fastf1.version import __version__


import pandas as pd


BASE_URL = 'https://ergast.com/api/f1'
HEADERS = {'User-Agent': f'FastF1/{__version__}'}


class ErgastResponseMixin:
    def __init__(self, *args, response_headers: dict, query_filters: dict,
                 metadata: dict, selectors: list, **kwargs):
        super().__init__(*args, **kwargs)
        self._response_headers = response_headers
        self._query_filters = query_filters
        self._metadata = metadata
        self._selectors = selectors

    @property
    def total_results(self):
        return int(self._response_headers.get("total", 0))

    @property
    def is_complete(self):
        # if offset is non-zero, data is missing at the beginning
        if int(self._response_headers.get('offset', 0)) != 0:
            return False

        # if limit is less than total, data is missing at the end
        return (int(self._response_headers.get("limit", 0))
                < int(self._response_headers.get("total", 0)))

    def get_next_result_page(self):
        n_last = (int(self._response_headers.get("offset", 0))
                  + int(self._response_headers.get("limit", 0)))

        if n_last >= int(self._response_headers.get("total", 0)):
            raise ValueError("No more data after this response.")

        return Ergast()._build_default_result(  # noqa: access to builtin
            **self._metadata,
            selectors=self._selectors,
            limit=int(self._response_headers.get("limit")),
            offset=n_last
        )

    def get_prev_result_page(self):
        n_first = int(self._response_headers.get("offset", 0))

        if n_first <= 0:
            raise ValueError("No more data before this response.")

        limit = int(self._response_headers.get("limit", 0))
        new_offset = max(n_first - limit, 0)

        return Ergast()._build_default_result(  # noqa: access to builtin
            **self._metadata,
            selectors=self._selectors,
            limit=int(self._response_headers.get("limit")),
            offset=new_offset
        )

    def get_all_results(self):
        # TODO: may need manual rate limiting; better: add in 'Ergast'
        raise NotImplementedError


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
    _internal_names = ['base_class_view']

    def __init__(self, data=None, *,
                 category: Optional[dict] = None,
                 response: Optional[dict] = None,
                 auto_cast: bool = True,
                 **kwargs):
        if (data is not None) and (response is not None):
            raise ValueError(f"Cannot initialize {type(self)} with `data`"
                             f"and `response`.")
        if (data is None) and (response is not None):
            data = self._prepare_response(response, category, auto_cast)
        super().__init__(data, **kwargs)

    @classmethod
    def _prepare_response(cls, response: dict, category: dict, cast: bool):
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
    pass


class ErgastMultiResponse(ErgastResponseMixin):
    """
    Provides complex Ergast result data in the form of multiple Pandas
    ``DataFrames``.

    This class additionally offers response information and paging
    (see :class:`ErgastResponseMixin`).

    Note: You this object is usually not instantiated by the user. Instead
    you should use one of the API endpoint methods that are provided by
    :class:`Ergast` get data from the API.

    Example:

    .. doctest::

        >>> from fastf1.ergast import Ergast
        >>> ergast = Ergast(result_type='pandas', auto_cast=True)
        >>> result = ergast.select(season=2022).get_race_results()

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
        3       63         4  ...                     kph             202.313
        4       20         5  ...                     kph             201.641
        5       77         6  ...                     kph             201.691
        6       31         7  ...                     kph             200.630
        7       22         8  ...                     kph             200.642
        8       14         9  ...                     kph             201.412
        9       24        10  ...                     kph             201.512
        10      47        11  ...                     kph             200.948
        11      18        12  ...                     kph             200.555
        12      23        13  ...                     kph             200.125
        13       3        14  ...                     kph             200.318
        14       4        15  ...                     kph             200.882
        15       6        16  ...                     kph             198.300
        16      27        17  ...                     kph             198.401
        17      11        18  ...                     kph             202.762
        18       1        19  ...                     kph             204.140
        19      10        20  ...                     kph             200.189
        <BLANKLINE>
        [20 rows x 26 columns]

        # The second element is incomplete and only contains the first 11
        # positions of the second Grand Prix. This is because by default,
        # every query on Ergast is limited to 30 result values. You can
        # manually change this limit for each request though.
        >>> result.content[1]
           number  position  ... fastestLapAvgSpeedUnits  fastestLapAvgSpeed
        0       1         1  ...                     kph             242.191
        1      16         2  ...                     kph             242.556
        2      55         3  ...                     kph             241.841
        3      11         4  ...                     kph             241.481
        4      63         5  ...                     kph             239.454
        5      31         6  ...                     kph             238.729
        6       4         7  ...                     kph             239.629
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

    Example::

        ergast = Ergast()
        ergast.get_circuits()
        # will return all circuits in the database
        ergast.select(season=2022).get_circuits()
        # will only return circuits that hosted a GP in 2022

    Args:
        result_type: Determines the default type of the returned result object

            - 'raw': :class:`ErgastRawResponse`
            - 'pandas': :class:`ErgastSimpleResponse` or
              :class:`ErgastMultiResponse` depending on endpoint

        auto_cast: Determines whether result values are cast from there default
            string representation to a better matching type

        limit: The maximum number of results returned by the API. Defaults to
            30 if not set. Maximum: 1000. See also "Response Paging",
            https://ergast.com/mrd/.
    """
    def __init__(self,
                 result_type: Literal['raw', 'pandas'] = 'raw',
                 auto_cast: bool = True,
                 limit: Optional[int] = None):
        self._selectors = []
        self._default_result_type = result_type
        self._default_auto_cast = auto_cast
        self._limit = limit

    @classmethod
    def _get(cls, url: str, params: dict) -> Union[dict, list]:
        # request data from ergast and load the returned json data.
        r = Cache.requests_get(url, headers=HEADERS, params=params)
        if r.status_code == 200:
            try:
                return json.loads(r.content.decode('utf-8'))
            except Exception as exc:
                raise ErgastJsonException(
                    f"Failed to parse Ergast response ({url})"
                ) from exc
        else:
            raise ErgastInvalidRequest(
                f"Invalid request to Ergast ({url})\n"
                f"Server response: '{r.reason}'"
            )

    @staticmethod
    def _build_url(endpoint: Optional[str] = None,
                   selectors: Optional[list] = None) -> str:
        # build url from base, selector and endpoint
        url_fragments = [BASE_URL]
        if selectors is not None:
            url_fragments.extend(selectors)
        if endpoint is not None:
            url_fragments.append(f"/{endpoint}")
        url_fragments.append(".json")
        url = ''.join(url_fragments)
        return url

    def _build_default_result(
            self, *,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            selectors: Optional[list] = None,
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
        if selectors is None:
            selectors = self._selectors

        return self._build_result(
            result_type=result_type,
            auto_cast=auto_cast,
            limit=limit,
            selectors=selectors,
            **kwargs
        )

    @classmethod
    def _build_result(
            cls, *,
            endpoint: Optional[str],
            table: str,
            category: dict,
            subcategory: Optional[dict],
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
            limit: Optional[int] = None,
            offset: Optional[int] = None,
            selectors: Optional[list] = None,
    ) -> Union[ErgastSimpleResponse,
               ErgastMultiResponse,
               ErgastRawResponse]:
        # query the Ergast database and
        # split the raw response into multiple parts, depending also on what
        # type was selected for the response data format.

        url = cls._build_url(endpoint, selectors=selectors)
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

    def select(self,
               season: Union[Literal['current'], int] = None,
               round: Union[Literal['last'], int] = None,
               circuit: Optional[str] = None,
               constructor: Optional[str] = None,
               driver: Optional[str] = None,
               grid_position: Optional[int] = None,
               results_position: Optional[int] = None,
               fastest_rank: Optional[int] = None,
               status: Optional[str] = None,
               ) -> 'Ergast':
        """
        For each endpoint, the results can be refined adding different
        criteria to the request. Multiple criteria can be used to refine a
        single request. But note that not all criteria are supported by all
        endpoints. For details, refer to the documentation of each endpoint
        on https://ergast.com/mrd.

        Args:
            season: select a season by its year
            round: select a round by its number
            circuit: select a circuit by its circuit id
            constructor: select a constructor by its constructor id
            driver: select a driver by its driver id
            grid_position: select a grid position by its number
            results_position: select a finishing result by its position
            fastest_rank: select fastest by rank number
            status: select by finishing status
        """
        if season is not None:
            self._selectors.append(f"/{season}")
        if round is not None:
            self._selectors.append(f"/{round}")
        if circuit is not None:
            self._selectors.append(f"/circuits/{circuit}")
        if constructor is not None:
            self._selectors.append(f"/constructors/{constructor}")
        if driver is not None:
            self._selectors.append(f"/drivers/{driver}")
        if grid_position is not None:
            self._selectors.append(f"/grid/{grid_position}")
        if results_position is not None:
            self._selectors.append(f"/results/{results_position}")
        if fastest_rank is not None:
            self._selectors.append(f"/fastest/{fastest_rank}")
        if status is not None:
            self._selectors.append(f"/status/{status}")

        return self

    # ### endpoints with single-result responses ###
    #
    # can be represented by a DataFrame-like object
    def get_seasons(self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='seasons',
                                          table='SeasonTable',
                                          category=API.Seasons,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_race_schedule(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='races',
                                          table='RaceTable',
                                          category=API.Races_Schedule,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_driver_info(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='drivers',
                                          table='DriverTable',
                                          category=API.Drivers,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_constructor_info(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='constructors',
                                          table='ConstructorTable',
                                          category=API.Constructors,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_circuits(self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='circuits',
                                          table='CircuitTable',
                                          category=API.Circuits,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_finishing_status(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='status',
                                          table='StatusTable',
                                          category=API.Status,
                                          subcategory=None,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    # ### endpoint with multi-result responses ###
    #
    # example: qualifying results filtered only by season will yield a
    # result for each weekend
    #
    # needs to be represented by multiple DataFrame-like objects
    def get_race_results(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='results',
                                          table='RaceTable',
                                          category=API.Races_RaceResults,
                                          subcategory=API.RaceResults,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_qualifying_results(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='qualifying',
                                          table='RaceTable',
                                          category=API.Races_QualifyingResults,
                                          subcategory=API.QualifyingResults,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_sprint_results(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='sprint',
                                          table='RaceTable',
                                          category=API.Races_SprintResults,
                                          subcategory=API.SprintResults,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_driver_standings(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='driverStandings',
                                          table='StandingsTable',
                                          category=API.StandingsLists_Driver,
                                          subcategory=API.DriverStandings,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_constructor_standings(
            self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(
            endpoint='constructorStandings',
            table='StandingsTable',
            category=API.StandingsLists_Constructor,
            subcategory=API.ConstructorStandings,
            result_type=result_type,
            auto_cast=auto_cast,
            limit=limit,
            offset=offset
        )

    def get_lap_times(self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='laps',
                                          table='RaceTable',
                                          category=API.Races_Laps,
                                          subcategory=API.Laps,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)

    def get_pit_stops(self,
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
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
            limit: Overwrites the default value for ``limit``
            offset: An offset into the result set for response paging.
                Defaults to 0 if not set. See also "Response Paging",
                https://ergast.com/mrd/.
        """
        return self._build_default_result(endpoint='pitstops',
                                          table='RaceTable',
                                          category=API.Races_PitStops,
                                          subcategory=API.PitStops,
                                          result_type=result_type,
                                          auto_cast=auto_cast,
                                          limit=limit,
                                          offset=offset)


class ErgastException(Exception):
    pass


class ErgastJsonException(ErgastException):
    pass


class ErgastInvalidRequest(ErgastException):
    pass
