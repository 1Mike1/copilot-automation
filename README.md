# Commit Conquerors

## Overview
Commit Conquerors is a tool designed to streamline the process of reviewing and managing merge requests. It provides features to fetch merge request details, analyze changes, and generate suggestions for code improvements.

## Installation
To set up the project, follow these steps:

1. Install the required Python dependencies:
```bash
pip3 install -r requirements.txt
```

2. Install additional tools:
```bash
sudo apt install xdotool python3-bandit
```

## Usage
Run the application using the following command:
```bash
python3 app.py
```

## API Endpoints
The application provides the following API endpoints:

### 1. Fetch Merge Request Prompt
**GET** `/merge-request/{merge_id}/generate-prompt`

Fetches the prompt for a specific merge request by its ID.

### 2. Generate Copilot Suggestions
**POST** `/copilot_suggestion`

**Request Body:**
```json
{
    "file_type": "String"
}
```

### 3. Fetch Changes for a Merge Request
**GET** `/merge-request/{merge_id}/changes`

Retrieves all changes for a specific merge request and saves the file name and content as key-value pairs.

### 4. Save Merge Request Changes Locally
**POST** `/save_mr_changes`

Saves all the merge request files locally.

**Request Body:**
Provide the path to the JSON file containing the changes, e.g., `output/changes/mr_151_changes.json`.

### 5. Read Results
**GET** `/read-results`

Fetches all suggestions and provides a detailed check of the project in JSON format.

## Example Requests

### Fetch Merge Request Details
```bash
curl -X GET "http://localhost:5005/merge-request/151/generate-prompt"
```

### Fetch Changes for a Merge Request
```bash
curl -X GET "http://localhost:5005/merge-request/151/changes"
```

### Save Merge Request Changes Locally
```bash
curl -X POST http://localhost:5005/save_mr_changes -H "Content-Type: application/json" -d @output/changes/mr_151_changes.json
```

### Generate Copilot Suggestions
```bash
curl -X POST http://localhost:5005/copilot_suggestion -H "Content-Type: application/json" -d '{"file_path": "old_file.py, output/changes/mr_151_changes.json"}'
```

### Read Results
```bash
curl -X GET "http://localhost:5005/read-results"
```

### Demo Steps
``` bash
curl -X GET "http://localhost:5005/merge-request/151/files"

curl -X GET "http://localhost:5005/merge-request/151/changes"

curl -X POST http://localhost:5005/save_mr_changes -H "Content-Type: application/json" -d @output/changes/mr_151_changes.json

curl -X POST http://localhost:5005/copilot_suggestion -H "Content-Type: application/json" -d '{"file_path": "output/changes/mr_151_changes.json"}'

curl -X GET "http://localhost:5005/read-results"
```