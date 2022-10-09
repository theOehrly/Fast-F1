import copy
import json
from typing import Literal, Optional, Union

from fastf1.api import Cache
import fastf1.ergast.structure as API
from fastf1.version import __version__


import pandas as pd


BASE_URL = 'https://ergast.com/api/f1'
HEADERS = {'User-Agent': f'FastF1/{__version__}'}


class _ErgastResponseMixin:
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


class ErgastResponseRaw(_ErgastResponseMixin, list):
    def __init__(self, *, response_headers, query_filters, query_result):
        super().__init__(query_result,
                         response_headers=response_headers,
                         query_filters=query_filters)


class ErgastResponse(_ErgastResponseMixin):
    def __init__(self, *args, response_description, response_data, category,
                 subcategory, auto_cast, **kwargs):
        super().__init__(*args, **kwargs)
        self._description = ErgastResultFrame(response=response_description,
                                              category=category,
                                              auto_cast=auto_cast)
        self._results = [ErgastResultFrame(response=elem,
                                           category=subcategory,
                                           auto_cast=auto_cast)
                         for elem in response_data]

    @property
    def description(self):
        return self._description

    @property
    def results(self):
        return self._results


class _ErgastResponseItem:
    def __init__(self, response):
        self._response = response

    def __repr__(self):
        return "<meta>"


class ErgastResultFrame(pd.DataFrame):
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

        if (postprocessor := category['post']) is not None:
            data = postprocessor(data)

        return data

    @classmethod
    def _flatten_element(cls, nested: dict, category: dict, cast: bool):
        flat = {}

        # call the categories associated flattening method on the data
        # (operations on 'nested' and 'flat' are inplace, therefore no return)
        category['method'](nested, category, flat, cast)

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


class ErgastSelectionObject:
    # TODO: maximum size of response and offset relevant?

    def __init__(self,
                 selectors: Optional[list] = None,
                 result_type: str = 'raw',
                 auto_cast: bool = True):
        self._selectors = selectors
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

    def _build_result(self,
                      endpoint: Optional[str],
                      table: str,
                      category: dict,
                      subcategory: Optional[dict],
                      result_type: Optional[Literal['pandas', 'raw']] = None,
                      auto_cast: Optional[bool] = None,
                      ) -> Union[ErgastResponse, ErgastResponseRaw]:

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
            return ErgastResponseRaw(response_headers=resp,
                                     query_filters=body,
                                     query_result=query_result,
                                     auto_cast=auto_cast)

        if result_type == 'pandas':
            # result element description remains in query result
            result_element_data = list()
            if subcategory is not None:
                for i in range(len(query_result)):
                    result_element_data.append(
                        query_result[i].pop(subcategory['name'])
                    )
            return ErgastResponse(response_headers=resp,
                                  query_filters=body,
                                  response_description=query_result,
                                  response_data=result_element_data,
                                  category=category,
                                  subcategory=subcategory,
                                  auto_cast=auto_cast)

    def get_seasons(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='seasons',
                                  table='SeasonTable',
                                  category=API.Seasons,
                                  subcategory=None)

    def get_race_schedule(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='races',
                                  table='RaceTable',
                                  category=API.Races_Schedule,
                                  subcategory=None)

    def get_race_results(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='results',
                                  table='RaceTable',
                                  category=API.Races_RaceResults,
                                  subcategory=API.RaceResults)

    def get_qualifying_results(self) \
            -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='qualifying',
                                  table='RaceTable',
                                  category=API.Races_QualifyingResults,
                                  subcategory=API.QualifyingResults)

    def get_sprint_results(self) \
            -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='sprint',
                                  table='RaceTable',
                                  category=API.Races_SprintResults,
                                  subcategory=API.SprintResults)

    def get_driver_standings(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='driverStandings',
                                  table='StandingsTable',
                                  category=API.StandingsLists_Driver,
                                  subcategory=API.DriverStandings)

    def get_constructor_standings(self) \
            -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='constructorStandings',
                                  table='StandingsTable',
                                  category=API.StandingsLists_Constructor,
                                  subcategory=API.ConstructorStandings)

    def get_driver_info(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='drivers',
                                  table='DriverTable',
                                  category=API.Drivers,
                                  subcategory=None)

    def get_constructor_info(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='constructors',
                                  table='ConstructorTable',
                                  category=API.Constructors,
                                  subcategory=None)

    def get_circuits(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='circuits',
                                  table='CircuitTable',
                                  category=API.Circuits,
                                  subcategory=None)

    def get_finishing_status(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='status',
                                  table='StatusTable',
                                  category=API.Status,
                                  subcategory=None)

    def get_lap_times(self) -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='laps',
                                  table='RaceTable',
                                  category=API.Races_Laps,
                                  subcategory=API.Laps)

    def get_pit_stops(self, **kwargs) \
            -> Union[ErgastResponse, ErgastResponseRaw]:
        return self._build_result(endpoint='pitstops',
                                  table='RaceTable',
                                  category=API.Races_PitStops,
                                  subcategory=API.PitStops,
                                  **kwargs)


class Ergast(ErgastSelectionObject):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._args = args
        self._kwargs = kwargs

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
               ) -> ErgastSelectionObject:

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

        return ErgastSelectionObject(*self._args,
                                     selectors=selectors,
                                     **self._kwargs)


class ErgastException(Exception):
    pass


class ErgastJsonException(ErgastException):
    pass


class ErgastInvalidRequest(ErgastException):
    pass
