import os
import random
import sys
import pickle
import time
from typing import List, Dict, Any
import tempfile # To create temporary files during download
import requests
# --- Libraries ---
import threading #incase 2 users press indexing at the same time
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_community.document_loaders import PyPDFLoader
# LangChain & Graph
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_chroma import Chroma

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Google Gemini
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
# groq
from langchain_groq import ChatGroq
# Vector Store & Retrieval
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
# Ensemble and ContextualCompression are in the main 'langchain' package
from langchain_classic.retrievers.ensemble import EnsembleRetriever

from langchain_classic.retrievers.document_compressors import CrossEncoderReranker

# HuggingFaceCrossEncoder is currently most stable in 'langchain_community'
from langchain_community.cross_encoders import HuggingFaceCrossEncoder
from collections import defaultdict

#Supabase Imports
from supabase import create_client, Client
from langchain_community.vectorstores import SupabaseVectorStore


#Extras
from services.document_processor import DocumentProcessorService


# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# --- Configuration ---
# Load API keys from .env or environment variables
# Priority: .env file > Windows environment variables
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
SUPABASE_URL= os.getenv("SUPABASE_URL")
SUPABASE_KEY= os.getenv("SUPABASE_KEY")

if not GOOGLE_API_KEY:
    print("Error: GOOGLE_API_KEY not found in .env or environment variables.")
    sys.exit(1)
if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY not found in .env or environment variables (needed for Llama 3.3).")
    sys.exit(1)

# Set them in os.environ for libraries that expect them there
os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY
os.environ["GROQ_API_KEY"] = GROQ_API_KEY

# Configuration Constants
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "llama-3.3-70b-versatile"  # Flash is fast and supports long context/caching
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K_RETRIEVAL = 15  # Fetch more for hybrid search
TOP_K_RERANK = 5      # Final number of docs to LLM
PERSIST_DIRECTORY = "chroma_db" 
BM25_DATA_DIR = "bm25_data"

