import os
import requests

# Get environment variables
GITHUB_TOKEN = os.getenv("INPUT_GITHUB-TOKEN")    
REPO = os.getenv("GITHUB_REPOSITORY")       

missing_vars = []
if not GITHUB_TOKEN:
    missing_vars.append("INPUT_GITHUB-TOKEN")
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

def notify_prs():
    """Trigger all PR workflows to rerun"""
    # Get all open PRs
    pr_url = f"https://api.github.com/repos/{REPO}/pulls?state=open"
    response = requests.get(pr_url, headers=headers)
    
    if response.status_code != 200:
        print("Error fetching PRs")
        return 0, "failure"

    prs = response.json()
    if not prs:
        print("No open PRs found")
        return 0, "success"

    print(f"Found {len(prs)} open PRs - triggering reruns")
    rerun_count = 0

    for pr in prs:
        pr_number = pr["number"]
        pr_branch = pr["head"]["ref"]
        
        # Get PR's latest workflow run
        run_url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={pr_branch}"
        run_response = requests.get(run_url, headers=headers)
        
        if run_response.status_code != 200:
            print(f"Error fetching workflows for PR #{pr_number}")
            continue
            
        runs = run_response.json().get("workflow_runs", [])
        if not runs:
            print(f"No workflows found for PR #{pr_number}")
            continue

        # Trigger rerun
        run_id = runs[0]["id"]
        rerun_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/rerun"
        rerun_response = requests.post(rerun_url, headers=headers)

        if rerun_response.status_code == 201:
            rerun_count += 1
            print(f"✓ Triggered rerun for PR #{pr_number} ({pr_branch})")
        else:
            print(f"✗ Failed to trigger PR #{pr_number}")

    print(f"\nSummary: Triggered {rerun_count} PR workflow reruns")
    write_output("rerun-count", str(rerun_count))
    write_output("rerun-status", "success")
    return rerun_count, "success"

def main():
    notify_prs()

if __name__ == "__main__":
    main() 