"""
This module implement low level classes to access Zenodo API. The only class intended to 
users use is APIResponseError, that can be used to capture errors from API requests.

Examples:
    Make sure to run the examples in Zenodo's sandbox::
    
        from zen import Zenodo
        # Create an instance of Zenodo with a base URL and token
        zen = Zenodo(url=Zenodo.sandbox_url, token='your_access_token')
        
        # List all depositions of the authenticated user
        deps = zen.depositions.list(sort="bestmatch", size=10)
        
        # Retrieve the first deposition
        dep = zen.depositions.retrieve(deps[0].id)
    
Note:
    - Before using this submodule, make sure you have a valid Zenodo account and access token.
    - Always refer to the Zenodo API documentation for detailed information about available 
      endpoints and parameters.
    - For more information, visit: https://developers.zenodo.org/

"""
from __future__ import annotations
from typing import Tuple, List, Dict, Any, Optional, Union, Iterator, TYPE_CHECKING
from typing_extensions import Self
if TYPE_CHECKING:
    from requests import Response
    from .dataset import Deposition
    from .metadata import Metadata
import zen.dataset as __dataset__
import zen.metadata as __metadata__
import os
import requests

class APIResponseError(Exception):
    """Exception for Zenodo API response errors.
    
    This class encapsulates API response errors and provides a structured way to handle them.
    
    Args: 
        response (Response): The response object received from the API. 
    
    Examples:
        
        >>> from zen import Zenodo
        >>> from zen.api import APIResponseError
        
        1. Create an instance of Zenodo with a base URL and token
        
        >>> zen = Zenodo(url=Zenodo.sandbox_url, token='wrong_token')
        
        2. Catch APIResponseError
        
        >>> # Will generate an error - Wrong token
        >>> try:
        ...     zen.depositions.list()
        ... except APIResponseError as e:
        ...     print('Invalid operation')
        Invalid operation
        
    """
    
    bad_status_codes = {
        400: {
            "name": "Bad Request",
            "description": "Request failed."
        },
        401: {
            "name": "Unauthorized",
            "description": "Request failed, due to an invalid access token."
        },
        403: {
            "name": "Forbidden",
            "description": "Request failed, due to missing authorization (e.g. deleting an already " +
                "submitted upload or missing scopes for your access token)."
        },
        404: {
            "name": "Not Found",
            "description": "Request failed, due to the resource not being found."
        },
        405: {
            "name": "Method Not Allowed",
            "description": "Request failed, due to unsupported HTTP method."
        },
        409: {
            "name": "Conflict",
            "description": "Request failed, due to the current state of the resource (e.g. edit " +
                "a deposition which is not fully integrated)."
        },
        415: {
            "name": "Unsupported Media Type",
            "description": "Request failed, due to missing or invalid request header Content-Type."
        },
        422: {
            "name": "Unprocessable Entity",
            "description": "Resumption tokens are only valid for 2 minutes."
        },
        429: {
            "name": "Too Many Requests",
            "description": "Request failed, due to rate limiting."
        },
        500: {
            "name": "Internal Server Error",
            "description": "Request failed, due to an internal server error."
        }
    }

    def __init__(self, response: Response) -> None:
        self.status_code = response.status_code
        self.name = APIResponseError.bad_status_codes[self.status_code]['name']
        self.description = self.get_response_description(response)
        super().__init__(f"Status code {self.status_code} ({self.name}): {self.description}")
    
    def get_response_description(self, response: Response) -> str:
        """Returns the description of the error based on the response object. 
        
        Args: 
            response (Response): The response object received from the API. 
        
        Returns: 
            str: The description of the error. 
        
        """ 
        try:
            content = response.json()
            message = content['message']
            try:
                error = content['errors'][0]
                return f"{message} Field '{error['field']}'. {error['message']}"
            except:
                return message
        except:
            return APIResponseError.bad_status_codes[self.status_code]['description']


