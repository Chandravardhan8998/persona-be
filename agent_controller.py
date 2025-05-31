from dotenv import load_dotenv
from openai import OpenAI

from agent_tools import (run_command,
                         # run_on_browser, save_on_github
    )
from app import CODE_AGENT_SYSTEM_PROMPT
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
        print("saving  to session")
        await r.set(session_key, json.dumps(messages))  # Store latest state
        parsed = json.loads(msg)
        print(parsed)
        if parsed.get("step") == "plan":
            print(f"🧠: {parsed.get("content")}")
            continue
        if parsed.get("step") == "action":
            tool = parsed["function"]
            tool_input = parsed["input"]
            print("tool_input "+tool_input)
            output = None
            if tool == "run_command":
                output = run_command(tool_input)
                messages.append({"role": "user", "content": json.dumps({
                    "step": "observe", "output": output
                })})
            # elif tool == "run_on_browser":
            #     output = run_on_browser(tool_input)
            # elif tool == "save_on_github":
            #     output = save_on_github(tool_input)

            await r.set(session_key, json.dumps(messages))
            yield f"data: {json.dumps(parsed)}\n\n"
            continue

        elif parsed.get("step") == "output":
            yield f"data: {json.dumps(parsed)}\n\n"
            break
    print("exited in loop")