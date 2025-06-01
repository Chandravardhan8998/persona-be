from dotenv import load_dotenv
from openai import OpenAI

from agent_tools import (run_command, generate_cmd,
    # run_on_browser, save_on_github
                         )
from models import GenerateCMD, CommandType
from prompts import CODE_AGENT_SYSTEM_PROMPT
from redis_config import r
import json
import subprocess
load_dotenv()
client = OpenAI()

def cleanup_session(session_id: str):
    folder_path = f"apps/{session_id}"
    subprocess.getoutput(f"rm -rf {folder_path}")  # Dangerous! Use with checks
    r.delete(f"chat:{session_id}")


async def code_generator(prompt: str, session_id: str):
    session_key = f"chat:{session_id}"
    print("working on redis")
    prev_msgs = await r.get(session_key)
    print("working on redis done")
    messages = json.loads(prev_msgs) if prev_msgs else []

    messages.append({"role": "system", "content": CODE_AGENT_SYSTEM_PROMPT})
    messages.append({"role": "user", "content": prompt})

    print("entered in loop")
    while True:
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
        print("STEP: ",parsed.get("step"))
        # add yield here
        if parsed.get("step") == "generate":
            tool = parsed["function"]
            tool_input = parsed["input"]
            print(f"tool_input {tool_input}")
            if tool == "run_command":
                if tool_input["type"]=="CREATE":
                    data = GenerateCMD(filename=tool_input["filename"], content=tool_input["content"], session_id=session_id,command_type=CommandType.CREATE)
                    cmd=generate_cmd(data)
                    output = run_command(cmd)
                    messages.append({"role": "user", "content": json.dumps({
                        "step": "generate", "content": tool_input["content"]
                    })})
                    yield f"data: {json.dumps({
                        "step": "generate", "content": tool_input["content"],"filename":tool_input["filename"]
                    })}\n\n"

                if tool_input["type"]=="REMOVE":
                    print(tool_input)
                    data = GenerateCMD(filename="", content=tool_input["content"], session_id=session_id,command_type=CommandType.REMOVE)
                    cmd=generate_cmd(data)
                    messages.append({"role": "user", "content": json.dumps({
                        "step": "generate", "content": tool_input["content"]
                    })})
                    yield f"data: {json.dumps({
                        "step": "generate", "content": tool_input["content"], "filename":"N/A"
                    })}\n\n"
            # elif tool == "run_on_browser":
            #     output = run_on_browser(tool_input)
            # elif tool == "save_on_github":
            #     output = save_on_github(tool_input)
            await r.set(session_key, json.dumps(messages))
            continue
        elif parsed.get("step") == "review":
            yield f"data: {json.dumps(parsed)}\n\n"
            break
        else:
            print("here----")
            yield f"data: {json.dumps(parsed)}\n\n"
            continue
    print("exited in loop")