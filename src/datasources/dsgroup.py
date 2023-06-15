from __future__ import annotations

from typing import Dict, Tuple, List, Union, Any, ClassVar
import copy
import pandas as pd
import fastparquet as fp
from engines.engines import EngineInstanceProvider, EngineFactory
from engines.teradata import TeradataEngineBuilder
from engines.hadoop import HadoopEngineBuilder
from .dsmodel import DataSource
import teradatasql
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


class DataSourcesGroup():
    

    # data_sources_dict: ClassVar[Dict[str,DataSource]]

    def __init__(self, ds_config: Dict[str,Dict[str,Dict[str,List[str]]]], engines_config: Dict[str,Dict[str,List[str]]]):
        self.engines_factory = self.__init_engines_factory(engines_config)
        self.df_audience, self.data_sources = self.__init_data_sources(ds_config)
        self.current_ds: DataSource

        
    # def __enter__(self, flavour: str) -> Dict[str,DataSource]:
    #     self.engine = self.engines_factory.get(flavour)
    #     return self.data_sources
      

    # def __iter__(self) -> Dict[str,DataSource]:
    #     yield from self.data_sources



    #Registers the builders for all the possible engines declared on the config file
    def __init_engines_factory(self, eng_params: Dict[str,Dict]) -> EngineInstanceProvider:
        engines_factory = EngineInstanceProvider(eng_params)
        engines_factory.register_builder('TERADATA', TeradataEngineBuilder)
        #engines_factory.register_builder('HADOOP', HadoopEngineBuilder)
        return engines_factory

    # Returns the entity containing data about the audience used for modelling
    def _init_audience_df(self, pub_ds_config: Dict[str,Union[str,List[str]]]) -> DataSource:
        
        aud_engine = self.engines_factory.get(pub_ds_config['ds_details']['engine'])
        
        aud_ds = DataSource(pub_ds_config, aud_engine) 
        setattr(aud_ds, 'audience_pk', pub_ds_config['audience_pk'])

        parquet_file_path = '/temp/PQ_DATA_SOURCE_'
        parquet_file = ''.join([parquet_file_path, aud_ds.alias.upper(), '.parquet'])
        fp.write(parquet_file, aud_ds.data_batch, compression='SNAPPY', append=True)

        return aud_ds 
    

    #Binds the data source parameters to a different instance of DataSource each
    def __init_data_sources (self, ds_config: Dict[str,Dict[str,Union[str,List[str]]]]) -> Tuple:
        pub_ds_config = ds_config['AUDIENCE_TABLE']
        
        ds_audience = self._init_audience_df(pub_ds_config)
        
        data_sources_dict = {ds_audience.alias: ds_audience}
                                                           
        for ds_info in ds_config:
            config_dict = ds_config[ds_info]
            #ds_engine = config_dict['engine']
            #DataSource(pub_ds_config, self.engines_factory.get(self.current_ds.engine))
            new_engine = self.engines_factory.get(self.current_ds.engine)

            new_ds = DataSource(config_dict, new_engine)
            data_sources_dict[new_ds.alias] = new_ds

        return ds_audience, data_sources_dict



    
    


    #Return the audience data
    def get_df_audience(self) -> DataSource:
        return copy.deepcopy(self.df_audience)       
    

    def get_audience_pk(self) -> List[str]:
        return getattr(self.get_df_audience(), 'audience_pk')
    
    
    def get_data_batch(self, columns_to_read: List[str]) -> pd.DataFrame:
        data_source: DataSource = getattr(self, 'current_ds')
        
        df = data_source.read_data_batch(columns_to_read, self.get_audience_pk())

        df['PK_DATREF_XX'] = pd.to_datetime(df['PK_DATREF_XX'])
        df['PK_DATVER_XX'] = pd.to_datetime(df['PK_DATVER_XX'])

        return df


    def left_join_audience_tb(self, data_source: DataSource, mob: int) -> None:
        query = f"""
            CREATE TABLE {data_source.schema}.BASE_INFERENCIA_MLTOOLS_{data_source.alias} AS (
                SELECT 
                    A.*
                FROM {self.get_df_audience().get_schema()}.{self.get_df_audience().get_physical_name()} AS B
                LEFT JOIN {data_source.schema}.{data_source.physical_name} AS A
                    ON A.PK_RIZNUMDOC_XX = B.RIZNUMDOC_XX
                    AND A.PK_DATREF_XX = ADD_MONTHS(B.PK_DATREF_XX, {mob})
                    AND A.PK_TPP_XX = B.PK_TPP_XX
            ) WITH DATA PRIMARY INDEX (PK_RIZNUMDOC_XX,PK_DATREF_XX)
        """
        new_engine = self.engines_factory.get(data_source.engine_name)()
        return new_engine.execute_query(query)


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