from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, field_validator


class QueenMessageItem(BaseModel):
    id: int
    role: str
    content: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class SendMessageRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def content_valido(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Message cannot be empty")
        if len(v) > 4000:
            raise ValueError("Message too long (max 4000 chars)")
        return v


class SendMessageResponse(BaseModel):
    user_message: QueenMessageItem
    assistant_message: QueenMessageItem
    suggestion: Optional[str] = None


class TrainingNoteItem(BaseModel):
    id: int
    rule: str
    criado_em: datetime

    model_config = {"from_attributes": True}


class CreateTrainingNoteRequest(BaseModel):
    rule: str

    @field_validator("rule")
    @classmethod
    def rule_valido(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Rule cannot be empty")
        if len(v) > 500:
            raise ValueError("Rule too long (max 500 chars)")
        return v
