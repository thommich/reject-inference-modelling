from __future__ import annotations

from typing import Union, List, Tuple, Any, Mapping, Dict, Optional
from engines.engines import EnginesInterface
import pandas as pd
from dataclasses import dataclass


@dataclass
class DataSource:
    
    
#    @module_logger
    def __init__(self, ds_info: Mapping[str, Any], engine: EnginesInterface):
        self.alias: str = ds_info['alias']
        self.ds_details: Dict[str,Any] = ds_info['ds_details']
        self.engine_name: str = self.ds_details['engine']
        self.schema: str = self.ds_details['schema']
        self.physical_name: str = self.ds_details['physical_name']
        self.fields_to_remove: Union[str,List[str]] = self.ds_details['fields_to_remove']
        self.engine: EnginesInterface = engine
        self.shape: Tuple[int,int] = self.get_shape()
        self.columns: List[str] = self.get_columns()
        self.data_batch: pd.DataFrame
        self.candidate_features = []
        self.top_rnkd_feats = []
        

#    @module_logger
    def get_shape(self) -> Tuple[int,int]:
        eng = self.engine
        return eng.get_table_shape(self.schema, self.physical_name)


#    @module_logger
    def get_columns(self) ->  List[str]:
        return self.engine.get_table_columns(self.schema, self.physical_name)


#    @module_logger
    def get_columns_count(self) ->  int:
        if self.columns is not None:
             return len(self.columns)
        
        return 0
    
    
#    @module_logger
    def has_data(self) -> bool:
        return True if self.shape else False