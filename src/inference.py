class InferenceModel:

    paramenters
    technologies_params
    data_srcs_param
    data sources: List[DataSource]

    def __init_(self, cfg_file_path: str): 
        self.__cfg_file = cfg_file_path 
        self.parameters, self.technologies_params, self.data_srcs_params = self.__load_config()
        self.data_sources_list = DataSource(data_srcs_params) 
    

    #Reads YAML config file
    def __load_config(self)-> Tuple[Dict[str, str], Dict[str, str]]:
        pass


    #Recursive feature elimination implementation
    def rfe(self):
        #Initializes RFE object as an instance attribute
        self.__rfe RFE(self.parameters)

        #Identify the 'n_features_batch' best var candidates from each data source (univariate analysis)
        self.__narrow_down_candidates_univar() 

        #Identify the 'n_features' best var candidates from each data source (multivariate analysis)
        self.__choose_top_features_multivar() 
        
        #Consolidates all the chosen variables into a single dataframe
        .get_df_rfe()

        pass


    #Select the 'n_features_batch' best feature candidates from each data source (univariate analysis)
    def __narrow_down_candidates_univar(self): 
        #Read data sources
        self.data_sources = self._read_data_sources()
        
        for ds in self.data_sources:
            #Read chunk of data from DBMS
            #Train model and evaluate feature metrics
            #Merge results with current best candidates, sort in desc order, keep only top n_features

        #Write best candidates to .parquet file
        pass


    def __read_data_sources (self) -> List [DataSource]:

    #Reevaluates features discardaded during the previous analysis step
    def eval_data_sources(self): 
        pass


    #Retrocompatibility
    def get_features (self):
        return self.eval_data_sources()
    
    
    def get_results(self): 
        pass