class AdvancedRAGSystem:
    def __init__(self):
        print("Initializing Advanced RAG System...")
        self.index_lock = threading.Lock() # Create a lock for indexing operations
        
        # 1. Initialize Supabase Client
        self.supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        
        
        # 1. Initialize LLMs
        # Main LLM for Generation
        #=================switching to groq================================
        # self.llm = ChatGoogleGenerativeAI(
        #     model=LLM_MODEL,
        #     temperature=0.3,
        #     # Gemini automatically handles caching for long identical prefixes (System Prompts)
        #     # We will structure our prompts to take advantage of this.
        # )
        
        # # Cheaper/Faster LLM for Contextualizing Chunks (using Flash for speed)
        # self.contextualizer_llm = ChatGoogleGenerativeAI(
        #     model="gemini-2.5-flash",
        #     temperature=0.0
        # )
        #========================================================================
        self.llm = ChatGroq(
            model=LLM_MODEL,
            temperature=0.5,
            max_tokens=None,
            timeout=None,
            max_retries=2,
            # Groq is extremely fast, so no special caching needed like Gemini
        )
        
        # 2. Contextualizer LLM (Using Llama 3.3 again, or you can use llama-3.1-8b-instant for speed)
        # We will use 70b here too because Groq is fast enough to handle it.
        self.contextualizer_llm = ChatGroq(
            model="llama-3.1-8b-instant",
            temperature=0.0
        )

        # 2. Initialize Embeddings
        self.embeddings = GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)
        
        # Initialize Vector Store (Pointer to Supabase)
        self.vectorstore = SupabaseVectorStore(
            client=self.supabase,
            embedding=self.embeddings,
            table_name="document_chunks",
            query_name="match_document_chunks"
        )

        # 3. Initialize Reranker (Cross Encoder)
        # We use a standard efficient cross-encoder from HuggingFace
        self.reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.reranker_model, top_n=TOP_K_RERANK)


        self.doc_processor = DocumentProcessorService(self.contextualizer_llm)

        self.bm25_retrievers = {} #Dictionary to hold a separate retriever for each space
        self.space_docs_map = defaultdict(list) #Map to store documents grouped by space for rebuilding indexes
        print("System Initialized.")
    

    def load_and_process_pdf(self, file_url: str, db_id: int, space_id: int) -> List[Document]:
        """
        Downloads PDF from a URL (Supabase), processes it safely with Rate Limiting, and cleans up.
        """
        with self.index_lock:
            return self.doc_processor.process_pdf(file_url, db_id, space_id)
                
    def build_index(self, documents: List[Document]):
        with self.index_lock:
            print("--- Updating Partitioned Indexes ---")
            
            # 1. Update Supabase (Incremental)
            # Unlike FAISS, we just add the new documents to the existing DB
            
            self.vectorstore.add_documents(documents)
            print(f"Added {len(documents)} documents to Supabase vector store.")
            
            print("Indexing Complete.")

    def query(self, user_query: str, space_id: int = None, history_messages: List[Dict] = None) -> Dict[str, Any]:
        """
        Query with Partitioned Retrieval & (NEW) History awareness.
        1. Chromadb: Chroma handles filtering natively.
        2. BM25: Selects the specific retriever for the given space_id.
        3. Reranks the combined results.
        """
        print(f"\n--- Querying: {user_query} (Space ID: {space_id}) ---")

        # --- STEP 0: Query Contextualization ---
        # We use the rewritten query for SEARCH, but the original query for the final CHAT.
        search_query = user_query
        if history_messages:
            search_query = self.contextualize_query(user_query, history_messages)
    
        # --- STEP 1: Vector Retrieval (Supabase) ---
        # We explicitly filter by space_id using metadata
        vector_docs = []
        
        try:
            # 1. Generate the embedding vector for the query
            query_vector = self.embeddings.embed_query(search_query)
            
            # 2. Prepare params for the SQL function
            params = {
                "query_embedding": query_vector,
                "match_threshold": 0.5, # Adjust this threshold as needed
                "match_count": TOP_K_RETRIEVAL,
                "filter": {'space_id': space_id} if space_id else {}
            }
            
            # 3. Execute RPC
            response = self.supabase.rpc("match_document_chunks", params).execute()
            
            # 4. Convert results to LangChain Documents
            if response.data:
                for item in response.data:
                    doc = Document(
                        page_content=item['content'],
                        metadata=item['metadata']
                    )
                    vector_docs.append(doc)
            
            print(f"DEBUG: Vector RPC returned {len(vector_docs)} documents")
            
        except Exception as e:
            print(f"Vector Error: {e}")
            vector_docs = []

            
        # --- STEP 2: Keyword Retrieval (Supabase Full Text Search) ---
        # Replaces BM25. We call the RPC function we created in SQL.
        print("Running Keyword Search via Supabase RPC...")
        
        rpc_params = {
            "query_text": search_query, 
            "match_count": TOP_K_RETRIEVAL,
            "filter_space_id": space_id  # Pass as int or None, not string
        }
        try:
            keyword_response = self.supabase.rpc("kw_match_document_chunks", rpc_params).execute()
        except Exception as e:
            print(f"ERROR in RPC call: {type(e).__name__}: {str(e)}")
            print(f"ERROR details: {repr(e)}")
            keyword_response = None

        # Convert RPC response back to LangChain Documents
        keyword_docs = []
        if keyword_response and keyword_response.data:
            for item in keyword_response.data:
                doc = Document(
                    page_content=item['content'],
                    metadata=item['metadata']
                )
                keyword_docs.append(doc)
        
        print(f"DEBUG: Converted {len(keyword_docs)} keyword documents")

        # --- STEP 3: Ensemble (Merge & Deduplicate) ---
        # Combine lists and remove duplicates based on page_content
        combined_docs_map = {doc.page_content: doc for doc in vector_docs + keyword_docs}
        combined_docs = list(combined_docs_map.values())
        
        print(f"DEBUG: Combined {len(combined_docs)} unique documents")

        if not combined_docs:
            print("DEBUG: No documents found, returning empty response")
            return {"answer": "I couldn't find relevant information in this space.", "source_document": None}

        # --- STEP 4: Reranking (Cross Encoder) ---
        # We manually call the compressor on our combined list
        print(f"DEBUG: Reranking {len(combined_docs)} documents...")
        try:
            reranked_docs = self.compressor.compress_documents(
                documents=combined_docs, 
                query=search_query
            )
            print(f"DEBUG: Reranking returned {len(reranked_docs)} documents")
        except Exception as e:
            print(f"ERROR in reranking: {type(e).__name__}: {str(e)}")
            print(f"ERROR details: {repr(e)}")
            reranked_docs = combined_docs[:TOP_K_RERANK]  # Fallback to top N without reranking

        if not reranked_docs:
            print("DEBUG: No documents after reranking, returning empty response")
            return {"answer": "Found documents, but they weren't relevant enough.", "source_document": None}

        # --- STEP 5: Prepare Context & LLM (Standard Logic) ---
        
        # Identify Top Document for citation
        top_doc = reranked_docs[0]
        top_source_filename = top_doc.metadata.get('source_document', 'Unknown Document')

        def format_docs(docs):
            formatted_results = []
            for doc in docs:
                # Use original content if available (cleaner), otherwise use contextualized
                content = doc.metadata.get('original_content', doc.page_content)
                source_file = doc.metadata.get('source_document', 'Unknown')
                formatted_results.append(f"<source doc='{source_file}'>\n{content}\n</source>")
            return "\n\n".join(formatted_results)

        context_text = format_docs(reranked_docs)

        system_prompt = (
            "Your name is Clark, you were created by Omar the G. You are an expert Engineering Professor and Tutor. Your goal is to help college students "
            "deeply understand complex engineering concepts based on the provided course material.\n\n"
            
            "INSTRUCTIONS:\n"
            "1. **Core Accuracy**: Base your factual answer primarily on the provided CONTEXT below. "
            "Do not contradict the context.\n"
            "2. **Elaboration & Depth**: Do not just summarize. Expand on the concepts mentioned in the context. "
            "Explain the 'Why' and 'How' behind the theories. If the context is brief, use your internal knowledge "
            "to provide the theoretical background.\n"
            "3. **Examples**: Provide concrete, real-world engineering examples or analogies to illustrate the points, whenever you see fits, "
            "even if they are not explicitly in the context.\n"
            "4. **Structure**: Use clear formatting, bullet points, and bold text to make the answer easy to read.\n"
            "5. **Citation**: explicitely mention what part of the answer comes from the context and what part is your own elaboration.\n\n"
            
            "CONTEXT:\n"
            "{context}"
        )
        # Build Prompt: System -> History -> Original Question
        messages_list = [("system", system_prompt)]

        if history_messages:
            for msg in history_messages:
                role = "human" if msg.get('role') == 'user' else "ai"
                content = msg.get('content', '')
                messages_list.append((role, content))

        messages_list.append(("human", "{question}"))

        prompt = ChatPromptTemplate.from_messages(messages_list)

        chain = prompt | self.llm | StrOutputParser()


        try:
            response_text = chain.invoke({
                "context": context_text,
                "question": user_query
            })

        except Exception as e:

            return {
                "answer": "An error occurred while generating the response.",
                "source_document": top_source_filename,
                "error": str(e)
            }

        # Debug print
        print({
            "answer": response_text[:200] + "..." if len(response_text) > 200 else response_text,
            "source_document": top_source_filename,
            "top_chunk_page_content": top_doc.page_content[:200] + "..." 
        })

        return {
            "answer": response_text,
            "source_document": top_source_filename,
            "top_chunk_page_content": top_doc.page_content[:200] + "..." 
        }
    
    def contextualize_query(self, user_query: str, history_messages: List[Dict]) -> str:
        """
        If history exists, rewrite the query to be standalone.
        If no history, return the query as is.
        """
        if not history_messages:
            return user_query

        # Simple prompt for the rewriter
        system_prompt = (
            "Given a chat history and the latest user question "
            "which might reference context in the chat history, "
            "formulate a standalone question which can be understood "
            "without the chat history. Do NOT answer the question, "
            "just reformulate it if needed and otherwise return it as is."
        )

        # Create the chain
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "History: {history}\n\nQuestion: {question}")
        ])

        chain = prompt | self.llm | StrOutputParser()

        # Format history as a simple string for the LLM
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history_messages])

        standalone_query = chain.invoke({
            "history": history_str,
            "question": user_query
        })

        print(f"--- Rewritten Query: {standalone_query} ---")
        return standalone_query

