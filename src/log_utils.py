import logging

def setup_logging(name):
    
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    #handler = logging.StreamHandler()
    handler = logging.FileHandler('inference_model.log')
    handler.setLevel(logging.DEBUG)
    
    formatter = logging.Formatter(
        '%(asctime)s|%(name)s|%(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    
    return logger 


def log_func(log_name):
    def log_this(function):
        logger = logging.getLogger(log_name)
        def new_function(*args,**kwargs):
            logger.debug(f"Executando {function.__name__}: args({args}) | kwargs({kwargs})")
            output = function(*args,**kwargs)
            logger.debug(f"{function.__name__} returned: {output}")
            return output
        return new_function
    return log_this