from fastapi import FastAPI, HTTPException, Response, Request
from fastapi.middleware.cors import CORSMiddleware  
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse 
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
from src.utils.db import db_loader
from sqlalchemy.exc import IntegrityError
from datetime import datetime
from sqlalchemy.sql import text
from pathlib import Path
import uuid

class ChatbotAPI:
    def __init__(self):
        '''Initialize the chatbot API components'''
        app_logger.info('Starting the app initialization...')

        # Initialize models
        app_logger.info('Initializing models...')
        try:
            self.model_loader = ModelLoader()
            self.embedding_model = self.model_loader.embedding_model
            self.llm_model = self.model_loader.get_llm_model()
            app_logger.info('Models initialized successfully')
        except Exception as e:
            app_logger.error(f'Failed to initialize models: {str(e)}')
            raise

        # Process data
        app_logger.info('Processing data...')
        try:
            self.df = DataLoader().load_data()
            self.embed_df = DataEmbedder(self.embedding_model, self.df).embed_data()
            self.index = FaissIndex(self.df).data_index()
            app_logger.info('Data processing completed successfully')
        except Exception as e:
            app_logger.error(f'Failed to process data: {str(e)}')
            raise

        # Initialize RAG components
        app_logger.info('Initializing RAG components...')
        try:
            self.retriever = Retriever(self.embedding_model, self.index, self.df)
            self.answer_generator = AnswerGenerator(self.llm_model, self.retriever)
            app_logger.info('RAG components initialized successfully')
        except Exception as e:
            app_logger.error(f'Failed to initialize RAG components: {str(e)}')
            raise
        
        # Initialize Manager
        app_logger.info('Initializing Manager...')
        try:
            self.manager = AppointmentManager(llm=self.llm_model)
            app_logger.info('Manager initialized successfully')
        except Exception as e:
            app_logger.error(f'Failed to initialize Manager: {str(e)}')
            raise

        self.chat_memories = {}

        # Initialize Agent
        app_logger.info('Initializing Agent...')
        try:
            self.agent = LumiAgent(
                llm=self.llm_model,
                retriever=self.retriever,
                generator=self.answer_generator,
                appointment_manager=self.manager
            )
            app_logger.info('Agent initialized successfully')
        except Exception as e:
            app_logger.error(f'Failed to initialize Agent: {str(e)}')
            raise
        
        self.app = FastAPI()
        # Serve static files (frontend)
        app_logger.info('Serving static files...')
        frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"
        self.app.mount("/static", StaticFiles(directory=frontend_path, html=True), name="frontend")

        app_logger.info('Enabling CORS...')
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self._setup_routes()

    def _setup_routes(self):
        """Setup all API routes."""
        @self.app.get('/')
        async def read_root():
            app_logger.info('Root endpoint accessed')
            frontend_path = Path(__file__).resolve().parent.parent.parent / "frontend"
            return FileResponse(frontend_path / "index.html")
        
        @self.app.get('/health')
        async def health_check():
            app_logger.info('Health check endpoint accessed')
            return {'status': 'healthy'}
        
        @self.app.get('/get_user_id')
        async def get_user_id(request: Request, response: Response):
            user_id = request.cookies.get('user_id')
            app_logger.info(f'get_user_id accessed, cookie user_id: {user_id}')
            with db_loader() as session:
                try:
                    if user_id:
                        result = session.execute(
                            text("SELECT user_id FROM users WHERE user_id = :user_id"),
                            {"user_id": user_id}
                        )
                        user = result.fetchone()
                        if not user:
                            app_logger.info(f"User {user_id} not found in database, inserting...")
                            session.execute(
                                text("INSERT INTO users (user_id) VALUES (:user_id)"),
                                {"user_id": user_id}
                            )
                            session.commit()
                    else:
                        user_id = str(uuid.uuid4())
                        app_logger.info(f"Generating new user_id: {user_id}")
                        session.execute(
                            text("INSERT INTO users (user_id) VALUES (:user_id)"),
                            {"user_id": user_id}
                        )
                        session.commit()
                        response.set_cookie(key='user_id', value=user_id, httponly=True, max_age=604800)
                    app_logger.info(f'Returning user_id: {user_id}')
                    return {'user_id': user_id}
                except IntegrityError as e:
                    session.rollback()
                    app_logger.error(f"Database integrity error in get_user_id: {str(e)}")
                    raise HTTPException(status_code=400, detail="Failed to process user_id due to database constraint violation")
                except Exception as e:
                    session.rollback()
                    app_logger.error(f"Error in get_user_id: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to process user_id: {str(e)}")
        
        @self.app.get('/create_chat/{user_id}')
        async def create_chat(user_id: str):
            app_logger.info(f"Creating chat for user_id: {user_id}")
            with db_loader() as session:
                try:
                    result = session.execute(
                        text("SELECT chat_id FROM chats WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    )
                    chat = result.fetchone()
                    if chat:
                        app_logger.info(f"Existing chat found: {chat[0]}")
                        return {'chat_id': chat[0]}
                    
                    chat_id = str(uuid.uuid4())
                    session.execute(
                        text("""
                            INSERT INTO chats (chat_id, user_id, chatmemory)
                            VALUES (:chat_id, :user_id, :chatmemory)
                        """),
                        {"chat_id": chat_id, "user_id": user_id, "chatmemory": ""}
                    )
                    session.commit()
                    app_logger.info(f"Created new chat {chat_id} for user {user_id}")
                    return {'chat_id': chat_id}
                except Exception as e:
                    session.rollback()
                    app_logger.error(f"Error creating chat for user {user_id}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to create chat: {str(e)}")
        
        @self.app.get('/chats/{user_id}')
        async def get_chats(user_id: str):
            app_logger.info(f"Getting chats for user_id: {user_id}")
            with db_loader() as session:
                try:
                    result = session.execute(
                        text("SELECT chat_id FROM chats WHERE user_id = :user_id"),
                        {"user_id": user_id}
                    )
                    chats = result.fetchall()
                    app_logger.info(f"Found {len(chats)} chats for user {user_id}")
                    return {'chats': [{'chat_id': chat[0]} for chat in chats]}
                except Exception as e:
                    app_logger.error(f"Error getting chats for user {user_id}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to get chats: {str(e)}")
        
        @self.app.get('/chat/{chat_id}/messages')
        async def get_chat_messages(chat_id: str):
            app_logger.info(f"Getting messages for chat_id: {chat_id}")
            with db_loader() as session:
                try:
                    result = session.execute(
                        text("""
                            SELECT message_id, message_text, message_type, timestamp
                            FROM messages
                            WHERE chat_id = :chat_id
                            ORDER BY timestamp
                        """),
                        {"chat_id": chat_id}
                    )
                    messages = result.fetchall()
                    if not messages:
                        app_logger.info(f"No messages found for chat {chat_id}")
                        raise HTTPException(status_code=404, detail="No messages found for this chat")
                    app_logger.info(f"Found {len(messages)} messages for chat {chat_id}")
                    return {
                        'messages': [{'type': msg[2], 'text': msg[1]} for msg in messages]
                    }
                except Exception as e:
                    app_logger.error(f"Error getting messages for chat {chat_id}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to get messages: {str(e)}")
        
        @self.app.get('/reservations/{user_id}')
        async def get_reservations(user_id: str):
            app_logger.info(f"Getting reservations for user: {user_id}")
            try:
                # Try AppointmentManager first
                reservations = self.manager.get_user_reservations(user_id)
                app_logger.info(f"Raw reservations from AppointmentManager: {reservations}")
                if "no current reservations" in reservations.lower():
                    app_logger.info("No reservations found via AppointmentManager")
                    reservations_list = []
                else:
                    reservations_list = []
                    lines = reservations.split('\n')
                    for line in lines:
                        if line.startswith('-'):
                            parts = line.split(' at ')
                            if len(parts) == 2:
                                day = parts[0].replace('- ', '').strip()
                                time = parts[1].strip()
                                reservations_list.append({'day': day, 'time': time})
                    app_logger.info(f"Parsed reservations from AppointmentManager: {reservations_list}")

                # Fallback to direct database query
                if not reservations_list:
                    with db_loader() as session:
                        result = session.execute(
                            text("""
                                SELECT day, time
                                FROM reservations
                                WHERE user_id = :user_id
                                ORDER BY day, time
                            """),
                            {"user_id": user_id}
                        )
                        db_reservations = result.fetchall()
                        app_logger.info(f"Raw reservations from database: {db_reservations}")
                        reservations_list = [
                            {
                                'day': res[0].strftime('%Y-%m-%d'),
                                'time': res[1].strftime('%H:%M')
                            } for res in db_reservations
                        ]
                        app_logger.info(f"Parsed reservations from database: {reservations_list}")

                return {'reservations': reservations_list}
            except Exception as e:
                app_logger.error(f"Error fetching reservations for user {user_id}: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Failed to fetch reservations: {str(e)}")
        
        @self.app.post('/chat/{user_id}/{chat_id}')
        async def chat(user_id: str, chat_id: str, query: Query):
            app_logger.info(f"Processing chat for user {user_id}, chat {chat_id}, question: {query.question}")
            with db_loader() as session:
                try:
                    result = session.execute(
                        text("SELECT chat_id FROM chats WHERE chat_id = :chat_id AND user_id = :user_id"),
                        {"chat_id": chat_id, "user_id": user_id}
                    )
                    chat = result.fetchone()
                    if not chat:
                        app_logger.error(f"Chat {chat_id} not found for user {user_id}")
                        raise HTTPException(status_code=404, detail="Chat not found")

                    agent_executor = self.agent.init_agent(user_id=user_id, chat_id=chat_id)
                    session.execute(
                        text("""
                            INSERT INTO messages (chat_id, message_text, message_type, timestamp)
                            VALUES (:chat_id, :message_text, :message_type, CURRENT_TIMESTAMP)
                        """),
                        {
                            "chat_id": chat_id,
                            "message_text": query.question,
                            "message_type": "sent"
                        }
                    )
                    
                    response = await agent_executor.ainvoke({"input": query.question})
                    session.execute(
                        text("""
                            INSERT INTO messages (chat_id, message_text, message_type, timestamp)
                            VALUES (:chat_id, :message_text, :message_type, CURRENT_TIMESTAMP)
                        """),
                        {
                            "chat_id": chat_id,
                            "message_text": response['output'],
                            "message_type": "received"
                        }
                    )
                    session.commit()
                    app_logger.info(f"Chat response for user {user_id}, chat {chat_id}: {response['output']}")
                    return {'response': response['output']}
                except Exception as e:
                    session.rollback()
                    app_logger.error(f"Error processing chat for user {user_id}, chat {chat_id}: {str(e)}")
                    raise HTTPException(status_code=500, detail=f"Failed to process chat: {str(e)}")

app_logger.info('Creating Chatbot API instance...')
chatbot_api = ChatbotAPI()
app = chatbot_api.app