class _APIRequest:
    """Internal class for handling API 
    
    This class prepares HTTP requests and handles responses.
    """ 
    def __init__(self, token: Optional[str]=None, params: Optional[Dict[str,str]]=None, 
                 headers: Optional[Dict[str,str]]=None) -> None:
        if token is not None:
            params = _APIRequest._merge_dicts(params, {'access_token': f'{token}'})
            headers = _APIRequest._merge_dicts(headers, {'Authorization': f'Bearer {token}'})
        self._params = params
        self._headers = headers

    @staticmethod
    def _merge_dicts(params1: Optional[Dict[str,Any]], 
                     params2: Optional[Dict[str,Any]]) -> Union[Dict[str,Any],None]:
        if params1 is None:
            params1 = {}
        merged_params = params1.copy()
        if params2 is not None:
            merged_params.update(params2)
        return merged_params
    
    def _prepare_params_headers(self, **kwargs) -> Tuple[Dict,Dict,Dict]:
        """Prepares the parameters and headers for the API request. 
 
        Args: 
            **kwargs: Additional keyword arguments for the API request. 
 
        Returns: 
            Tuple[Dict,Dict,Dict]: A tuple containing the parameters, headers, and remaining 
                keyword arguments. 
 
        Raises: 
            None 
        
        """ 
        params = self._params
        if 'params' in kwargs:
            params = _APIRequest._merge_dicts(params, kwargs['params'])
            del kwargs['params']
        headers = self._headers
        if 'headers' in kwargs:
            headers = _APIRequest._merge_dicts(headers, kwargs['headers'])
            del kwargs['headers']
        return params, headers, kwargs
    
    def url_token(self, url: str, **kwargs) -> str:
        """Returns a provided base url with the Zenodo API token as a query string parameter. 
        
        Args: 
            url (str): The URL to send the GET request to. 
            **kwargs: Additional keyword arguments for the GET request. 
        
        Returns: 
            str: The URL with 'access_token=<token>' parameter in the query string. 
        
        """ 
        params, _, _ = self._prepare_params_headers(**kwargs)
        prep = requests.models.PreparedRequest()
        prep.prepare_url(url, params=params)
        return prep.url
    
    def get(self, url: str, **kwargs) -> Response:
        """Performs a GET request to the specified URL. 
        
        Args: 
            url (str): The URL to send the GET request to. 
            **kwargs: Additional keyword arguments for the GET request. 
        
        Returns: 
            Response: The response object received from the GET request. 
        
        Raises: 
            APIResponseError: If the response status code indicates an error. 
        
        """ 
        params, headers, kwargs = self._prepare_params_headers(**kwargs)
        response = requests.get(url, params=params, headers=headers, **kwargs)
        if response.status_code in APIResponseError.bad_status_codes:
            raise APIResponseError(response)
        return response
    
    def post(self, url: str, **kwargs) -> Response:
        """Performs a POST request to the specified URL. 
        
        Args: 
            url (str): The URL to send the POST request to. 
            **kwargs: Additional keyword arguments for the POST request. 
        
        Returns: 
            Response: The response object received from the POST request. 
        
        Raises: 
            APIResponseError: If the response status code indicates an error. 
        
        """ 
        params, headers, kwargs = self._prepare_params_headers(**kwargs)
        response = requests.post(url, params=params, headers=headers, **kwargs)
        if response.status_code in APIResponseError.bad_status_codes:
            raise APIResponseError(response)
        return response
    
    def put(self, url: str, **kwargs) -> Response:
        """Performs a PUT request to the specified URL. 
        
        Args: 
            url (str): The URL to send the PUT request to. 
            **kwargs: Additional keyword arguments for the PUT request. 
        
        Returns: 
            Response: The response object received from the PUT request. 
        
        Raises: 
            APIResponseError: If the response status code indicates an error. 
        
        """ 
        params, headers, kwargs = self._prepare_params_headers(**kwargs)
        response = requests.put(url, params=params, headers=headers, **kwargs)
        if response.status_code in APIResponseError.bad_status_codes:
            raise APIResponseError(response)
        return response
    
    def delete(self, url: str, **kwargs) -> Response:
        """Performs a DELETE request to the specified URL. 
        
        Args: 
            url (str): The URL to send the DELETE request to. 
            **kwargs: Additional keyword arguments for the DELETE request. 
        
        Returns: 
            Response: The response object received from the DELETE request. 
        
        Raises: 
            APIResponseError: If the response status code indicates an error. 
        
        """ 
        params, headers, kwargs = self._prepare_params_headers(**kwargs)
        response = requests.delete(url, params=params, headers=headers, **kwargs)
        if response.status_code in APIResponseError.bad_status_codes:
            raise APIResponseError(response)
        return response


