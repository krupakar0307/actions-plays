import os
import requests

# Get environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")    
REPO = os.getenv("GITHUB_REPOSITORY")       
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")  

if not GITHUB_TOKEN or not REPO:
    print("Missing required environment variables")
    exit(1)

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json",
}

def write_output(name, value):
    status_file = os.getenv('GITHUB_OUTPUT')
    if status_file:
        with open(status_file, 'a') as f:
            f.write(f"{name}={value}\n")

def check_base_branch_exists():
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={BASE_BRANCH}"
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200 or not response.json().get("workflow_runs", []):
        print(f"Base branch '{BASE_BRANCH}' not found or has no workflows")
        exit(1)

def check_base_branch_status():
    # Simply get the latest workflow run on main branch
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={BASE_BRANCH}&status=completed"
    response = requests.get(url, headers=headers)
    runs = response.json().get("workflow_runs", [])
    
    if not runs:
        print(f"No completed workflow runs found for {BASE_BRANCH}")
        exit(1)
        
    latest_run = runs[0]  # GitHub API returns newest first
    is_green = latest_run["conclusion"] == "success"
    
    if is_green:
        print(f"✅ {BASE_BRANCH} is green - PR can be merged")
    else:
        print(f"❌ {BASE_BRANCH} is not green (status: {latest_run['conclusion']}) - fix {BASE_BRANCH} first")
    
    return is_green

def main():
    if os.getenv("GITHUB_EVENT_NAME") != "pull_request":
        print("This action only runs on pull requests")
        exit(1)
        
    is_green = check_base_branch_status()
    if not is_green:
        exit(1)

if __name__ == "__main__":
    main() 