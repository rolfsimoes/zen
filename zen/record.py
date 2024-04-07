from __future__ import annotations
from typing import Tuple, List, Dict, Any, Optional, Union, Iterator, TYPE_CHECKING
from typing_extensions import Self
if TYPE_CHECKING:
    from .invenioRDM import InvenioRDM
import os
from time import sleep
from random import randint
from .utils import save_json, download_file
from tqdm import tqdm
from tqdm.utils import CallbackIOWrapper


accepted_schemas = ('http://', 'https://')

class RecordFile:
    def __init__(self, data: Dict[str,Any], api: InvenioRDM) -> None:
        self._api = api
        self._data = data
    
    def __repr__(self):
        return self.data.__repr__()
    
    def download(self, filename: str):
        url: str = self.links['content']
        if not url.startswith(accepted_schemas):
            raise ValueError(f"Invalid `url` parameter. URL '{url}' is invalid.")
        response = self.api.http_get(url=url, stream=True)
        with open(filename, 'wb') as file:
            for chunk in response.iter_content(chunk_size=4096):
                if chunk:
                    file.write(chunk)
        return filename
        
    @property
    def key(self) -> str:
        return self.data['key']
    
    @property
    def size(self) -> int:
        return self.data['size']
    
    @property
    def checksum(self) -> str:
        return self.data['checksum']
    
    @property
    def status(self) -> str:
        return self.data['status']
    
    @property
    def links(self) -> Dict[str,Any]:
        return self.data['links']
    
    @property
    def data(self):
        return self._data
    
    @property
    def api(self) -> InvenioRDM:
        return self._api


class DraftFile(RecordFile):
    def __init__(self, data: Dict[str,Any], api: InvenioRDM) -> None:
        super().__init__(data, api)
    
    def upload(self, filename: str, quietly: bool=False):
        file_size = os.path.getsize(filename)
        headers = {'Content-Type': 'application/octet-stream'}
        with open(filename, 'rb') as _data:
            with tqdm(total=file_size, disable=quietly, unit="B", unit_scale=True, unit_divisor=1024) as pb:
                data = CallbackIOWrapper(pb.update, _data, "read")
                self.api.http_put(url=self.links['content'], data=data, headers=headers)
                            
    def commit(self, quietly: bool=False):
        url = self.links['commit']
        self.api.http_post(url=url)
        if not quietly: print(f"File '{self.key}' uploaded.")
    
    def delete(self, quietly: bool=False):
        url = self.links['self']
        self.api.http_delete(url=url)
        if not quietly: print(f"File '{self.key}' was deleted.")


class RecordFiles:
    def __init__(self, data: Dict[str,Any], api: InvenioRDM) -> None:
        self._api = api
        self._data = data
    
    def __getitem__(self, key: str) -> RecordFile:
        index = self.keys().index(key)
        return RecordFile(self.data['entries'][index], self.api)
    
    def __len__(self) -> int:
        return len(self.data['entries'])
    
    def __iter__(self) -> Iterator[RecordFile]:
        for item in self.data['entries']:
            yield RecordFile(item, self.api)
    
    def __repr__(self):
        return self.data['entries'].__repr__()
    
    def keys(self) -> List[str]:
        return [file['key'] for file in self.data['entries']]
    
    @property
    def links(self):
        return self.data['links']
    
    @property
    def data(self):
        return self._data
    
    @property
    def api(self) -> InvenioRDM:
        return self._api


class DraftFiles(RecordFiles):
    def __init__(self, data: Dict[str,Any], api: InvenioRDM) -> None:
        super().__init__(data, api)
    
    def __getitem__(self, key: str) -> DraftFile:
        item = super().__getitem__(key)
        return DraftFile(item.data, item.api)
    
    def __iter__(self) -> Iterator[DraftFile]:
        for item in self.data['entries']:
            yield DraftFile(item, self.api)
    
    def create(self, key: str) -> DraftFile:
        url = self.links['self']
        response = self.api.http_post(url=url, json=[{'key': key}])
        files = DraftFiles(response.json(), self.api)
        return files[key]


