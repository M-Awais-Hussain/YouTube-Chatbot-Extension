from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from config import Config
import logging
from typing import List
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class Document(BaseModel):
    page_content: str
    metadata: dict = {}

class LLMService:
    def __init__(self):
        """Initialize LLM service with Groq"""
        try:
            self.llm = ChatGroq(
                model_name=Config.LLM_MODEL,
                temperature=0.3,
                api_key=Config.GROQ_API_KEY,
                max_tokens=1024
            )
            self._setup_chains()
            logger.info("LLM service initialized successfully")
        except Exception as e:
            logger.error(f"LLM initialization failed: {str(e)}")
            raise

    def _setup_chains(self):
        """Setup LangChain pipelines"""
        # Main QA prompt
        self.qa_prompt = ChatPromptTemplate.from_template(
            """You are a YouTube video expert. Answer using ONLY these transcript excerpts.
            
            Transcripts:
            {context}
            
            Question: {question}
            
            Guidelines:
            1. Be concise (1-2 paragraphs max)
            2. Use only the provided context
            3. If unsure, say "I couldn't find that in the video"
            
            Answer:"""
        )
        
        # Setup chains
        self.qa_chain = (
            {"context": RunnablePassthrough(), "question": RunnablePassthrough()}
            | self.qa_prompt
            | self.llm
            | StrOutputParser()
        )

    def format_docs(self, docs: List[Document]) -> str:
        """Format documents for context"""
        formatted_docs = []
        for doc in docs:
            formatted_docs.append(f"Content: {doc.page_content}")
        return "\n\n".join(formatted_docs)


    def generate_answer(self, question: str, context: List[Document]) -> str:
        """Generate answer with improved query and context"""
        try:
            # Format context without timestamps
            formatted_context = self.format_docs(context)
            
            # Get answer using the original question
            response = self.qa_chain.invoke({
                "question": question,  # Use original question for answering
                "context": formatted_context
            })
            
            if not response.strip():
                return "I couldn't find that information in the video."
                
            return response
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return "An error occurred while generating the answer."
