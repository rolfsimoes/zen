"""
This module implement low level classes to access InvenioRDM API.

Examples:
    Make sure to run the examples in InvenioRDM's sandbox::
    
        from zen import InvenioRDM
        # Create an instance of InvenioRDM with a base URL and token
        zen = InvenioRDM(url=InvenioRDM.sandbox_url, token='your_access_token')
        
        # List all depositions of the authenticated user
        deps = zen.depositions.list(sort="bestmatch", size=10)
        
        # Retrieve the first deposition
        dep = zen.depositions.retrieve(deps[0].id)
    
Note:
    - Before using this submodule, make sure you have a valid InvenioRDM account and access token.
    - Always refer to the InvenioRDM API documentation for detailed information about available 
      endpoints and parameters.
    - For more information, visit: https://inveniosoftware.org/products/rdm/

"""
from __future__ import annotations
from typing import Tuple, List, Dict, Any, Optional, Union, Iterator, TYPE_CHECKING
from typing_extensions import Self
import requests
import os
from .record import RecordFile, DraftFile, RecordFiles, DraftFiles, Record, Draft
from .utils import merge, load_json
if TYPE_CHECKING:
    from requests import Response

class InvenioRDMError(Exception):
    """Exception for InvenioRDM API response errors.
    
    This class encapsulates API response errors and provides a structured way to handle them.
    
    Args: 
        response (Response): The response object received from the API. 
    
    Examples:
        
        >>> from zen import InvenioRDM
        >>> from zen.api import APIResponseError
        
        1. Create an instance of InvenioRDM with a base URL and token
        
        >>> zen = InvenioRDM(url=InvenioRDM.sandbox_url, token='wrong_token')
        
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
        self.name = InvenioRDMError.bad_status_codes[self.status_code]['name']
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
            return InvenioRDMError.bad_status_codes[self.status_code]['description']

class NoNextPageError(Exception):
    pass

class InvenioRDM:
    """Interact with InvenioRDM API.
    
    This class provides methods to interact with various aspects of the InvenioRDM API, such as 
    licenses, records, depositions, and more.
    
    Args: 
        base_url (str): The base URL of the InvenioRDM API. 
        token (Optional[str]=None): The access token for authorization. 
        params (Optional[Dict[str,str]]=None): Additional params to be included in the 
            API requests. 
        headers (Optional[Dict[str,str]]=None): Additional headers to be included in the 
            API requests. 
    
    """ 
    def __init__(self, 
                 base_url: str, 
                 token: Optional[str]=None, 
                 params: Optional[Dict[str,str]]=None, 
                 headers: Optional[Dict[str,str]]=None) -> None:
        # To-Do: check input parameters
        self.base_url = base_url.rstrip('/')
        self._params = None
        self._headers = dict(Accept='application/json')
        if token is not None:
            #self._params = merge(self._params, dict(access_token=f'{token}'))
            self._headers = merge(self._headers, self._authorization(token))
        if params is not None:
            self._params = merge(self._params, params)
        if headers is not None:
            self._headers = merge(self._headers, headers)
    
    def _url(self, path):
        return f'{self.base_url}{path}'
    
    def _authorization(self, token):
        return dict(Authorization=f'Bearer {token}')
        
    def http_get(self, 
             url: str,
             params: Optional[Dict[str,str]]=None,
             headers: Optional[Dict[str,str]]=None, **kwargs) -> Response:
        response = requests.get(url=url, params=merge(self._params, params), 
                                headers=merge(self._headers, headers), **kwargs)
        if response.status_code in InvenioRDMError.bad_status_codes:
            raise InvenioRDMError(response)
        return response
    
    def http_post(self, 
              url: str,
              json: Optional[Dict[str,Any]]=None,
              data: Optional[Any]=None,
              params: Optional[Dict[str,str]]=None,
              headers: Optional[Dict[str,str]]=None, **kwargs) -> Response:
        response = requests.post(url=url, data=data, json=json, params=merge(self._params, params), 
                                 headers=merge(self._headers, headers), **kwargs)
        if response.status_code in InvenioRDMError.bad_status_codes:
            raise InvenioRDMError(response)
        return response
    
    def http_put(self, 
             url: str,
             json: Optional[Dict[str,Any]]=None,
             data: Optional[Any]=None,
             params: Optional[Dict[str,str]]=None,
             headers: Optional[Dict[str,str]]=None, **kwargs) -> Response:
        response = requests.put(url=url, data=data, json=json, params=merge(self._params, params), 
                                headers=merge(self._headers, headers), **kwargs)
        if response.status_code in InvenioRDMError.bad_status_codes:
            raise InvenioRDMError(response)
        return response
    
    def http_delete(self, 
                url: str,
                json: Optional[Dict[str,Any]]=None,
                data: Optional[Any]=None,
                params: Optional[Dict[str,str]]=None,
                headers: Optional[Dict[str,str]]=None, **kwargs) -> Response:
        response = requests.delete(url=url, data=data, json=json, params=merge(self._params, params), 
                                   headers=merge(self._headers, headers), **kwargs)
        if response.status_code in InvenioRDMError.bad_status_codes:
            raise InvenioRDMError(response)
        return response
    
    def list_drafts(self,
                    q: Optional[str]=None, 
                    sort: str=None, 
                    size: int=10, 
                    page: int=1, 
                    all_versions: bool=False,
                    token: Optional[str]=None,
                    params: Optional[Dict[str,str]]=None, 
                    headers: Optional[Dict[str,str]]=None) -> Draft:
        """Retrieves a list of drafts from the InvenioRDM API. 
    
        Args: 
            query_args (Optional[Dict[str,Any]]=None): Additional query arguments for the API request. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the list of drafts. 
    
        Raises: 
            TypeError: If the query_args parameter is not a dictionary. 
            APIResponseError: If the response status code indicates an error during the API request. 
        """ 
        query = dict(q=q, sort=sort, size=size, page=page, allversions=all_versions)
        if token is not None:
            headers = merge(headers, self._authorization(token))
        response = self.http_get(url=self._url(f'/api/user/records'), 
                             params=merge(params, query), 
                             headers=headers)
        data = response.json()
        return data

    def create_draft(self,
                     token: Optional[str]=None,
                     params: Optional[Dict[str,str]]=None, 
                     headers: Optional[Dict[str,str]]=None,
                     quietly: bool=False) -> Draft:
        """Creates a new deposition on the InvenioRDM API. 
    
        Args: 
            metadata (Optional[Dict[str,Any]]=None): The metadata for the new deposition. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the newly created deposition. 
    
        Raises: 
            ValueError: If the metadata parameter is not a dictionary. 
            APIResponseError: If the response status code indicates an error during the API request. 
        """ 
        url = self._url('/api/records')
        body = dict(access=access_public(), files=dict(enabled=True))
        if token is not None:
            headers = merge(headers, self._authorization(token))
        response = self.http_post(url, json=body, params=params, headers=headers)
        data = response.json()
        draft = Draft(data, InvenioRDM(self.base_url, params=params, headers=headers))
        draft.refresh_files()
        if not quietly: print(f'New Draft (id={draft.id}) created.')
        return draft

    def get_draft(self,
                  id: str, 
                  token: Optional[str]=None,
                  params: Optional[Dict[str,str]]=None, 
                  headers: Optional[Dict[str,str]]=None) -> Draft:
        """Retrieves a specific deposition from the InvenioRDM API.

        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to retrieve, or a dictionary 
                containing the deposition information. 
            **kwargs: Additional keyword arguments for the API request. 
        
        Returns: 
            dict: The response JSON containing the deposition information. 
        
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        url = self._url(f'/api/records/{id}/draft')
        if token is not None:
            headers = merge(headers, self._authorization(token))
        response = self.http_get(url=url, params=params, headers=headers)
        data = response.json()
        draft = Draft(data, InvenioRDM(self.base_url, params=params, headers=headers))
        draft.refresh_files()
        return draft

    def load_draft(self,
                   filename: str,
                   token: Optional[str]=None,
                   params: Optional[Dict[str,str]]=None, 
                   headers: Optional[Dict[str,str]]=None,
                   quietly: bool=False) -> Draft:
        try:
            data = load_json(filename)
            if token is not None:
                headers = merge(headers, self._authorization(token))
            draft = Draft(data, InvenioRDM(self.base_url, params=params, headers=headers))
            if not quietly: print(f"Draft (id={draft.id}) loaded from '{filename}'")
            return draft
        except FileNotFoundError:
            raise FileNotFoundError(f'File `{filename}` not found.')

    def load_or_create_draft(self,
                             filename: str,
                             token: Optional[str]=None,
                             params: Optional[Dict[str,str]]=None,
                             headers: Optional[Dict[str,str]]=None,
                             quietly: bool=False) -> Draft:
        try:
            draft = self.load_draft(filename, token, params, headers, quietly)
        except FileNotFoundError:
            if not quietly: print(f"File '{filename}' not found.")
            draft = self.create_draft(token, params, headers, quietly)
            draft.to_json(filename)
            if not quietly: print(f"Draft saved at '{filename}'.")
        return draft
    
    def list_draft_files(self,
                         id: str, 
                         token: Optional[str]=None,
                         params: Optional[Dict[str,str]]=None, 
                         headers: Optional[Dict[str,str]]=None):
        url = self._url(f'/api/records/{id}/draft/files')
        if token is not None:
            headers = merge(headers, self._authorization(token))
        response = self.http_get(url=url, params=params, headers=headers)
        data = response.json()
        files = DraftFiles(data, InvenioRDM(self.base_url, params=params, headers=headers))
        return files

    def get_record(self,
                   id: str,
                   params: Optional[Dict[str,str]]=None, 
                   headers: Optional[Dict[str,str]]=None) -> Draft:
        """Retrieves a record from the InvenioRDM API. 
    
        Args: 
            id (str): The ID of the record to be retrieved.
            
        Returns: 
            Record: The retrieved Record. 
    
        Raises: 
            InvenioRDMError: If the response status code indicates an error during the request.
        """ 
        response = self.http_get(url=self._url(f'/api/records/{id}'), 
                                 params=params, 
                                 headers=headers)
        data = response.json()
        return Record(data, self)

    def list_record_files(self,
                          id: str, 
                          params: Optional[Dict[str,str]]=None, 
                          headers: Optional[Dict[str,str]]=None):
        url = self._url(f'/api/records/{id}/files')
        response = self.http_get(url=url, params=params, headers=headers)
        data = response.json()
        files = RecordFiles(data, InvenioRDM(self.base_url, params=params, headers=headers))
        return files
    
    def search_records(self,
                       q: Optional[str]=None, 
                       sort: str=None, 
                       size: int=10, 
                       page: int=1, 
                       all_versions: bool=False,
                       params: Optional[Dict[str,str]]=None, 
                       headers: Optional[Dict[str,str]]=None) -> Draft:
        """Searches a list of records from the InvenioRDM API. 
    
        Args: 
            query_args (Optional[Dict[str,Any]]=None): Additional query arguments for the API request. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the list of records. 
    
        Raises: 
            TypeError: If the query_args parameter is not a dictionary. 
            InvenioRDMError: If the response status code indicates an error during the API request. 
        """ 
        query = dict(q=q, sort=sort, size=size, page=page, allversions=all_versions)
        response = self.http_get(url=self._url(f'/api/records'), 
                             params=merge(params, query), 
                             headers=headers)
        data = response.json()
        return data
    
    def next_page(self, 
                  data: Dict[str,Any],
                  headers: Optional[Dict[str,str]]=None, 
                  **kwargs) -> Dict[str,Any]:
        """Get the next page from a paginated data of the InvenioRDM API.
    
        Args: 
            data (Dict[str,Any]): The current page of data from the API response. 
            **kwargs: Additional keyword arguments for the API request.
    
        Returns: 
            Dict[str,Any]: The next page of data. 
    
        Raises: 
            InvenioRDMError: If the response status code indicates an error during the API request. 
            NoNextPageError: If there is no new page to retrieve
        """ 
        if not 'links' in data and 'next' in data['links']:
            raise NoNextPageError("No 'next' field found in the data.")
        
        url = data['links']['next']
        response = self.http_get(url, headers=headers, **kwargs)
        data = response.json()
        return data
        
    
    def list_deposition_files(self, deposition_id: Union[int,Dict], **kwargs) -> Dict:
        """Retrieves a list of files for a specific deposition from the InvenioRDM API. 
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition, or a dictionary containing the 
                deposition information. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the list of files. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}/files"
        response = self._req.get(url, **kwargs)
        return response.json()
    
    def new_version_deposition(self, deposition_id: Union[int,Dict], **kwargs) -> Dict:
        """Creates a new version of a specific deposition on the InvenioRDM API. Unlike InvenioRDM API, this 
        function returns the new version of the deposition.
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to create a new version of, or a 
                dictionary containing the deposition information. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the newly created version of the deposition. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}/actions/newversion"
        response = self._req.post(url, **kwargs).json()
        last_draft_url = response['links']['latest_draft']
        response = self._req.get(last_draft_url, **kwargs)
        return response.json()
    
    def create_deposition_file(self, deposition_id: Union[int,Dict], filename: str, \
        bucket_filename: Optional[str]=None, **kwargs) -> Dict:
        """Creates a new file for a specific deposition on the InvenioRDM API. 
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to create the file for, or a 
                dictionary containing the deposition information. 
            filename (str): The local file path of the file to upload. 
            bucket_filename (str or None): The desired filename for the file in the deposition's bucket. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the newly created file. 
    
        Raises: 
            ValueError: If the specified file does not exist. 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if not os.path.isfile(filename):
            raise ValueError(f"File '{filename}' does not exist")
        bucket_url = self.get_deposition_bucket(deposition_id)
        if bucket_filename is None:
            bucket_filename = os.path.basename(filename)
        url = f"{bucket_url}/{bucket_filename}"
        with open(filename, 'rb') as file_data:
            response = self._req.put(url, data=file_data, **kwargs)
        return response.json()
    
    def sort_deposition_files(self, deposition_id: Union[int,Dict], 
                              file_id_list: List[Union[str,Dict]], **kwargs) -> Dict:
        """Sorts the files of a specific deposition on the InvenioRDM API. 
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to sort the files for, or a 
                dictionary containing the deposition information. 
            file_id_list (list): The list of file IDs in the desired order. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the sorted deposition files. 
    
        Raises: 
            ValueError: If the file_id_list parameter is not a list. 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if not isinstance(file_id_list, list):
            raise ValueError('Invalid file_id_list parameter: value should be a list')
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        file_id_list = [{'id': v['id']} for v in file_id_list]
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}/files"
        response = self._req.put(url, json=file_id_list, **kwargs)
        return response.json()
    
    def retrieve_deposition_file(self, file_id: Union[str,Dict], **kwargs) -> Dict:
        """Retrieves a specific file of a deposition from the InvenioRDM API. 
    
        Args: 
            file_id (Union[str,Dict]): The ID of the file to retrieve, or a dictionary containing the 
                file information. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the file information. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API 
                request. 
        
        """ 
        if isinstance(file_id, dict):
            file_id = file_id['links']['self']
        response = self._req.get(file_id, **kwargs)
        return response.json()
    
    def delete_deposition_file(self, file_id: Union[str,Dict], **kwargs) -> None:
        """Deletes a specific file of a deposition from the InvenioRDM API. 
        
        Args: 
            file_id (Union[str,Dict]): The ID of the file to delete, or a dictionary containing the 
                file information. 
            **kwargs: Additional keyword arguments for the API request. 
        
        Returns: 
            None 
        
        Raises: 
            APIResponseError: If the response status code indicates an error during the 
                API request. 
        
        """ 
        if isinstance(file_id, dict):
            file_id = file_id['links']['self']
        self._req.delete(file_id, **kwargs)
    
    def checksum_deposition_file(self, file_id: Union[str,Dict], **kwargs) -> str:
        """Retrieves the checksum of a specific file of a deposition from the InvenioRDM API. 
        
        Args: 
            file_id (Union[str,Dict]): The ID of the file to retrieve the checksum for, or a dictionary 
                containing the file information. 
            **kwargs: Additional keyword arguments for the API request. 
        
        Returns: 
            str: The checksum of the file. 
        
        Raises: 
            APIResponseError: If the response status code indicates an error during the 
                API request. 
        
        """ 
        if not isinstance(file_id, dict) or 'checksum' not in file_id:
            file_id = self.retrieve_deposition_file(file_id, **kwargs)
        if file_id['checksum'].startswith('md5:'):
            return file_id['checksum'][4:]
        return file_id['checksum']


class _Page:
    def __init__(self, page: Dict[str,Any], api: InvenioRDM) -> None:
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

    
def _embargo(active, until, reason):
    data = dict(active=active)
    if until is not None:
        data['until'] = until
    if reason is not None:
        data['reason'] = reason
    return data

def access(record, files, embargo_active=None, embargo_until=None, embargo_reason=None):
    data = dict(record=record, files=files)
    if embargo_active is not None:
        data['embargo'] = _embargo(embargo_active, embargo_until, embargo_reason)
    return data

def access_public():
    return access(record='public', files='public')

def access_restricted(embargo_active=False, until=None, reason=None):
    return access(record='restricted', files='restricted', 
                  embargo=_embargo(embargo_active, until, reason))

