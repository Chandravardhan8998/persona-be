
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from agent_controller import code_generator
from fastapi.responses import StreamingResponse
import redis.asyncio as redis
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from models import PromptInput

load_dotenv()
app = FastAPI()
r = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/session/{session_id}/files")
async def list_session_files(session_id: str):
    session_path = Path(f"./{session_id}")  # Path to the session folder

    if not session_path.exists() or not session_path.is_dir():
        raise HTTPException(status_code=404, detail="Session folder not found")

    # Recursively list all files
    files = [
        str(p.relative_to(session_path))
        for p in session_path.rglob("*")
        if p.is_file()
    ]

    return JSONResponse(content={"session_id": session_id, "files": files})

@app.post("/generate-code")
async def generate_code(body:PromptInput):
    stream = code_generator(body.prompt, body.session_id)
    return (StreamingResponse(stream, media_type="text/event-stream"))



# async def code_generator(prompt: str, session_id: str):
#     session_key = f"chat:{session_id}"
#     prev_msgs = await r.get(session_key)
#     messages = json.loads(prev_msgs) if prev_msgs else []
#
#     if not prev_msgs:
#         messages.append({"role": "system", "content": CODE_AGENT_SYSTEM_PROMPT})
#
#     client = OpenAI()
#     messages.append({"role": "user", "content": prompt})
#
#     while True:
#         response = client.chat.completions.create(
#             model="gpt-4.1-mini",
#             messages=messages,
#             response_format={'type': "json_object"}
#         )
#
#         content = response.choices[0].message.content
#         messages.append({"role": "assistant", "content": content})
#
#         parsed_response = json.loads(content)
#
#         if parsed_response.get("step") == "action":
#             tool_name = parsed_response.get("function")
#             tool_input = parsed_response.get("input")
#
#             if available_tools.get(tool_name):
#                 output = available_tools[tool_name](tool_input)
#                 messages.append({
#                     "role": "user",
#                     "content": json.dumps({"step": "observe", "output": output})
#                 })
#                 yield f"data: {json.dumps(parsed_response)}\n\n"
#                 continue
#
#         if parsed_response.get("step") == "output":
#             yield f"data: {json.dumps(parsed_response)}\n\n"
#             break
#
#     # ✅ Store updated messages back to Redis
#     await r.set(session_key, json.dumps(messages), ex=36000)


# @app.post("/generate")
# async def generate_text(query: PromptInput):
#     prompt = query.prompt
#     return StreamingResponse(event_generator(prompt),   media_type="text/event-stream")
#
# def event_generator(prompt: str):
#     client = OpenAI()
#     messages = [
#         {"role": "system", "content": SYSTEM_PROMPT},
#         {"role": "user", "content": prompt}
#     ]
#     while True:
#         response = client.chat.completions.create(
#             model="gpt-4.1-mini",
#             messages=messages,
#             response_format={'type': "json_object"},
#             stream=False
#         )
#         content = response.choices[0].message.content
#         messages.append({"role": "assistant", "content": content})
#         parsed_response = json.loads(content)
#
#         yield f"data: {json.dumps(parsed_response)}\n\n"
#
#         if parsed_response.get("step") == "result":
#             break























