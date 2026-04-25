from __future__ import annotations

import abc
from abc import abstractmethod
from typing import List, Tuple, Dict
import pandas as pd


class EnginesInterface(abc.ABC):
    """ Defines an interface for the implementation Engines.

    This interface is designed to be extensible so that the algorithm can be adapted to consume data from 
    virtually any data source. It is defined as a metaclass that should
    """
    _eng_registry = {}
        
    @classmethod
    def __init_subclass__(cls, eng=None, **kwargs):
        super().__init_subclass__()
        if eng is not None:
            #super(cls,cls)._eng_registry[eng] = cls
            cls._eng_registry[eng] = cls
            cls.eng = cls
    
    @classmethod
    @abstractmethod
    def conn(cls):
        raise NotImplementedError
    

    @abc.abstractmethod
    def get_db_connection(self):
        raise NotImplementedError


    @abc.abstractmethod
    def close_db_connection(self):
        raise NotImplementedError


    @abc.abstractmethod
    def execute_query(self, query: str):
        raise NotImplementedError


    @abc.abstractmethod
    def read_data_from_db(self, query: str) -> pd.DataFrame:
        raise NotImplementedError


    @abc.abstractmethod
    def get_table_shape(self, table_schema: str, table_name: str) -> Tuple[int,int]:
        raise NotImplementedError


    @abc.abstractmethod
    def get_table_columns(self, table_schema: str, table_name: str) -> List[str]:
        raise NotImplementedError
    
    
    @abc.abstractmethod
    def join_aud_ds_query(self, **kwargs) -> str:
        raise NotImplementedError
    
    @abc.abstractmethod
    def read_data_batch(self, **kwargs) -> str:
        raise NotImplementedError

    