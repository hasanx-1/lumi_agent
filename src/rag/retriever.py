from src.utils.logger import pipeline_logger

class Retriever:
    '''
    Setting up a retriever
    Args:
        embedding_model: all-MiniLM-L6-v2 embedding model
        index: faiss index
        df: Faqs dataframe

    Returns:
        relevant_ans : relevant data from the datafram
    
    '''
    def __init__(self,embedding_model,index,df):
        self.embedding_model = embedding_model
        self.index = index
        self.df = df

    def retriever(self,query,top_k = 3):

        try:
            embedded_query = self.embedding_model.encode(query).reshape(1,-1)
            distances, indices = self.index.search(embedded_query,top_k)
            relevant_ans = [self.df['answer'].iloc[idx] for idx in indices[0]]
            return '\n'.join(relevant_ans)
        
        except Exception as e:
            raise RuntimeError('Retrieving has failed')