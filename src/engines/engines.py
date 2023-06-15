from __future__ import annotations

import abc 
from abc import abstractmethod
from typing import List, Type, Tuple, Dict
import pandas as pd
import logging

# Create Logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Create stream handler
handler = logging.StreamHandler()
    
handler.setLevel(logging.INFO)
handler.setFormatter(logging.Formatter(
    '%(asctime)s|%(name)s|%(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))

# Add handler to Logger
logger.addHandler(handler)


class EngineFactory:
    
    def __init__(self, eng_params: Dict, builders: Dict):
        self.eng_params = eng_params
        self._builders = builders
    
    def register_builder(self, flavour, builder):
        self._builders[flavour] = builder(self.eng_params)

    def create(self, flavour) -> Type[EnginesInterface]:
        builder = self._builders.get(flavour)
        if not builder:
            raise ValueError(flavour)
        return builder()
    
    def get(self, flavour):
        return self.create(flavour)    




class EngineInstanceProvider(EngineFactory):
        
    def __init__(self, eng_params: Dict) -> None:
        self._builders = {}
        super().__init__(eng_params, self._builders)
        
                        
    def get(self, flavour: str) -> Type[EnginesInterface]:
        return self.create(flavour)



class EnginesInterface(metaclass=abc.ABCMeta):
    """

    """
    @property
    @abstractmethod
    def name(cls):
        raise NotImplementedError
    
    @classmethod
    @property
    @abstractmethod
    def conn(self):#cls):
        raise NotImplementedError

    @classmethod
    def __subclasshook__(cls, subclass):
        return (hasattr(subclass, 'get_db_connection') and 
                callable(subclass.get_db_connection) and 
                hasattr(subclass, 'close_db_connection') and 
                callable(subclass.close_db_connection) and
                hasattr(subclass, 'execute_query') and 
                callable(subclass.execute_query) and
                hasattr(subclass, 'read_data_from_db') and 
                callable(subclass.read_data_from_db) and
                hasattr(subclass, 'get_table_shape') and 
                callable(subclass.get_table_shape) and                               
                hasattr(subclass, 'get_table_columns') and 
                callable(subclass.get_table_columns) or 
                NotImplemented)
    
    @abc.abstractmethod
    def __init__(self, engines_cfg: Dict[str,dict]):
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