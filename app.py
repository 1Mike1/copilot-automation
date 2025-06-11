from flask import Flask, jsonify, request
from gitlab_client import GitlabClient
from config import gitlab_url, private_token, project_id, script_path
import subprocess
import json
import os

CODE_DIR = r"Merge_Code_Changes"
os.makedirs(CODE_DIR, exist_ok=True)

app = Flask(__name__)
client = GitlabClient(gitlab_url, private_token)

@app.route("/project-info", methods=["GET"])
def project_info():
    project = client.get_project(project_id)
    return jsonify({"project_name": project.name, "project_id": project.id})

@app.route("/merge-requests", methods=["GET"])
def merge_requests():
    mrs = client.get_merge_requests(project_id)
    return jsonify([{"title": mr.title, "iid": mr.iid} for mr in mrs])

@app.route("/merge-request/<int:mr_id>/generate-prompt", methods=["GET"])
def generate_prompt(mr_id):
    client.generate_prompt_for_copilot(project_id, mr_id)
    prompt_path = f"output/prompts/mr_{mr_id}.py"
    return jsonify({"message": "Prompt generated successfully.", "file": prompt_path})

@app.route("/merge-request/<int:mr_id>/files", methods=["GET"])
def get_files(mr_id):
    changes = client.get_merge_request_changes(project_id, mr_id)
    modified_files = [change['new_path'] for change in changes]
    return jsonify({"modified_files": modified_files})

@app.route("/merge-request/<int:mr_id>/changes", methods=["GET"])
def get_changes(mr_id):
    changes = client.get_merge_request_changes(project_id, mr_id)
    changes_dict = {change['new_path']: change['diff'] for change in changes}
    changes_json = json.dumps(changes_dict, indent=4)
    with open(f"output/changes/mr_{mr_id}_changes.json", 'w') as f:
        f.write(changes_json)

    return jsonify(changes_dict)

@app.route('/save_mr_changes', methods=['POST'])
def save_mr_changes():
    data = request.get_json()

    if not isinstance(data, dict):
        return jsonify({"error": "Invalid JSON format"}), 400

    saved_files = []

    for filename, diff_content in data.items():
        filename = f"merge_request_{filename.split('/')[-1]}"
        full_path = os.path.join(CODE_DIR, filename)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        with open(full_path, 'w') as f:
            f.write(diff_content)

        saved_files.append(full_path)

    return jsonify({"message": "Files saved successfully", "files": saved_files})

@app.route("/copilot_suggestion", methods=['POST'])
def copilot_suggestion():
    file_path = None
    data = request.get_json()
    if data:
        file_path = data.get('file_path')
    print(f"File path received: {file_path}")
    _files = file_path.split(',') if file_path else []
    print(f"Files: {_files}")
    print(f"File path: {file_path}")
    file_path = _files
    
    if not file_path:
        return jsonify({"error": "No file path provided"}), 400
    
    #script_path = r'/home/mithlesh.kumar2/Practice/Hackthon/code_reviewer/bin/copilot'
    try:
        subprocess.run([script_path, file_path[0]], check=True)
        return jsonify({"message": "Script executed successfully!"}), 200
    except subprocess.CalledProcessError as e:
        return jsonify({"error": f"Error running script: {e}"}), 500

@app.route("/read-results", methods=["GET"])
def read_results():
    results_file = r"output/changes/result.json"

    if not os.path.exists(results_file):
        return jsonify({"error": "result.json file not found"}), 404

    try:
        with open(results_file, "r") as f:
            data = json.load(f)
        return jsonify(data)
    except json.JSONDecodeError:
        return jsonify({"error": "Failed to parse result.json"}), 400

if __name__ == "__main__":
    app.run(debug=True, port=5005)
