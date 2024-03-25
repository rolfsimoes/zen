from __future__ import annotations
from typing import Tuple, List, Dict, Any, Optional, Union, Iterator, TYPE_CHECKING
from typing_extensions import Self
from .api import _Request
from .api import Zenodo
from .utils import load_json, save_json

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

def list_drafts(token: str, 
                q: Optional[str]=None, 
                sort: str=None, 
                size: int=10, 
                page: int=1, 
                all_versions: bool=False,
                base_url=Zenodo.url, 
                params: Optional[Dict[str,str]]=None, 
                headers: Optional[Dict[str,str]]=None) -> Draft:
    req = _Request(base_url=base_url, token=token, params=params, headers=headers)
    query = dict(q=q, sort=sort, size=size, page=page, allversions=all_versions)
    response = req.get(f'/api/user/records', params=query)
    return response.json()

def create_draft(token: str,
                 record_access=access_public(),
                 files_enabled=True,
                 base_url=Zenodo.url, 
                 params: Optional[Dict[str,str]]=None, 
                 headers: Optional[Dict[str,str]]=None) -> Draft:
    req = _Request(base_url, token, params, headers)
    body = dict(access=record_access, files=dict(enabled=files_enabled))
    response = req.post(f'/api/records', json=body)
    data = response.json()
    return Draft(data=data, token=token, base_url=base_url, params=params, headers=headers)

def get_draft(id: str, 
              token: str,
              base_url=Zenodo.url, 
              params: Optional[Dict[str,str]]=None, 
              headers: Optional[Dict[str,str]]=None) -> Draft:
    req = _Request(base_url, token, params, headers)
    response = req.get(f'/api/records/{id}/draft')
    data = response.json()
    return Draft(data=data, token=token, base_url=base_url, params=params, headers=headers)

def load_draft(filename: str,
               token: str,
               base_url=Zenodo.url, 
               params: Optional[Dict[str,str]]=None, 
               headers: Optional[Dict[str,str]]=None) -> Draft:
    try:
        data = load_json(file=filename)
        if not isinstance(data, dict):
            raise TypeError('Invalid file content. Expecting `dict` ' +
                            f'but got `{type(data)}` instead.')
        if 'id' not in data:
            raise ValueError('Invalid file content. `id` entry not found.')
        id = data['id']
        return get_draft(id, token=token, base_url=base_url, params=params, headers=headers)
    except FileNotFoundError:
        raise FileNotFoundError(f'File `{filename}` not found.')

def load_or_create_draft(filename: str,
                         token: str,
                         record_access=access_public(),
                         files_enabled=True,
                         base_url=Zenodo.url, 
                         params: Optional[Dict[str,str]]=None, 
                         headers: Optional[Dict[str,str]]=None) -> Draft:
    try:
        return load_draft(filename=filename, token=token, base_url=base_url, params=params, 
                          headers=headers)
    except FileNotFoundError:
        data = create_draft(token=token, record_access=record_access, 
                            files_enabled=files_enabled, base_url=base_url, params=params, 
                            headers=headers)
        save_json(data=data, file=filename)

