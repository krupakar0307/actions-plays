import os
import requests

# Get environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")    # Changed from INPUT_GITHUB-TOKEN
REPO = os.getenv("GITHUB_REPOSITORY")       
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")  # Changed from INPUT_BASE-BRANCH

missing_vars = []
if not GITHUB_TOKEN:
    missing_vars.append("GITHUB_TOKEN")
if not REPO:
    missing_vars.append("GITHUB_REPOSITORY")

if missing_vars:
    print(f"Missing required environment variables: {', '.join(missing_vars)}")
    exit(1)

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

def write_output(name, value):
    output_file = os.getenv('GITHUB_OUTPUT')
    if output_file:
        with open(output_file, 'a') as f:
            f.write(f"{name}={value}\n")
    else:
        print(f"Output {name}={value}")

def check_main_status():
    """Check if main branch is green or red"""
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={BASE_BRANCH}&status=completed"
    response = requests.get(url, headers=headers)
    runs = response.json().get("workflow_runs", [])
    
    if not runs:
        print(f"No workflow runs found for {BASE_BRANCH} branch")
        return None
    
    # Get the most recent completed run
    latest_run = runs[0]  # GitHub API returns newest first
    print(f"Latest workflow run details:")
    print(f"  Name: {latest_run.get('name')}")
    print(f"  Status: {latest_run.get('status')}")
    print(f"  Conclusion: {latest_run.get('conclusion')}")
    print(f"  Created at: {latest_run.get('created_at')}")
    
    is_green = latest_run["conclusion"] == "success"
    print(f"Main branch status: {'GREEN' if is_green else 'RED'}")
    write_output("is-main-green", str(is_green).lower())
    return is_green

if __name__ == "__main__":
    is_green = check_main_status()
    if is_green is None:
        print("Could not determine main branch status")
        exit(1)
    exit(0 if is_green else 1) 