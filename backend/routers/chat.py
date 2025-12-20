from fastapi import APIRouter, Query, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dependencies import chat_controller, db_manager
from users import current_active_user, User 

router = APIRouter()

class QueryRequest(BaseModel):
    text: str
    thread_id: Optional[int] = None
    branch_id: Optional[int] = None

class BranchRequest(BaseModel):
    content: str
    parent_message_id: int

class MessageRequest(BaseModel):
    content: str

@router.post("/chat")
async def chat(
    request: QueryRequest, 
    space_id: int = Query(1),
    user: User = Depends(current_active_user)
):
    try:

        result = chat_controller.process_user_query(
            query_text=request.text,
            user_id=user.id, 
            thread_id=request.thread_id,
            space_id=space_id,
            is_fork=False,
            branch_id=request.branch_id
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
            parent_message_id=request.parent_message_id,
            is_fork=True
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: int,
    user: User = Depends(current_active_user)
):
    try:
        # 1. Get the standard linear thread
        thread = db_manager.get_thread_with_messages(thread_id)
        if not thread:
            raise HTTPException(status_code=404, detail="Thread not found")
        
        # 2. Get the fork/branch previews (Optimized separate query)
        # Returns: { parent_msg_id: [ {branch_id, preview, created_at}, ... ] }
        forks_map = db_manager.get_thread_forks(thread_id)

        # 3. Inject fork data into the messages list for the frontend
        if 'messages' in thread:
            for msg in thread['messages']:
                # The frontend can checks if msg['forks'].length > 0 to show the icon
                msg['forks'] = forks_map.get(msg['id'], [])

        return {"thread": thread}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/branches/{branch_id}")
async def get_branch_conversation(
    branch_id: int,
    user: User = Depends(current_active_user)
):
    try:
        # Fetches history + branch start + branch replies
        messages = db_manager.get_branch_full_view(branch_id)
        
        return {
            "branch_id": branch_id,
            "messages": messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/branches/{branch_id}/messages")
async def get_branch_messages_only(
    branch_id: int,
    user: User = Depends(current_active_user)
):
    """Returns only the branch messages without ancestor context."""
    try:
        messages = db_manager.get_branch_messages_only(branch_id)
        
        # IMPORTANT: Attach fork/branch data to each message so the frontend can display
        # branch indicators. This allows users to see and navigate to sub-branches that
        # were created from messages within this branch (branches from branches).
        # Without this, the branch view wouldn't show any "Dig Deeper" indicators.
        if messages:
            thread_id = messages[0]['thread_id']
            # Get fork/branch previews for this thread
            forks_map = db_manager.get_thread_forks(thread_id)
            
            # Inject fork data into messages
            for msg in messages:
                msg['forks'] = forks_map.get(msg['id'], [])
        
        return {
            "branch_id": branch_id,
            "messages": messages
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# NOTE: Currently not used by the frontend.
# Purpose: Add a user message to a thread WITHOUT triggering an AI response.
# Use cases: Manual logging, multi-step input, testing, annotations.
@router.post("/threads/{thread_id}/messages")

async def add_message_to_thread(
    thread_id: int, 
    request: MessageRequest,
    user: User = Depends(current_active_user)
):
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