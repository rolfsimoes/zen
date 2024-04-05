from __future__ import annotations
from typing import Tuple, List, Dict, Any, Optional, Union, Iterator, TYPE_CHECKING
from typing_extensions import Self

from zen.record import Draft
from .invenioRDM import InvenioRDM


dict(upload_type='dataset', 
     publication_date='',
     access_right='open',
     license='cc-zero',
     prereserve_doi=True)

class Zenodo(InvenioRDM):
    def create_draft(self, 
                     params: Optional[Dict[str, str]]=None, 
                     headers: Optional[Dict[str, str]]=None, 
                     quietly: bool=False) -> Draft:
        draft = super().create_draft(params, headers, quietly)
        draft.data['metadata']