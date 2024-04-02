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
from .utils import merge
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


class _HTTPRequest:
    """Internal class for handling API 
    
    This class prepares HTTP requests and handles responses.
    """ 
    def __init__(self, 
                 token: Optional[str]=None,
                 base_url: str='https://InvenioRDM.org',
                 params: Optional[Dict[str,str]]=None, 
                 headers: Optional[Dict[str,str]]=None) -> None:
        # To-Do: check input parameters
        self.base_url = base_url
        self._params = None
        self._headers = None
        self._update_headers(dict(Accept='application/json'))
        if token is not None:
            self._update_params(dict(access_token=f'{token}'))            
            self._update_headers(dict(Authorization=f'Bearer {token}'))
        self._update_params(params)
        self._update_headers(headers)
    
    def _update_params(self, params):
        self._params = merge(self._params, params)
    
    def _update_headers(self, headers):
        self._headers = merge(self._headers, headers)
    
    def get(self, 
            path: str,
            params: Optional[Dict[str,str]]=None,
            headers: Optional[Dict[str,str]]=None, **kwargs) -> Response:
        url = f'{self.base_url}{path}'
        response = requests.get(url, params=merge(self._params, params), 
                                headers=merge(self._headers, headers), **kwargs)
        if response.status_code in InvenioRDMError.bad_status_codes:
            raise InvenioRDMError(response)
        return response
    
    def post(self, 
             path: str,
             json: Optional[Dict[str,Any]]=None,
             data: Optional[Any]=None,
             params: Optional[Dict[str,str]]=None,
             headers: Optional[Dict[str,str]]=None, **kwargs) -> Response:
        url = f'{self.base_url}{path}'
        response = requests.post(url, data=data, json=json, params=merge(self._params, params), 
                                 headers=merge(self._headers, headers), **kwargs)
        if response.status_code in InvenioRDMError.bad_status_codes:
            raise InvenioRDMError(response)
        return response
    
    def put(self, 
            path: str,
            json: Optional[Dict[str,Any]]=None,
            data: Optional[Any]=None,
            params: Optional[Dict[str,str]]=None,
            headers: Optional[Dict[str,str]]=None, **kwargs) -> Response:
        url = f'{self.base_url}{path}'
        response = requests.put(url, data=data, json=json, params=merge(self._params, params), 
                                headers=merge(self._headers, headers), **kwargs)
        if response.status_code in InvenioRDMError.bad_status_codes:
            raise InvenioRDMError(response)
        return response
    
    def delete(self, 
               path: str,
               json: Optional[Dict[str,Any]]=None,
               data: Optional[Any]=None,
               params: Optional[Dict[str,str]]=None,
               headers: Optional[Dict[str,str]]=None, **kwargs) -> Response:
        url = f'{self.base_url}{path}'
        response = requests.delete(url, data=data, json=json, params=merge(self._params, params), 
                                   headers=merge(self._headers, headers), **kwargs)
        if response.status_code in InvenioRDMError.bad_status_codes:
            raise InvenioRDMError(response)
        return response


