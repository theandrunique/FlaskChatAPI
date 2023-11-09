from typing import Optional
import uuid
from pydantic import BaseModel, Field


class CreateGroupChatModel(BaseModel):
    users_id: Optional[list[int]] = Field(default=None)
    chat_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class GetChatUpdatesModel(BaseModel):
    chat_id: str
    count: Optional[int] = Field(default=20)
    offset: Optional[int] = Field(default=0)
    