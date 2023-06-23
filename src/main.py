from inference import InferenceModel

def main():
    inf = InferenceModel('../config/inference_config.yaml')
    print('Initialized inference')
    inf.rfe()

    #inf.get_features()
    #inf.double_check_eliminated()

    #inf.get_results()
    #inf.final_results()

if __name__ == "__main__":
    main()