import os
import time
import random
import requests
import tempfile
from typing import List
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Configuration Constants
CHUNK_SIZE = 800
CHUNK_OVERLAP = 150
# Threshold: 30k chars is roughly 7.5k tokens. 
# Groq's Llama-3.3-70b free tier often has a 6k-30k TPM limit.
CONTEXT_THRESHOLD_CHARS = 30000 

class DocumentProcessorService:
    def __init__(self, contextualizer_llm):
        self.contextualizer_llm = contextualizer_llm
        self.context_prompt = ChatPromptTemplate.from_template(
            """<document>{doc_context}</document>
               Here is a chunk of text: <chunk>{chunk_content}</chunk>
               Briefly explain the context of this chunk within the document."""
        )
        self.chain = self.context_prompt | self.contextualizer_llm | StrOutputParser()

    def process_pdf(self, file_url: str, db_id: int, space_id: int) -> List[Document]:
        """
        Downloads and processes PDF with Claude's Contextual Retrieval method.
        Optimized for Groq Rate Limits.
        """
        filename = file_url.split('/')[-1].split('?')[0]
        local_temp_path = self._download_file(file_url)

        try:
            loader = PyPDFLoader(local_temp_path)
            pages = loader.load()
            full_text = "\n\n".join([p.page_content for p in pages])

            # 1. Split into raw chunks
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=CHUNK_SIZE,
                chunk_overlap=CHUNK_OVERLAP
            )
            raw_docs = text_splitter.create_documents([full_text])
            
            # 2. Decide Strategy based on Token/Char limit
            if len(full_text) <= CONTEXT_THRESHOLD_CHARS:
                print(f"--- Strategy: Global Context (Size: {len(full_text)} chars) ---")
                return self._process_with_global_context(raw_docs, full_text, filename, space_id, file_url, db_id)
            else:

                # print(f"--- Strategy: Sliding Window Placeholder (Size: {len(full_text)} chars) ---")
                # return self._process_with_sliding_window(raw_docs, full_text, filename, space_id, file_url, db_id)
                
                # FALLBACK STRATEGY: No context injection for large documents to avoid 429 errors
                print(f"--- Strategy: Skip Context Injection (Size: {len(full_text)} chars) ---")
                contextualized_docs = []
                for i, doc in enumerate(raw_docs):
                    # We pass a simple indicator or empty string as context
                    # This keeps your 'combined_content' format consistent for the DB
                    new_doc = self._create_contextual_doc(
                        doc, 
                        "", 
                        filename, 
                        space_id, 
                        file_url, 
                        db_id
                    )
                    contextualized_docs.append(new_doc)
                return contextualized_docs

        finally:
            if os.path.exists(local_temp_path):
                os.remove(local_temp_path)

    def _process_with_global_context(self, raw_docs, full_text, filename, space_id, file_url, db_id):
        """Your original logic: uses the whole (truncated) doc for every chunk."""
        contextualized_docs = []
        document_context_str = full_text[:CONTEXT_THRESHOLD_CHARS]

        for i, doc in enumerate(raw_docs):
            # Mandatory sleep for Groq Free Tier (adjust based on your specific TPM)
            time.sleep(1.5) 

            retries = 3
            success = False
            while retries > 0 and not success:
                try:
                    chunk_context = self.chain.invoke({
                        "doc_context": document_context_str,
                        "chunk_content": doc.page_content
                    })
                    
                    new_doc = self._create_contextual_doc(doc, chunk_context, filename, space_id, file_url, db_id)
                    contextualized_docs.append(new_doc)
                    print(f"Processed chunk {i + 1}/{len(raw_docs)}...", end='\r')
                    success = True

                except Exception as e:
                    success, retries = self._handle_error(e, i, retries, contextualized_docs, doc)

        return contextualized_docs

    def _process_with_block_context(self, raw_docs, full_text, filename, space_id, file_url, db_id):
        """
        Divides the document into 'Big Blocks' that fit Groq's TPM.
        Chunks inside a block only 'see' that block as their context.
        """
        contextualized_docs = []
    
        # 1. Group raw_docs into blocks that fit the character limit
        blocks = []
        current_block_docs = []
        current_block_chars = 0
    
        for doc in raw_docs:
            doc_len = len(doc.page_content)
            if current_block_chars + doc_len > CONTEXT_THRESHOLD_CHARS:
                # Block is full, save it and start new one
                blocks.append(current_block_docs)
                current_block_docs = [doc]
                current_block_chars = doc_len
            else:
                current_block_docs.append(doc)
                current_block_chars += doc_len
    
        if current_block_docs: # Add the last remaining block
            blocks.append(current_block_docs)

        print(f"--- Document divided into {len(blocks)} Big Context Blocks ---")

        # 2. Process each block
        total_processed = 0
        for block_idx, block_chunks in enumerate(blocks):
            # Create the context string for this specific block
            block_context_str = "\n\n".join([d.page_content for d in block_chunks])
        
            print(f"\nProcessing Block {block_idx + 1}/{len(blocks)} ({len(block_chunks)} chunks)")
        
            for i, doc in enumerate(block_chunks):
                # Groq Sleep: Essential for Free Tier
                time.sleep(1.5) 
            
                retries = 3
                success = False
                while retries > 0 and not success:
                    try:
                        chunk_context = self.chain.invoke({
                            "doc_context": block_context_str,
                            "chunk_content": doc.page_content
                        })
                    
                        new_doc = self._create_contextual_doc(doc, chunk_context, filename, space_id, file_url, db_id)
                        contextualized_docs.append(new_doc)
                    
                        total_processed += 1
                        print(f"Chunk {total_processed}/{len(raw_docs)} (Block {block_idx+1}) complete...", end='\r')
                        success = True

                    except Exception as e:
                        success, retries = self._handle_error(e, total_processed, retries, contextualized_docs, doc)

        return contextualized_docs

    def _download_file(self, file_url: str) -> str:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            response = requests.get(file_url, stream=True)
            response.raise_for_status()
            for chunk in response.iter_content(chunk_size=8192):
                temp_file.write(chunk)
            return temp_file.name

    def _create_contextual_doc(self, doc, context, filename, space_id, file_url, db_id):
        combined_content = f"Context: {context}\n\nContent: {doc.page_content}"
        new_doc = Document(page_content=combined_content, metadata=doc.metadata.copy())
        new_doc.metadata.update({
            'source_document': filename,
            'space_id': space_id,
            'file_url': file_url,
            'db_id': db_id,
            'original_content': doc.page_content
        })
        return new_doc

    def _handle_error(self, e, index, retries, docs_list, original_doc):
        error_msg = str(e)
        if "429" in error_msg or "rate limit" in error_msg.lower():
            wait_time = 15 + random.randint(1, 5)
            print(f"\nRate Limit Hit on chunk {index}! Sleeping {wait_time}s...")
            time.sleep(wait_time)
            return False, retries - 1
        else:
            print(f"\nError on chunk {index}: {e}. Skipping context.")
            docs_list.append(original_doc)
            return True, 0