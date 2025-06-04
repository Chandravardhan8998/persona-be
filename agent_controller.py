import openai
from dotenv import load_dotenv
from openai import OpenAI

from agent_tools import (run_command, generate_cmd,
                         )
import asyncio
from models import GenerateCMD, CommandType, SESSION_BASE_DIR, PromptInput
from prompts import CODE_AGENT_SYSTEM_PROMPT
from redis_config import r
import json
import subprocess
import redis
import re
from pathlib import Path

load_dotenv()
client = OpenAI()

def cleanup_session(session_id: str):
    folder_path = f"{SESSION_BASE_DIR}/{session_id}"
    subprocess.getoutput(f"rm -rf {folder_path}")  # Dangerous! Use with checks
    try:
        r.delete(f"chat:{session_id}")
    except redis.exceptions.ConnectionError as e:
        print("❌ Redis connection failed:", e)

def to_snake_case(name: str) -> str:
    # Convert to snake_case
    name = re.sub(r'[\W_]+', '_', name)
    return name.lower()

async def code_generator(body:PromptInput):
    # Convert filename to snake_case for folder/redis key
    safe_filename = to_snake_case(body.filename)
    redis_key = f"chat:{body.session_id}/{safe_filename}"

    print("🔑 Using Redis key:", redis_key)

    # Fetch previous messages if any
    prev_msgs = ""
    try:
        exist = await r.exists(redis_key)
        if exist:
            prev_msgs = await r.get(redis_key)
    except redis.exceptions.ConnectionError as e:
        print("❌ Redis connection failed:", e)

    messages = json.loads(prev_msgs) if prev_msgs else []
    if len(messages)==0:
        messages.append({"role": "system", "content": CODE_AGENT_SYSTEM_PROMPT})
    if not body.continuingInteraction:
         messages.append({"role": "user", "content": f"{body.prompt} where app and folder name is strictly {safe_filename}"})
    print(messages)
    while True:
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                response_format={"type": "json_object"},
                messages=messages,
            )
            msg = response.choices[0].message.content
            parsed = json.loads(msg)
            step = parsed.get("step")
            messages.append({"role": "assistant", "content": msg})

            try:
                await r.set(redis_key, json.dumps(messages), ex=3600)
            except redis.exceptions.ConnectionError as e:
                print("❌ Redis connection failed:", e)

            # if step == "review":
            #     json_data={}
            #     yield f"data: {json.dumps(json_data)}\n\n"
            #     await asyncio.sleep(0.01)
            if step != "generate":
                yield f"data: {json.dumps(parsed)}\n\n"
                await asyncio.sleep(0.01)

            elif step == "generate":
                # Create session project folder if doesn't exist
                project_path = Path(f"./{SESSION_BASE_DIR}/{body.session_id}/{safe_filename}")
                project_path.mkdir(parents=True, exist_ok=True)

                tool = parsed["function"]
                tool_input = parsed["input"]
                if tool == "run_command":
                    if tool_input["type"] in ["CREATE", "EDIT", "MODIFY"]:
                        data = GenerateCMD(
                            filename=tool_input["filename"],
                            content=tool_input["content"],
                            session_id=body.session_id,
                            command_type=CommandType.CREATE
                        )
                        cmd = generate_cmd(data)
                        output = run_command(cmd)

                        messages.append({
                            "role": "user",
                            "content": json.dumps({
                                "step": "generate",
                                "content": tool_input["content"]
                            })
                        })

                        yield f"data: {json.dumps({'step': 'generate','content': tool_input['content'],'filename': tool_input['filename']})}\n\n"
                        await asyncio.sleep(0.01)

                    elif tool_input["type"] == "REMOVE":
                        yield f"data: {json.dumps({'step': 'generate','content': tool_input['content'],'filename': 'N/A'})}\n\n"
                        await asyncio.sleep(0.01)
                else:
                    yield f"data: {json.dumps({'step': 'generate','content': tool_input['content'],'filename': tool_input.get('filename', 'N/A')})}\n\n"
                    await asyncio.sleep(0.01)

                try:
                    await r.set(redis_key, json.dumps(messages), ex=3600)
                except redis.exceptions.ConnectionError as e:
                    print("❌ Redis connection failed:", e)

            if step == "review" or step=="user-interaction":
                break
        except Exception as e:
            print("❌ Error:", e)
            yield f"data: {json.dumps({'step': 'review','content': 'Something went wrong with the LLM. Possibly token limit or API error.'})}\n\n"
            await asyncio.sleep(0.01)
            break

    print("✅ Code generation session finished")