class Draft:
    """Represents a new record
    
    Used for interacting with unpublished or edited draft records.
    
    Args:
        base_url (Zenodo): The Zenodo instance used to interact with Zenodo API.
        data (Dict[str,Any]): The deposition data, including 'id', 'metadata', 'files', 
            and 'links' entries.
    
    Examples:
    
        1. Create a new Zenodo deposition:
        
        >>> from zen import Zenodo
        >>> zen = Zenodo(url=Zenodo.sandbox_url, token='your_api_token')
        >>> meta = {
        ...     'title': 'My New Deposition',
        ...     'description': 'A test deposition for demonstration purposes.'
        ... }
        >>> dep = zen.depositions.create(metadata=meta)
        >>> print(dep.id)  # print the deposition id

        2. Retrieve an existing Zenodo deposition by id:

        >>> deposition_id = dep.id
        >>> existing_dep = zen.depositions.retrieve(deposition_id)
        
        3. Modifying deposition metadata
        
        >>> dep.metadata.title = 'New Deposition Title'
        >>> dep.metadata.access_right.set_open('cc-by')
        >>> dep.update()  # Commit changes
        
        Discard the deposition example.
        
        >>> dep.discard()
    
    """ 
    def __init__(self, data: Dict[str,Any], token: str, 
                 base_url: str=Zenodo.url, 
                 params: Optional[Dict[str,str]]=None, 
                 headers: Optional[Dict[str,str]]=None) -> None:
        if not isinstance(data, dict):
            raise TypeError('Invalid `data` parameter. Expecting `dict` ' +
                            f'but got `{type(data)}` instead.')
        if 'id' not in data:
            raise ValueError('Invalid data parameter. `id` entry not found.')
        self._data = data
        self._req = _Request(base_url, token, params, headers)

    def refresh(self) -> Self:
        """Refreshes the draft data from API.
        
        This method sends a request to the API to fetch the most up-to-date details
        about the draft record. It discards any non-saved editions.
        
        Returns:
            Draft: The current refreshed Draft object.

        Raises:
            APIResponseError: If the response status code indicates an error during 
            the API request.
        """
        response = self._req.get(f'/api/records/{self.id}/draft')
        self._data = response.json()
        return self

    def save(self, custom_fields: Optional[List[str]]=None) -> Self:
        """Saves changes made to the draft.
        
        This method saves the draft's editions on its metadata property.
        
        Returns:
            Draft: The current Draft object.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        body_fields = ['access', 'files', 'metadata']
        if custom_fields is not None:
            if not isinstance(custom_fields, list):
                raise TypeError('Invalid `custom_fields` parameter. Expecting `list` ' +
                                f'but got {type(custom_fields)} instead.')
            if not all([isinstance(field, str) for field in custom_fields]):
                raise ValueError('Invalid `custom_fields` parameter. Not all elements are `str`.')
            body_fields += custom_fields
        body = {field: self._data[field] for field in body_fields}
        self._req.put(f'/api/records/{self.id}/draft', json=body)
        return self

    def publish(self) -> Self:
        """Publishes the draft.
        
        This method sends a request to publish the draft.
        
        Returns:
            Draft: The current Draft object.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        response = self._req.post('/api/records/{id}/draft/actions/publish')
        self._data = response.json()
        return self

    def edit(self) -> Self:
        """Edit a published record.
        
        Create a draft record from a published record.

        Returns:
            Draft: The current Draft object.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        response = self._req.post('/api/records/{id}/draft')
        self._data = response.json()
        return self

    def delete(self) -> None:
        """Discards the draft's editions.
        
        Deleting a draft for an unpublished record will remove the draft and associated files 
        from the system.
        
        Deleting a draft for a published record will remove the draft but not the published record.
        
        Returns:
            None.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        self._req.delete('/api/records/{id}/draft')
    
    def to_json(self, filename: str) -> None:
        """Saves the draft data to a JSON file.

        Args:
            filename (str): The name of the JSON file to save.

        Raises:
            FileNotFoundError: If the file cannot be created or written to.
        """
        save_json(data=self._data, file=filename)

    @property
    def id(self) -> str:
        """Returns the ID of the record."""
        return self._data['id']

    @property
    def concept_id(self) -> str:
        """Returns the concept ID of the record."""
        if 'conceptrecid' in self._data and self._data['conceptrecid'] != '':
            return self._data['conceptrecid']

    @property
    def doi(self) -> str:
        """Returns the DOI of the record."""
        # Implement logic to fetch DOI from draft data
        pass

    @property
    def title(self) -> str:
        """Returns the title of the record."""
        if 'title' in self._data:
            return self._data['title']
        return ''

    @property
    def is_editing(self) -> bool:
        """Returns True if the draft is in editing mode, False otherwise."""
        # Implement logic to check if the draft is in editing mode
        pass

    @property
    def is_published(self) -> bool:
        """Returns True if the draft is published, False otherwise."""
        # Implement logic to check if the draft is published
        pass

    @property
    def metadata(self) -> Dict:
        """Returns the metadata of the draft."""
        # Implement logic to fetch metadata from draft data
        pass

    @property
    def files(self) -> Dict:
        """Returns the files attached to the draft."""
        # Implement logic to fetch files from draft data
        pass
