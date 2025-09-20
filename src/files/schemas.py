"""
Schematy Pydantic dla modułu files.
"""
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel
from pathlib import Path


class FileInfo(SQLModel):
    """Informacje o pliku."""
    file_path: str
    file_name: str
    file_size: int
    file_type: str
    created_at: datetime
    modified_at: datetime
    exists: bool


class FileResponse(SQLModel):
    """Odpowiedź z informacjami o pliku."""
    status: str
    message: str
    file_info: Optional[FileInfo] = None


class FileAccessRequest(SQLModel):
    """Żądanie dostępu do pliku."""
    file_path: str
    user_id: Optional[int] = None
    bill_id: Optional[int] = None
    message_id: Optional[int] = None


class FileAccessResponse(SQLModel):
    """Odpowiedź na żądanie dostępu do pliku."""
    status: str
    message: str
    access_granted: bool
    file_url: Optional[str] = None
    expires_at: Optional[datetime] = None
