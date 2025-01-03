from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class FeedbackCreate(BaseModel):
    type: str
    content: str
    contact: Optional[str] = None
    kb_id: Optional[int] = None
    kb_name: Optional[str] = None

class FeedbackResponse(BaseModel):
    id: int
    type: str
    content: str
    contact: Optional[str]
    created_at: datetime
    username: str
    kb_id: Optional[int]
    kb_name: Optional[str]

    class Config:
        from_attributes = True 