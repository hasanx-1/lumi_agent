from fastapi import FastAPI, HTTPException
from src.rag.retriever import Retriever
from src.rag.answer_generator import AnswerGenerator
from src.tools.agent import LumiAgent
from src.processing.data_loader import DataLoader
from src.processing.data_embedder import DataEmbedder
from src.processing.data_index import FaissIndex
from src.utils.logger import app_logger
from src.model.load_models import ModelLoader
from src.tools.manager import AppointmentManager
from src.utils.setting import Query

class ChatbotAPI:
    def __init__(self):
        '''Initialize the chatbot API components'''
        app_logger.info('Starting the app initialization...')

        #Initialize models
        app_logger.info('Initialize models...')
        self.model_loader = ModelLoader()
        self.embedding_model = self.model_loader.embedding_model
        self.llm_model = self.model_loader.get_llm_model()
        app_logger.info('Models initialized successfully')

        #Process data
        app_logger.info('Processing data...')
        self.df = DataLoader().load_data()
        self.embed_df = DataEmbedder(self.embedding_model,self.df).embed_data()
        self.index = FaissIndex(self.df).data_index()
        app_logger.info('Data processing completed successfully')

        #Initialize RAG components
        app_logger.info('Initializing RAG components...')
        self.retriver = Retriever(self.embedding_model,self.index,self.df)
        self.answer_generator = AnswerGenerator(self.llm_model, self.retriver)
        app_logger.info('RAG components initialized successfully')
        
        #Initialize Manager
        app_logger.info('Initializing Manager...')
        self.manager = AppointmentManager(llm=self.llm_model)
        self.answer_generator = AnswerGenerator(self.llm_model, self.retriver)
        app_logger.info('Manager initialized successfully')
        #Initialize Agent
        app_logger.info('Initializing Agent...')
        self.agent = LumiAgent(llm=self.llm_model,retriever=self.retriver,
                                generator= self.answer_generator,appointment_manager=self.manager).init_agent()
        app_logger.info('Agent initialized successfully')

        self.app = FastAPI()
        self._setup_routes()

    def _setup_routes(self):
        """Setup all API routes."""
        @self.app.get('/')
        async def read_root():
            app_logger.info('Root endpoint accessed')
            return {'message': 'Chatbot API is running'}
        
        @self.app.get('/health')
        async def health_check():
            app_logger.info('Health check endpoint accessed.')
            return {'status': 'healthy'}
        
        @self.app.post('/chat')
        async def chat(query: Query):
            try:
                app_logger.info(f'Generating response for query: {query.question}')
                answer = self.agent.invoke({"input":query.question})

                
                return {
                    "response": answer,

                }
            except Exception as e:
                app_logger.error(f'Failed to generate response: {e}')
                raise HTTPException(status_code=500, detail=f"Failed to generate response: {str(e)}")



app_logger.info('Creating Chatbot API instance...')
chatbot_api = ChatbotAPI()
app = chatbot_api.app