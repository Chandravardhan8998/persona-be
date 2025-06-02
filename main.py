import asyncio
import json

from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

from agent_controller import code_generator
from fastapi.responses import StreamingResponse
import redis.asyncio as redis
import os
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from models import PromptInput, DeleteFileRequest, SESSION_BASE_DIR

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
    session_path = Path(f"./{SESSION_BASE_DIR}/{session_id}")  # Path to the session folder

    if not session_path.exists() or not session_path.is_dir():
        raise HTTPException(status_code=404, detail="Session folder not found")

    # Recursively list all files
    files = [
        str(p.relative_to(session_path))
        for p in session_path.rglob("*")
        if p.is_file()
    ]

    return JSONResponse(content={"session_id": session_id, "files": files})



@app.post("/test-code")
async def test_code():
    stream = test_code_generate()
    return StreamingResponse(stream, media_type="text/event-stream")


@app.post("/delete-file")
async def delete_file_from_session(data: DeleteFileRequest):
    # session_folder = os.path.join(SESSION_BASE_DIR, data.session_id)
    session_folder = os.path.abspath(os.path.join(SESSION_BASE_DIR, data.session_id))

    # Security check: file must be under the session folder
    file_path = os.path.abspath(data.filepath)
    if not file_path.startswith(os.path.abspath(session_folder)):
        raise HTTPException(status_code=403, detail="Access to this file is not allowed.")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found.")

    try:
        # 🗑️ Delete the file
        os.remove(file_path)

        parent_dir = os.path.dirname(file_path)

        # 🔍 Check if parent directory is now empty
        if os.path.abspath(parent_dir).startswith(session_folder) and len(os.listdir(parent_dir)) == 0:
            os.rmdir(parent_dir)
            return {
                "message": f"✅ File deleted: {data.filepath}",
                "folder_deleted": parent_dir.replace(session_folder + "/", "")
            }

        return {
            "message": f"✅ File deleted: {data.filepath}",
            "folder_deleted": None
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"❌ Error deleting file: {str(e)}")

