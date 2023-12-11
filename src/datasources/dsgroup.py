from __future__ import annotations

from typing import Dict, Tuple, List, Union, Any, Optional, Mapping, Sequence
import pandas as pd
import fastparquet as fp
from engines.engines import EngineInstanceProvider
#from engines.teradata import TeradataEngineBuilder
#from engines.hadoop import HadoopEngineBuilder
from engines.sqlite import SQLiteEngineBuilder
from .dsmodel import DataSource

class DataSourcesGroup():
    
    #@module_logger                                  
    def __init__(self, ds_config: Dict[str,Dict[str,Union[str, Dict[str,Union[str,List[str], None]]]]], engines_config: Dict[str,Dict[str,List[str]]]):
        self.engines_factory = self.__init_engines_factory(engines_config)
        self.df_audience, self.data_sources = self.__init_data_sources(ds_config)
        self.current_ds: DataSource
        self.top_ranked_feats = []


    #Registers the builders for all the possible engines declared on the config file
    #@module_logger
    def __init_engines_factory(self, eng_params: Dict[str,Dict]) -> EngineInstanceProvider:
        engines_factory = EngineInstanceProvider(eng_params)
        engines_factory.register_builder('SQLITE', SQLiteEngineBuilder)
        #engines_factory.register_builder('TERADATA', TeradataEngineBuilder)
        #engines_factory.register_builder('HADOOP', HadoopEngineBuilder)
        return engines_factory


    # Returns the entity containing data about the audience used for modelling
    #@module_logger
    def _init_audience_df(self, pub_ds_config: Mapping[str,Any]) -> DataSource:
        aud_engine = self.engines_factory.get(pub_ds_config['ds_details']['engine'])
        
        aud_ds = DataSource(pub_ds_config, aud_engine) 
        self.audience_pk = pub_ds_config['audience_pk']

        parquet_file_path = './tmp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, aud_ds.alias.upper(), '.parquet'])
        
        self.current_ds = aud_ds
        data_batch = self.get_data_batch(aud_ds.columns, aud_ds.schema, aud_ds.physical_name)
        
        fp.write(parquet_file, data_batch, compression='SNAPPY')

        return aud_ds
    

    #Binds the data source parameters to a different instance of DataSource each
    #@module_logger
    def __init_data_sources (self, ds_config: Dict[str,Any]) -> Tuple:
      
        aud_ds_config = ds_config['AUDIENCE_TABLE']
        
        ds_audience = self._init_audience_df(aud_ds_config)
        
        data_sources_dict = {}
        #data_sources_dict[ds_audience.alias] = ds_audience
        ds_list = [ds_info for ds_info in ds_config if ds_info != 'AUDIENCE_TABLE']
                                                          
        for ds_info in ds_list:
            config_dict = ds_config[ds_info]
            new_engine = self.engines_factory.get(config_dict['ds_details']['engine'])

            new_ds = DataSource(config_dict, new_engine)

            data_sources_dict[new_ds.alias] = new_ds

        return ds_audience, data_sources_dict


    #@module_logger
    def get_data_batch(self, columns_to_read: List[str], table_schema: str, table_name: str) -> pd.DataFrame:        
        new_engine = self.engines_factory.get(self.current_ds.engine_name)
                
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
    
        # df['PK_DATREF_XX'] = pd.to_datetime(df['PK_DATREF_XX'])
        # df['PK_DATVER_XX'] = pd.to_datetime(df['PK_DATVER_XX'])

        # return df


    #@module_logger
    def left_join_audience_tb(self, 
                              data_source: DataSource, 
                              mob: int,
                              approved_column: str,
                              target_column: str) -> None:
        
        new_engine = self.engines_factory.get(data_source.engine_name)
        
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
























# uow = DataSourceHandler()

# def get_all_account_balances(
#     uow: IDataSourcesHandler,
# ) -> float:
#     with uow:
#         accounts = uow.data_sources.get_all()
    
#     return sum([account.balance for account in accounts])


# all_account_balances = get_all_account_balances(uow)