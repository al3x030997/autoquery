"""File upload schemas."""
from pydantic import BaseModel


class UploadResponse(BaseModel):
    text: str
    word_count: int
    category: str
    filename: str
