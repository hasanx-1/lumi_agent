import faiss
import numpy as np
from src.utils.config import config
from src.utils.logger import pipeline_logger

class FaissIndex:
    def __init__(self,df):
        self.index_path = config.INDEX_PATH
        self.df = df
    
    def data_index(self):
        '''
        Creating faiss index
    
        Args:
            df: faqs dataframe
        Returns:
            index: faiss index 
        '''    
        try:
            pipeline_logger.info('Creating Index for the dataset')
            embedded_array = np.array(self.df['faqs_embed'].tolist()).astype('float32')
            index = faiss.IndexFlatL2(embedded_array.shape[1])
            index.add(embedded_array)
            faiss.write_index(index, self.index_path)
            pipeline_logger.info(f"FAISS index contains {index.ntotal} vectors")
            pipeline_logger.info('Index creation compleated successfully')
            return index
        except Exception as e:
            pipeline_logger.error(f'Failed to create index')
            raise RuntimeError('Creating Index has failed')