async def test_code_generate():
    one={"step": "analyse", "content": "User wants a basic Todo app built using React and TypeScript. The app should allow adding, listing, and deleting todos. No backend or advanced features specified."}
    two={"step": "plan",
           "content": "Plan to create a React TypeScript todo app named 'react-todo-ts'. The project structure will have: react-todo-ts/src/index.tsx, react-todo-ts/src/App.tsx, react-todo-ts/src/components/TodoList.tsx, react-todo-ts/src/components/TodoItem.tsx, react-todo-ts/src/types.d.ts, react-todo-ts/src/index.css."}
    three={"step": "plan",
           "content": "File structure: react-todo-ts/src/index.tsx, react-todo-ts/src/App.tsx, react-todo-ts/src/components/TodoList.tsx, react-todo-ts/src/components/TodoItem.tsx, react-todo-ts/src/types.d.ts, react-todo-ts/src/index.css."}
    four={"step": "generate",
           "content": "import React from 'react';\nimport ReactDOM from 'react-dom/client';\nimport App from './App';\nimport './index.css';\n\nconst root = ReactDOM.createRoot(document.getElementById('root') as HTMLElement);\nroot.render(<React.StrictMode><App /></React.StrictMode>);",
           "filename": "react-todo-ts/src/index.tsx"}
    five={"step": "generate",
           "content": "import React, { useState } from 'react';\nimport TodoList from './components/TodoList';\nimport { Todo } from './types';\n\nconst App: React.FC = () => {\n  const [todos, setTodos] = useState<Todo[]>([]);\n\n  const addTodo = (text: string) => {\n    const newTodo: Todo = { id: Date.now(), text };\n    setTodos([...todos, newTodo]);\n  };\n\n  const removeTodo = (id: number) => {\n    setTodos(todos.filter(todo => todo.id !== id));\n  };\n\n  return (\n    <div className=\"container mx-auto p-4\">\n      <h1 className=\"text-2xl font-bold mb-4\">React TypeScript Todo App</h1>\n      <input\n        type=\"text\"\n        placeholder=\"Add a todo and press Enter\"\n        className=\"border p-2 w-full mb-4\"\n        onKeyDown={(e) => {\n          if (e.key === 'Enter' && e.currentTarget.value.trim() !== '') {\n            addTodo(e.currentTarget.value.trim());\n            e.currentTarget.value = '';\n          }\n        }}\n      />\n      <TodoList todos={todos} onRemove={removeTodo} />\n    </div>\n  );\n};\n\nexport default App;",
           "filename": "react-todo-ts/src/App.tsx"}
    six={"step": "generate",
           "content": "import React from 'react';\nimport TodoItem from './TodoItem';\nimport { Todo } from '../types';\n\ninterface TodoListProps {\n  todos: Todo[];\n  onRemove: (id: number) => void;\n}\n\nconst TodoList: React.FC<TodoListProps> = ({ todos, onRemove }) => {\n  return (\n    <ul>\n      {todos.map(todo => (\n        <TodoItem key={todo.id} todo={todo} onRemove={onRemove} />\n      ))}\n    </ul>\n  );\n};\n\nexport default TodoList;",
           "filename": "react-todo-ts/src/components/TodoList.tsx"}
    seven={"step": "generate",
           "content": "import React from 'react';\nimport { Todo } from '../types';\n\ninterface TodoItemProps {\n  todo: Todo;\n  onRemove: (id: number) => void;\n}\n\nconst TodoItem: React.FC<TodoItemProps> = ({ todo, onRemove }) => {\n  return (\n    <li className=\"flex justify-between items-center p-2 border mb-2\">\n      <span>{todo.text}</span>\n      <button\n        className=\"bg-red-500 text-white px-2 py-1 rounded\"\n        onClick={() => onRemove(todo.id)}\n      >\n        Delete\n      </button>\n    </li>\n  );\n};\n\nexport default TodoItem;",
           "filename": "react-todo-ts/src/components/TodoItem.tsx"}
    eight={"step": "generate",
           "content": "import React from 'react';\nimport { Todo } from '../types';\n\ninterface TodoItemProps {\n  todo: Todo;\n  onRemove: (id: number) => void;\n}\n\nconst TodoItem: React.FC<TodoItemProps> = ({ todo, onRemove }) => {\n  return (\n    <li className=\"flex justify-between items-center p-2 border mb-2\">\n      <span>{todo.text}</span>\n      <button\n        className=\"bg-red-500 text-white px-2 py-1 rounded\"\n        onClick={() => onRemove(todo.id)}\n      >\n        Delete\n      </button>\n    </li>\n  );\n};\n\nexport default TodoItem;",
           "filename": "react-todo-ts/src/components/TodoItem.tsx"}
    nine={"step": "generate", "content": "export interface Todo {\n  id: number;\n  text: string;\n}", "filename": "react-todo-ts/src/types.d.ts"}
    ten={"step": "generate",
           "content": "body {\n  font-family: Arial, sans-serif;\n  background-color: #f9f9f9;\n}\n\n.container {\n  max-width: 600px;\n  margin: 2rem auto;\n  background: white;\n  padding: 1rem;\n  border-radius: 5px;\n  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);\n}\n\ninput:focus {\n  outline: none;\n  border-color: #3182ce;\n  box-shadow: 0 0 0 1px #3182ce;\n}\n\nbutton {\n  cursor: pointer;\n  transition: background-color 0.3s ease;\n}\n\nbutton:hover {\n  background-color: #e53e3e;\n}",
           "filename": "react-todo-ts/src/index.css"}
    eleven={"step": "package",
           "content": "All files for the basic React TypeScript Todo app have been generated and organized."}
    twelve={"step": "review",
           "content": "The React TypeScript Todo app code is clean, modular, and uses proper typing. Basic styling is applied via CSS with clear class names."}
    data=[
        f"data: {json.dumps(one)}\n\n",
        f"data: {json.dumps(two)}\n\n",
        f"data: {json.dumps(three)}\n\n",
        f"data: {json.dumps(four)}\n\n",
        f"data: {json.dumps(five)}\n\n",
        f"data: {json.dumps(six)}\n\n",
        f"data: {json.dumps(seven)}\n\n",
        f"data: {json.dumps(eight)}\n\n",
        f"data: {json.dumps(nine)}\n\n",
        f"data: {json.dumps(ten)}\n\n",
        f"data: {json.dumps(eleven)}\n\n",
        f"data: {json.dumps(twelve)}\n\n",
    ]
    for item in data:
        await asyncio.sleep(2)
        yield item

@app.post("/generate-code")
async def generate_code(body:PromptInput):
    print("here")
    stream = code_generator(body.prompt, body.session_id)
    return StreamingResponse(stream, media_type="text/event-stream")



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























