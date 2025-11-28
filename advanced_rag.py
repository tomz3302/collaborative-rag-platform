import os
import sys
import time
from typing import List, Tuple, Dict, Any
from operator import itemgetter

# --- Libraries ---
import numpy as np
from docling.document_converter import DocumentConverter
from langchain_classic.retrievers import ContextualCompressionRetriever
from langchain_community.document_loaders import PyPDFLoader
# LangChain & Graph
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
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

class AdvancedRAGSystem:
    def __init__(self):
        print("Initializing Advanced RAG System...")
        
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
        print("System Initialized.")

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
        """
        print("--- Building Hybrid Index ---")
        
        # 1. Build Vector Store (FAISS) with Gemini 004 Embeddings
        print("Indexing into FAISS...")
        self.vectorstore = FAISS.from_documents(documents, self.embeddings)
        faiss_retriever = self.vectorstore.as_retriever(search_kwargs={"k": TOP_K_RETRIEVAL})

        # 2. Build BM25 Retriever
        print("Indexing into BM25...")
        bm25_retriever = BM25Retriever.from_documents(documents)
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
        print("Indexing Complete.")

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


# --- Main Execution Flow ---
if __name__ == "__main__":
    # Create the pipeline
    rag_system = AdvancedRAGSystem()
    
    # --- INPUT: Define your PDF path here ---
    # Create a dummy pdf or point to a real one
    pdf_path = "example_document.pdf" 
    
    # Check if file exists for the demo
    if not os.path.exists(pdf_path):
        print(f"File {pdf_path} not found. Creating a dummy PDF for demonstration...")
        from reportlab.pdfgen import canvas
        c = canvas.Canvas(pdf_path)
        c.drawString(100, 750, "The Apollo 11 mission landed on the moon in 1969.")
        c.drawString(100, 730, "Neil Armstrong was the first human to walk on the lunar surface.")
        c.drawString(100, 710, "The module was named Eagle. The command module was Columbia.")
        c.drawString(100, 690, "It is estimated that 650 million people watched the landing.")
        c.save()

    # 1. Ingest
    docs = rag_system.load_and_process_pdf(pdf_path)
    
    # 2. Index
    rag_system.build_index(docs)
    
    # 3. Query Loop
    while True:
        q = input("\nAsk a question (or 'q' to quit): ")
        if q.lower() in ['q', 'quit']:
            break
            
        answer = rag_system.query(q)
        print("\nAnswer:\n", answer)