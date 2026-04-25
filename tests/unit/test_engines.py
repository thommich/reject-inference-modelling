# import unittest
# from src.engines.engines import EngineFactory, EngineInstanceProvider
# from src.engines.teradata import TeradataEngineBuilder
# from src.datasources.dsmodel import DataSourceModel

# class TestEngineFactory(unittest.TestCase):
#     def setUp(self):
#         # Load test data
#         self.engines_factory = EngineInstanceProvider(database='fixtures/eng_params.json')
#         self.engines_factory.register_builder('TERADATA', TeradataEngineBuilder)
    
#     def test_register_builder(self):
#         """
#         Test that it can
#         """
#         data = [1, 2, 3]
#         result = sum(data)
#         self.assertEqual(result, 6)

# if __name__ == '__main__':
#     unittest.main()