import os
import shutil
from fastapi import APIRouter, UploadFile, File, Query, HTTPException, Depends
from fastapi.responses import FileResponse
from dependencies import rag_system, db_manager, STORAGE_DIR
from users import current_active_user

router = APIRouter()

@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...), 
    space_id: int = Query(1),
    user = Depends(current_active_user)
):
    try:
        file_location = os.path.join(STORAGE_DIR, file.filename)
        with open(file_location, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        docs = rag_system.load_and_process_pdf(file_location, space_id)
        rag_system.build_index(docs)

        db_id = db_manager.add_document(
            space_id=space_id, 
            filename=file.filename, 
            file_type='pdf', 
            file_url=file_location
        )
        return {"status": "success", "document_id": db_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/documents")
async def get_documents(space_id: int = Query(1)):
    # Public or Protected? Let's make it protected
    return {"documents": db_manager.get_documents_for_space(space_id)}

@router.get("/documents/{doc_id}/content")
async def get_document_content(doc_id: int, space_id: int = Query(1)):
    docs = db_manager.get_documents_for_space(space_id)
    target_doc = next((d for d in docs if d['id'] == doc_id), None)
    
    if not target_doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = os.path.join(STORAGE_DIR, target_doc['filename'])
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File missing")

    return FileResponse(file_path, media_type='application/pdf')

@router.get("/documents/{doc_id}/threads")
async def get_document_threads(doc_id: int):
    return {"threads": db_manager.get_threads_for_document(doc_id)}