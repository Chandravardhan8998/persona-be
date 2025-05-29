
from dotenv import load_dotenv
from openai import OpenAI
from fastapi import FastAPI
from pydantic import BaseModel
from app import SYSTEM_PROMPT
from fastapi.responses import StreamingResponse
import json
load_dotenv()
app = FastAPI()

class PromptInput(BaseModel):
    prompt: str

@app.post("/generate")
async def generate_text(query: PromptInput):
    prompt = query.prompt
    return StreamingResponse(event_generator(prompt),   media_type="text/event-stream")

def event_generator(prompt: str):
    client = OpenAI()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt}
    ]
    while True:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=messages,
            response_format={'type': "json_object"},
            stream=False
        )
        content = response.choices[0].message.content
        messages.append({"role": "assistant", "content": content})
        parsed_response = json.loads(content)

        yield f"data: {json.dumps(parsed_response)}\n\n"

        if parsed_response.get("step") == "result":
            break