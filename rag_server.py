import os
import shutil
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# Import the RAG system class from the previous step
# Assuming the previous file was named 'advanced_rag.py'
# If you pasted it all in one file, ensure the class AdvancedRAGSystem is available here.
from advanced_rag import AdvancedRAGSystem
from database_manager import DBManager
from handlers import OmarHandlers

# --- Setup Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("RAG_Server")

# --- FastAPI App ---
app = FastAPI(title="Fluid RAG")

# Global RAG Instance (In production, use a proper session manager)
rag_system = AdvancedRAGSystem()

db_manager = DBManager()
handler = OmarHandlers(db_manager=db_manager, rag_system=rag_system)

is_indexed = False

class QueryRequest(BaseModel):
    text: str
    user_id: int = 1       # Default user ID
    thread_id: Optional[int] = None # Optional thread ID
@app.get("/", response_class=HTMLResponse)
async def read_root():
    with open("static/index.html", "r") as f:
        return f.read()

@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_location = f"temp_{file.filename}"
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File saved: {file_location}")

        # 1. Index document in RAG
        docs = rag_system.load_and_process_pdf(file_location)
        rag_system.build_index(docs)

        # 2. Add document record to Database (Missing piece!)
        conn = db_manager.get_connection()
        cursor = conn.cursor()
        # We store just the filename for now.
        # Ideally, read the binary data here if you want to store the PDF in DB
        cursor.execute(
            "INSERT INTO documents (filename, file_type) VALUES (%s, 'pdf')",
            (file.filename,)  # Store original filename without 'temp_'
        )
        conn.commit()
        cursor.close()
        conn.close()

        # Cleanup
        os.remove(file_location)

        return JSONResponse(content={"status": "success", "message": "Knowledge Base Ready"})

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)

@app.post("/api/chat")
async def chat(request: QueryRequest):
    # global is_indexed
    # if not is_indexed:
    #     return JSONResponse(content={"answer": "Please upload a document first (PDF)."}, status_code=400)

    try:
        # ROUTE THROUGH HANDLER
        result = handler.handle_user_query(
            user_id=request.user_id,
            query_text=request.text,
            thread_id=request.thread_id
        )
        return JSONResponse(content=result)

    except Exception as e:
        logger.error(e)
        return JSONResponse(content={"error": str(e)}, status_code=500)

# Create static folder if it doesn't exist (logic handled by manual file creation below)
if not os.path.exists("static"):
    os.makedirs("static")

if __name__ == "__main__":
    import uvicorn
    print("Starting Server on http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)