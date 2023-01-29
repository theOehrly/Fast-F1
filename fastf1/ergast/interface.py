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
    def __init__(self, *args, response_headers: dict,
                 query_filters: dict, **kwargs):
        super().__init__(*args, **kwargs)
        self._response_headers = response_headers
        self._query_filters = query_filters

    @property
    def total_results(self):
        return self._response_headers.get("total", "")

    def get_next_result_page(self):
        raise NotImplementedError

    def get_prev_result_page(self):
        raise NotImplementedError

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
    def __init__(self, *, response_headers, query_filters, query_result,
                 category, auto_cast):
        if auto_cast:
            query_result = self._prepare_response(query_result, category)

        super().__init__(query_result,
                         response_headers=response_headers,
                         query_filters=query_filters)

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
    """
    def __init__(self, *args, response_description, response_data, category,
                 subcategory, auto_cast, **kwargs):
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
        return self._description

    @property
    def content(self) -> List[ErgastResultFrame]:
        return self._content


class Ergast:
    """
    Args:
        result_type: determines the default type of the returned result object

            - 'raw': :class:`ErgastRawResponse`
            - 'pandas': :class:`ErgastSimpleResponse` or
              :class:`ErgastMultiResponse` depending on endpoint

        auto_cast: determines whether result values are cast from there default
            string representation to a better matching type
    """
    # TODO: maximum size of response and offset relevant?

    def __init__(self,
                 result_type: Literal['raw', 'pandas'] = 'raw',
                 auto_cast: bool = True):
        self._selectors = []
        self._default_result_type = result_type
        self._default_auto_cast = auto_cast

    def _get(self, url: str) -> Union[dict, list]:
        r = Cache.requests_get(url, headers=HEADERS)
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

    def _build_result(
            self,
            endpoint: Optional[str],
            table: str,
            category: dict,
            subcategory: Optional[dict],
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None,
    ) -> Union[ErgastSimpleResponse,
               ErgastMultiResponse,
               ErgastRawResponse]:

        # use defaults or per-call overrides if specified
        if result_type is None:
            result_type = self._default_result_type
        if auto_cast is None:
            auto_cast = self._default_auto_cast

        # build url from base, selector and endpoint
        url_fragments = [BASE_URL]
        if self._selectors is not None:
            url_fragments.extend(self._selectors)
        if endpoint is not None:
            url_fragments.append(f"/{endpoint}")
        url_fragments.append(".json")
        url = ''.join(url_fragments)

        # get response and split it into individual parts
        resp = self._get(url)
        resp = resp['MRData']
        body = resp.pop(table)
        # response headers remain in response
        query_result = body.pop(category['name'])
        # query filters remain in body

        if result_type == 'raw':
            return ErgastRawResponse(response_headers=resp,
                                     query_filters=body,
                                     query_result=query_result,
                                     category=category,
                                     auto_cast=auto_cast)

        if result_type == 'pandas':
            # result element description remains in query result
            result_element_data = list()
            if subcategory is not None:
                for i in range(len(query_result)):
                    result_element_data.append(
                        query_result[i].pop(subcategory['name'])
                    )
                return ErgastMultiResponse(response_headers=resp,
                                           query_filters=body,
                                           response_description=query_result,
                                           response_data=result_element_data,
                                           category=category,
                                           subcategory=subcategory,
                                           auto_cast=auto_cast)
            else:
                return ErgastSimpleResponse(response_headers=resp,
                                            query_filters=body,
                                            response=query_result,
                                            category=category,
                                            auto_cast=auto_cast)

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
                    auto_cast: Optional[bool] = None
                    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of seasons.

        See: https://ergast.com/mrd/methods/seasons/

        .. ergast-api-map:: Seasons
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='seasons',
                                  table='SeasonTable',
                                  category=API.Seasons,
                                  subcategory=None,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_race_schedule(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of races.

        See: https://ergast.com/mrd/methods/schedule/

        .. ergast-api-map:: Races_Schedule
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='races',
                                  table='RaceTable',
                                  category=API.Races_Schedule,
                                  subcategory=None,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_driver_info(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of drivers.

        See: https://ergast.com/mrd/methods/drivers/

        .. ergast-api-map:: Drivers
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='drivers',
                                  table='DriverTable',
                                  category=API.Drivers,
                                  subcategory=None,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_constructor_info(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of constructors.

        See: https://ergast.com/mrd/methods/constructors/

        .. ergast-api-map:: Constructors
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='constructors',
                                  table='ConstructorTable',
                                  category=API.Constructors,
                                  subcategory=None,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_circuits(self,
                     result_type: Optional[Literal['pandas', 'raw']] = None,
                     auto_cast: Optional[bool] = None
                     ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of circuits.

        See: https://ergast.com/mrd/methods/circuits/

        .. ergast-api-map:: Circuits
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='circuits',
                                  table='CircuitTable',
                                  category=API.Circuits,
                                  subcategory=None,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_finishing_status(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastSimpleResponse, ErgastRawResponse]:
        """Get a list of finishing status codes.

        See: https://ergast.com/mrd/methods/status/

        .. ergast-api-map:: Status
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='status',
                                  table='StatusTable',
                                  category=API.Status,
                                  subcategory=None,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    # ### endpoint with multi-result responses ###
    #
    # example: qualifying results filtered only by season will yield a
    # result for each weekend
    #
    # needs to be represented by multiple DataFrame-like objects
    def get_race_results(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get race results for one or multiple races.

        See: https://ergast.com/mrd/methods/results/

        .. ergast-api-map:: Races_RaceResults
            :subcategory: RaceResults
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='results',
                                  table='RaceTable',
                                  category=API.Races_RaceResults,
                                  subcategory=API.RaceResults,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_qualifying_results(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get qualifying results for one or multiple qualifying sessions.

        See: https://ergast.com/mrd/methods/qualifying/

        .. ergast-api-map:: Races_QualifyingResults
            :subcategory: QualifyingResults
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='qualifying',
                                  table='RaceTable',
                                  category=API.Races_QualifyingResults,
                                  subcategory=API.QualifyingResults,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_sprint_results(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get sprint results for one or multiple sprints.

        See: https://ergast.com/mrd/methods/sprint/

        .. ergast-api-map:: Races_SprintResults
            :subcategory: SprintResults
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='sprint',
                                  table='RaceTable',
                                  category=API.Races_SprintResults,
                                  subcategory=API.SprintResults,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_driver_standings(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get driver standings at specific points of a season.

        See: https://ergast.com/mrd/methods/standings/

        .. ergast-api-map:: StandingsLists_Driver
            :subcategory: DriverStandings
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='driverStandings',
                                  table='StandingsTable',
                                  category=API.StandingsLists_Driver,
                                  subcategory=API.DriverStandings,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_constructor_standings(
            self,
            result_type: Optional[Literal['pandas', 'raw']] = None,
            auto_cast: Optional[bool] = None
    ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get constructor standings at specific points of a season.

        See: https://ergast.com/mrd/methods/standings/

        .. ergast-api-map:: StandingsLists_Constructor
            :subcategory: ConstructorStandings
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='constructorStandings',
                                  table='StandingsTable',
                                  category=API.StandingsLists_Constructor,
                                  subcategory=API.ConstructorStandings,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_lap_times(self,
                      result_type: Optional[Literal['pandas', 'raw']] = None,
                      auto_cast: Optional[bool] = None
                      ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get sprint results for one or multiple sprints.

        See: https://ergast.com/mrd/methods/laps/

        .. ergast-api-map:: Races_Laps
            :subcategory: Laps
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='laps',
                                  table='RaceTable',
                                  category=API.Races_Laps,
                                  subcategory=API.Laps,
                                  result_type=result_type,
                                  auto_cast=auto_cast)

    def get_pit_stops(self,
                      result_type: Optional[Literal['pandas', 'raw']] = None,
                      auto_cast: Optional[bool] = None
                      ) -> Union[ErgastMultiResponse, ErgastRawResponse]:
        """Get pit stop information for one or multiple sessions.

        See: https://ergast.com/mrd/methods/standings/

        .. ergast-api-map:: Races_PitStops
            :subcategory: PitStops
            :describe-dataframe:

        Args:
            result_type: Overwrites the default result type
            auto_cast: Overwrites the default value for ``auto_cast``
        """
        return self._build_result(endpoint='pitstops',
                                  table='RaceTable',
                                  category=API.Races_PitStops,
                                  subcategory=API.PitStops,
                                  result_type=result_type,
                                  auto_cast=auto_cast)


class ErgastException(Exception):
    pass


class ErgastJsonException(ErgastException):
    pass


class ErgastInvalidRequest(ErgastException):
    pass