class Depositions:
    """Managing depositions on the Zenodo API. 
    
    The Depositions class simplifies interactions with the Zenodo API. It is utilized to give 
    an intuitive way to explore Zenodo API depositions, making it easier to retrieve, filter, 
    and work with deposition data.
    
    It is used by the Zenodo class to perform various Zenodo API operations, such as listing 
    depositions, retrieving specific depositions, and facilitating advanced searches based on 
    different criteria.

    Args:
        api (Zenodo): The Zenodo instance used to interact with Zenodo API.
    
    Examples:
        
        1. Accessing the instance of the Deposition class:
        
        >>> from zen import Zenodo
        >>> zen = Zenodo(url=Zenodo.sandbox_url, api_token='your_api_token')
        >>> zen.depositions  # Instance of class Depositions
        
        2. Retrieving a list of depositions that match a specific query:
        
        >>> zen.depositions.list(q="title:(My title)", sort="bestmatch", size=10)
        
        3. Creating a new deposition on Zenodo:
        
        >>> new_dep = zen.depositions.create()  # Empty metadata
        
        4. Retrieving an existing Zenodo deposition by ID:
        
        >>> existing_dep = zen.depositions.retrieve(new_dep.id)
        >>> new_dep.discard()  # Cancel deposition creation
    
    """ 
    status_options = ['draft', 'published']
    
    sort_options = ['bestmatch', '-bestmatch', 'mostrecent', '-mostrecent']
    
    def __init__(self, api: Zenodo) -> None:
        self._api = api
    
    def list(self, q: Optional[str]=None, status: Optional[str]=None, sort: Optional[str]=None, 
             size: Optional[int]=None, all_versions: Optional[bool]=None) -> List[Deposition]:
        """Retrieve a list of depositions from Zenodo.
        
        This method searches depositions associated with current Zenodo account (determined by 
        the Zenodo token). It provides a streamlined way to query and filter depositions based 
        on specific criteria, including search terms, status, sorting options, and the maximum 
        number of depositions to retrieve.
        
        Args: 
            q (Optional[str]=None): The Elasticsearch query to filter the depositions. 
            status (Optional[str]=None): The status of the depositions to filter. See 
                `status_options` attribute for supported options.
            sort (Optional[str]=None): The field to sort the depositions by. See `sort_options` 
                attribute for supported options.
            size (Optional[int]=None): The maximum number of depositions to retrieve. 
            all_versions (Optional[bool]=None): Whether to include all versions of the 
                depositions. 
        
        Returns: 
            List[Deposition]: A list of Deposition objects representing the retrieved depositions. 
        
        """ 
        if status is not None and not status in Depositions.status_options:
            raise ValueError('Invalid `status` parameter. Please, see `Depositions.status_options` ' +
                             'attribute for supported options.')
        if sort is not None and not sort in Depositions.sort_options:
            raise ValueError('Invalid `sort` parameter. Please, see `Depositions.sort_options` ' +
                             'attribute for supported options.')
        # Builds the query
        query = dict(q=q, status=status, sort=sort, size=size, all_versions=all_versions)
        query = {k: v for k, v in query.items() if v is not None}
        # Prepare for pagination
        items = []
        page_results = self._api.api.list_depositions(query)
        while len(page_results) > 0:
            items.extend(page_results)
            if 'page' not in query:
                query['page'] = 1
            query.update(dict(page=query['page'] + 1))
            page_results = self._api.api.list_depositions(query)
        return [__dataset__.Deposition(self._api, item) for item in items]
    
    def create(self, metadata: Optional[Union[Metadata,Dict[str,Any]]]=None) -> Deposition:
        """Creates a new deposition on the Zenodo API.
        
        Args: 
            local (str): The path to a JSON file where the local dataset will be stored to or 
                read from.
            metadata (Optional[Union[MetaGeneric,Dict[str,Any]]]=None): The metadata for the 
                new deposition. 
        
        Returns: 
            Deposition: A Deposition object representing the newly created deposition. 
        
        Raises: 
            None 
        
        """ 
        if isinstance(metadata, __metadata__.Metadata):
            metadata = metadata.render()
        data = self._api.api.create_deposition(metadata)
        return __dataset__.Deposition(self._api, data)
    
    def retrieve(self, deposition: Union[Deposition,Dict[str,Any],int]) -> Deposition:
        """Retrieves a specific deposition from the Zenodo API.
        
        Args: 
            deposition (Union[Deposition,Dict[str,Any],int]): The ID of the deposition to 
                retrieve, or a dictionary containing the deposition information. 
        
        Returns: 
            Deposition: A Deposition object representing the retrieved deposition. 
        
        """ 
        if isinstance(deposition, __dataset__.Deposition):
            deposition = deposition.id
        data = self._api.api.retrieve_deposition(deposition)
        return __dataset__.Deposition(self._api, data)


