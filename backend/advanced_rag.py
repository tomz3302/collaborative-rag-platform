import os
import sys
import pickle
from typing import List, Dict, Any


# --- Libraries ---

from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_community.document_loaders import PyPDFLoader
# LangChain & Graph
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_text_splitters import RecursiveCharacterTextSplitter

# Google Gemini
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

# Vector Store & Retrieval
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
# Ensemble and ContextualCompression are in the main 'langchain' package
from langchain_classic.retrievers.ensemble import EnsembleRetriever

from langchain_classic.retrievers.document_compressors import CrossEncoderReranker

# HuggingFaceCrossEncoder is currently most stable in 'langchain_community'
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

# --- Configuration ---
# Ensure you have GOOGLE_API_KEY set in your environment variables
# os.environ["GOOGLE_API_KEY"] = "your_key_here"

if "GOOGLE_API_KEY" not in os.environ:
    print("Error: GOOGLE_API_KEY environment variable not found.")
    sys.exit(1)

# Configuration Constants
EMBEDDING_MODEL = "models/text-embedding-004"
LLM_MODEL = "gemini-2.5-flash"  # Flash is fast and supports long context/caching
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
TOP_K_RETRIEVAL = 15  # Fetch more for hybrid search
TOP_K_RERANK = 5      # Final number of docs to LLM
EMBEDDINGS_DIR = "embeddings"  # Directory to store vector embeddings

