import pandas as pd
from src.utils.config import config
from src.utils.logger import pipeline_logger

class DataLoader:
    def __init__(self):
        self.df_path = config.DATA_PATH
        self.df = None

    def load_data(self):
        try:
            pipeline_logger.info('Loading dataset')
            self.df = pd.read_csv(self.df_path)
            pipeline_logger.info('Loading compleated successfully')
            return self.df
        except Exception as e:
            pipeline_logger.error(f'Failed to load dataset : {e}')
            raise RuntimeError('Dataset loading has faild')
    