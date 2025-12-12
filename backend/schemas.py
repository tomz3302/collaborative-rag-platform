from typing import Optional
from fastapi_users import schemas
from pydantic import field_validator

# 1. User Read Schema (Output)
class UserRead(schemas.BaseUser[int]):
    full_name: Optional[str]

# 2. User Create Schema (Registration Input)
class UserCreate(schemas.BaseUserCreate):
    full_name: Optional[str]

    @field_validator("email")
    @classmethod
    def validate_college_email(cls, v: str) -> str:
        # Change this string to your specific college domain
        allowed_domain = "@eng.asu.edu.eg"
        
        if not v.endswith(allowed_domain):
            raise ValueError(f"Registration is restricted to {allowed_domain} emails only.")
        return v

# 3. User Update Schema (Profile Edit)
class UserUpdate(schemas.BaseUserUpdate):
    full_name: Optional[str]