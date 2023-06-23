from __future__ import annotations

from typing import Union, List, Tuple, Any, Mapping, Dict, Iterable, Sequence, MappingView, Collection, Iterator, MutableSequence, Type
from engines.engines import EnginesInterface
import pandas as pd
from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader



@dataclass
class DataSource:
    # alias: str
    # ds_details: Dict[str,Union[str,None]]
    # engine_name: str
    # schema: str
    # physical_name: str
    # fields_to_remove: Union[List[str], None]
    # engine: EnginesInterface
    # shape: Tuple[int,int]
    # columns: Union[List[str], None,List[None]]
    # data_batch: pd.DataFrame
    # candidate_features: List[str]
    # top_rnkd_feats: List[str]
    
    def __init__(self, ds_info: Mapping[str,Any], engine:EnginesInterface):
        self.alias: str = ds_info['alias']
        self.ds_details: Dict[str,Any] = ds_info['ds_details']
        self.engine_name: str = self.ds_details['engine']
        self.schema: str = self.ds_details['schema']
        self.physical_name: str = self.ds_details['physical_name']
        self.fields_to_remove: Union[str,List[str]] = self.ds_details['fields_to_remove']
        self.engine: EnginesInterface = engine
        self.shape: Tuple[int,int] = self.get_shape()
        self.columns: Sequence[str] = self.get_columns()
        #self.data_batch: pd.DataFrame
        self.candidate_features = []
        self.top_rnkd_feats = []
        
        
    def get_schema(self) -> Union[str,List[str]]:
        return self.schema


    def get_physical_name(self) -> Union[str,List[str]]:
        return self.physical_name


    def get_shape(self) -> Tuple[int,int]:
        eng = self.engine
        return eng.get_table_shape(self.physical_name, self.schema)

    def get_columns(self) ->  List[str]:
        return self.engine.get_table_columns(self.schema, self.physical_name)

    def get_columns_count(self) ->  Union[int, None]:
        # if self.columns is not None:
        #     return len(self.columns)
        return 12
        
    # def get_top_features(self) ->  Union[List[str],str]:
    #     return self.top_rnkd_feats
    
    
    def has_data(self) -> bool:
        return True if hasattr(self, 'ds_data') else False

    #Read data from DBMS
    def read_data_batch(self, columns_to_read: Sequence[str], audience_pk: List[str]) -> pd.DataFrame:         

        env = Environment(loader=FileSystemLoader('/templates'))
        query = env.get_template('read_batch_of_cols').render(columns_list=columns_to_read,
                                                              table_schema = self.schema,
                                                              table_name = self.physical_name,
                                                              primary_key = audience_pk)
        
        try:
            data_batch = self.engine.read_data_from_db(query)
        except Exception as err:
            raise err
        
        return data_batch