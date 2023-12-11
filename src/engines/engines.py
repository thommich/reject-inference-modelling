from __future__ import annotations

import abc 
from abc import abstractmethod
from typing import List, Callable, Tuple, Dict
import pandas as pd

class EngineFactory:
    """Factory for creating all different types of engine objects"""
    
#    @module_logger
    def __init__(self, eng_params: Dict, builders: Dict):
        """
        Initializes the new Engine Factory object

        Parameters
        ----------
        eng_params : Dict
            Dictionary of engine parameters
        builders : Dict
            Container to hold the available engine builders
        """
        self.eng_params = eng_params
        self._builders = builders
    
    
#    @module_logger
    def register_builder(self, flavour: str, builder: Callable):
        """
        Register a new builder to the factory

        Parameters
        ----------
        flavour : str
            A name that designates the type of the DBMS served by the engine
        builder : Callable
            The custom builder developed for the engine's creation
        """
        self._builders[flavour] = builder(self.eng_params)


#    @module_logger
    def create(self, flavour:str) -> EnginesInterface:
        """
        Retrieves and calls the appropiate builder using the name provided by the 'flavour' parameter

        Parameters
        ----------
        flavour : str
            A name that designates the type of the DBMS engine

        Returns
        -------
        EnginesInterface
            The Engine object created by the builder

        Raises
        ------
        ValueError
            If the 'flavour' parameter doesn't correspond to a previously registered builder
        """
        builder = self._builders.get(flavour)
        
        if not builder:
            raise ValueError("No engine specified for the value {flavour}")
        
        return builder()
    
    
#    @module_logger
    def get(self, flavour: str) -> EnginesInterface:
        """
        Calls the 'create' method on the instance itself passing down the 'flavour' parameter

        Parameters
        ----------
        flavour : str
            A name that designates the type of the DBMS served by the engine

        Returns
        -------
        EnginesInterface
            The Engine object created by the builder
        """
        return self.create(flavour)    




class EngineInstanceProvider(EngineFactory):
        
#    @module_logger
    def __init__(self, eng_params: Dict) -> None:
        self._builders = {}
        super().__init__(eng_params, self._builders)
        
        
#    @module_logger                
    def get(self, flavour: str) -> EnginesInterface:
        return self.create(flavour)



class EnginesInterface(metaclass=abc.ABCMeta):
    """

    """
    @property
    @abstractmethod
    def name(self):
        raise NotImplementedError
    
    @classmethod
    @property
    @abstractmethod
    def conn(cls):#cls):
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
    
    
    @abc.abstractmethod
    def join_aud_ds_query(self, **kwargs) -> str:
        raise NotImplementedError
    
    @abc.abstractmethod
    def read_data_batch(self, **kwargs) -> str:
        raise NotImplementedError
    
    
# class EnginesBuilder(metaclass=abc.ABCMeta):
#     pass