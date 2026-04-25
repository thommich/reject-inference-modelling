from __future__ import annotations

from create_dataset import create_test_database
from log_utils import setup_logging, log_func
from inference import InferenceModel


logger = setup_logging(name=__name__)
module_logger = log_func(__name__)

@module_logger
def main():   
    
    logger.info('Starting Inference Model module execution')
    create_test_database()
    
    logger.info('Initializing InferenceModel instance with yaml config file at: %s' % yaml_config_path)
    inf = InferenceModel(yaml_config_path)
    
    logger.info('Starting the execution of the "rfe()" function')
    inf.rfe()

    #inf.get_features(cut_threshold=20, max_br_reduction=0.05)
    inf.double_check_eliminated(cut_threshold=20, max_br_reduction=0.05)

    #inf.get_results()
    inf.final_results()

if __name__ == "__main__":
    yaml_config_path = '../config/inference_config.yaml'
    main()