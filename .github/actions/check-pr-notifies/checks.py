import os
import requests

# Get environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")    
REPO = os.getenv("GITHUB_REPOSITORY")       
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")  

if not GITHUB_TOKEN or not REPO:
    print("Missing required environment variables: GITHUB_TOKEN or GITHUB_REPOSITORY")
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

def check_main_branch_status():
    """Check if main branch is green or red"""
    url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={BASE_BRANCH}"
    response = requests.get(url, headers=headers)
    runs = response.json().get("workflow_runs", [])
    
    if not runs:
        print(f"No workflow runs found for {BASE_BRANCH} branch")
        return None
        
    latest_run = runs[0]  # GitHub API returns newest first
    return latest_run["conclusion"] == "success"

def notify_and_rerun_prs():
    check_base_branch_exists()
    
    # First check main branch status
    is_main_green = check_main_branch_status()
    if is_main_green:
        print(f"{BASE_BRANCH} branch is green - PRs will pass if their changes are good")
    else:
        print(f"{BASE_BRANCH} branch is red - PRs will be marked as failed")
    
    # Get all open PRs
    pr_url = f"https://api.github.com/repos/{REPO}/pulls?state=open"
    pr_response = requests.get(pr_url, headers=headers)

    if pr_response.status_code != 200:
        print(f"Error fetching PRs: {pr_response.json()}")
        return 0, "failure"

    prs = pr_response.json()
    if not prs:
        print("No open PRs found.")
        return 0, "success"

    print(f"Found {len(prs)} open PRs. Base branch is {'green' if is_main_green else 'red'}")
    rerun_count = 0
    rerun_success = True
    processed_prs = []

    for pr in prs:
        pr_branch = pr["head"]["ref"]
        pr_number = pr["number"]
        pr_url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={pr_branch}"
        pr_response = requests.get(pr_url, headers=headers)

        if pr_response.status_code != 200:
            print(f"Error fetching workflows for PR #{pr_number} ({pr_branch})")
            continue

        runs = pr_response.json().get("workflow_runs", [])
        if not runs:
            print(f"No workflows found for PR #{pr_number} ({pr_branch})")
            continue

        latest_run = runs[0]
        run_id = latest_run["id"]
        rerun_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/rerun"
        rerun_response = requests.post(rerun_url, headers=headers)

        if rerun_response.status_code == 201:
            rerun_count += 1
            current_status = latest_run["conclusion"] or "running"
            processed_prs.append(f"PR #{pr_number} ({pr_branch}) - Previous status: {current_status}")
            print(f"Successfully triggered re-run for PR #{pr_number} ({pr_branch})")
            if not is_main_green:
                print(f"  Note: PR #{pr_number} will fail because {BASE_BRANCH} is red")
        else:
            print(f"Failed to re-run workflow for PR #{pr_number} ({pr_branch})")
            rerun_success = False

    # Print summary
    if rerun_count > 0:
        print(f"\nSummary: Triggered {rerun_count} PR workflow runs:")
        print(f"Base branch ({BASE_BRANCH}) status: {'green' if is_main_green else 'red'}")
        for pr in processed_prs:
            print(f"- {pr}")
    else:
        print("\nNo PR workflows were triggered.")

    write_output("rerun-count", str(rerun_count))
    write_output("rerun-status", "success" if rerun_success else "failure")
    return rerun_count, rerun_success

def trigger_pr_workflows():
    """Simply trigger all PR workflows"""
    # Get all open PRs
    pr_url = f"https://api.github.com/repos/{REPO}/pulls?state=open"
    pr_response = requests.get(pr_url, headers=headers)

    if pr_response.status_code != 200:
        print(f"Error fetching PRs: {pr_response.json()}")
        return

    prs = pr_response.json()
    if not prs:
        print("No open PRs found.")
        return

    print(f"Found {len(prs)} open PRs. Triggering their workflows...")

    for pr in prs:
        pr_branch = pr["head"]["ref"]
        pr_number = pr["number"]
        
        # Get latest workflow run for this PR
        workflow_url = f"https://api.github.com/repos/{REPO}/actions/runs?branch={pr_branch}"
        workflow_response = requests.get(workflow_url, headers=headers)
        
        if workflow_response.status_code != 200:
            print(f"Error fetching workflows for PR #{pr_number}")
            continue
            
        runs = workflow_response.json().get("workflow_runs", [])
        if not runs:
            print(f"No workflows found for PR #{pr_number}")
            continue

        # Trigger rerun of the latest workflow
        run_id = runs[0]["id"]
        rerun_url = f"https://api.github.com/repos/{REPO}/actions/runs/{run_id}/rerun"
        rerun_response = requests.post(rerun_url, headers=headers)

        if rerun_response.status_code == 201:
            print(f"✅ Triggered workflow rerun for PR #{pr_number} ({pr_branch})")
        else:
            print(f"❌ Failed to trigger workflow for PR #{pr_number} ({pr_branch})")

def main():
    event_name = os.getenv("GITHUB_EVENT_NAME")
    ref = os.getenv("GITHUB_REF")
    
    if not (event_name == "push" and ref == "refs/heads/main"):
        print("This action only runs on push to main branch")
        exit(1)
        
    trigger_pr_workflows()

if __name__ == "__main__":
    main() 