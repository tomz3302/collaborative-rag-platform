import os
import shutil
import sys
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Depends
from fastapi.responses import FileResponse
from dependencies import rag_system, db_manager, STORAGE_DIR
from users import current_active_user
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

router = APIRouter()

# SUPABASE CONFIGURATION
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL:
    print("Error: SUPABASE_URL not found in .env or environment variables.")
    sys.exit(1)
if not SUPABASE_KEY:
    print("Error: SUPABASE_KEY not found in .env or environment variables.")
    sys.exit(1)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
BUCKET_NAME = "course-materials" # Ensure this bucket exists and is set to PUBLIC in Supabase

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    space_id: int = Query(1),
    user = Depends(current_active_user)
):
    try:
        # 1. Read file content
        file_content = await file.read()
        
        # 2. Upload to Supabase
        # We use a folder structure: space_id/filename
        file_path_in_bucket = f"space_{space_id}/{file.filename}"
        
        print(f"Uploading to Supabase: {file_path_in_bucket}...")
        
        # 'upsert=True' overwrites if exists
        supabase.storage.from_(BUCKET_NAME).upload(
            path=file_path_in_bucket, 
            file=file_content,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )

        # 3. Get Public URL
        public_url = supabase.storage.from_(BUCKET_NAME).get_public_url(file_path_in_bucket)
        print(f"File accessible at: {public_url}")

        # 4. Process RAG (Pass the URL directly)
        # The updated function in advanced_rag.py now downloads from this URL
        docs = rag_system.load_and_process_pdf(public_url, space_id)
        rag_system.build_index(docs)

        # 5. Save to Database
        db_id = db_manager.add_document(
            space_id=space_id, 
            filename=file.filename, 
            file_type='pdf', 
            file_url=public_url  # Storing the HTTP Link
        )
        return {"status": "success", "document_id": db_id, "url": public_url}
    
    except Exception as e:
        print(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def get_documents(
    space_id: int = Query(1),
    user = Depends(current_active_user)
):
    return {"documents": db_manager.get_documents_for_space(space_id)}

@router.get("/documents/{doc_id}/content")
async def get_document_content(
    doc_id: int,
    space_id: int = Query(1),
    user = Depends(current_active_user)
):
    docs = db_manager.get_documents_for_space(space_id)
    target_doc = next((d for d in docs if d['id'] == doc_id), None)
    
    if not target_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "url": target_doc['file_url'], 
        "type": "external", 
        "filename": target_doc['filename']
    }

@router.get("/documents/{doc_id}/threads")
async def get_document_threads(
    doc_id: int,
    user = Depends(current_active_user)
):
    return {"threads": db_manager.get_threads_for_document(doc_id)}