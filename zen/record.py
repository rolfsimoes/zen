from __future__ import annotations
from typing import Tuple, List, Dict, Any, Optional, Union, Iterator, TYPE_CHECKING
from typing_extensions import Self
if TYPE_CHECKING:
    from .invenioRDM import InvenioRDM
from .utils import save_json

class _BaseRecord:
    def __init__(self, data: Dict[str,Any], api: InvenioRDM) -> None:
        if not isinstance(data, dict):
            raise TypeError('Invalid `data` parameter. Expecting `dict` ' +
                            f'but got `{type(data)}` instead.')
        if 'id' not in data:
            raise ValueError('Invalid data parameter. `id` entry not found.')
        self._data = data
        self._api = api
    
    def to_json(self, filename: str) -> None:
        """Saves the draft data to a JSON file.

        Args:
            filename (str): The name of the JSON file to save.

        Raises:
            FileNotFoundError: If the file cannot be created or written to.
        """
        save_json(self._data, filename)
    
    @property
    def access(self) -> Dict:
        if 'access' in self._data:
            return self._data['access']

    @property
    def files(self) -> Dict:
        return self._data['files']

    @property
    def id(self) -> str:
        return self._data['id']
    
    @property
    def links(self) -> Dict:
        return self._data['links']
    
    @property
    def metadata(self) -> Dict:
        return self._data['metadata']
    
    @property
    def data(self) -> Dict[str,Any]:
        return self._data
    
    @property
    def api(self) -> InvenioRDM:
        return self._api


class Draft(_BaseRecord):
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
    def __init__(self, data: Dict[str,Any], api: InvenioRDM) -> None:
        super().__init__(data, api)
    
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
        response = self._api._get(f'/api/records/{self.id}/draft')
        self._data = response.json()
        return self

    def update(self, custom_fields: Optional[List[str]]=None) -> Self:
        """Updates changes made to the draft.
        
        This method updates the draft's editions on the API.
        
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
        self._api._put(f'/api/records/{self.id}/draft', json=body)
        return self

    def publish(self) -> Self:
        """Publishes the draft.
        
        This method sends a request to publish the draft.
        
        Returns:
            Draft: The current Draft object.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        response = self._api._post(f'/api/records/{self.id}/draft/actions/publish')
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
        response = self._api._post(f'/api/records/{self.id}/draft')
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
        self._api._delete(f'/api/records/{self.id}/draft')

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
    def access(self) -> Dict:
        """Returns the access policy of the draft."""
        return super().access

    @property
    def files(self) -> Dict:
        """Returns the files attached to the draft."""
        return super().files

    @property
    def id(self) -> str:
        """Returns the ID of the record."""
        return super().id
    
    @property
    def is_published(self) -> bool:
        """Returns True if the draft is published, False otherwise."""
        if 'is_published' in self._data:
            return self._data['is_published']
        if 'submitted' in self._data:
            return self._data['submitted']
    
    @property
    def links(self) -> Dict:
        """Returns the links of the draft."""
        return super().links
    
    @property
    def metadata(self) -> Dict:
        """Returns the metadata of the draft."""
        return super().metadata
    
    @property
    def data(self) -> Dict[str,Any]:
        """Returns the associated record of the draft."""
        return super().data
    
    @property
    def api(self) -> InvenioRDM:
        """Returns the associated API client of the draft."""
        return super().api
    
class Record(_BaseRecord):
    """Represents an record
    
    Used for interacting with published records.
    
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
    def __init__(self, data: Dict[str,Any], api: InvenioRDM) -> None:
        super().__init__(data, api)
    
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
        response = self._api._get(f'/api/records/{self.id}')
        self._data = response.json()
        return self
    
    @property
    def access(self) -> Dict:
        """Returns the access policy of the record."""
        return super().access

    @property
    def files(self) -> Dict:
        """Returns the files attached to the record."""
        return super().files

    @property
    def id(self) -> str:
        """Returns the ID of the record."""
        return super().id
    
    @property
    def links(self) -> Dict:
        """Returns the links of the record."""
        return super().links
    
    @property
    def metadata(self) -> Dict:
        """Returns the metadata of the record."""
        return super().metadata
    
    @property
    def data(self) -> Dict[str,Any]:
        """Returns the associated record of the record."""
        return super().data
    
    @property
    def api(self) -> InvenioRDM:
        """Returns the associated API client of the draft."""
        return super().api