class AdvancedRAGSystem:
    def __init__(self):
        print("Initializing Advanced RAG System...")
        
        # Create embeddings directory if it doesn't exist
        os.makedirs(EMBEDDINGS_DIR, exist_ok=True)
        
        # 1. Initialize LLMs
        # Main LLM for Generation
        self.llm = ChatGoogleGenerativeAI(
            model=LLM_MODEL,
            temperature=0.3,
            # Gemini automatically handles caching for long identical prefixes (System Prompts)
            # We will structure our prompts to take advantage of this.
        )
        
        # Cheaper/Faster LLM for Contextualizing Chunks (using Flash for speed)
        self.contextualizer_llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
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
        print("System Initialized.")

    def load_existing_embeddings(self):
        """
        Load previously saved embeddings from disk if they exist.
        Returns True if embeddings were loaded, False otherwise.
        """
        faiss_index_path = os.path.join(EMBEDDINGS_DIR, "faiss_index")
        bm25_docs_path = os.path.join(EMBEDDINGS_DIR, "bm25_documents.pkl")
        indexed_docs_path = os.path.join(EMBEDDINGS_DIR, "indexed_documents.pkl")
        
        # Check if all required files exist
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
            faiss_retriever = self.vectorstore.as_retriever(search_kwargs={"k": TOP_K_RETRIEVAL})
            
            # 2. Load BM25 documents
            if os.path.exists(bm25_docs_path):
                with open(bm25_docs_path, "rb") as f:
                    bm25_docs = pickle.load(f)
                bm25_retriever = BM25Retriever.from_documents(bm25_docs)
                bm25_retriever.k = TOP_K_RETRIEVAL
            else:
                print("Warning: BM25 documents not found, using empty retriever")
                bm25_retriever = BM25Retriever.from_documents([])
                bm25_retriever.k = TOP_K_RETRIEVAL
            
            # 3. Create Ensemble Retriever
            self.ensemble_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, faiss_retriever],
                weights=[0.5, 0.5]
            )
            
            # 4. Add Reranking Layer
            self.retriever = ContextualCompressionRetriever(
                base_compressor=self.compressor,
                base_retriever=self.ensemble_retriever
            )
            
            # 5. Load indexed documents list
            if os.path.exists(indexed_docs_path):
                with open(indexed_docs_path, "rb") as f:
                    self.indexed_documents = pickle.load(f)
            
            print(f"Successfully loaded embeddings for {len(self.indexed_documents)} document(s).")
            print(f"Indexed documents: {', '.join(self.indexed_documents)}")
            return True
            
        except Exception as e:
            print(f"Error loading embeddings: {str(e)}")
            print("Will start with empty index.")
            self.vectorstore = None
            self.retriever = None
            self.indexed_documents = []
            return False

    #
    def load_and_process_pdf(self, file_path: str) -> List[Document]:

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
        """
        Builds Hybrid Index: FAISS (Vector) + BM25 (Keyword)
        Also saves the index to disk for persistence.
        """
        print("--- Building Hybrid Index ---")
        
        # 1. Build Vector Store (FAISS) with Gemini 004 Embeddings
        print("Indexing into FAISS...")
        if self.vectorstore is None:
            self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        else:
            # If vectorstore exists, add new documents to it
            new_vectorstore = FAISS.from_documents(documents, self.embeddings)
            self.vectorstore.merge_from(new_vectorstore)
        
        faiss_retriever = self.vectorstore.as_retriever(search_kwargs={"k": TOP_K_RETRIEVAL})

        # 2. Build BM25 Retriever
        print("Indexing into BM25...")
        # Load existing documents if they exist
        bm25_docs_path = os.path.join(EMBEDDINGS_DIR, "bm25_documents.pkl")
        existing_bm25_docs = []
        if os.path.exists(bm25_docs_path):
            with open(bm25_docs_path, "rb") as f:
                existing_bm25_docs = pickle.load(f)
        
        # Combine existing and new documents
        all_bm25_docs = existing_bm25_docs + documents
        bm25_retriever = BM25Retriever.from_documents(all_bm25_docs)
        bm25_retriever.k = TOP_K_RETRIEVAL

        # 3. Create Ensemble Retriever (Hybrid Search)
        # Weights: 0.5 for Dense, 0.5 for Sparse
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever],
            weights=[0.5, 0.5]
        )
        
        # 4. Add Reranking Layer
        # The ensemble retrieves TOP_K_RETRIEVAL (20), the compressor reranks and returns TOP_K_RERANK (5)
        self.retriever = ContextualCompressionRetriever(
            base_compressor=self.compressor,
            base_retriever=self.ensemble_retriever
        )
        
        # 5. Save embeddings to disk
        print("Saving embeddings to disk...")
        faiss_index_path = os.path.join(EMBEDDINGS_DIR, "faiss_index")
        self.vectorstore.save_local(faiss_index_path)
        
        # Save BM25 documents
        with open(bm25_docs_path, "wb") as f:
            pickle.dump(all_bm25_docs, f)
        
        # Track indexed documents
        for doc in documents:
            source = doc.metadata.get('source_document', 'Unknown')
            if source not in self.indexed_documents:
                self.indexed_documents.append(source)
        
        # Save indexed documents list
        indexed_docs_path = os.path.join(EMBEDDINGS_DIR, "indexed_documents.pkl")
        with open(indexed_docs_path, "wb") as f:
            pickle.dump(self.indexed_documents, f)
        
        print("Indexing Complete and Saved.")

    def query(self, user_query: str) -> Dict[str, Any]:
        """
        Returns a dictionary: {'answer': str, 'source_document': str}
        """
        if not self.retriever:
            return {"answer": "Index not built.", "source_document": None}

        print(f"\n--- Querying: {user_query} ---")

        # 1. Retrieve and Rerank MANUALLY (To inspect results)
        retrieved_docs = self.retriever.invoke(user_query)

        if not retrieved_docs:
            return {"answer": "I couldn't find relevant information.", "source_document": None}

        # 2. Identify the Top Source Document
        # Since retrieval is reranked, index 0 is the most relevant
        top_doc = retrieved_docs[0]
        # Get the filename we injected earlier
        top_source_filename = top_doc.metadata.get('source_document', 'Unknown Document')

        # 3. Prepare Context for LLM
        def format_docs(docs):
            formatted_results = []
            for doc in docs:
                # Use original content if available (cleaner), otherwise use contextualized
                content = doc.metadata.get('original_content', doc.page_content)
                formatted_results.append(f"<source doc='{doc.metadata.get('source_document')}'>\n{content}\n</source>")
            return "\n\n".join(formatted_results)

        context_text = format_docs(retrieved_docs)

        # 4. Generate Answer
        system_prompt = (
            "You are an expert assistant. Use the provided context to answer the user's question. "
            "If the answer is not in the context, say so."
            "\n\n"
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

        # 5. Return Structured Result
        # Debug: print the structured result (use a dict, not a set)
        print({
            "answer": response_text,
            "source_document": top_source_filename,
            "top_chunk_page_content": top_doc.page_content[:200] + "..."  # Optional: Debug info
        })
        return {
            "answer": response_text,
            "source_document": top_source_filename,
            "top_chunk_page_content": top_doc.page_content[:200] + "..."  # Optional: Debug info
        }

