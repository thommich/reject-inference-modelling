from __future__ import annotations

import abc 
from abc import abstractmethod
from typing import Any, List, Callable, Tuple, Dict
import pandas as pd
from enum import Enum, EnumMeta
#from engines.sqlite import SQLiteEngine
#from engines.teradata import TeradataEngine
#from engines.hadoop import HadoopEngine

#class EngineFactory:
#    """Factory for creating all different types of engine objects"""
#    
##    @module_logger
#    def __init__(self, eng_params: Dict, builders: Dict):
#        """
#        Initializes the new Engine Factory object
#
#        Parameters
#        ----------
#        eng_params : Dict
#            Dictionary of engine parameters
#        builders : Dict
#            Container to hold the available engine builders
#        """
#        self.eng_params = eng_params
#        self._builders = builders
#    
#    
##    @module_logger
#    def register_builder(self, flavour: str, builder: Callable):
#        """
#        Register a new builder to the factory
#
#        Parameters
#        ----------
#        flavour : str
#            A name that designates the type of the DBMS served by the engine
#        builder : Callable
#            The custom builder developed for the engine's creation
#        """
#        self._builders[flavour] = builder(self.eng_params)
#
#
##    @module_logger
#    def create(self, flavour:str) -> EnginesInterface:
#        """
#        Retrieves and calls the appropiate builder using the name provided by the 'flavour' parameter
#
#        Parameters
#        ----------
#        flavour : str
#            A name that designates the type of the DBMS engine
#
#        Returns
#        -------
#        EnginesInterface
#            The Engine object created by the builder
#
#        Raises
#        ------
#        ValueError
#            If the 'flavour' parameter doesn't correspond to a previously registered builder
#        """
#        builder = self._builders.get(flavour)
#        
#        if not builder:
#            raise ValueError("No engine specified for the value {flavour}")
#        
#        return builder()
#    
#    
##    @module_logger
#    def get(self, flavour: str) -> EnginesInterface:
#        """
#        Calls the 'create' method on the instance itself passing down the 'flavour' parameter
#
#        Parameters
#        ----------
#        flavour : str
#            A name that designates the type of the DBMS served by the engine
#
#        Returns
#        -------
#        EnginesInterface
#            The Engine object created by the builder
#        """
#        return self.create(flavour)    




#class EngineInstanceProvider(EngineFactory):
        
#    @module_logger
#    def __init__(self, eng_params: Dict) -> None:
#        self._builders = {}
#        super().__init__(eng_params, self._builders)
        
        
#    @module_logger                
#    def get(self, flavour: str) -> EnginesInterface:
#        return self.create(flavour)



class EnginesInterface(abc.ABCMeta):
    """

    """
    _eng_registry = {}
    engines_cfg = {}
    
    def __new__(cls, engines_cfg: Dict, **kwargs):
        namespace = type(cls).__prepare__(cls.__name__, cls.__bases__, **kwargs)
        obj = super().__new__(cls, cls.__name__, cls.__bases__, namespace, **kwargs)
        obj.engines_cfg = engines_cfg
        #print(obj.__dict__)
        return obj
        

    def __init_subclass__(cls, name=None, **kwargs):
        super().__init_subclass__(**kwargs)
        if name is not None:
            cls._eng_registry[name] = cls
    
    @classmethod
    @property
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
    

    

# class A(metaclass=abc.ABCMeta): pass
# class B(metaclass=EnumMeta): pass

# class ABCEnumMeta(abc.ABCMeta, EnumMeta): 

#     def __new__(cls, engines_cfg, **kwargs):
#         EnumMeta.__new__(EnumMeta, , **kwargs)
#         cls.engines_cfg = engines_cfg
            
    # def __init__(self, engines_cfg: Dict) -> None:
    #     self.engines_cfg = engines_cfg


# class EnginesEnum(EnginesInterface, Enum):#, metaclass=ABCEnumMeta):
    
#     def __new__(cls, engines_cfg, **kwargs):
#         value = 
#         obj = type(cls).__new__(cls, engines_cfg)
#         obj._value_ = value
#         obj.label = label
#         obj.unit = unit
#         return obj
    
#         value = len(cls.__members__) + 1
#         obj = object.__new__(cls)
#         obj._value_ = value
#         return obj
#         super().__new__(cls, **kwargs)
#         cls.engines_cfg = engines_cfg
    
