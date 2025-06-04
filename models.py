from pydantic import BaseModel
from enum import Enum


class PromptInput(BaseModel):
    prompt: str
    session_id: str | None = None  # Optional (for new user)
    filename:str
    continuingInteraction:bool


class CommandType(Enum):
    CREATE = "CREATE"
    REMOVE = "REMOVE"


class GenerateCMD:
    def __init__(self, filename: str, content: str, session_id:str,command_type: CommandType):
        self.filename = filename
        self.content = content
        self.session_id=session_id
        self.command_type = command_type


class DeleteFileRequest(BaseModel):
    session_id: str
    filepath: str  # full relative path of the file (e.g. "user_sessions/[session_id]/filename.tsx")

class FilePathInput(BaseModel):
    filepath: str

SESSION_BASE_DIR = "user_sessions"