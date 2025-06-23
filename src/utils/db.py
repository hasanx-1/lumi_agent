from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from contextlib import contextmanager
import os
from urllib.parse import quote_plus
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# PostgreSQL connection details
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = os.getenv("DB_PORT")
DB_NAME = os.getenv("DB_NAME")
DB_URL = os.getenv("DATABASE_URL")
# URL-encode the password to handle special characters
#encoded_password = quote_plus(DB_PASSWORD)
#DB_URL = f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Create engine with connection pooling
engine = create_engine(
    DB_URL,
    pool_size=5,      # Number of connections to keep open
    max_overflow=10,  # Allow up to 10 additional connections
    pool_timeout=30   # Wait up to 30 seconds for a connection
)

@contextmanager
def db_loader():
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
