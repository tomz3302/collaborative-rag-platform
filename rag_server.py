import os
import shutil
import logging
from typing import List
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import the RAG system class from the previous step
# Assuming the previous file was named 'advanced_rag.py'
# If you pasted it all in one file, ensure the class AdvancedRAGSystem is available here.
from advanced_rag import AdvancedRAGSystem

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG_Server")

# --- FastAPI App ---
app = FastAPI(title="Fluid RAG")

# Global RAG Instance (In production, use a proper session manager)
rag_system = AdvancedRAGSystem()
is_indexed = False

class QueryRequest(BaseModel):
    text: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    global is_indexed
    
    try:
        # Save temp file
        file_location = f"temp_{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        logger.info(f"File saved: {file_location}")
        
        # Process (Blocking for simplicity, ideally use background tasks for status updates)
        # We run this strictly to ensure it's ready before returning
        docs = rag_system.load_and_process_pdf(file_location)
        rag_system.build_index(docs)
        
        # Cleanup
        os.remove(file_location)
        is_indexed = True
        
        return JSONResponse(content={"status": "success", "message": "Knowledge Base Ready"})
        
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)

@app.post("/api/chat")
async def chat(request: QueryRequest):
    global is_indexed
    if not is_indexed:
        return JSONResponse(content={"answer": "Please upload a document first (PDF)."}, status_code=400)
    
    try:
        response = rag_system.query(request.text)
        # Basic markdown cleanup if needed
        # If the RAG system already returns a dict with 'answer' and 'source_document', return it directly
        if isinstance(response, dict) and "answer" in response:
            return JSONResponse(content=response)
        # Fallback: wrap string responses
        return JSONResponse(content={"answer": str(response)})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Create static folder if it doesn't exist (logic handled by manual file creation below)
if not os.path.exists("static"):
    os.makedirs("static")

if __name__ == "__main__":
    import uvicorn
    print("Starting Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)