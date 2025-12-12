from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from dependencies import chat_controller # <--- Import from dependencies
from users import current_active_user, User # <--- Import Auth

router = APIRouter()

class QueryRequest(BaseModel):
    text: str
    thread_id: Optional[int] = None

class BranchRequest(BaseModel):
    content: str
    parent_message_id: int

class MessageRequest(BaseModel):
    content: str

@router.post("/chat")
async def chat(
    request: QueryRequest, 
    space_id: int = Query(1),
    user: User = Depends(current_active_user) # <--- PROTECTED ROUTE
):
    try:
        # We use the ACTUAL user ID from the login now
        result = chat_controller.process_user_query(
            query_text=request.text,
            user_id=user.id, 
            thread_id=request.thread_id,
            space_id=space_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/threads/{thread_id}/branch")
async def branch_from_message(
    thread_id: int, 
    request: BranchRequest, 
    space_id: int = Query(1),
    user: User = Depends(current_active_user)
):
    try:
        result = chat_controller.process_user_query(
            query_text=request.content,
            user_id=user.id,
            space_id=space_id,
            thread_id=thread_id,
            parent_message_id=request.parent_message_id
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: int,
    user: User = Depends(current_active_user)
):
    from dependencies import db_manager
    try:
        thread = db_manager.get_thread_with_messages(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        return {"thread": thread}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/threads/{thread_id}/messages")
async def add_message_to_thread(
    thread_id: int, 
    request: MessageRequest,
    user: User = Depends(current_active_user)
):
    # Logic moved from main file, need to access db_manager via dependencies if needed
    # But chat_controller might not have this exact method exposed. 
    # Let's import db_manager directly for this simple DB op.
    from dependencies import db_manager
    try:
        parent_msg_id = db_manager.get_last_message_id(thread_id)
        message_id = db_manager.add_message(
            thread_id=thread_id,
            user_id=user.id,
            role="user",
            content=request.content,
            parent_message_id=parent_msg_id
        )
        return {"status": "success", "message_id": message_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))