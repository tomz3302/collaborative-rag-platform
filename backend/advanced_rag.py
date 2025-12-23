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
            model="llama-3.3-70b-versatile",
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

        self.bm25_retrievers = {} #Dictionary to hold a separate retriever for each space
        self.space_docs_map = defaultdict(list) #Map to store documents grouped by space for rebuilding indexes
        print("System Initialized.")
    
    def load_bm25_data(self):
        """Loads the BM25 data from pickle files."""
        bm25_map_path = os.path.join(BM25_DATA_DIR, "bm25_docs_map.pkl")
        
        if os.path.exists(bm25_map_path):
            try:
                print("Loading BM25 partitions...")
                with open(bm25_map_path, "rb") as f:
                    self.space_docs_map = pickle.load(f)
                
                # Rebuild Retrievers
                for space_id, docs in self.space_docs_map.items():
                    retriever = BM25Retriever.from_documents(docs)
                    retriever.k = TOP_K_RETRIEVAL
                    self.bm25_retrievers[space_id] = retriever
                print("BM25 Data Loaded.")
            except Exception as e:
                print(f"Error loading BM25: {e}")
                self.space_docs_map = defaultdict(list)

    # def load_existing_embeddings(self):
    #     """
    #     Load previously saved Partitioned embeddings from disk.
    #     """
    #     faiss_index_path = os.path.join(EMBEDDINGS_DIR, "faiss_index")
    #     bm25_map_path = os.path.join(EMBEDDINGS_DIR, "bm25_docs_map.pkl")
    #     indexed_docs_path = os.path.join(EMBEDDINGS_DIR, "indexed_documents.pkl")
        
    #     if not os.path.exists(faiss_index_path):
    #         print("No existing embeddings found.")
    #         return False
        
    #     try:
    #         print("Loading existing embeddings from disk...")
            
    #         # 1. Load FAISS index
    #         self.vectorstore = FAISS.load_local(
    #             faiss_index_path, 
    #             self.embeddings,
    #             allow_dangerous_deserialization=True
    #         )
            
    #         # 2. Load BM25 Partitions
    #         self.bm25_retrievers = {}
    #         self.space_docs_map = defaultdict(list)

    #         if os.path.exists(bm25_map_path):
    #             print("Loading BM25 partitions...")
    #             with open(bm25_map_path, "rb") as f:
    #                 self.space_docs_map = pickle.load(f)
                
    #             # Re-instantiate a retriever for each space
    #             for space_id, docs in self.space_docs_map.items():
    #                 retriever = BM25Retriever.from_documents(docs)
    #                 retriever.k = TOP_K_RETRIEVAL
    #                 self.bm25_retrievers[space_id] = retriever
    #         else:
    #             print("Warning: BM25 map not found.")

    #         # 3. Load indexed documents list
    #         if os.path.exists(indexed_docs_path):
    #             with open(indexed_docs_path, "rb") as f:
    #                 self.indexed_documents = pickle.load(f)
            
    #         print(f"Successfully loaded embeddings for {len(self.indexed_documents)} document(s).")
    #         return True
            
    #     except Exception as e:
    #         print(f"Error loading embeddings: {str(e)}")
    #         # Reset state on failure
    #         self.vectorstore = None
    #         self.bm25_retrievers = {}
    #         self.space_docs_map = defaultdict(list)
    #         self.indexed_documents = []
    #         return False
            
    #     except Exception as e:
    #         print(f"Error loading embeddings: {str(e)}")
    #         print("Will start with empty index.")
    #         self.vectorstore = None
    #         self.retriever = None
    #         self.indexed_documents = []
    #         return False

    def load_and_process_pdf(self, file_url: str, db_id: int, space_id: int) -> List[Document]:
        """
        Downloads PDF from a URL (Supabase), processes it safely with Rate Limiting, and cleans up.
        """
        # Extract filename from URL (simple split)
        filename = file_url.split('/')[-1].split('?')[0] # Handles query params if any
        print(f"--- Downloading from URL: {file_url} ---")

        # 1. Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            local_temp_path = temp_file.name

        try:
            # 2. Download from URL to temp file
            response = requests.get(file_url, stream=True)
            response.raise_for_status() # Check for errors
            
            with open(local_temp_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # 3. Fast Extraction (Standard PyPDFLoader reading the temp file)
            print(f"Processing local temp file: {local_temp_path}")
            loader = PyPDFLoader(local_temp_path)
            pages = loader.load()
            full_text = "\n\n".join([p.page_content for p in pages])

            # 4. Splitting
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP
            )

            raw_docs = text_splitter.create_documents([full_text])
            print(f"Created {len(raw_docs)} raw chunks.")

            # --- METADATA INJECTION ---
            for doc in raw_docs:
                doc.metadata['source_document'] = filename
                doc.metadata['space_id'] = space_id
                doc.metadata['file_url'] = file_url
                doc.metadata['db_id'] = db_id

            # 5. Contextual Embedding (With Rate Limiting)
            print("Generating Contextual Embeddings...")
            print("Note: This will take time to respect Groq rate limits.")
          
            # Limit context to first 30k chars to avoid blowing up the prompt size
            document_context_str = full_text[:30000]
            contextualized_docs = []
            
            context_prompt = ChatPromptTemplate.from_template(
                """<document>{doc_context}</document>
                   Here is a chunk of text: <chunk>{chunk_content}</chunk>
                   Briefly explain the context of this chunk within the document."""
            )
            chain = context_prompt | self.contextualizer_llm | StrOutputParser()
            
            # --- THE LOOP ---
            for i, doc in enumerate(raw_docs):
                
                # A. Mandatory Sleep to prevent hitting 60 RPM limit
                time.sleep(1.0) 

                retries = 3
                success = False
                
                while retries > 0 and not success:
                    try:
                        chunk_context = chain.invoke({
                            "doc_context": document_context_str,
                            "chunk_content": doc.page_content
                        })
                        combined_content = f"Context: {chunk_context}\n\nContent: {doc.page_content}"
                        new_doc = Document(page_content=combined_content, metadata=doc.metadata)
                        
                        # Persist metadata
                        new_doc.metadata['original_content'] = doc.page_content
                        contextualized_docs.append(new_doc)
                        
                        # Progress bar effect
                        print(f"Processed chunk {i + 1}/{len(raw_docs)}...", end='\r')
                        success = True

                    except Exception as e:
                        error_msg = str(e)
                        # Check for Rate Limit errors (429)
                        if "429" in error_msg or "rate limit" in error_msg.lower():
                            wait_time = 10 + random.randint(1, 5)
                            print(f"\nRate Limit Hit on chunk {i}! Sleeping {wait_time}s...")
                            time.sleep(wait_time)
                            retries -= 1
                        else:
                            # If it's a different error (e.g., content filter), just skip context
                            print(f"\nError on chunk {i}: {e}. Skipping context.")
                            contextualized_docs.append(doc) # Fallback to raw doc
                            success = True

                # If we failed after 3 retries, just append the raw doc to avoid losing data
                if not success:
                     contextualized_docs.append(doc)

            print(f"\nProcessing Complete. {len(contextualized_docs)} chunks ready.")
            return contextualized_docs
        except Exception as e:
            print(f"Error processing {filename}: {e}")
            return []
            
        finally:
            # 6. Cleanup
            if os.path.exists(local_temp_path):
                try:
                    os.remove(local_temp_path)
                    print("Temp file cleaned up.")
                except:
                    pass
                
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
        filter_dict = {'space_id': space_id} if space_id else None
        
        print(f"DEBUG: Running vector search with filter: {filter_dict}")
        try:
            vector_docs = self.vectorstore.similarity_search(
                search_query, 
                k=TOP_K_RETRIEVAL, 
                filter=filter_dict
            )
            print(f"DEBUG: Vector search returned {len(vector_docs)} documents")
        except Exception as e:
            print(f"ERROR in vector search: {type(e).__name__}: {str(e)}")
            print(f"ERROR details: {repr(e)}")
            vector_docs = []

        # --- STEP 2: Keyword Retrieval (Supabase Full Text Search) ---
        # Replaces BM25. We call the RPC function we created in SQL.
        print("Running Keyword Search via Supabase RPC...")
        
        rpc_params = {
            "query_text": search_query, 
            "match_count": TOP_K_RETRIEVAL,
            "filter_space_id": space_id  # Pass as int or None, not string
        }
        
        print(f"DEBUG: RPC params: {rpc_params}")
        
        try:
            keyword_response = self.supabase.rpc("kw_match_document_chunks", rpc_params).execute()
            print(f"DEBUG: RPC response status: {keyword_response}")
            print(f"DEBUG: RPC returned {len(keyword_response.data) if keyword_response.data else 0} documents")
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

        print(f"DEBUG: Invoking LLM with context length: {len(context_text)} chars")
        try:
            response_text = chain.invoke({
                "context": context_text,
                "question": user_query
            })
            print(f"DEBUG: LLM response length: {len(response_text)} chars")
        except Exception as e:
            print(f"ERROR in LLM call: {type(e).__name__}: {str(e)}")
            print(f"ERROR details: {repr(e)}")
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

