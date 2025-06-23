import os
import yaml
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "config", "config.yml")

class Config:
    def __init__(self,config_path=CONFIG_PATH):
        with open(config_path,'r') as file:
            config_data = yaml.safe_load(file)

        self.EMBEDDING_MODEL = config_data['embedding_model']
        self.LLM_MODEL = config_data['llm_model']
        self.TEMBERATURE =config_data['temperature']
        self.DATA_PATH = config_data['faqs_path']
        self.INDEX_PATH = config_data['index_path']
        self.OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
        self.EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
        self.LOGGER_FORMAT = config_data['logging']['format']
        self.PIPELINE_LOGGER = config_data['logging']['pipeline_log_file']
        self.APP_LOGGER = config_data['logging']['app_log_file']
        self.MANAGER_LOGGER = config_data['logging']['manager_log']
config = Config()