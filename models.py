from pydantic import BaseModel


class PromptInput(BaseModel):
    prompt: str
    session_id: str | None = None  # Optional (for new user)