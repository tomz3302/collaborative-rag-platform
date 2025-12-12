import os
import sys
import pickle
from typing import List, Dict, Any


# --- Libraries ---
import threading #incase 2 users press indexing at the same time
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_community.document_loaders import PyPDFLoader
# LangChain & Graph
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

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

# --- Configuration ---
# Ensure you have GOOGLE_API_KEY set in your environment variables
# os.environ["GOOGLE_API_KEY"] = "your_key_here"
if "GOOGLE_API_KEY" not in os.environ:
    print("Error: GOOGLE_API_KEY environment variable not found.")
    sys.exit(1)
if "GROQ_API_KEY" not in os.environ:
    print("Error: GROQ_API_KEY environment variable not found (needed for Llama 3.3).")
    sys.exit(1)

# Configuration Constants
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "llama-3.3-70b-versatile"  # Flash is fast and supports long context/caching
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K_RETRIEVAL = 15  # Fetch more for hybrid search
TOP_K_RERANK = 5      # Final number of docs to LLM
EMBEDDINGS_DIR = "embeddings"  # Directory to store vector embeddings

class AdvancedRAGSystem:
    def __init__(self):
        print("Initializing Advanced RAG System...")
        self.index_lock = threading.Lock() # Create a lock for indexing operations
        
        # Create embeddings directory if it doesn't exist
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        
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

        # 3. Initialize Reranker (Cross Encoder)
        # We use a standard efficient cross-encoder from HuggingFace
        self.reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.compressor = CrossEncoderReranker(model=self.reranker_model, top_n=TOP_K_RERANK)

        self.vectorstore = None
        self.retriever = None
        self.indexed_documents = []  # Track which documents are indexed
        self.bm25_retrievers = {} #Dictionary to hold a separate retriever for each space
        self.space_docs_map = defaultdict(list) #Map to store documents grouped by space for rebuilding indexes
        print("System Initialized.")

    def load_existing_embeddings(self):
        """
        Load previously saved Partitioned embeddings from disk.
        """
        faiss_index_path = os.path.join(EMBEDDINGS_DIR, "faiss_index")
        bm25_map_path = os.path.join(EMBEDDINGS_DIR, "bm25_docs_map.pkl")
        indexed_docs_path = os.path.join(EMBEDDINGS_DIR, "indexed_documents.pkl")
        
        if not os.path.exists(faiss_index_path):
            print("No existing embeddings found.")
            return False
        
        try:
            print("Loading existing embeddings from disk...")
            
            # 1. Load FAISS index
            self.vectorstore = FAISS.load_local(
                faiss_index_path, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
            
            # 2. Load BM25 Partitions
            self.bm25_retrievers = {}
            self.space_docs_map = defaultdict(list)

            if os.path.exists(bm25_map_path):
                print("Loading BM25 partitions...")
                with open(bm25_map_path, "rb") as f:
                    self.space_docs_map = pickle.load(f)
                
                # Re-instantiate a retriever for each space
                for space_id, docs in self.space_docs_map.items():
                    retriever = BM25Retriever.from_documents(docs)
                    retriever.k = TOP_K_RETRIEVAL
                    self.bm25_retrievers[space_id] = retriever
            else:
                print("Warning: BM25 map not found.")

            # 3. Load indexed documents list
            if os.path.exists(indexed_docs_path):
                with open(indexed_docs_path, "rb") as f:
                    self.indexed_documents = pickle.load(f)
            
            print(f"Successfully loaded embeddings for {len(self.indexed_documents)} document(s).")
            return True
            
        except Exception as e:
            print(f"Error loading embeddings: {str(e)}")
            # Reset state on failure
            self.vectorstore = None
            self.bm25_retrievers = {}
            self.space_docs_map = defaultdict(list)
            self.indexed_documents = []
            return False
            
        except Exception as e:
            print(f"Error loading embeddings: {str(e)}")
            print("Will start with empty index.")
            self.vectorstore = None
            self.retriever = None
            self.indexed_documents = []
            return False

    #
    def load_and_process_pdf(self, file_path: str, space_id: int) -> List[Document]:

        filename = os.path.basename(file_path)
        print(f"--- Fast Processing: {file_path} ---")

        # 1. Fast Extraction (No OCR, takes seconds)
        loader = PyPDFLoader(file_path)
        pages = loader.load()
        full_text = "\n\n".join([p.page_content for p in pages])

        # 2. Splitting
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=CHUNK_SIZE,
            chunk_overlap=CHUNK_OVERLAP
        )

        raw_docs = text_splitter.create_documents([full_text])
        print(f"Created {len(raw_docs)} raw chunks.")

        # --- CRITICAL CHANGE: INJECT METADATA ---
        for doc in raw_docs:
            doc.metadata['source_document'] = filename
            doc.metadata['space_id'] = space_id


        # 3. Contextual Embedding Pre-processing
        print("Generating Contextual Embeddings...")

        # We limit the context to the first 30,000 chars to fit in the fast LLM window
        document_context_str = full_text[:30000]

        contextualized_docs = []

        context_prompt = ChatPromptTemplate.from_template(
            """<document>
            {doc_context}
            </document>
            Here is a chunk of text:
            <chunk>
            {chunk_content}
            </chunk>
            Briefly explain the context of this chunk within the document."""
        )

        chain = context_prompt | self.contextualizer_llm | StrOutputParser()

        # We will only contextualize the first 20 chunks to keep the demo fast.
        # If you want the WHOLE book contextualized, remove the 'if i < 20' check.
        for i, doc in enumerate(raw_docs):

            try:
                    chunk_context = chain.invoke({
                        "doc_context": document_context_str,
                        "chunk_content": doc.page_content
                    })
                    combined_content = f"Context: {chunk_context}\n\nContent: {doc.page_content}"
                    new_doc = Document(page_content=combined_content, metadata=doc.metadata)
                    # Save original content for display
                    new_doc.metadata['original_content'] = doc.page_content
                    contextualized_docs.append(new_doc)
                    print(f"Contextualized chunk {i + 1}...", end='\r')
            except:
                    contextualized_docs.append(doc)

        return contextualized_docs

    def build_index(self, documents: List[Document]):
        with self.index_lock:
            """
            Builds Partitioned Indexes: 
            1. FAISS (Global Vector Store) 
            2. BM25 (Partitioned by Space ID)
            """
            print("--- Building Partitioned Indexes ---")
        
            # 1. Build Vector Store (FAISS) - Global Index
            # FAISS handles everything efficiently in one index using filter tags.
            print("Indexing into FAISS...")
            if self.vectorstore is None:
                self.vectorstore = FAISS.from_documents(documents, self.embeddings)
            else:
                new_vectorstore = FAISS.from_documents(documents, self.embeddings)
                self.vectorstore.merge_from(new_vectorstore)
        
            # 2. Build BM25 Retrievers (Partitioned by Space)
            print("Indexing into BM25 Partitions...")
        
            # Define path for the new map structure
            bm25_map_path = os.path.join(EMBEDDINGS_DIR, "bm25_docs_map.pkl")
        
            # Load existing map or create new
            # Structure: { space_id: [doc1, doc2, ...] }
            if os.path.exists(bm25_map_path):
                with open(bm25_map_path, "rb") as f:
                    self.space_docs_map = pickle.load(f)
            else:
                self.space_docs_map = defaultdict(list)

            # Sort new documents into their specific space buckets
            for doc in documents:
                # Default to 'global' if no space_id is found
                space_id = doc.metadata.get('space_id', 'global')
                self.space_docs_map[space_id].append(doc)

            # Rebuild Retrievers for ALL spaces
            # We maintain a dictionary: { space_id: BM25RetrieverObject }
            self.bm25_retrievers = {} 
        
            print(f"Rebuilding BM25 retrievers for {len(self.space_docs_map)} spaces...")
            for space_id, docs in self.space_docs_map.items():
                retriever = BM25Retriever.from_documents(docs)
                retriever.k = TOP_K_RETRIEVAL
                self.bm25_retrievers[space_id] = retriever

            # 3. Save embeddings to disk
            print("Saving embeddings to disk...")
        
            # Save FAISS
            faiss_index_path = os.path.join(EMBEDDINGS_DIR, "faiss_index")
            self.vectorstore.save_local(faiss_index_path)
        
            # Save BM25 Map (The dictionary of lists)
            with open(bm25_map_path, "wb") as f:
                pickle.dump(self.space_docs_map, f)
        
            # Track indexed documents (for logging/debugging)
            for doc in documents:
                source = doc.metadata.get('source_document', 'Unknown')
                if source not in self.indexed_documents:
                    self.indexed_documents.append(source)
        
            indexed_docs_path = os.path.join(EMBEDDINGS_DIR, "indexed_documents.pkl")
            with open(indexed_docs_path, "wb") as f:
                pickle.dump(self.indexed_documents, f)
        
            print("Indexing Complete and Saved.")

    def query(self, user_query: str, space_id: int = None) -> Dict[str, Any]:
        """
        Query with Partitioned Retrieval.
        1. FAISS: Filters by space_id using native metadata filtering.
        2. BM25: Selects the specific retriever for the given space_id.
        3. Reranks the combined results.
        """
        print(f"\n--- Querying: {user_query} (Space ID: {space_id}) ---")

        # --- STEP 1: FAISS Retrieval (Native Filtering) ---
        # FAISS allows strict filtering using a dictionary.
        if not self.vectorstore:
             return {"answer": "Index not built.", "source_document": None}

        filter_dict = {'space_id': space_id} if space_id else None
        
        # We call similarity_search directly instead of using a retriever wrapper
        faiss_docs = self.vectorstore.similarity_search(
            user_query, 
            k=TOP_K_RETRIEVAL, 
            filter=filter_dict
        )

        # --- STEP 2: BM25 Retrieval (Partitioned Lookup) ---
        bm25_docs = []
        if space_id:
            # CASE A: Specific Space
            # Look up the specific retriever in our dictionary
            target_retriever = self.bm25_retrievers.get(space_id)
            if target_retriever:
                bm25_docs = target_retriever.invoke(user_query)
            else:
                print(f"Warning: No BM25 index found for space {space_id} (might be empty).")
        else:
            # CASE B: Global Search (Optional fallback)
            # If no space is specified, we check all partitions
            for retriever in self.bm25_retrievers.values():
                bm25_docs.extend(retriever.invoke(user_query))

        # --- STEP 3: Ensemble (Merge & Deduplicate) ---
        # Combine lists and remove duplicates based on page_content
        combined_docs_map = {doc.page_content: doc for doc in faiss_docs + bm25_docs}
        combined_docs = list(combined_docs_map.values())

        if not combined_docs:
            return {"answer": "I couldn't find relevant information in this space.", "source_document": None}

        # --- STEP 4: Reranking (Cross Encoder) ---
        # We manually call the compressor on our combined list
        reranked_docs = self.compressor.compress_documents(
            documents=combined_docs, 
            query=user_query
        )

        if not reranked_docs:
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
            "Your namek is Clark, you were created by Omar the G. You are an expert Engineering Professor and Tutor. Your goal is to help college students "
            "deeply understand complex engineering concepts based on the provided course material.\n\n"
            
            "INSTRUCTIONS:\n"
            "1. **Core Accuracy**: Base your factual answer primarily on the provided CONTEXT below. "
            "Do not contradict the context.\n"
            "2. **Elaboration & Depth**: Do not just summarize. Expand on the concepts mentioned in the context. "
            "Explain the 'Why' and 'How' behind the theories. If the context is brief, use your internal knowledge "
            "to provide the theoretical background.\n"
            "3. **Examples**: Provide concrete, real-world engineering examples or analogies to illustrate the points, "
            "even if they are not explicitly in the context.\n"
            "4. **Structure**: Use clear formatting, bullet points, and bold text to make the answer easy to read.\n"
            "5. **Citation**: explicitely mention what part of the answer comes from the context and what part is your own elaboration.\n\n"
            
            "CONTEXT:\n"
            "{context}"
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{question}")
        ])

        chain = prompt | self.llm | StrOutputParser()

        response_text = chain.invoke({
            "context": context_text,
            "question": user_query
        })

        # Debug print
        print({
            "answer": response_text,
            "source_document": top_source_filename,
            "top_chunk_page_content": top_doc.page_content[:200] + "..." 
        })

        return {
            "answer": response_text,
            "source_document": top_source_filename,
            "top_chunk_page_content": top_doc.page_content[:200] + "..." 
        }