class License(dict):
    def __init__(self, data: Dict[str,Any]) -> None:
        super().__init__(data)
    
    def __repr__(self) -> str:
        return str(self['id'])


class _PagedData:
    def __init__(self, page: Dict[str,Any], api: Zenodo) -> None:
        self._start_page = page
        self._api = api
        self._pages_iter: Iterator[Dict[str,Any]] = None
        self._page: Dict[str,Any] = None
        self._num_pages = 0
        self.first_page()
        if len(self) > 0:
            self._num_pages = self.total / len(self)
    
    def __repr__(self) -> str:
        items = [item['id'] for item in self.data['hits']['hits']]
        return str(dict(total=self.total, items=items))
    
    def __len__(self):
        return len(self.data['hits']['hits'])
    
    def __getitem__(self, key: int) -> Dict[str,Any]:
        return self._item(self.data['hits']['hits'][key])
    
    def __iter__(self) -> Iterator[Dict[str,Any]]:
        for license in self.data['hits']['hits']:
            yield self._item(license)
    
    def _item(self, item: Dict[str,Any]) -> Dict[str,Any]:
        return item
    
    def first_page(self) -> Self:
        self._pages_iter = self._api.api.iter_pagination(self._start_page, limit=1)
        self._page = next(self._pages_iter)
        return self
    
    def next_page(self) -> Self:
        if self._pages_iter is None:
            self._pages_iter = self._api.api.iter_pagination(self._start_page, limit=1)
        self._page = next(self._pages_iter)
        return self
    
    @property
    def data(self) -> Dict[str,Any]:
        if self._page is None:
            self.next_page()
        return self._page
    
    @property
    def total(self) -> int:
        return self.data['hits']['total']
    
    @property
    def links(self) -> Dict[str,str]:
        return self.data['links']
    
    @property
    def pages(self) -> Iterator[Dict[str,Any]]:
        yield self.first_page()
        while True:
            yield self.next_page()
    
    @property
    def num_pages(self) -> int:
        return self._num_pages


class LicensesPage(_PagedData):
    def __init__(self, page: Dict[str,Any], api: Zenodo) -> None:
        super().__init__(page, api)
    
    def _item(self, item: Dict[str,Any]) -> License:
        return License(item)


