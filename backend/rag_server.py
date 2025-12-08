import os
import shutil
import logging
from typing import Optional
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from chat_controller import ChatController

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

# Allow frontend (served from same origin) but keep CORS for dev scenarios
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base repo directory (one level above backend/)
BASE_DIR = os.path.dirname(os.path.dirname(__file__))

# Setup Persistent Storage for PDFs in repo root
STORAGE_DIR = os.path.join(BASE_DIR, "backend", "storage")
if not os.path.exists(STORAGE_DIR):
    os.makedirs(STORAGE_DIR)

# Path to frontend build (dist) so backend can serve the static site on port 8000
FRONTEND_DIST = os.path.join(BASE_DIR, "frontend", "dist")

# Global RAG Instance (In production, use a proper session manager)
rag_system = AdvancedRAGSystem()
# Load any existing embeddings
try:
    rag_system.load_existing_embeddings()
except Exception:
    logger.warning("No embeddings loaded or load failed; continue without crashing.")

db_manager = DBManager()
handler = OmarHandlers(db_manager=db_manager)
chat_controller = ChatController(db_manager=db_manager, rag_system=rag_system)
is_indexed = False

class QueryRequest(BaseModel):
    text: str
    user_id: int = 1       # Default user ID
    thread_id: Optional[int] = None # Optional thread ID

class BranchRequest(BaseModel, ):
    content: str
    parent_message_id: int
    user_id: int = 1

class MessageRequest(BaseModel):
    content: str
    user_id: str = "Anonymous"

# New Pydantic model for creating Spaces
class SpaceCreate(BaseModel):
    name: str
    description: Optional[str] = None


# Serve the frontend index if available; otherwise return a JSON health response
@app.get("/")
async def read_root():
    index_path = os.path.join(FRONTEND_DIST, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type="text/html")
    return {"message": "Nexus RAG API Server", "status": "running"}


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Save to PERSISTENT storage, not temp
        file_location = os.path.join(STORAGE_DIR, file.filename)

        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        logger.info(f"File stored at: {file_location}")

        # 1. Index document in RAG
        docs = rag_system.load_and_process_pdf(file_location)
        rag_system.build_index(docs)

        # 2. Add document record to Database using DBManager.add_document
        # Use default space_id=1 for now; file_url is the relative path to the stored file
        space_id = 1
        file_url = file_location  # storing absolute path for now; adjust if using cloud storage
        db_id = db_manager.add_document(space_id=space_id, filename=file.filename, file_type='pdf', file_url=file_url)

        return JSONResponse(content={"status": "success", "message": "file uploaded correctly", "document_id": db_id})

    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=500)

@app.post("/api/chat")
async def chat(request: QueryRequest, space_id: int = Query(1)):
    """Process user query through the chat controller."""
    try:
        result = chat_controller.process_user_query(
            query_text=request.text,
            user_id=1,  # Always use user ID 1 as specified
            thread_id=request.thread_id,
            space_id=space_id,
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.post("/api/threads/{thread_id}/branch")
async def branch_from_message(thread_id: int, request: BranchRequest, space_id: int = Query(1)):
    """Create a branch from a specific message in a thread."""
    try:
        result = chat_controller.process_user_query(
            query_text=request.content,
            user_id=1,  # Always use user ID 1
            space_id=space_id,
            thread_id=thread_id,
            parent_message_id=request.parent_message_id
        )
        return JSONResponse(content=result)
    except Exception as e:
        logger.error(f"Error branching conversation: {str(e)}")
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/documents")
async def get_documents(space_id: int = Query(1)):
    """Fetch list of documents for the sidebar. If `space_id` is provided, return documents for that space."""
    try:
        if space_id is not None:
            logger.info(f"Fetching documents for space_id={space_id}")
            # Use the singular compatibility method requested
            docs = db_manager.get_documents_for_space(space_id)

        return JSONResponse(content={"documents": jsonable_encoder(docs)})
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/documents/{doc_id}/content")
async def get_document_content(doc_id: int, space_id: int = Query(1)):
    """Stream the PDF file itself."""
    # In a real app, you'd fetch the filename from DB using doc_id to be safe
    # For simplicity, we just look for matching files in storage
    docs = db_manager.get_documents_for_space(space_id)
    logger.info(f"Requested doc_id: {doc_id}")
    logger.info(f"Available docs: {docs}")
    target_doc = next((d for d in docs if d['id'] == doc_id), None)

    if not target_doc:
        logger.info("Document not found in database")
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join(STORAGE_DIR, target_doc['filename'])
    if not os.path.exists(file_path):
        logger.info(f"File missing from server storage: {file_path}")
        raise HTTPException(status_code=404, detail="File missing from server storage")

    return FileResponse(file_path, media_type='application/pdf')


@app.get("/api/documents/{doc_id}/threads")
async def get_document_threads(doc_id: int):
    """Fetch social threads linked to this document."""
    try:
        threads = db_manager.get_threads_for_document(doc_id)
        return JSONResponse(content={"threads": jsonable_encoder(threads)})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.get("/api/threads/{thread_id}")
async def get_thread(thread_id: int):
    """Fetch a single thread with all its messages."""
    try:
        thread = db_manager.get_thread_with_messages(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        return JSONResponse(content={"thread": jsonable_encoder(thread)})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/spaces")
async def create_space(request: SpaceCreate):
    """Create a new workspace/space."""
    try:
        space_id = db_manager.create_space(name=request.name, description=request.description)
        return JSONResponse(content={"status": "success", "space_id": space_id})
    except Exception as e:
        logger.error(f"Error creating space: {e}")
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/threads/{thread_id}/messages")
async def add_message_to_thread(thread_id: int, request: MessageRequest):
    """Add a new message to an existing thread."""
    try:
        # Get the last message ID to maintain conversation flow
        parent_msg_id = db_manager.get_last_message_id(thread_id)

        # Add the message (using user_id=1 for now, you can extend this)
        message_id = db_manager.add_message(
            thread_id=thread_id,
            user_id=1,  # Default user ID - extend with actual user system later
            role="user",
            content=request.content,
            parent_message_id=parent_msg_id
        )

        return JSONResponse(content={"status": "success", "message_id": message_id})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/spaces")
async def list_spaces():
    try:
        spaces = db_manager.get_spaces()
        return JSONResponse(content={"spaces": jsonable_encoder(spaces)})
    except Exception as e:
        logger.error(f"Error fetching spaces: {e}")

    """Return a list of available spaces."""
# Mount frontend static files (this makes the frontend and backend available on the same port)
if os.path.isdir(FRONTEND_DIST):
    # Mounting at root will let API routes (/api/...) take precedence and serve files otherwise
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
else:
    logger.info(f"Frontend dist not found at {FRONTEND_DIST}. Build the frontend with `npm run build` in the frontend folder to serve it from the backend.")

# NOTE: Do NOT create a local 'static' folder here; frontend build artifacts are expected in frontend/dist

if __name__ == "__main__":
    import uvicorn
    print("Starting Nexus RAG Backend Server on http://localhost:8000")
    print("If you want the frontend served from the backend, run `npm run build` in the frontend folder first.")
    uvicorn.run(app, host="0.0.0.0", port=8000)