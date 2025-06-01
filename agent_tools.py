import os

from models import GenerateCMD, CommandType, SESSION_BASE_DIR


def run_command(cmd: str):
    print("Running:", cmd)
    result = os.system(cmd)
    return result

def generate_cmd(input_data: GenerateCMD) -> str:
    filename = input_data.filename
    directory = os.path.dirname(filename)
    if input_data.command_type==CommandType.CREATE :
        content = input_data.content.replace("'", "'\"'\"'")  # escape single quotes safely
        path=f"{SESSION_BASE_DIR}/{input_data.session_id}"
        return f"mkdir -p {path}/{directory} && echo '{content}' > {path}/{filename}"

    elif input_data.command_type==CommandType.REMOVE :
        return input_data.content
    else:
        return ""



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
