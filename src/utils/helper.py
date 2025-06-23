from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
import re
from src.model.load_models import ModelLoader



model_loader = ModelLoader()
llm_model = model_loader.get_llm_model()

def social_response(query):
    prompt = PromptTemplate(
            input_variables=['message'],
    template = """
    Response to the provided message as the following:
    - Response to greeting with this: (Hey there, I am Lumi a customers service Agent.
    I can answer any question about NeuroSphere Lab company and I can book you an appointment for a meeting with the company.
    I am ready to help you.)
    - Response to farewell with this: (Goodbye! Have a great day!)
    - Response to thanking with this: (You are welcome! Tell me if you need any other help.) 
    This is the meesage : {message}
    """)

    llm_chain = prompt | llm_model
    respnse = llm_chain.invoke({'message' : query})
    cleaned_response = re.sub(r'\*\*(.*?)\*\*',r'\1',respnse.content)
    return cleaned_response

def enhance_response (query):
    prompt = PromptTemplate(
            input_variables=['message'],
    template = """
    You are an expert cutomers srvice agent enhance the following message to be suitable for the customer:
    message: {message}
    """)

    llm_chain = prompt | llm_model
    respnse = llm_chain.invoke({'message' : query})
    cleaned_response = re.sub(r'\*\*(.*?)\*\*',r'\1',respnse.content)
    return cleaned_response