#         def __new__(cls, *args):      # this is the only change from above
#         value = len(cls.__members__) + 1
#         obj = object.__new__(cls)
#         obj._value_ = value
#         return obj
#     # enum = super().__new__(metacls, cls, bases, classdict, **kwds)

    
#     def __init__(self, engines_cfg: Dict) -> None:
#         eng_registry = {
#             k: v for k, v in EnginesInterface._eng_registry.items() if k in engines_cfg.keys()}
        




# class ABCEnumMeta(abc.ABCMeta, enum.EnumMeta):

#     def __new__(cls, cls_value, cfg):
#         obj = cls_value.__class__.__init__(cfg)
#         obj._value_ = value
#         obj.extra = extra
#         return 

#     # def __new__(mcls, *args, **kw):
#     #     cls = super().__new__(mcls, *args, **kw)
#     #     if issubclass(cls, enum.Enum) and getattr(cls, "__abstractmethods__", None):
#     #         raise TypeError("...")
#     #     return cls

#     def __call__(cls, *args, **kw):
#         if getattr(cls, "__abstractmethods__", None):
#             raise TypeError(f"Can't instantiate abstract class {cls.__name__} "
#                             f"with frozen methods {set(cls.__abstractmethods__)}")
#         return super().__call__(*args, **kw)


# class EnginesEnum(EnginesInterface, enum.Enum, metaclass=ABCEnumMeta):
#     TERADATA = TeradataEngine
#     SQLITE = SQLiteEngine
#     # HADOOP = HadoopEngine
    
#     def __init__(self, engines_cfg: Dict) -> None:
#         super().__init__(engines_cfg)
#         self.engines_cfg = engines_cfg

#     def __call__(self) -> EnginesInterface:
#         return self.value(self.engines_cfg)
    




    
# class RepositoryType(Enum):
#     HG = auto()
#     GIT = auto()
#     SVN = auto()
#     PERFORCE = auto()


# class Repository():
#     _registry = {t: {} for t in RepositoryType}

#     def __init_subclass__(cls, scm_type=None, name=None, **kwargs):
#         super().__init_subclass__(**kwargs)
#         if scm_type is not None:
#             cls._registry[scm_type][name] = cls


# class MainHgRepository(Repository, scm_type=RepositoryType.HG, name='main'):
#     pass


# class GenericGitRepository(Repository, scm_type=RepositoryType.GIT):
#    pass






    

#from inference import InferenceModel as inf

# class Engines():
#     _registry = {}

#     def __init_subclass__(cls, name=None, **kwargs):
#         super().__init_subclass__(**kwargs)
#         if name is not None:
#             cls._registry[name] = cls


# class Engines(EnginesInterface, enum.Enum):
#     TERADATA = TeradataEngine
#     SQLITE = SQLiteEngine
    
#     def __new__(cls, value, cfg):
#         obj = object.__new__(cls,)
#         obj.value_ = value
#         obj.extra = extra
#         return


# class TeradataEngine(Engines, name="TERADATA"):
#     pass




# class NoValue(Enum):
#     def __repr__(self):
#         return '<%s.%s>' % (self.__class__.__name__, self.name)
    
# class AutoNumber(NoValue):
#     def __new__(cls, *args):      # this is the only change from above
#         value = len(cls.__members__) + 1
#         obj = object.__new__(cls)
#         obj._value_ = value
#         return obj
    
    
# class Swatch(AutoNumber):
#     def __init__(self, pantone='unknown'):
#         self.pantone = pantone
#     AUBURN = '3497'
#     SEA_GREEN = '1246'
#     BLEACHED_CORAL = () # New color, no Pantone code yet!










# if __name__ == "__main__":
#         #yaml_config_path = '../config/inference_config.yaml'
#         #_, engines_config, _ = #inf._load_config(yaml_config_path)
        
#         engines_config =   {'SQLITE': {'conn_vars': {'db_name': 'inference_modelling_test.db'}},            
#                             'TERADATA': {'conn_vars': {'host': "10.0.2.15",
#                                                     'username': 'dbc',
#                                                     'password': None,
#                                                     'logmech': None}}}
        
#         eng = EnginesEnum(engines_config)        
            
        print(eng)    
        #EngEnum = enum.Enum('EnginesEnum', eng.registry, module=__name__)
        
        #print(EngEnum)
        
        
        
        
        
#- eng int herda de abc e define os abstrct meths
#- engs enum é um mixin de eng intr e enum e onde def __new__ criando as inst eng iinter com super().__new