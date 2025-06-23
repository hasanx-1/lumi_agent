from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from src.utils.config import config
from src.utils.logger import pipeline_logger
from transformers import AutoTokenizer

class ModelLoader:
    '''Initiakizing and loading models'''
    def __init__(self):
        try:
            pipeline_logger.info('Initializing Embedding,LLM,sentiment and zero shot models')
            self.embedding_model = SentenceTransformer(config.EMBEDDING_MODEL)
            #self.embedding_model = SentenceTransformer(
            #    config.EMBEDDING_MODEL,
            #    tokenizer=AutoTokenizer.from_pretrained(
            #        config.EMBEDDING_MODEL,
            #        clean_up_tokenization_spaces=True  # Explicitly set to True
            #    )
            #)
            self.llm_model = ChatOpenAI(model=config.LLM_MODEL,temperature=config.TEMBERATURE,api_key=config.OPENAI_API_KEY)
            pipeline_logger.info('Initializing Compleated successfully')

        except Exception as e:
            pipeline_logger.error(f'Failed to initilize models:{e}')
            raise RuntimeError('Models Initializing has failed')
        
    def get_embedding_model(self):

        return self.embedding_model
    
    def get_llm_model(self):

        return self.llm_model