def detect_project_type(project_path: Path) -> str:
    package_json = project_path / "package.json"
    if package_json.exists():
        try:
            with open(package_json, "r") as f:
                data = json.load(f)
                deps = data.get("dependencies", {})
                if "react" in deps or "react-dom" in deps:
                    return "REACT"
        except Exception:
            pass

    html_files = list(project_path.glob("*.html"))
    if html_files:
        return "HTML"

    return "UNKNOWN"

# async def code_generator(prompt: str, session_id: str):
#     print("here")
#     session_key = f"chat:{session_id}"
#     print("working on redis")
#     prev_msgs=""
#     try:
#         exist=await r.exists(session_key)
#         print("exist",exist)
#         if exist:
#             prev_msgs = await r.get(session_key)
#     except redis.exceptions.ConnectionError as e:
#         print("❌ Redis connection failed:", e)
#     print("working on redis done")
#     messages = json.loads(prev_msgs) if prev_msgs else []
#
#     messages.append({"role": "system", "content": CODE_AGENT_SYSTEM_PROMPT})
#     messages.append({"role": "user", "content": prompt})
#
#     print("entered in loop")
#     while True:
#         try:
#             print("fetching response")
#             response = client.chat.completions.create(
#                 model="gpt-4o-mini",
#                 response_format={"type": "json_object"},
#                 messages=messages,
#             )
#
#             print("fetching response done")
#             msg = response.choices[0].message.content
#             messages.append({"role": "assistant", "content": msg})
#             print("saving to session")
#             try:
#                 await r.set(session_key, json.dumps(messages),ex=3600)
#                 # Store latest state
#             except redis.exceptions.ConnectionError as e:
#                 print("❌ Redis connection failed:", e)
#             parsed = json.loads(msg)
#             step = parsed.get("step")
#             print("BEFORE STEP LOG")
#             # # non-generate block
#             if step != "generate":
#                 print("STEP: ", step)
#                 yield f"data: {json.dumps(parsed)}\n\n"
#                 await asyncio.sleep(0.01)  # 🚀 Force flush to client
#
#             # For generate steps
#             elif step == "generate":
#                 tool = parsed["function"]
#                 tool_input = parsed["input"]
#                 print(f"tool_input: {tool_input}")
#
#                 if tool == "run_command":
#                     if tool_input["type"] in ["CREATE", "EDIT", "MODIFY"]:
#                         data = GenerateCMD(
#                             filename=tool_input["filename"],
#                             content=tool_input["content"],
#                             session_id=session_id,
#                             command_type=CommandType.CREATE
#                         )
#                         cmd = generate_cmd(data)
#                         output = run_command(cmd)
#
#                         messages.append({
#                             "role": "user",
#                             "content": json.dumps({
#                                 "step": "generate",
#                                 "content": tool_input["content"]
#                             })
#                         })
#                         data={
#                             'step': 'generate',
#                             'content': tool_input['content'],
#                             'filename': tool_input['filename']
#                         }
#                         yield f"data: {json.dumps(data)}\n\n"
#                         await asyncio.sleep(0.01)
#
#                     elif tool_input["type"] == "REMOVE":
#                         data={
#                             'step': 'generate',
#                             'content': tool_input['content'],
#                             'filename': 'N/A'
#                         }
#                         yield f"data: {json.dumps(data)}\n\n"
#                         await asyncio.sleep(0.01)
#                 else:
#                     data={
#                         'step': 'generate',
#                         'content': tool_input['content'],
#                         'filename': tool_input.get('filename', 'N/A')
#                     }
#                     yield f"data: {json.dumps(data)}\n\n"
#                     await asyncio.sleep(0.01)
#                 try:
#                     await r.set(session_key, json.dumps(messages),ex=3600)
#                 except redis.exceptions.ConnectionError as e:
#                     print("❌ Redis connection failed:", e)
#
#             # Break if review step found
#             if step == "review":
#                 break
#         except Exception as e:
#             print(e)
#             error_data = {
#                 "step": "review",
#                 "content": 'Something went wrong with the LLM, most likely: "Paisa khatam".'
#             }
#             yield f"data: {json.dumps(error_data)}\n\n"
#             await asyncio.sleep(0.01)
#             break
#
#     print("exited in loop")