class Record:
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
        if not isinstance(data, dict):
            raise TypeError('Invalid data content. Expecting `dict` ' +
                            f'but got `{type(data)}` instead.')
        if 'id' not in data:
            raise ValueError('Invalid data content. `id` entry not found.')
        if 'links' not in data:
            raise ValueError('Invalid data content. `links` entry not found.')
        self._data = data
        self._api = api
        self.refresh_files()
    
    def refresh(self) -> Self:
        """Refreshes the record data.
        
        This method sends a request to the API to fetch the most up-to-date details
        about the record. It discards any non-saved editions.
        
        Returns:
            BaseRecord: The current refreshed object.

        Raises:
            APIResponseError: If the response status code indicates an error during 
            the API request.
        """
        url = self.links['self']
        response = self.api.http_get(url)
        self._data = response.json()
        self.refresh_files()
        return self
    
    def refresh_files(self) -> Self:
        url = self.links['files']
        response = self.api.http_get(url)
        data = response.json()
        self._data['files'] = data
        return self
    
    def to_json(self, filename: str) -> None:
        """Saves the record data to a JSON file.

        Args:
            filename (str): The name of the JSON file to save.

        Raises:
            FileNotFoundError: If the file cannot be created or written to.
        """
        save_json(self._data, filename)
    
    @property
    def access(self) -> Union[str,Dict[str,Any]]:
        if 'access' in self._data: # not implemented by Zenodo
            return self._data['access']
        if 'access_right' in self.metadata:
            return self.metadata['access_right']

    @property
    def files(self) -> RecordFiles:
        return RecordFiles(self._data['files'], self.api)

    @property
    def id(self) -> str:
        return self._data['id']
    
    @property
    def links(self) -> Dict[str,Any]:
        return self._data['links']
    
    @property
    def metadata(self) -> Dict[str,Any]:
        return self._data['metadata']
    
    @property
    def data(self) -> Dict[str,Any]:
        return self._data
    
    @property
    def api(self) -> InvenioRDM:
        return self._api


class Draft(Record):
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
    
    def update(self, quietly: bool=False) -> Self:
        """Updates changes made to the draft.
        
        This method updates the draft's editions on the API.
        
        Returns:
            Draft: The current Draft object.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        url = self.links['self']
        self.api.http_put(url, json=self.data)
        if not quietly: print(f"Draft (id={self.id}) updated.")
        return self

    def publish(self, quietly: bool=False) -> Self:
        """Publishes the draft.
        
        This method sends a request to publish the draft.
        
        Returns:
            Draft: The current Draft object.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        url = self.links['publish']
        self.api.http_post(url)
        if not quietly: print(f"Draft (id={self.id}) updated.")
        return self

    def edit(self, quietly: bool=False) -> Self:
        """Edit a published record.
        
        Create a draft record from a published record.

        Returns:
            Draft: The current Draft object.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        url = self.links['self']
        response = self.api.http_post(url)
        data = response.json()
        draft = Draft(data, self.api)
        draft.refresh_files()
        if not quietly: print(f"New Draft (id={draft.id}) created.")
        return draft

    def delete(self, quietly: bool=False) -> None:
        """Discards the draft's editions.
        
        Deleting a draft for an unpublished record will remove the draft and associated files 
        from the system.
        
        Deleting a draft for a published record will remove the draft but not the published record.
        
        Returns:
            None.

        Raises:
            APIResponseError: If the response status code indicates an error during the API request.
        """
        url = self.links['self']
        self.api.http_delete(url)
        if not quietly: print(f"Draft (id={self.id}) deleted.")
    
    def upload_file(self, 
                    filename: str, 
                    key: Optional[str]=None,
                    max_retries: int=15,
                    min_delay: int=10, 
                    max_delay: int=60,
                    quietly: bool=False):
        if not os.path.isfile(filename) and not filename.startswith(accepted_schemas):
            raise ValueError(f"Invalid `file` parameter. File '{filename}' is invalid.")
        if key is None:
            key = os.path.basename(filename)
        # start file upload preparation
        uploaded = False
        file = self.files.create(key)
        # try download file if it is a remote address
        try:
            tempfile = None
            if filename.startswith(accepted_schemas):
                tempdir = os.path.join(os.getcwd(), '.zen')
                if not os.path.isdir(tempdir):
                    os.makedirs(tempdir)
                tempfile = os.path.join(tempdir, os.path.basename(filename))
                filename = download_file(filename, tempfile)
            # try upload with retries
            retries = 1
            while not uploaded:
                try:
                    # upload
                    file.upload(filename, quietly)
                    # commit
                    file.commit(quietly)
                    uploaded = True # success, exit while loop!
                except Exception as e:
                    if not quietly: print(f"Attempt {retries} failed:", e)
                    if retries >= max_retries:
                        raise RuntimeError("Max retries exceeded.")  
                    random_delay = randint(min_delay, max_delay)
                    if not quietly: print(f"Retrying in {random_delay} seconds...")
                    sleep(random_delay)  # wait random delay
                    retries += 1
        finally:
            if uploaded:
                self.refresh_files()
            else:
                file.delete(quietly)
            if tempfile is not None:
                os.remove(tempfile)
    
    @property
    def files(self) -> DraftFiles:
        return DraftFiles(self._data['files'], self.api)

    @property
    def concept_id(self) -> str:
        """Returns the concept ID of the record."""
        if 'conceptrecid' in self._data and self._data['conceptrecid'] != '':
            return self._data['conceptrecid']
    
    @property
    def is_published(self) -> bool:
        """Returns True if the draft is published, False otherwise."""
        if 'is_published' in self._data:
            return self._data['is_published']
        if 'submitted' in self._data:
            return self._data['submitted']
