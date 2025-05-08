from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.retrievers import MultiQueryRetriever
from services.llm_service import LLMService
from langchain.prompts import PromptTemplate
from langchain.output_parsers import CommaSeparatedListOutputParser
from config import Config
from typing import List
from pydantic import BaseModel
import logging
logger = logging.getLogger(__name__)

# Initialize LLM service
llm_service = LLMService()

class Document(BaseModel):
    page_content: str
    metadata: dict = {}

def create_vector_store(text: str) -> FAISS:
    """Create FAISS vector store from text"""
    embeddings = HuggingFaceEmbeddings(model_name=Config.EMBEDDING_MODEL)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=150,
        length_function=len,
        add_start_index=True
    )

    chunks = splitter.create_documents([text])

    # Add metadata
    total_chars = len(text)
    for chunk in chunks:
        chunk.metadata = {
            'timestamp': int((chunk.metadata['start_index'] / total_chars) * 3600),
            'source': 'youtube'
        }

    return FAISS.from_documents(chunks, embeddings)

def create_retriever(vector_store: FAISS):
    return vector_store.as_retriever(search_kwargs={"k": 8})


def answer_with_retriever(question: str, retriever: MultiQueryRetriever) -> str:
    """Get answer using retriever"""
    try:
        # Get relevant documents using the retriever
        docs = retriever.get_relevant_documents(question)

        # Generate answer using both question and context
        answer = llm_service.generate_answer(question=question, context=docs)

        return answer

    except Exception as e:
        logger.error(f"Error in answer_with_retriever: {str(e)}")
        return "Sorry, I encountered an error while processing your question."