class Licenses:
    """Interacting with licenses on the Zenodo API. 
    
    The Vocabularies class implements `vocabularies` endpoint of the Zenodo API. This class is 
    used by the `Zenodo` class to perform vocabularies queries on Zenodo API.
    
    Args:
        api (Zenodo): The Zenodo instance used to interact with Zenodo API.
    
    Examples:
        
        1. Accessing the instance of the Licenses class:
        
        >>> from zen import Zenodo
        >>> zen = Zenodo(url=Zenodo.sandbox_url, api_token='your_api_token')
        >>> zen.vocabularies  # Instance of class Vocabularies
        
        2. Retrieving a list of licenses that match a specific query:
        
        >>> zen.vocabularies.list(type='licenses', q='cc', size=25, page=2)
        
        3. Retrieving a Zenodo license:
        
        >>> zen.vocabularies.retrieve(type='license', id='cc-zero')
    
    """ 
    def __init__(self, api: Zenodo) -> None:
        self._api = api
    
    def list(self, q: Optional[str]=None, page: Optional[int]=None, 
             size: Optional[int]=None) -> LicensesPage:
        """Retrieve a list of licenses from Zenodo.
        
        This method searches licenses registered in Zenodo. It provides a streamlined way to 
        query and filter licenses based on specific criteria, including search terms, and the 
        maximum number of licenses per page, and the page number to retrieve.
        
        Args: 
            q (Optional[str]=None): The Elasticsearch query to filter the licenses.
            page (Optional[int]=None): The page number of pagination. 
            size (Optional[int]=None): The maximum number of licenses to retrieve per page.
        
        Returns: 
            LicensesPage: The first page of the licenses list. 
        
        """ 
        # Builds the query
        query = dict(q=q, page=page, size=size)
        query = {k: v for k, v in query.items() if v is not None}
        # Prepare for pagination
        page_results = self._api.api.list_licenses(query)
        return LicensesPage(page_results, self._api)
    
    def retrieve(self, license: Union[Dict[str,Any],int]) -> License:
        """Retrieves a specific license from the Zenodo API.
        
        Args: 
            license (Union[Deposition,Dict[str,Any],int]): The ID of the license to 
                retrieve, or a dictionary containing the license information. 
        
        Returns: 
            License: A License object representing the retrieved license. 
        
        """ 
        if isinstance(license, dict):
            license = license.id
        data = self._api.api.retrieve_license(license)
        return License(data)


class Zenodo:
    """Interact with the Zenodo API.
    
    The `Zenodo` class provides a Python interface for interacting with the Zenodo API, allowing 
    the user to create and manage depositions, access records, and retrieve license information. 
    The class organization resembles the API endpoints, making it easy to work with various Zenodo 
    functionalities:
    
    - `depositions` property: Access the depositions endpoint. This is represented by `Depositions` 
      class. Using this instance, users can manage depositions, create new ones, and retrieve 
      existing ones.
    - `records` property: Retrieve detailed information about Zenodo records, making it easy to 
      access, update, and manipulate metadata and content of records.
    - `licenses` property: Access information about licenses available on Zenodo vocabulary.
    
    Args: 
        url (str): The base URL of the Zenodo API. 
        token (Optional[str]=None): The access token for making authenticated requests to the 
            Zenodo API. 
        headers (Optional[Dict[str,str]]=None): Additional headers to include in API requests. 
    
    Examples:
        You can use the `Zenodo` class to interact with the Zenodo API:
        
        1. Initialize `Zenodo` with your access token:
        
        >>> zen = Zenodo(url=Zenodo.sandbox_url, token='your_access_token')
        
        2. Access the `depositions` endpoint to list depositions:
        
        >>> deposition_list = zen.depositions.list(status='published')
    
    """ 
    url = 'https://zenodo.org'
    sandbox_url = 'https://sandbox.zenodo.org'
    max_storage_size = int(5e10)
    max_deposition_files = 100
    
    
    def __init__(self, url: str='https://zenodo.org', token: Optional[str]=None, 
                 headers: Optional[Dict[str,str]]=None) -> None:
        if not isinstance(url, str):
            raise TypeError('Invalid `url` parameter. Expecting a `str` but got a ' +
                            f'{type(url)} instead.')
        if token is not None and not isinstance(token, str):
            raise TypeError('Invalid `token` parameter. Expecting a `str` but got a ' +
                            f'{type(token)} instead.')
        if headers is not None and not isinstance(headers, dict):
            raise TypeError('Invalid `headers` parameter. Expecting a `dict` but got a ' +
                            f'{type(headers)} instead.')
        self._api = APIZenodo(url, token, headers)
        self._depositions = Depositions(self)
        self._records = None
        self._licenses = Licenses(self)
    
    @property
    def api(self) -> APIZenodo:
        """The internal API object.
        """ 
        return self._api
    
    @property
    def depositions(self) -> Depositions:
        """The depositions endpoint.
        """ 
        return self._depositions

    @property
    def records(self):
        """The records endpoint.
        """ 
        return self._records

    @property
    def licenses(self):
        """The licenses endpoint.
        """ 
        return self._licenses
