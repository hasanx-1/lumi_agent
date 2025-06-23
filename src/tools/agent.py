import re
import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from langchain_openai import ChatOpenAI
from langchain.agents import create_react_agent, AgentExecutor
from langchain import hub
from langchain.tools import Tool
import asyncio

class LumiAgent:
    def __init__(self, llm, retriever, generator, appointment_manager):
        self.llm = llm
        self.retriever = retriever
        self.generator = generator
        self.appointment_manager = appointment_manager
    
    def init_agent(self, user_id=None, chat_id=None):
        async def faq_tool(query):
            return await self.generator.generator(query)
        self.tools = [

            Tool(
                name="FAQ",
                func=lambda q: self.generator.generator(q),
                description="""USE THIS FOR: services,contact info , questions about company, product info.
                Input MUST BE DIRECT QUESTION ABOUT the company or greetings, frarwll or thanking.
                NEVER USE THIS FOR: Appointments, bookings, or time-related queries."""
            ),
            Tool(
                name="CheckAvailability",
                func=lambda q: self.appointment_manager.check_available_slots_wrapper(q),
                description="Useful for checking available appointment slots. Input should mention a date/time."
            ),
            Tool(
                name="BookAppointment",
                func=lambda q: self.appointment_manager.book_appointment_wrapper(q, user_id, chat_id),
                description="Useful for booking appointments. Input must include specific date or time."
            ),
            Tool(
                name="CancelAppointment",
                func=lambda q: self.appointment_manager.cancel_appointment_wrapper(q, user_id),
                description="Useful for canceling appointments. Input must include date and time."
            ),
            Tool(
                name="ViewReservations",
                func=lambda _: self.appointment_manager.get_user_reservations(user_id),
                description="Useful for viewing existing reservations."
            )
        ]
        self.prompt = hub.pull("hwchase17/react")

        # Create the agent
        self.agent = create_react_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=10,
        )

        return self.agent_executor