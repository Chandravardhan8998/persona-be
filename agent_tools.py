import os
import subprocess

def run_command(cmd: str):
    result = os.system(cmd)
    return result

# def run_command(cmd: str):
#     result = subprocess.getoutput(cmd)
#     return result
#
# def run_on_browser(cmd: str):
#     # This could build and serve via HTTP or WebSocket
#     return "App running on http://localhost:3000"
#
# def save_on_github(repo_details: dict):
#     # Use GitHub API with token
#     return "Pushed to GitHub successfully"
#
# def generate_file(prompt: str, session_id: str, filename: str):
#     folder_path = f"apps/{session_id}"
#     os.makedirs(folder_path, exist_ok=True)
#
#     full_path = os.path.join(folder_path, filename)
#     cmd = f"echo '{prompt}' > {full_path}"  # ⚠️ prompt must be sanitized
#     result = subprocess.getoutput(cmd)
#
#     return full_path