class InvenioRDMClient:
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
    def __init__(self, base_url: str, token: Optional[str]=None, params: Optional[Dict[str,str]]=None, 
                 headers: Optional[Dict[str,str]]=None) -> None:
        self.base_url = base_url.rstrip('/')
        self._req = _HTTPRequest(token, params, headers)
    
    def list_licenses(self, query_args: Optional[Dict[str,Any]]=None, 
                          **kwargs) -> Dict:
        """Retrieves a list of licenses entries.

        Args: 
            query_args (Optional[Dict[str,Any]]=None): Additional query arguments for the API request. 
            **kwargs: Additional keyword arguments for the API request. 
        
        Returns: 
            dict: The response JSON containing the list of licenses entries. 
        
        Raises: 
            TypeError: If the `query_args` parameter is not a dictionary. 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if query_args is not None and not isinstance(query_args, dict):
            raise TypeError('Invalid `query_args` parameter. Value must be `dict` but got ' +
                            f'`{type(query_args)}`.')
        url = f"{self.base_url}/api/licenses"
        response = self._req.get(url, params=query_args, **kwargs)
        return response.json()
    
    def retrieve_license(self, license_id: str, **kwargs) -> Dict:
        """Retrieves a specific license entry from the InvenioRDM API. 
    
        Args: 
            license_id (str): The ID of the license to retrieve. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the license entry information. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if isinstance(license_id, dict):
            license_id = license_id['id']
        url = f"{self.base_url}/api/licenses/{license_id}"
        response = self._req.get(url, **kwargs)
        return response.json()
    
    def list_records(self, query_args: Optional[Dict[str,Any]]=None, **kwargs) -> Dict:
        """Retrieves a list of records from the InvenioRDM API. 
    
        Args: 
            query_args (Optional[Dict[str,Any]]=None): Additional query arguments for the API request. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the list of records. 
    
        Raises: 
            TypeError: If the query_args parameter is not a dictionary. 
            APIResponseError: If the response status code indicates an error during the API request. 
        """ 
        if query_args is not None and not isinstance(query_args, dict):
            raise TypeError('Invalid `query_args` parameter. Value must be `dict` but got ' +
                            f'`{type(query_args)}` instead.')
        url = f"{self.base_url}/api/records"
        response = self._req.get(url, params=query_args, **kwargs)
        return response.json()
    
    def retrieve_record(self, record_id: Union[int,Dict], **kwargs) -> Dict:
        """Retrieves a specific record from the InvenioRDM API. 
    
        Args: 
            record_id (Union[int,Dict]): The ID of the record to retrieve, or a dictionary containing 
                the record information. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the record information. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        """ 
        if isinstance(record_id, dict):
            record_id = record_id['id']
        url = f"{self.base_url}/api/records/{record_id}"
        response = self._req.get(url, **kwargs)
        return response.json()
    
    def iter_pagination(self, data: Dict[str,Any], limit: Optional[int]=None, **kwargs) -> Iterator[Dict[str,Any]]:
        """Iterates over paginated data from the InvenioRDM API. 
    
        Args: 
            data (Dict[str,Any]): The initial page of data from the API response. 
            limit (Optional[int]=None): The maximum number of pages to retrieve. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            Iterator[Dict[str,Any]]: An iterator that yields each page of data. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        """ 
        page = data
        yield page
        i = 0
        while 'links' in page and 'next' in page['links'] and (limit is None or i < limit):
            url = page['links']['next']
            response = self._req.get(url, **kwargs)
            page = response.json()
            yield page
            i += 1
    
    def list_depositions(self, query_args: Optional[Dict[str,Any]]=None, **kwargs) -> Dict:
        """Retrieves a list of depositions from the InvenioRDM API. 
    
        Args: 
            query_args (Optional[Dict[str,Any]]=None): Additional query arguments for the API request. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the list of depositions. 
    
        Raises: 
            TypeError: If the query_args parameter is not a dictionary. 
            APIResponseError: If the response status code indicates an error during the API request. 
        """ 
        if query_args is not None and not isinstance(query_args, dict):
            raise TypeError('Invalid `query_args` parameter. Value must be `dict` but got ' +
                            f'`{type(query_args)}` instead.')
        url = f"{self.base_url}/api/deposit/depositions"
        response = self._req.get(url, params=query_args, **kwargs)
        return response.json()
    
    def create_deposition(self, metadata: Optional[Dict[str,Any]]=None, **kwargs) -> Dict:
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
        if metadata is None:
            metadata = dict()
        if not isinstance(metadata, dict):
            raise TypeError('Invalid `metadata` parameter. Value must be `dict` but got ' +
                            f'`{type(metadata)}` instead.')
        if len(metadata) > 0 and 'metadata' not in metadata:
            metadata = dict(metadata=metadata)
        url = f"{self.base_url}/api/deposit/depositions"
        response = self._req.post(url, json=metadata, **kwargs)
        return response.json()
        
    
    def retrieve_deposition(self, deposition_id: Union[int,Dict], **kwargs) -> Dict:
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
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        if not isinstance(deposition_id, int):
            raise TypeError('Invalid `deposition_id` parameter. Value must be `int` but got ' +
                            f'`{type(deposition_id)}`.')
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}"
        response = self._req.get(url, **kwargs)
        return response.json()
    
    def update_deposition(self, deposition_id: Union[int,Dict], 
                          metadata: Dict[str,Any], **kwargs) -> Dict:
        """Updates a specific deposition on the InvenioRDM API.
        
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to update, or a dictionary 
                containing the deposition information. 
            metadata (Dict[str,Any]): The updated metadata for the deposition. 
            **kwargs: Additional keyword arguments for the API request. 
        
        Returns: 
            dict: The response JSON containing the updated deposition.
        
        Raises: 
            ValueError: If the metadata parameter is not a dictionary. 
            APIResponseError: If the response status code indicates an error during the API request. 

        """ 
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        if not isinstance(metadata, dict):
            raise TypeError('Invalid `metadata` parameter. Value must be `dict` but got ' +
                            f'`{type(metadata)}` instead.')
        if 'metadata' not in metadata:
            metadata = dict(metadata=metadata)
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}"
        response = self._req.put(url, json=metadata, **kwargs)
        return response.json()
    
    def delete_deposition(self, deposition_id: Union[int,Dict], **kwargs) -> None:
        """Deletes a specific deposition from the InvenioRDM API. 
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to delete, or a dictionary 
                containing the deposition information. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            None 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}"
        self._req.delete(url, **kwargs)
        
    def get_deposition_bucket(self, deposition_id: Union[int,Dict]) -> str:
        """Retrieves the bucket URL for a specific deposition on the InvenioRDM API. 
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition, or a dictionary containing the 
                deposition information. 
    
        Returns: 
            str: The URL of the deposition's bucket. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if not isinstance(deposition_id, dict) or 'links' not in deposition_id or \
            'bucket' not in deposition_id['links']:
            deposition_id = self.retrieve_deposition(deposition_id)
        return deposition_id['links']['bucket']
    
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
    
    def publish_deposition(self, deposition_id: Union[int,Dict], **kwargs) -> Dict:
        """Publishes a specific deposition on the InvenioRDM API. 
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to publish, or a dictionary 
                containing the deposition information. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the published deposition. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}/actions/publish"
        response = self._req.post(url, **kwargs)
        return response.json()
    
    def edit_deposition(self, deposition_id: Union[int,Dict], **kwargs) -> Dict:
        """Sets a specific deposition to the "edit" state on the InvenioRDM API. 
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to set to "edit", or a 
                dictionary containing the deposition information. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the edited deposition. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}/actions/edit"
        response = self._req.post(url, **kwargs)
        return response.json()
    
    def discard_deposition(self, deposition_id: Union[int,Dict], **kwargs) -> Dict:
        """Discards changes of a specific deposition on the InvenioRDM API. 
    
        Args: 
            deposition_id (Union[int,Dict]): The ID of the deposition to discard changes, or a 
                dictionary containing the deposition information. 
            **kwargs: Additional keyword arguments for the API request. 
    
        Returns: 
            dict: The response JSON containing the deposition with the discarded changes. 
    
        Raises: 
            APIResponseError: If the response status code indicates an error during the API request. 
        
        """ 
        if isinstance(deposition_id, dict):
            deposition_id = deposition_id['id']
        url = f"{self.base_url}/api/deposit/depositions/{deposition_id}/actions/discard"
        response = self._req.post(url, **kwargs)
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
    
    @property
    def request(self) -> _HTTPRequest:
        return self._req


