from __future__ import annotations

import abc 
from abc import abstractmethod
from typing import List, Tuple, Dict
import pandas as pd


class EnginesInterface(abc.ABCMeta):
    """ Defines an interface for the implementation Engines.

    This interface is designed to be extensible so that the algorithm can be adapted to consume data from 
    virtually any data source. It is defined as a metaclass that should
    """
    _eng_registry = {}
    engines_cfg = {}
    
    def __new__(cls, engines_cfg: Dict, **kwargs):
        namespace = type(cls).__prepare__(cls.__name__, cls.__bases__, **kwargs)
        obj = super().__new__(cls, cls.__name__, cls.__bases__, namespace, **kwargs)
        obj.engines_cfg = engines_cfg
        return obj
        

    def __init_subclass__(cls, name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if name is not None:
            cls._eng_registry[name] = cls
    
    @classmethod
    @abstractmethod
    def conn(cls):
        raise NotImplementedError

    # @classmethod
    # def __subclasshook__(cls, subclass):
    #     return (hasattr(subclass, 'get_db_connection') and 
    #             callable(subclass.get_db_connection) and 
    #             hasattr(subclass, 'close_db_connection') and 
    #             callable(subclass.close_db_connection) and
    #             hasattr(subclass, 'execute_query') and 
    #             callable(subclass.execute_query) and
    #             hasattr(subclass, 'read_data_from_db') and 
    #             callable(subclass.read_data_from_db) and
    #             hasattr(subclass, 'get_table_shape') and 
    #             callable(subclass.get_table_shape) and                               
    #             hasattr(subclass, 'get_table_columns') and 
    #             callable(subclass.get_table_columns) or 
    #             NotImplemented)
    

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