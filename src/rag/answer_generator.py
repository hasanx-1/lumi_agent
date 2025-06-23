from langchain.prompts import PromptTemplate
from langchain_core.runnables import RunnablePassthrough
import re

class AnswerGenerator:
    def __init__(self,llm,retriever):

        '''
        Setting up answer generator with chat memory and sentiment analysis.
        
        Args:
            llm: LLM model (e.g., gpt-4o-mini)
            retriever: A retriever method
            sentiment_analyzer: Sentiment analysis pipeline
        '''
        self.llm_model = llm
        self.retriever = retriever

        
        self.prompt = PromptTemplate(
            input_variables=['context', 'question'],
            template=''' You are an expert \customer support Agent named Lumi. 
             
            You have two options:
            1. if the question is greetings or farwell or thanking:
                - Response to greeting with this ONLY: (Hey there, I am Lumi a customers service Agent.
                I can answer any question about NeuroSphere Lab company and I can book you an appointment for a meeting with the company.
                I am ready to help you.)
                - Response to farewell with this ONLY: (Goodbye! Have a great day!)
                - Response to thanking with this ONLY: (You are welcome! Tell me if you need any other help.) 

            2. else ansewer based on context provided:
            Context: 
            {context}
            
            Question: 
            {question}
            
            Answer:
                '''
                )
        self.rag_chain = (
            {
                'context': self._retrieve_context,
                'question': RunnablePassthrough(),
            }
            | self.prompt
            | self.llm_model
        )


    def _retrieve_context(self,question):
        """Retrieve context using the retriever."""
        return self.retriever.retriever(question)
    

        
    def generator(self,question:str) -> str:
        '''
        Generate a response using the RAG pipeline with memory and sentiment analysis.
        
        Args:
            question: The user's question as a string
        
        Returns:
            cleaned_response: A generated response based on context, history, and sentiment'''
        
        try:
            response = self.rag_chain.invoke(question)

            cleaned_response = re.sub(r'\*\*(.*?)\*\*',r'\1',response.content)

            return cleaned_response
        except Exception as e:
            raise RuntimeError(f'Generating response has failed: {str(e)}')