import numpy as np
from src.utils.config import config
from src.utils.logger import pipeline_logger

class DataEmbedder:
    
    def __init__(self,embedding_model,df):
        

        self.embedding_model = embedding_model
        self.df = df

    def embed_data(self):
        '''Embedding data
        Args:
            embedding_model: all-MiniLM-L6-v2 embedding model
            df: faqs dataframe
        Returns:
        Embedded dataframe          
        '''
        try:
            pipeline_logger.info('Embedding dataset')
            self.df['faqs_embed'] = self.df['faqs'].apply(lambda x: self.embedding_model.encode(x))
            pipeline_logger.info('Embedding dataset compleated successfully')
            return self.df
        except Exception as e:
            pipeline_logger.error(f'Failed to embed dataset : {e}')
            raise RuntimeError('Dataset embedding has faild')        