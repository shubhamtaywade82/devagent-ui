from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Project(BaseModel):
    id: Optional[str] = None
    name: str
    description: Optional[str] = ""
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

class File(BaseModel):
    id: Optional[str] = None
    project_id: str
    path: str
    content: str
    updated_at: Optional[datetime] = None

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None

