from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from dependencies import db_manager
from users import current_active_user

router = APIRouter()

class SpaceCreate(BaseModel):
    name: str
    description: Optional[str] = None

@router.post("/spaces")
async def create_space(request: SpaceCreate, user = Depends(current_active_user)):
    try:
        space_id = db_manager.create_space(name=request.name, description=request.description)
        return {"status": "success", "space_id": space_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/spaces")
async def list_spaces():
    # Making this public so users can see spaces before joining? 
    # Or protected? Let's keep it open for now, or add Depends(current_active_user)
    return {"spaces": db_manager.get_spaces()}