from __future__ import annotations

from typing import Dict, List, Union, Any, Mapping
import pandas as pd
import fastparquet as fp
from .dsmodel import DataSource
from engines.engines import EnginesInterface
import enum
from engines import *
from log_utils import setup_logging, log_func

logger = setup_logging(name=__name__)
module_logger = log_func(__name__)

class DataSourcesGroup():
    
    @module_logger                                  
    def __init__(self, ds_config: Dict[str,Dict[str,Union[str, Dict[str,Union[str,List[str], None]]]]], engines_config: Dict[str,Dict[str,List[str]]]):
        self.enginesEnum = self._init_engines_enum(engines_config)
        self.df_audience, self.data_sources = self._init_data_sources(ds_config)
        self.current_ds: DataSource
        self.top_ranked_feats = []

    @module_logger
    def _init_engines_enum(self, engines_config: Dict[str, Dict]):
        enum_members = {k: v for k, v in EnginesInterface(
            engines_config)._eng_registry.items() if k in engines_config.keys()}
        
        EnginesEnum = enum.Enum('EnginesEnum', enum_members, module=engines)
        #print(EnginesEnum)
        return EnginesEnum

#    @module_logger
#    def _init_engines(self, engines_config: Dict[str, Dict]):
#        eng_enum = self._init_engines_enum(engines_config)
#
#        ds_group_engines = {k,v for k,v }
#        
#        
#        EnginesEnum = enum.Enum('EnginesEnum', eng_registry, module=engines)
#        # print(EnginesEnum)
#        return EnginesEnum

    # Returns the entity containing data about the audience used for modelling
    @module_logger
    def _init_audience_df(self, pub_ds_config: Mapping[str,Any]) -> DataSource:        
        aud_engine = self.enginesEnum[pub_ds_config['ds_details']['engine']].value
        
        aud_ds = DataSource(pub_ds_config, aud_engine) # type: ignore
        self.audience_pk = pub_ds_config['audience_pk']

        parquet_file_path = './tmp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, aud_ds.alias.upper(), '.parquet'])
        
        self.current_ds = aud_ds
        data_batch = self.get_data_batch(aud_ds.columns, aud_ds.schema, aud_ds.physical_name)
        
        fp.write(parquet_file, data_batch, compression='SNAPPY')

        return aud_ds
    

    #Binds the data source parameters to a different instance of DataSource each
    @module_logger
    def _init_data_sources (self, ds_config: Dict[str,Any]):# -> Tuple:
        aud_ds_config = ds_config['AUDIENCE_TABLE']
        
        ds_audience = self._init_audience_df(aud_ds_config)
        
        data_sources_dict = {}
        ds_list = [ds_info for ds_info in ds_config if ds_info != 'AUDIENCE_TABLE']
                                                          
        for ds_info in ds_list:
            config_dict = ds_config[ds_info]
            new_engine = self.enginesEnum[config_dict['ds_details']['engine']]

            new_ds = DataSource(config_dict, new_engine) # type: ignore

            data_sources_dict[new_ds.alias] = new_ds

        return ds_audience, data_sources_dict


    #@module_logger
    def get_data_batch(self, columns_to_read: List[str], table_schema: str, table_name: str) -> pd.DataFrame:        
        new_engine = self.enginesEnum[self.current_ds.engine_name].value
                
        try:
            data_batch = new_engine.read_data_from_db(
                            new_engine.read_data_batch(
                                        columns_list=columns_to_read, 
                                        primary_key=self.audience_pk,
                                        table_schema=table_schema, 
                                        table_name= table_name))
        except Exception as err:
            raise err
        
        return data_batch


    @module_logger
    def left_join_audience_tb(self, 
                              data_source: DataSource, 
                              mob: int,
                              approved_column: str,
                              target_column: str) -> None:
        
        new_engine = self.enginesEnum[data_source.engine_name].value
        
        new_engine.execute_query(
            new_engine.join_aud_ds_query(
                                        aud_ds_physical_name=self.df_audience.physical_name,
                                        audience_pk = self.audience_pk,
                                        ds_alias=data_source.alias,
                                        ds_schema=data_source.schema, 
                                        ds_physical_name=data_source.physical_name,
                                        bk_features = [feat for feat in data_source.columns if feat not in self.audience_pk],
                                        approved_column = approved_column,
                                        target_column = target_column,
                                        mob=mob
                                        ))
        return


    #@module_logger
    def get_current_ds(self) -> DataSource:
        return self.current_ds
    
    
#if __name__ == "__main__":
#
#    engines_config = {'SQLITE': {'conn_vars': {'db_name': 'inference_modelling_test.db'}},
#                      'TERADATA': {'conn_vars': {'host': "10.0.2.15",
#                                                 'username': 'dbc',
#                                                 'password': None,
#                                                 'logmech': None}}}
#
#    ds = DataSourcesGroup({}, engines_config)
#
#    print(ds.enginesEnum.TERADATA.__dict__)
