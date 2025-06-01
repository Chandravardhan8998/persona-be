import openai
from dotenv import load_dotenv
from openai import OpenAI

from agent_tools import (run_command, generate_cmd,
                         )
import asyncio
from models import GenerateCMD, CommandType, SESSION_BASE_DIR
from prompts import CODE_AGENT_SYSTEM_PROMPT
from redis_config import r
import json
import subprocess
import redis

load_dotenv()
client = OpenAI()

def cleanup_session(session_id: str):
    folder_path = f"{SESSION_BASE_DIR}/{session_id}"
    subprocess.getoutput(f"rm -rf {folder_path}")  # Dangerous! Use with checks
    r.delete(f"chat:{session_id}")


async def code_generator(prompt: str, session_id: str):
    try:
        r.ping()
    except redis.exceptions.ConnectionError:
        print("redis error")
    session_key = f"chat:{session_id}"
    print("working on redis")
    prev_msgs = await r.get(session_key)
    print("working on redis done")
    messages = json.loads(prev_msgs) if prev_msgs else []

    messages.append({"role": "system", "content": CODE_AGENT_SYSTEM_PROMPT})
    messages.append({"role": "user", "content": prompt})

    print("entered in loop")
    while True:
        try:
            print("fetching response")
            response = client.chat.completions.create(
                model="gpt-4.1-mini",
                response_format={"type": "json_object"},
                messages=messages,
            )

            print("fetching response done")
            msg = response.choices[0].message.content
            messages.append({"role": "assistant", "content": msg})
            print("saving to session")
            await r.set(session_key, json.dumps(messages))  # Store latest state

            parsed = json.loads(msg)
            step = parsed.get("step")
            print("BEFORE STEP LOG")
            # # non-generate block
            if step != "generate":
                print("STEP: ", step)
                yield f"data: {json.dumps(parsed)}\n\n"
                await asyncio.sleep(0.01)  # 🚀 Force flush to client

            # For generate steps
            elif step == "generate":
                tool = parsed["function"]
                tool_input = parsed["input"]
                print(f"tool_input: {tool_input}")

                if tool == "run_command":
                    if tool_input["type"] in ["CREATE", "EDIT", "MODIFY"]:
                        data = GenerateCMD(
                            filename=tool_input["filename"],
                            content=tool_input["content"],
                            session_id=session_id,
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
                        data={
                            'step': 'generate',
                            'content': tool_input['content'],
                            'filename': tool_input['filename']
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        await asyncio.sleep(0.01)

                    elif tool_input["type"] == "REMOVE":
                        data={
                            'step': 'generate',
                            'content': tool_input['content'],
                            'filename': 'N/A'
                        }
                        yield f"data: {json.dumps(data)}\n\n"
                        await asyncio.sleep(0.01)
                else:
                    data={
                        'step': 'generate',
                        'content': tool_input['content'],
                        'filename': tool_input.get('filename', 'N/A')
                    }
                    yield f"data: {json.dumps(data)}\n\n"
                    await asyncio.sleep(0.01)

                await r.set(session_key, json.dumps(messages))

            # Break if review step found
            if step == "review":
                break
        except Exception as e:
            print(e)
            error_data = {
                "step": "review",
                "content": 'Something went wrong with the LLM, most likely: "Paisa khatam".'
            }
            yield f"data: {json.dumps(error_data)}\n\n"
            await asyncio.sleep(0.01)
            break

    print("exited in loop")
