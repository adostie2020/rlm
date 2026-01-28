import os
from dotenv import load_dotenv

# Load env same as main.py
if os.path.exists(".env.local"):
    print("Loading .env.local")
    load_dotenv(".env.local")
else:
    print("Loading .env")
    load_dotenv()

try:
    from jira_utils import jira_list_projects, JiraError, jira_get_recent_projects
    
    print("--- Listing Projects ---")
    projects = jira_list_projects()
    if projects and isinstance(projects[0], JiraError):
        print(f"Error: {projects[0].error}")
    else:
        for p in projects:
            print(f"Key: {p.key}, Name: {p.name}")

    print("\n--- Recent Projects ---")
    recent = jira_get_recent_projects()
    if recent and isinstance(recent[0], JiraError):
        print(f"Error: {recent[0].error}")
    else:
        for p in recent:
            print(f"Key: {p.key}, Name: {p.name}")

except Exception as e:
    print(f"Execution failed: {e}")
