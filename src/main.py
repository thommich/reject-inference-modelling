from inference import InferenceModel




def main():
    inf = InferenceModel('/config/inference_config.yaml')

    inf.rfe()

    inf.get_features()

    inf.get_results()

if __name__ == "__main__":
    main()